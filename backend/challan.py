"""
TrafficGuard Pro E-Challan & Payment Receipt PDF Generator
Generates:
1. High-resolution Official Traffic Violation E-Challan PDF with QR verification code.
2. Official Payment Settlement Receipt PDF with transaction ID and stamp.
"""

import os
import qrcode
import sqlite3
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, Image as RLImage, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

from config import APP_NAME, TAGLINE, ORGANIZATION, MOTTO

# ── FINE SCHEDULE (Motor Vehicles Act 1988, amended 2019) ────────────────────
BASE_FINES = {
    "NO HELMET":     1000,
    "TRIPLE RIDING": 1000,
    "WRONG WAY":     5000,
    "OVERSPEEDING":  2000,
    "NO SEATBELT":   1000,
    "SIGNAL JUMP":   1000,
    "DRUNK DRIVING": 10000,
}

SECTIONS = {
    "NO HELMET":     "Sec 129 MV Act (Protective Headgear)",
    "TRIPLE RIDING": "Sec 128 MV Act (Safety of Pillion Rider)",
    "WRONG WAY":     "Sec 184 MV Act (Dangerous Driving)",
    "OVERSPEEDING":  "Sec 183 MV Act (Excessive Speed)",
    "NO SEATBELT":   "Sec 194B MV Act (Seatbelt Non-compliance)",
    "SIGNAL JUMP":   "Sec 184(c) MV Act (Red Light Violation)",
    "DRUNK DRIVING": "Sec 185 MV Act (Driving Under Influence)",
}

SEVERITY_MULTIPLIER = {
    1: 1.0,   # 1st offence
    2: 2.0,   # 2nd offence
    3: 3.0,   # 3rd+ offence (habitual offender)
}

PAYMENT_BASE_URL = "http://localhost:5001/verify/"


def get_offence_count(db_path, plate):
    """Count previous violations recorded for this plate."""
    if not plate or plate == "UNKNOWN":
        return 1
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM violations WHERE UPPER(REPLACE(plate, ' ', ''))=?",
                  (plate.upper().replace(" ", ""),))
        count = c.fetchone()[0]
        conn.close()
        return max(1, count)
    except Exception:
        return 1


def calculate_fine(violations_list, offence_count=1):
    """Calculate total fine with habitual offender severity multiplier."""
    base = sum(BASE_FINES.get(v.strip().upper(), 500) for v in violations_list)
    multiplier = SEVERITY_MULTIPLIER.get(min(max(1, offence_count), 3), 3.0)
    total = int(base * multiplier)
    return base, multiplier, total


def generate_qr(challan_id, amount, base_verify_url=PAYMENT_BASE_URL):
    """Generate high-contrast QR code for digital verification and payment."""
    url = f"{base_verify_url}{challan_id:06d}"
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(tmp.name)
    return tmp.name, url


