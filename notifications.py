"""
VehicleTrack Notification System
Handles both WhatsApp (Meta Cloud API) and Email alerts

═══════════════════════════════════════════════════════
SETUP — never hardcode credentials here.
Store them in a .env file (never pushed to GitHub).

Create a .env file in your project root:
    GMAIL_ADDRESS=your@gmail.com
    GMAIL_APP_PASS=your16charpassword
    CITIZEN_EMAIL=faculty@domain.com
    ADMIN_EMAIL=friend@domain.com

Then run: python app.py
Credentials load automatically from .env
═══════════════════════════════════════════════════════
"""

import os
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — env vars must be set manually

# ══════════════════════════════════════════════════════
# CONFIG — all values come from environment variables
# ══════════════════════════════════════════════════════

WHATSAPP_PHONE_ID = os.environ.get("WA_PHONE_ID", "")
WHATSAPP_TOKEN    = os.environ.get("WA_TOKEN",    "")
WHATSAPP_API_URL  = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"

CITIZEN_WA_NUMBER = os.environ.get("CITIZEN_WA", "")
ADMIN_WA_NUMBER   = os.environ.get("ADMIN_WA",   "")

GMAIL_ADDRESS      = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASS", "")

CITIZEN_EMAIL = os.environ.get("CITIZEN_EMAIL", "")
ADMIN_EMAIL   = os.environ.get("ADMIN_EMAIL",   "")

CITIZEN_INCENTIVE_PCT = 10  # 10% of fine

# ── Retry config ────────────────────────────────────
MAX_RETRIES  = 3    # try up to 3 times
RETRY_DELAY  = 2    # seconds between retries


# ══════════════════════════════════════════════════════
# CONFIGURATION CHECKS
# ══════════════════════════════════════════════════════

def _is_wa_configured():
    return bool(WHATSAPP_PHONE_ID and WHATSAPP_TOKEN)

def _is_email_configured():
    pw = GMAIL_APP_PASSWORD.replace(" ", "")
    # Check both address and password are non-empty — avoids brittle length checks
    # that break if Google ever changes their app-password format.
    return bool(GMAIL_ADDRESS and pw)


# ══════════════════════════════════════════════════════
# RETRY HELPER
# ══════════════════════════════════════════════════════

