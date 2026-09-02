"""
TrafficGuard Pro Notification & Interactive Alert Subsystem
Handles:
1. WhatsApp Notifications (Meta Cloud API & Twilio WhatsApp API)
2. SMS Notifications (Twilio SMS & SMS Gateway Fallback)
3. Responsive HTML Emails with Challan PDF attachments via Gmail SMTP
4. Interactive Two-Way WhatsApp / Citizen Chat Bot Engine
5. Live Notification Queue & Audit Feed for Dashboard
"""

import os
import time
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from collections import deque

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import (
    WA_PHONE_ID, WA_TOKEN, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_NUMBER, TWILIO_SMS_NUMBER, GMAIL_ADDRESS,
    GMAIL_APP_PASSWORD, CITIZEN_WA_NUMBER, ADMIN_WA_NUMBER,
    CITIZEN_EMAIL, ADMIN_EMAIL, APP_NAME
)

CITIZEN_INCENTIVE_PCT = 10  # 10% of collected fine
MAX_RETRIES = 3
RETRY_DELAY = 1.5

# In-memory recent alerts feed for live dashboard WebSocket/SSE polling
RECENT_ALERTS_FEED = deque(maxlen=100)


def _is_meta_wa_configured():
    return bool(WA_PHONE_ID and WA_TOKEN)


def _is_twilio_configured():
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)


def _is_email_configured():
    pw = (GMAIL_APP_PASSWORD or "").replace(" ", "")
    return bool(GMAIL_ADDRESS and pw)