# ── 1. E-CHALLAN PDF BUILDER ──────────────────────────────────────────────────
def generate_challan(challan_dir, screenshot_dir,
                     violation_id, timestamp, video,
                     violation_str, plate, screenshot_filename,
                     db_path, owner_name="Citizen",
                     offence_count=None, vehicle_details=None,
                     officer_name="Inspector R. K. Sharma (Badge #404)"):
    """
    Generate Official High-Resolution Traffic Enforcement E-Challan PDF.
    """
    challan_filename = f"challan_RX{violation_id:06d}.pdf"
    challan_path = os.path.join(challan_dir, challan_filename)

    violations_list = [v.strip() for v in violation_str.split("+") if v.strip()]
    if not violations_list:
        violations_list = [violation_str.strip() or "TRAFFIC INFRACTION"]

    if offence_count is None:
        offence_count = get_offence_count(db_path, plate)

    base_fine, multiplier, total_fine = calculate_fine(violations_list, offence_count)

    is_repeat = offence_count > 1
    severity = "HABITUAL OFFENDER (3X FINE)" if offence_count >= 3 else ("REPEAT OFFENDER (2X FINE)" if is_repeat else "FIRST OFFENCE (STANDARD)")
    sev_color = colors.HexColor('#c0392b') if offence_count >= 3 else (
                colors.HexColor('#e67e22') if is_repeat else colors.HexColor('#138808'))

    qr_path, payment_url = generate_qr(violation_id, total_fine)

    doc = SimpleDocTemplate(
        challan_path, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.2*cm, bottomMargin=1.2*cm
    )

    title_style = ParagraphStyle('title', fontSize=16, fontName='Helvetica-Bold',
                                 alignment=TA_CENTER, textColor=colors.HexColor('#001a4d'),
                                 spaceAfter=2, spaceBefore=0)
    sub_style = ParagraphStyle('sub', fontSize=8.5, fontName='Helvetica',
                               alignment=TA_CENTER, textColor=colors.HexColor('#555555'),
                               spaceAfter=2, leading=11)
    satyamev_style = ParagraphStyle('sat', fontSize=10, fontName='Helvetica-Bold',
                                   alignment=TA_CENTER, textColor=colors.HexColor('#e61c16'),
                                   spaceAfter=4)
    section_style = ParagraphStyle('section', fontSize=10.5, fontName='Helvetica-Bold',
                                   textColor=colors.HexColor('#001a4d'), spaceBefore=6, spaceAfter=4)
    foot_style = ParagraphStyle('foot', fontSize=7, fontName='Helvetica',
                                alignment=TA_CENTER, textColor=colors.HexColor('#777777'))

    story = []

    # ── HEADER ───────────────────────────────────────────────────────────────
    story.append(Paragraph("सत्यमेव जयते · GOVERNMENT OF INDIA", satyamev_style))
    story.append(Paragraph("MINISTRY OF ROAD TRANSPORT & HIGHWAYS", title_style))
    story.append(Paragraph(f"{APP_NAME} — Automated AI Vision Traffic Enforcement System", sub_style))
    story.append(Paragraph("Issued under Motor Vehicles Act, 1988 (as amended by MV Amendment Act 2019)", sub_style))
    story.append(Spacer(1, 0.2*cm))

    # Tricolor Accent Line
    story.append(HRFlowable(width="100%", thickness=3, color=colors.HexColor('#ff9933'), spaceAfter=4))

    # Challan Banner
    sev_text = f"E-CHALLAN NO: RX-{violation_id:06d}   |   {severity}   |   OFFENCE #{offence_count}"
    sev_data = [[Paragraph(sev_text, ParagraphStyle('sev', fontSize=9.5, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER))]]
    sev_table = Table(sev_data, colWidths=[18*cm])
    sev_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), sev_color),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(sev_table)
    story.append(Spacer(1, 0.25*cm))

    # ── VEHICLE & VIOLATOR PARTICULARS ────────────────────────────────────────
    story.append(Paragraph("1. Vehicle & Offender Particulars (Vahan Ledger Record)", section_style))

    make_model = (vehicle_details.get("make_model") if vehicle_details else None) or "Two-Wheeler / Motor Vehicle"
    rto_office = (vehicle_details.get("rto") if vehicle_details else None) or "Regional Transport Office"

    owner_data = [
        ["Registration No", plate if plate != "UNKNOWN" else "PLATE UNRESOLVED",
         "Vehicle Make/Model", make_model],
        ["Registered Owner", owner_name,
         "RTO Authority", rto_office[:32]],
        ["Date & Time of Offence", timestamp,
         "Issuing Officer", officer_name],
        ["Interception Camera/Feed", (video[:32] + "..") if len(video) > 32 else video,
         "Offence Frequency", f"Count #{offence_count} (Multiplier: {multiplier}x)"]
    ]

    owner_table = Table(owner_data, colWidths=[4.2*cm, 4.8*cm, 4.2*cm, 4.8*cm])
    owner_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d7de')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f6f8fa')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f6f8fa')),
        ('TOPPADDING', (0,0), (-1,-1), 4.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('TEXTCOLOR', (1,0), (1,0), colors.HexColor('#c0392b')),
        ('FONTNAME', (1,0), (1,0), 'Helvetica-Bold'),
    ]))
    story.append(owner_table)
    story.append(Spacer(1, 0.25*cm))

    # ── OFFENCE DETAILS & PENALTY BREAKDOWN ────────────────────────────────────
    story.append(Paragraph("2. Offence Citation & Statutory Fine Breakdown", section_style))
    fine_rows = [["#", "Violation Committed", "Legal Citation (MV Act 1988)", "Base Penalty"]]
    for i, v in enumerate(violations_list, 1):
        v_upper = v.strip().upper()
        fine_rows.append([
            str(i),
            v.strip(),
            SECTIONS.get(v_upper, "Sec 177 MV Act (General Offence)"),
            f"Rs. {BASE_FINES.get(v_upper, 500):,}"
        ])
    fine_rows.append(["", "Subtotal Base Fine", "", f"Rs. {base_fine:,}"])
    fine_rows.append(["", f"Offence Multiplier ({multiplier}x — Offence Record #{offence_count})", "", f"{multiplier}x"])
    fine_rows.append(["", "TOTAL STATUTORY PENALTY DUE", "", f"Rs. {total_fine:,}"])

    fine_table = Table(fine_rows, colWidths=[0.8*cm, 7.2*cm, 6.5*cm, 3.5*cm])
    fine_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#001a4d')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#d0d7de')),
        ('TOPPADDING', (0,0), (-1,-1), 4.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,-3), (-1,-3), colors.HexColor('#f0f4f8')),
        ('FONTNAME', (0,-3), (-1,-3), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-2), (-1,-2), colors.HexColor('#fff8e1')),
        ('TEXTCOLOR', (0,-2), (-1,-2), colors.HexColor('#b78103')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#c0392b')),
        ('TEXTCOLOR', (0,-1), (-1,-1), colors.white),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,-1), (-1,-1), 10),
    ]))
    story.append(fine_table)
    story.append(Spacer(1, 0.25*cm))

    # ── PHOTOGRAPHIC EVIDENCE & QR VERIFICATION ───────────────────────────────
    story.append(Paragraph("3. AI Photographic Evidence & Instant Digital Settlement", section_style))

    ss_path = os.path.join(screenshot_dir, screenshot_filename) if screenshot_filename else None
    row_content = []

    if ss_path and os.path.exists(ss_path):
        ev_img = RLImage(ss_path, width=11.2*cm, height=5.8*cm)
        row_content.append(ev_img)
    else:
        row_content.append(Paragraph("<i>Photographic Frame Preserved in Secure Forensic Vault</i>", ParagraphStyle('ns', fontSize=8.5)))

    qr_img = RLImage(qr_path, width=4.2*cm, height=4.2*cm)
    pay_txt = Paragraph(
        f"<b>SCAN WITH ANY UPI APP</b><br/>"
        f"Amount: <b>Rs. {total_fine:,}</b><br/>"
        f"Ref: <b>RX-{violation_id:06d}</b><br/>"
        f"Online Verification:<br/>"
        f"<font size='6.5' color='#001a4d'>{payment_url[:35]}</font>",
        ParagraphStyle('pay', fontSize=8, fontName='Helvetica', alignment=TA_CENTER, leading=11)
    )
    qr_block = Table([[qr_img], [pay_txt]], colWidths=[6.2*cm])
    qr_block.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    row_content.append(qr_block)

    ev_row = Table([row_content], colWidths=[11.5*cm, 6.5*cm])
    ev_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d7de')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(ev_row)
    story.append(Spacer(1, 0.2*cm))

    # ── STATUTORY SETTLEMENT INSTRUCTIONS ──────────────────────────────────────
    pay_data = [
        [Paragraph("<b>OFFICIAL PAYMENT & DISPUTE PROTOCOL</b>", ParagraphStyle('pi', fontSize=8.5, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER))],
        [Paragraph(
            "1. Settle online via <b>UPI / NetBanking / Debit Card</b> by scanning the QR code above or at <b>trafficguard.gov.in/citizen</b>.<br/>"
            "2. Non-payment within <b>60 days</b> of notice will initiate proceedings under <b>Section 184/129 MV Act</b> resulting in court summons and potential driving license suspension.<br/>"
            "3. <b>Citizen Dispute Right:</b> If this detection was recorded in error, file a digital dispute with dashcam proof at <b>/citizen</b> within 15 days.",
            ParagraphStyle('pitext', fontSize=7.5, fontName='Helvetica', leading=10.5)
        )],
    ]
    pay_table = Table(pay_data, colWidths=[18*cm])
    pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#138808')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#f0fbf0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#a9dfbf')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(pay_table)
    story.append(Spacer(1, 0.15*cm))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Paragraph(
        f"Computer Generated E-Challan issued by {APP_NAME} AI Vision Network. "
        f"Timestamp: {datetime.now().strftime('%d %b %Y, %H:%M:%S IST')}  |  "
        f"Ref: RX-{violation_id:06d}  |  SHA-256 Cryptographic Hash Registered",
        foot_style
    ))

    doc.build(story)

    try:
        os.unlink(qr_path)
    except Exception:
        pass

    return challan_filename