def _with_retry(fn, label):
    """
    Run fn() up to MAX_RETRIES times.
    Returns True if any attempt succeeds, False if all fail.
    All failures are printed so they're visible in logs even with stdout buffering.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = fn()
            if result:
                return True
            raise RuntimeError("fn returned False (non-200 or explicit False)")
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                print(f"  [{label}] ⚠️  Attempt {attempt}/{MAX_RETRIES} failed: {e}"
                      f" — retrying in {RETRY_DELAY}s...", flush=True)
                time.sleep(RETRY_DELAY)
            else:
                # flush=True ensures this is visible even if stdout is line-buffered
                print(f"  [{label}] ❌ All {MAX_RETRIES} attempts failed."
                      f" Last error: {last_error}", flush=True)
    return False


# ══════════════════════════════════════════════════════
# WHATSAPP via Meta Cloud API
# ══════════════════════════════════════════════════════

def send_whatsapp(to_number, message):
    if not to_number:
        return False
    if not _is_wa_configured():
        print(f"  [WhatsApp MOCK] → {to_number}\n  {message[:80]}...\n")
        return True

    def _attempt():
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type":  "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to":   to_number,
            "type": "text",
            "text": {"body": message}
        }
        resp = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            print(f"  [WhatsApp] ✅ Sent to {to_number}")
            return True
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:100]}")

    return _with_retry(_attempt, f"WhatsApp→{to_number}")


# ══════════════════════════════════════════════════════
# EMAIL via Gmail SMTP
# ══════════════════════════════════════════════════════

def send_email(to_address, subject, html_body, attachment_path=None):
    if not to_address:
        return False
    if not _is_email_configured():
        print(f"  [Email MOCK] → {to_address} | {subject}")
        return True

    def _attempt():
        msg = MIMEMultipart('mixed')
        msg['From']    = f"VehicleTrack Traffic Enforcement <{GMAIL_ADDRESS}>"
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

        print(f"  [Email] ✅ Sent to {to_address}")
        return True

    return _with_retry(_attempt, f"Email→{to_address}")


# ══════════════════════════════════════════════════════
# MESSAGE TEMPLATES
# ══════════════════════════════════════════════════════

def _violator_whatsapp_msg(plate, violation_str, total_fine, challan_ref, owner_name):
    pay_link = f"https://parivahan.gov.in/challan/{challan_ref}"
    return (
        f"🚨 *TRAFFIC VIOLATION NOTICE — VehicleTrack*\n\n"
        f"Dear *{owner_name}*,\n\n"
        f"Your vehicle has been detected committing a traffic violation "
        f"by an AI-powered enforcement system.\n\n"
        f"🚗 *Vehicle:* {plate}\n"
        f"⚠️ *Violation:* {violation_str}\n"
        f"💰 *Fine Amount:* Rs. {total_fine:,}\n"
        f"📋 *Challan Ref:* {challan_ref}\n\n"
        f"Pay online within *60 days* to avoid court summons:\n"
        f"{pay_link}\n\n"
        f"For disputes: 1800-XXX-XXXX (Toll Free)\n"
        f"— VehicleTrack Automated Enforcement System"
    )

def _violator_email_html(plate, violation_str, total_fine, challan_ref, timestamp, owner_name):
    pay_link = f"https://parivahan.gov.in/challan/{challan_ref}"
    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;background:#f5f5f5;">
      <div style="background:#c0392b;padding:20px;border-radius:8px;text-align:center;margin-bottom:20px;">
        <h1 style="color:white;margin:0;font-size:24px;">🚨 TRAFFIC VIOLATION NOTICE</h1>
        <p style="color:#ffcccc;margin:5px 0;">VehicleTrack Automated Enforcement System</p>
      </div>
      <div style="background:white;border-radius:8px;padding:20px;margin-bottom:16px;border-left:4px solid #c0392b;">
        <p style="color:#333;">Dear <b>{owner_name}</b>,</p>
        <p style="color:#555;">Your vehicle has been detected committing a traffic violation.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#fdf0f0;">
            <td style="padding:10px;color:#888;font-size:13px;width:40%;">Vehicle Plate</td>
            <td style="padding:10px;color:#c0392b;font-weight:bold;font-size:18px;letter-spacing:2px;">{plate}</td>
          </tr>
          <tr>
            <td style="padding:10px;color:#888;font-size:13px;">Violation</td>
            <td style="padding:10px;color:#333;font-weight:bold;">{violation_str}</td>
          </tr>
          <tr style="background:#fdf0f0;">
            <td style="padding:10px;color:#888;font-size:13px;">Date &amp; Time</td>
            <td style="padding:10px;color:#333;">{timestamp}</td>
          </tr>
          <tr>
            <td style="padding:10px;color:#888;font-size:13px;">Challan No</td>
            <td style="padding:10px;color:#333;font-weight:bold;">{challan_ref}</td>
          </tr>
          <tr style="background:#fff3cd;">
            <td style="padding:12px;color:#856404;font-weight:bold;font-size:13px;">Fine Amount</td>
            <td style="padding:12px;color:#856404;font-weight:bold;font-size:20px;">Rs. {total_fine:,}</td>
          </tr>
        </table>
      </div>
      <div style="background:#c0392b;border-radius:8px;padding:20px;text-align:center;margin-bottom:16px;">
        <h3 style="color:white;margin-top:0;">Pay Your Fine Online</h3>
        <a href="{pay_link}" style="background:white;color:#c0392b;padding:12px 30px;border-radius:4px;font-weight:bold;text-decoration:none;display:inline-block;font-size:16px;">
          PAY NOW — Rs. {total_fine:,}
        </a>
        <p style="color:#ffcccc;font-size:12px;margin-bottom:0;">Pay within 60 days to avoid court summons</p>
      </div>
      <p style="color:#999;font-size:11px;text-align:center;">
        Automated notice by VehicleTrack under the Motor Vehicles Act 1988.<br/>
        {datetime.now().strftime('%d %b %Y %H:%M')} | Ref: {challan_ref}
      </p>
    </body></html>
    """