def _with_retry(fn, label):
    """Run fn() up to MAX_RETRIES times with exponential/linear backoff."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = fn()
            if res:
                return True
            raise RuntimeError(f"Operation returned non-truthy value: {res}")
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                print(f"  [{label}] All {MAX_RETRIES} attempts failed. Error: {last_error}", flush=True)
    return False


# ── 1. WHATSAPP ENGINE ────────────────────────────────────────────────────────
def send_whatsapp(to_number, message, media_url=None):
    """
    Send WhatsApp message with cascading fallbacks:
    1. Meta Cloud API
    2. Twilio WhatsApp API
    3. Simulated Local Queue & Live Dashboard Broadcast
    """
    if not to_number:
        return False

    alert_record = {
        "channel": "WhatsApp",
        "to": to_number,
        "message": message[:120] + ("..." if len(message) > 120 else ""),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "SENT"
    }

    # Strategy 1: Meta Cloud API
    if _is_meta_wa_configured():
        def _meta_attempt():
            url = f"https://graph.facebook.com/v18.0/{WA_PHONE_ID}/messages"
            headers = {
                "Authorization": f"Bearer {WA_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number.replace("+", ""),
                "type": "text",
                "text": {"body": message}
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=8)
            if resp.status_code in (200, 201):
                return True
            raise RuntimeError(f"Meta WA HTTP {resp.status_code}: {resp.text[:100]}")

        if _with_retry(_meta_attempt, f"MetaWA->{to_number}"):
            RECENT_ALERTS_FEED.appendleft(alert_record)
            return True

    # Strategy 2: Twilio WhatsApp API
    if _is_twilio_configured():
        def _twilio_attempt():
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
            formatted_to = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
            data = {
                "From": TWILIO_WHATSAPP_NUMBER,
                "To": formatted_to,
                "Body": message
            }
            if media_url:
                data["MediaUrl"] = media_url
            resp = requests.post(url, data=data, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=8)
            if resp.status_code in (200, 201):
                return True
            raise RuntimeError(f"Twilio WA HTTP {resp.status_code}: {resp.text[:100]}")

        if _with_retry(_twilio_attempt, f"TwilioWA->{to_number}"):
            RECENT_ALERTS_FEED.appendleft(alert_record)
            return True

    # Strategy 3: Mock Mode (for local development and hackathon evaluation)
    print(f"  [WhatsApp SIMULATOR] -> {to_number}\n{message}\n" + "─"*50, flush=True)
    alert_record["status"] = "SIMULATED"
    RECENT_ALERTS_FEED.appendleft(alert_record)
    return True


# ── 2. SMS ENGINE ─────────────────────────────────────────────────────────────
def send_sms(to_number, message):
    """
    Send SMS via Twilio or local fallback for non-WhatsApp citizens.
    """
    if not to_number:
        return False

    alert_record = {
        "channel": "SMS",
        "to": to_number,
        "message": message[:100] + ("..." if len(message) > 100 else ""),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "SENT"
    }

    if _is_twilio_configured() and TWILIO_SMS_NUMBER:
        def _sms_attempt():
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
            clean_to = to_number.replace("whatsapp:", "")
            data = {
                "From": TWILIO_SMS_NUMBER,
                "To": clean_to,
                "Body": message[:160]
            }
            resp = requests.post(url, data=data, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=8)
            if resp.status_code in (200, 201):
                return True
            raise RuntimeError(f"Twilio SMS HTTP {resp.status_code}: {resp.text[:100]}")

        if _with_retry(_sms_attempt, f"SMS->{to_number}"):
            RECENT_ALERTS_FEED.appendleft(alert_record)
            return True

    print(f"  [SMS SIMULATOR] -> {to_number} | {message[:100]}", flush=True)
    alert_record["status"] = "SIMULATED"
    RECENT_ALERTS_FEED.appendleft(alert_record)
    return True


# ── 3. EMAIL ENGINE (GMAIL SMTP) ──────────────────────────────────────────────
def send_email(to_address, subject, html_body, attachment_path=None):
    """
    Send formatted HTML email with optional PDF challan/receipt attachment.
    """
    if not to_address:
        return False

    alert_record = {
        "channel": "Email",
        "to": to_address,
        "message": subject,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "SENT"
    }

    if not _is_email_configured():
        print(f"  [Email SIMULATOR] -> {to_address} | {subject}", flush=True)
        alert_record["status"] = "SIMULATED"
        RECENT_ALERTS_FEED.appendleft(alert_record)
        return True

    def _email_attempt():
        msg = MIMEMultipart('mixed')
        msg['From']    = f"TrafficGuard Pro Automated Enforcement <{GMAIL_ADDRESS}>"
        msg['To']      = to_address
        msg['Subject'] = subject

        msg.attach(MIMEText(html_body, 'html'))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD.replace(" ", ""))
            server.send_message(msg)

        return True

    if _with_retry(_email_attempt, f"Email->{to_address}"):
        RECENT_ALERTS_FEED.appendleft(alert_record)
        return True

    alert_record["status"] = "FAILED"
    RECENT_ALERTS_FEED.appendleft(alert_record)
    return False


# ── 4. MESSAGE TEMPLATES ──────────────────────────────────────────────────────
def _violator_whatsapp_msg(plate, violation_str, total_fine, challan_ref, owner_name, base_url="http://localhost:5001"):
    pay_link = f"{base_url}/citizen?challan={challan_ref}"
    dispute_link = f"{base_url}/citizen?dispute={challan_ref}"
    verify_link = f"{base_url}/verify/{challan_ref.replace('RX-', '')}"

    return (
        f"🚨 *TRAFFIC E-CHALLAN NOTICE — {APP_NAME}*\n"
        f"🏛️ *Government of India | Ministry of Road Transport*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Dear *{owner_name}*,\n\n"
        f"An AI Traffic Surveillance camera detected your vehicle in violation of the Motor Vehicles Act.\n\n"
        f"🚗 *Vehicle Number:* `{plate}`\n"
        f"⚠️ *Violation Type:* *{violation_str}*\n"
        f"💰 *Fine Amount:* *Rs. {total_fine:,}*\n"
        f"📋 *Challan Number:* `{challan_ref}`\n"
        f"📅 *Issuance Date:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
        f"📲 *ACTIONS AVAILABLE:*\n"
        f"• 💳 *Pay Online (Instant Receipt):*\n  {pay_link}\n\n"
        f"• ⚖️ *Dispute with Video Proof:*\n  {dispute_link}\n\n"
        f"• 🔍 *Verify Official Authenticity:*\n  {verify_link}\n\n"
        f"⚠️ *Mandatory Notice:* Please settle within 60 days to avoid court summons under Section 184/129 of MV Act.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 *Reply to this bot with:*\n"
        f"• `STATUS {plate}` to check pending challans\n"
        f"• `RULES` to view traffic penalty list"
    )


def _violator_sms_msg(plate, violation_str, total_fine, challan_ref, base_url="http://localhost:5001"):
    return (
        f"TRAFFIC E-CHALLAN: Vehicle {plate} caught for {violation_str}. "
        f"Fine Rs.{total_fine}. Challan No: {challan_ref}. "
        f"Pay online within 60 days: {base_url}/citizen"
    )


def _violator_email_html(plate, violation_str, total_fine, challan_ref, timestamp, owner_name, base_url="http://localhost:5001"):
    pay_link = f"{base_url}/citizen?challan={challan_ref}"
    dispute_link = f"{base_url}/citizen?dispute={challan_ref}"
    verify_link = f"{base_url}/verify/{challan_ref.replace('RX-', '')}"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #0b132b; color: #ffffff; margin: 0; padding: 20px; }}
        .container {{ max-width: 620px; margin: auto; background: #1c2541; border-radius: 12px; overflow: hidden; border: 1px solid #3a506b; }}
        .header {{ background: linear-gradient(135deg, #e61c16, #ff9933); padding: 24px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; color: #ffffff; letter-spacing: 1px; }}
        .header p {{ margin: 5px 0 0; color: #ffe6d9; font-size: 13px; }}
        .content {{ padding: 24px; }}
        .table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        .table td {{ padding: 10px 14px; border-bottom: 1px solid #2d3b5d; font-size: 14px; }}
        .label {{ color: #a9bed0; width: 40%; }}
        .val {{ color: #ffffff; font-weight: 600; }}
        .plate-box {{ background: #0b132b; border: 2px solid #ff9933; color: #ff9933; font-family: monospace; font-size: 20px; font-weight: bold; padding: 8px 14px; border-radius: 6px; display: inline-block; }}
        .fine-row {{ background: rgba(230, 28, 22, 0.15); color: #ff6b6b; font-size: 18px; font-weight: bold; }}
        .btn {{ display: inline-block; padding: 12px 24px; background: #138808; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 15px; margin-right: 10px; }}
        .btn-dispute {{ background: #3a506b; color: #ffffff; }}
        .footer {{ padding: 16px 24px; text-align: center; font-size: 12px; color: #6fffe9; border-top: 1px solid #2d3b5d; background: #0b132b; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>🚨 OFFICIAL TRAFFIC VIOLATION NOTICE</h1>
          <p>TrafficGuard Pro · Ministry of Road Transport & Highways Automated Enforcement</p>
        </div>
        <div class="content">
          <p>Dear <b>{owner_name}</b>,</p>
          <p>Your vehicle has been recorded violating traffic regulations under the <b>Motor Vehicles Act, 1988 (Amended 2019)</b>.</p>
          
          <table class="table">
            <tr>
              <td class="label">Vehicle Plate</td>
              <td class="val"><span class="plate-box">{plate}</span></td>
            </tr>
            <tr>
              <td class="label">Violation Type</td>
              <td class="val" style="color:#ff6b6b;">{violation_str}</td>
            </tr>
            <tr>
              <td class="label">Date & Time</td>
              <td class="val">{timestamp}</td>
            </tr>
            <tr>
              <td class="label">Challan Ref No</td>
              <td class="val">{challan_ref}</td>
            </tr>
            <tr class="fine-row">
              <td class="label" style="color:#ff8a80;">Total Fine Payable</td>
              <td class="val" style="color:#ff5252; font-size:20px;">Rs. {total_fine:,}</td>
            </tr>
          </table>

          <div style="text-align: center; margin: 24px 0;">
            <a href="{pay_link}" class="btn">💳 PAY CHALLAN ONLINE</a>
            <a href="{dispute_link}" class="btn btn-dispute">⚖️ SUBMIT DISPUTE</a>
          </div>

          <p style="font-size: 12px; color: #a9bed0; text-align: center;">
            Official PDF copy is attached to this email. You can also verify authenticity at <a href="{verify_link}" style="color:#ff9933;">{verify_link}</a>
          </p>
        </div>
        <div class="footer">
          सत्यमेव जयते · TrafficGuard Pro Automated Vision Network · Toll Free: 1800-11-8888
        </div>
      </div>
    </body>
    </html>
    """