# ── 2. PAYMENT RECEIPT PDF BUILDER ────────────────────────────────────────────
def generate_receipt(receipt_dir, violation_id, plate, violation_str,
                     amount_paid, payment_mode="Online UPI / Razorpay",
                     txn_id=None, payer_name="Citizen"):
    """
    Generate Official Payment Settlement Receipt PDF for paid challans.
    """
    if txn_id is None:
        txn_id = f"TXN-TG-{violation_id:06d}-{int(datetime.now().timestamp())}"

    receipt_filename = f"receipt_RX{violation_id:06d}.pdf"
    receipt_path = os.path.join(receipt_dir, receipt_filename)

    doc = SimpleDocTemplate(
        receipt_path, pagesize=A4,
        rightMargin=2.0*cm, leftMargin=2.0*cm,
        topMargin=2.0*cm, bottomMargin=2.0*cm
    )

    story = []
    title_style = ParagraphStyle('rtitle', fontSize=18, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.HexColor('#138808'), spaceAfter=4)
    sub_style = ParagraphStyle('rsub', fontSize=9, fontName='Helvetica', alignment=TA_CENTER, textColor=colors.HexColor('#444444'), spaceAfter=6)

    story.append(Paragraph("सत्यमेव जयते", ParagraphStyle('sat', fontSize=12, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=colors.HexColor('#e61c16'))))
    story.append(Paragraph("OFFICIAL E-CHALLAN PAYMENT RECEIPT", title_style))
    story.append(Paragraph(f"{ORGANIZATION} — {APP_NAME}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#138808'), spaceAfter=14))

    # Paid Stamp banner
    stamp_text = "PAID & SETTLED · NO FURTHER PENALTY DUE"
    stamp_data = [[Paragraph(f"<b>{stamp_text}</b>", ParagraphStyle('st', fontSize=11, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER))]]
    stamp_table = Table(stamp_data, colWidths=[17*cm])
    stamp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#138808')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(stamp_table)
    story.append(Spacer(1, 0.4*cm))

    # Receipt Details
    r_data = [
        ["Receipt Number", f"RCP-2026-{violation_id:06d}", "Transaction ID", txn_id],
        ["Challan Reference", f"RX-{violation_id:06d}", "Payment Status", "SUCCESSFUL (200 OK)"],
        ["Vehicle Registration", plate, "Payer Name", payer_name],
        ["Offence Description", violation_str, "Payment Method", payment_mode],
        ["Settlement Date & Time", datetime.now().strftime("%d %b %Y, %I:%M %p"), "Amount Paid", f"Rs. {amount_paid:,}"]
    ]

    r_table = Table(r_data, colWidths=[4.2*cm, 4.3*cm, 4.2*cm, 4.3*cm])
    r_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d7de')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f6f8fa')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f6f8fa')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (3,4), (3,4), colors.HexColor('#138808')),
        ('FONTNAME', (3,4), (3,4), 'Helvetica-Bold'),
        ('FONTSIZE', (3,4), (3,4), 11),
    ]))
    story.append(r_table)
    story.append(Spacer(1, 0.6*cm))

    story.append(Paragraph("Thank you for settling your penalty and helping keep Indian roadways safe and lawful.", ParagraphStyle('thx', fontSize=9, fontName='Helvetica-Oblique', alignment=TA_CENTER, textColor=colors.HexColor('#555555'))))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(f"Digital Seal of Ministry of Road Transport & Highways · Generated by {APP_NAME}", ParagraphStyle('foot', fontSize=7.5, fontName='Helvetica', alignment=TA_CENTER, textColor=colors.grey)))

    doc.build(story)
    return receipt_filename