def _citizen_whatsapp_msg(plate, violation_str, total_fine, challan_ref):
    reward = int(total_fine * CITIZEN_INCENTIVE_PCT / 100)
    return (
        f"🏆 *VehicleTrack — Violation Captured!*\n\n"
        f"Your dashcam just caught a traffic violator!\n\n"
        f"🚗 *Vehicle:* {plate}\n"
        f"⚠️ *Violation:* {violation_str}\n"
        f"💰 *Fine Issued:* Rs. {total_fine:,}\n\n"
        f"🎁 *Your Incentive:* Rs. {reward:,} ({CITIZEN_INCENTIVE_PCT}%)\n"
        f"Credited after the challan is paid.\n\n"
        f"📋 *Ref:* {challan_ref}\n\n"
        f"You're making Indian roads safer! 🛣️\n"
        f"— VehicleTrack Team"
    )

def _admin_whatsapp_msg(plate, violation_str, total_fine, timestamp, challan_ref):
    return (
        f"🚔 *NEW VIOLATION — VehicleTrack Alert*\n\n"
        f"📋 Challan: *{challan_ref}*\n"
        f"🚗 Plate: *{plate}*\n"
        f"⚠️ Violation: {violation_str}\n"
        f"💰 Fine: Rs. {total_fine:,}\n"
        f"🕐 Time: {timestamp}\n\n"
        f"Challan auto-generated & sent.\n"
        f"— VehicleTrack System"
    )