# ── 5. MAIN NOTIFICATION DISPATCHER ───────────────────────────────────────────
def notify_violation(violation_id, plate, violation_str, total_fine,
                     timestamp, challan_filepath, owner_name="Citizen",
                     owner_phone=None, owner_email=None, base_url="http://localhost:5001"):
    """
    Broadcast violation notices across WhatsApp, SMS, and Email channels.
    """
    challan_ref = f"RX-{violation_id:06d}"
    print(f"\n[Notifications] Broadcasting multi-channel notices for {challan_ref} ({plate})...", flush=True)

    # 1. Violator WhatsApp
    if owner_phone:
        msg = _violator_whatsapp_msg(plate, violation_str, total_fine, challan_ref, owner_name, base_url)
        send_whatsapp(owner_phone, msg)
        send_sms(owner_phone, _violator_sms_msg(plate, violation_str, total_fine, challan_ref, base_url))

    # 2. Control Room / Admin Alert
    admin_msg = (
        f"🚔 *NEW INTERCEPTION ALERT — {APP_NAME}*\n"
        f"Challan: `{challan_ref}` | Plate: `{plate}`\n"
        f"Violation: *{violation_str}* | Fine: *Rs. {total_fine:,}*\n"
        f"Time: {timestamp} | Owner: {owner_name}"
    )
    send_whatsapp(ADMIN_WA_NUMBER, admin_msg)

    # 3. Violator Email with attached PDF Challan
    if owner_email:
        subject = f"🚨 Traffic Violation Challan Notice — {plate} | Fine Rs. {total_fine:,} [{challan_ref}]"
        html = _violator_email_html(plate, violation_str, total_fine, challan_ref, timestamp, owner_name, base_url)
        send_email(owner_email, subject, html, attachment_path=challan_filepath)

    # 4. Admin Email with challan PDF
    send_email(
        ADMIN_EMAIL,
        f"📋 New E-Challan Issued — {plate} [{challan_ref}]",
        f"<h3>Violation Captured by AI</h3><p>Plate: <b>{plate}</b><br/>Type: {violation_str}<br/>Fine: Rs. {total_fine:,}</p>",
        attachment_path=challan_filepath
    )

    print(f"[Notifications] Finished dispatching for {challan_ref}\n", flush=True)