def _citizen_email_html(plate, violation_str, total_fine, challan_ref, timestamp):
    reward = int(total_fine * CITIZEN_INCENTIVE_PCT / 100)
    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
      <div style="background:#1a1a2e;padding:20px;border-radius:8px;text-align:center;margin-bottom:20px;">
        <h1 style="color:#00e5ff;margin:0;font-size:28px;">⚡ ROAD<span style="color:white">X</span></h1>
        <p style="color:#aaa;margin:5px 0;">Traffic Enforcement System</p>
      </div>
      <div style="background:#0d1b2a;border:1px solid #1c3a52;border-radius:8px;padding:20px;margin-bottom:16px;">
        <h2 style="color:#00ff88;margin-top:0;">🏆 Violation Captured!</h2>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#1c3a52;">
            <td style="padding:10px;color:#aaa;font-size:13px;">Vehicle Plate</td>
            <td style="padding:10px;color:#00e5ff;font-weight:bold;font-size:16px;letter-spacing:2px;">{plate}</td>
          </tr>
          <tr>
            <td style="padding:10px;color:#aaa;font-size:13px;">Violation</td>
            <td style="padding:10px;color:#ff6b6b;font-weight:bold;">{violation_str}</td>
          </tr>
          <tr style="background:#1c3a52;">
            <td style="padding:10px;color:#aaa;font-size:13px;">Fine Issued</td>
            <td style="padding:10px;color:#fff;font-weight:bold;">Rs. {total_fine:,}</td>
          </tr>
          <tr>
            <td style="padding:10px;color:#aaa;font-size:13px;">Date &amp; Time</td>
            <td style="padding:10px;color:#fff;">{timestamp}</td>
          </tr>
          <tr style="background:#1c3a52;">
            <td style="padding:10px;color:#aaa;font-size:13px;">Challan Ref</td>
            <td style="padding:10px;color:#ffd60a;font-weight:bold;">{challan_ref}</td>
          </tr>
        </table>
      </div>
      <div style="background:#0d2818;border:1px solid #1a5c34;border-radius:8px;padding:20px;margin-bottom:16px;text-align:center;">
        <h3 style="color:#00ff88;margin-top:0;">🎁 Your Incentive</h3>
        <div style="font-size:36px;font-weight:bold;color:#00ff88;">Rs. {reward:,}</div>
        <p style="color:#aaa;font-size:13px;">{CITIZEN_INCENTIVE_PCT}% of the fine — credited after payment</p>
      </div>
      <p style="color:#666;font-size:12px;text-align:center;">Generated by VehicleTrack • {datetime.now().strftime('%d %b %Y %H:%M')}</p>
    </body></html>
    """

def _admin_email_html(plate, violation_str, total_fine, owner_name, timestamp, challan_ref):
    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
      <div style="background:#1a1a2e;padding:20px;border-radius:8px;text-align:center;margin-bottom:20px;">
        <h1 style="color:#00e5ff;margin:0;font-size:28px;">⚡ ROAD<span style="color:white">X</span></h1>
        <p style="color:#aaa;margin:5px 0;">Traffic Enforcement System</p>
      </div>
      <div style="background:#2d0a0a;border:1px solid #5c1a1a;border-radius:8px;padding:20px;margin-bottom:16px;">
        <h2 style="color:#ff4444;margin-top:0;">🚨 New Violation Detected</h2>
        <table style="width:100%;border-collapse:collapse;">
          <tr style="background:#1c0808;"><td style="padding:10px;color:#aaa;">Challan No</td>
            <td style="padding:10px;color:#ffd60a;font-weight:bold;">{challan_ref}</td></tr>
          <tr><td style="padding:10px;color:#aaa;">Vehicle Plate</td>
            <td style="padding:10px;color:#00e5ff;font-weight:bold;letter-spacing:2px;">{plate}</td></tr>
          <tr style="background:#1c0808;"><td style="padding:10px;color:#aaa;">Owner Name</td>
            <td style="padding:10px;color:#fff;">{owner_name}</td></tr>
          <tr><td style="padding:10px;color:#aaa;">Violation</td>
            <td style="padding:10px;color:#ff6b6b;font-weight:bold;">{violation_str}</td></tr>
          <tr style="background:#1c0808;"><td style="padding:10px;color:#aaa;">Fine Amount</td>
            <td style="padding:10px;color:#fff;font-weight:bold;">Rs. {total_fine:,}</td></tr>
          <tr><td style="padding:10px;color:#aaa;">Date &amp; Time</td>
            <td style="padding:10px;color:#fff;">{timestamp}</td></tr>
        </table>
      </div>
      <p style="color:#888;font-size:12px;text-align:center;">Challan PDF attached. VehicleTrack • {datetime.now().strftime('%d %b %Y %H:%M')}</p>
    </body></html>
    """