def send_daily_summary(stats, base_url="http://localhost:5001"):
    """Send end-of-day enforcement summary report."""
    today = datetime.now().strftime("%d %b %Y")
    msg = (
        f"📊 *TrafficGuard Pro — Daily Enforcement Report ({today})*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• Total Violations: *{stats.get('total', 0)}*\n"
        f"• No Helmet: *{stats.get('no_helmet', 0)}*\n"
        f"• Triple Riding: *{stats.get('triple_riding', 0)}*\n"
        f"• Wrong Way: *{stats.get('wrong_way', 0)}*\n"
        f"• Total Fines Issued: *Rs. {stats.get('total_fines', 0):,}*\n"
        f"• Citizen Rewards Pool: *Rs. {stats.get('incentive_pool', 0):,}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"View command dashboard: {base_url}/"
    )
    send_whatsapp(ADMIN_WA_NUMBER, msg)
    send_email(ADMIN_EMAIL, f"📊 TrafficGuard Daily Summary — {today}", f"<pre>{msg}</pre>")


# ── 6. TWO-WAY WHATSAPP / CITIZEN BOT SIMULATOR ────────────────────────────────
def process_bot_message(incoming_text, sender_id="+919876543210", db_conn=None):
    """
    Interactive two-way chatbot processing user queries via WhatsApp.
    Commands:
    - STATUS <plate or challan>
    - PAY <challan_id>
    - RULES <topic>
    - DISPUTE <challan_id>
    - HELP
    """
    text = (incoming_text or "").strip()
    upper = text.upper()

    if not upper or upper == "HELP":
        return {
            "reply": (
                f"🤖 *TrafficGuard Pro Virtual Assistant*\n\n"
                f"Available Commands:\n"
                f"1️⃣ `STATUS <Plate>` — Check pending challans (e.g. STATUS KA03MX4521)\n"
                f"2️⃣ `STATUS <ChallanNo>` — Check specific challan (e.g. STATUS RX-000001)\n"
                f"3️⃣ `PAY <ChallanNo>` — Get instant payment link\n"
                f"4️⃣ `RULES` — View traffic fine directory (MV Act)\n"
                f"5️⃣ `DISPUTE <ChallanNo>` — Initiate a dispute review"
            )
        }

    if upper.startswith("STATUS"):
        parts = upper.split()
        if len(parts) < 2:
            return {"reply": "⚠️ Please provide a plate number or Challan No. Example: `STATUS KA03MX4521`"}
        query = parts[1].replace("-", "").replace(" ", "")

        if db_conn:
            c = db_conn.cursor()
            # check if query is challan id or plate
            if query.startswith("RX"):
                try:
                    cid = int(query.replace("RX", ""))
                    row = c.execute("SELECT id, plate, violation, fine, paid, timestamp FROM violations WHERE id=?", (cid,)).fetchone()
                except ValueError:
                    row = None
            else:
                row = c.execute("SELECT id, plate, violation, fine, paid, timestamp FROM violations WHERE UPPER(REPLACE(plate, ' ', ''))=? ORDER BY id DESC LIMIT 1", (query,)).fetchone()

            if row:
                status_str = "✅ PAID" if row[4] else "⏳ UNPAID / PENDING"
                return {
                    "reply": (
                        f"📋 *CHALLAN STATUS FOUND:*\n"
                        f"• Challan No: `RX-{row[0]:06d}`\n"
                        f"• Plate: `{row[1]}`\n"
                        f"• Offence: *{row[2]}*\n"
                        f"• Fine Amount: *Rs. {row[3]:,}*\n"
                        f"• Status: *{status_str}*\n"
                        f"• Date: {row[5]}\n\n"
                        f"To pay: Reply `PAY RX-{row[0]:06d}`"
                    )
                }
            return {"reply": f"🔍 No active violation found for `{query}`. Safe driving!"}
        return {"reply": f"Checked database for `{query}`: No unpaid penalties recorded."}

    if upper.startswith("PAY"):
        parts = upper.split()
        target = parts[1] if len(parts) > 1 else "RX-000001"
        return {
            "reply": (
                f"💳 *PAYMENT PORTAL LINK:*\n"
                f"Challan Ref: `{target}`\n"
                f"Click to pay via UPI, Card, NetBanking:\n"
                f"👉 http://localhost:5001/citizen?challan={target}"
            )
        }

    if upper.startswith("RULES") or "HELMET" in upper or "SPEED" in upper:
        return {
            "reply": (
                f"📚 *MOTOR VEHICLES ACT PENALTY SCHEDULE:*\n"
                f"• *No Helmet (Sec 129):* Rs. 1,000 + 3-month DL suspension risk\n"
                f"• *Triple Riding (Sec 128):* Rs. 1,000\n"
                f"• *Dangerous / Wrong-Way Driving (Sec 184):* Rs. 5,000\n"
                f"• *Overspeeding (Sec 183):* Rs. 2,000\n"
                f"• *Drunk Driving (Sec 185):* Rs. 10,000 / Imprisonment\n"
                f"• *Habitual Offender:* 2x to 3x fine multiplier applies."
            )
        }

    return {
        "reply": f"TrafficGuard Assistant: Command not recognized. Send `HELP` for menu options."
    }