def _daily_summary_email_html(stats):
    today = datetime.now().strftime('%d %b %Y')
    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
      <div style="background:#1a1a2e;padding:20px;border-radius:8px;text-align:center;margin-bottom:20px;">
        <h1 style="color:#00e5ff;margin:0;">⚡ VEHICLETRACK — Daily Summary</h1>
        <p style="color:#aaa;">{today}</p>
      </div>
      <table style="width:100%;border-collapse:collapse;">
        <tr style="background:#2c3e50;color:white;">
          <td style="padding:12px;font-weight:bold;">Metric</td>
          <td style="padding:12px;font-weight:bold;text-align:right;">Count</td>
        </tr>
        <tr><td style="padding:10px;background:#f8f9fa;">Total Violations</td>
          <td style="padding:10px;background:#f8f9fa;text-align:right;font-weight:bold;">{stats.get('total',0)}</td></tr>
        <tr><td style="padding:10px;">No Helmet</td>
          <td style="padding:10px;text-align:right;">{stats.get('no_helmet',0)}</td></tr>
        <tr><td style="padding:10px;background:#f8f9fa;">Triple Riding</td>
          <td style="padding:10px;background:#f8f9fa;text-align:right;">{stats.get('triple_riding',0)}</td></tr>
        <tr><td style="padding:10px;">Wrong Way</td>
          <td style="padding:10px;text-align:right;">{stats.get('wrong_way',0)}</td></tr>
        <tr style="background:#27ae60;color:white;">
          <td style="padding:12px;font-weight:bold;">Total Fines Generated</td>
          <td style="padding:12px;text-align:right;font-weight:bold;">Rs. {stats.get('total_fines',0):,}</td></tr>
        <tr style="background:#f39c12;color:white;">
          <td style="padding:12px;font-weight:bold;">Citizen Incentive Pool</td>
          <td style="padding:12px;text-align:right;font-weight:bold;">Rs. {stats.get('incentive_pool',0):,}</td></tr>
      </table>
      <p style="color:#999;font-size:12px;text-align:center;margin-top:20px;">VehicleTrack Automated Report • {today}</p>
    </body></html>
    """


# ══════════════════════════════════════════════════════
# MAIN NOTIFICATION FUNCTION
# ══════════════════════════════════════════════════════

def notify_violation(violation_id, plate, violation_str, total_fine,
                     timestamp, challan_filepath, owner_name="Not Available",
                     owner_phone=None, owner_email=None):
    challan_ref = f"RX-{violation_id:06d}"
    print(f"\n  [Notifications] Sending alerts for {challan_ref}...")

    # 1. VIOLATOR WhatsApp (from Vahan lookup)
    if owner_phone:
        send_whatsapp(
            owner_phone,
            _violator_whatsapp_msg(plate, violation_str, total_fine, challan_ref, owner_name)
        )

    # 2. Citizen & Admin WhatsApp
    send_whatsapp(CITIZEN_WA_NUMBER,
                  _citizen_whatsapp_msg(plate, violation_str, total_fine, challan_ref))
    send_whatsapp(ADMIN_WA_NUMBER,
                  _admin_whatsapp_msg(plate, violation_str, total_fine, timestamp, challan_ref))

    # 3. VIOLATOR email (from Vahan lookup)
    if owner_email:
        send_email(
            owner_email,
            f"🚨 Traffic Violation Notice — {plate} | Fine Rs. {total_fine:,} | {challan_ref}",
            _violator_email_html(plate, violation_str, total_fine, challan_ref, timestamp, owner_name),
            attachment_path=challan_filepath
        )

    # 4. Citizen incentive email
    send_email(
        CITIZEN_EMAIL,
        f"🏆 VehicleTrack — You Earned Rs. {int(total_fine * CITIZEN_INCENTIVE_PCT / 100):,} Incentive! [{challan_ref}]",
        _citizen_email_html(plate, violation_str, total_fine, challan_ref, timestamp)
    )

    # 5. Admin email with challan PDF
    send_email(
        ADMIN_EMAIL,
        f"🚨 VehicleTrack — New Violation Detected | {plate} | {challan_ref}",
        _admin_email_html(plate, violation_str, total_fine, owner_name, timestamp, challan_ref),
        attachment_path=challan_filepath
    )

    print(f"  [Notifications] Done for {challan_ref}\n")


def send_daily_summary(stats):
    today = datetime.now().strftime("%d %b %Y")
    msg = (
        f"📊 *VehicleTrack Daily Summary — {today}*\n\n"
        f"Violations: *{stats.get('total',0)}*\n"
        f"No Helmet: {stats.get('no_helmet',0)}\n"
        f"Triple Riding: {stats.get('triple_riding',0)}\n"
        f"Wrong Way: {stats.get('wrong_way',0)}\n\n"
        f"Total Fines: *Rs. {stats.get('total_fines',0):,}*\n"
        f"Incentive Pool: Rs. {stats.get('incentive_pool',0):,}\n\n"
        f"— VehicleTrack Automated Report"
    )
    send_whatsapp(ADMIN_WA_NUMBER, msg)
    send_email(ADMIN_EMAIL, f"📊 VehicleTrack Daily Summary — {today}",
               _daily_summary_email_html(stats))