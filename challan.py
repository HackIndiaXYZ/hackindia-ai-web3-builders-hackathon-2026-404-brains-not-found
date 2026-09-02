import os
import qrcode
import sqlite3
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, Image as RLImage)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── FINE SCHEDULE (Motor Vehicles Act 1988, amended 2019) ──
BASE_FINES = {
    "NO HELMET":     1000,
    "TRIPLE RIDING": 1000,
    "WRONG WAY":     5000,
    "OVERSPEEDING":  2000,
}

SEVERITY_MULTIPLIER = {
    1: 1.0,   # 1st offence
    2: 2.0,   # 2nd offence
    3: 3.0,   # 3rd+ offence (habitual offender)
}

PAYMENT_BASE_URL = "https://parivahan.gov.in/challan/"


def get_offence_count(db_path, plate):
    """Count previous violations for this plate."""
    if not plate or plate == "UNKNOWN":
        return 0
    try:
        conn = sqlite3.connect(db_path)
        c    = conn.cursor()
        c.execute("SELECT COUNT(*) FROM violations WHERE plate=?", (plate,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def calculate_fine(violations_list, offence_count):
    """Calculate total fine with severity multiplier."""
    base   = sum(BASE_FINES.get(v.strip(), 500) for v in violations_list)
    mult   = SEVERITY_MULTIPLIER.get(min(offence_count, 3), 3.0)
    total  = int(base * mult)
    return base, mult, total


def generate_qr(challan_id, amount):
    """Generate QR code for payment."""
    url = f"{PAYMENT_BASE_URL}RX{challan_id:06d}?amount={amount}"
    qr  = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img     = qr.make_image(fill_color="black", back_color="white")
    tmp     = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(tmp.name)
    return tmp.name, url


def generate_challan(challan_dir, screenshot_dir,
                     violation_id, timestamp, video,
                     violation_str, plate, screenshot_filename,
                       db_path, owner_name="Not Available",
                     offence_count=None):

    challan_filename = f"challan_RX{violation_id:06d}.pdf"
    challan_path     = os.path.join(challan_dir, challan_filename)

    violations_list = [v.strip() for v in violation_str.split("+")]
    # Use caller-supplied count when available — avoids counting the already-inserted
    # row and inflating the offence number by 1.
    if offence_count is None:
        offence_count = get_offence_count(db_path, plate)
    base_fine, multiplier, total_fine = calculate_fine(violations_list, offence_count)

    is_repeat   = offence_count > 1
    severity    = "HABITUAL OFFENDER" if offence_count >= 3 else ("REPEAT OFFENDER" if is_repeat else "FIRST OFFENCE")
    sev_color   = colors.HexColor('#c0392b') if offence_count >= 3 else (
                  colors.HexColor('#e67e22') if is_repeat else colors.HexColor('#27ae60'))

    qr_path, payment_url = generate_qr(violation_id, total_fine)

    doc    = SimpleDocTemplate(challan_path, pagesize=A4,
                                rightMargin=1.8*cm, leftMargin=1.8*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)

    # ── STYLES ──────────────────────────────────────────
    title_style  = ParagraphStyle('title',  fontSize=18, fontName='Helvetica-Bold',
                                  alignment=TA_CENTER, textColor=colors.HexColor('#c0392b'),
                                  spaceAfter=8, spaceBefore=4)
    sub_style    = ParagraphStyle('sub',    fontSize=9,  fontName='Helvetica',
                                  alignment=TA_CENTER, textColor=colors.HexColor('#666666'),
                                  spaceAfter=3, leading=14)
    section_style= ParagraphStyle('section',fontSize=11, fontName='Helvetica-Bold',
                                  textColor=colors.HexColor('#2c3e50'), spaceBefore=10, spaceAfter=4)
    foot_style   = ParagraphStyle('foot',   fontSize=7.5,fontName='Helvetica',
                                  alignment=TA_CENTER, textColor=colors.grey)

    story = []

    # ── HEADER ──────────────────────────────────────────
    story.append(Paragraph("TRAFFIC VIOLATION CHALLAN", title_style))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph("TrafficGuard Pro Automated Enforcement System  |  Powered by AI Vision", sub_style))
    story.append(Paragraph("Under Motor Vehicles Act, 1988 (Amended 2019)", sub_style))
    story.append(Spacer(1, 0.35*cm))

    # Challan number + severity bar
    sev_text = f"CHALLAN NO: RX-{violation_id:06d}   |   {severity}   |   OFFENCE #{offence_count}"
    sev_data  = [[Paragraph(sev_text, ParagraphStyle('sev', fontSize=10,
                            fontName='Helvetica-Bold', textColor=colors.white,
                            alignment=TA_CENTER))]]
    sev_table = Table(sev_data, colWidths=[17.4*cm])
    sev_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), sev_color),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(sev_table)
    story.append(Spacer(1, 0.4*cm))

    # ── VEHICLE & OWNER DETAILS ──────────────────────────
    story.append(Paragraph("Vehicle & Owner Information", section_style))
    owner_data = [
        ["License Plate",  plate if plate != "UNKNOWN" else "Not Detected",
         "Owner Name",     owner_name],
        ["Date & Time",    timestamp,
         "Video Source",   video[:35] + "..." if len(video) > 35 else video],
        ["Previous Offences", str(offence_count - 1),
         "Offender Status", severity],
    ]
    owner_table = Table(owner_data, colWidths=[4*cm, 4.7*cm, 4*cm, 4.7*cm])
    owner_table.setStyle(TableStyle([
        ('FONTNAME',      (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',      (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#dfe6e9')),
        ('BACKGROUND',    (0,0), (0,-1), colors.HexColor('#f0f4f8')),
        ('BACKGROUND',    (2,0), (2,-1), colors.HexColor('#f0f4f8')),
        ('ROWBACKGROUNDS',(0,0), (-1,-1), [colors.white, colors.HexColor('#fafafa')]),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        # Highlight repeat offender
        ('TEXTCOLOR',     (1,2), (1,2), sev_color),
        ('FONTNAME',      (1,2), (1,2), 'Helvetica-Bold'),
        ('TEXTCOLOR',     (3,2), (3,2), sev_color),
        ('FONTNAME',      (3,2), (3,2), 'Helvetica-Bold'),
    ]))
    story.append(owner_table)
    story.append(Spacer(1, 0.3*cm))

    # ── VIOLATION & FINE BREAKDOWN ───────────────────────
    story.append(Paragraph("Violation Details & Fine Breakdown", section_style))
    fine_rows = [["#", "Violation", "Section", "Base Fine"]]
    sections  = {
        "NO HELMET":     "Sec 129 MV Act",
        "TRIPLE RIDING": "Sec 128 MV Act",
        "WRONG WAY":     "Sec 184 MV Act",
        "OVERSPEEDING":  "Sec 183 MV Act",
    }
    for i, v in enumerate(violations_list, 1):
        fine_rows.append([
            str(i),
            v.strip(),
            sections.get(v.strip(), "MV Act 1988"),
            f"Rs. {BASE_FINES.get(v.strip(), 500):,}"
        ])
    fine_rows.append(["", "Base Total",  "", f"Rs. {base_fine:,}"])
    fine_rows.append(["", f"Severity Multiplier ({multiplier}x — Offence #{offence_count})", "", ""])
    fine_rows.append(["", "TOTAL PAYABLE", "", f"Rs. {total_fine:,}"])

    fine_table = Table(fine_rows, colWidths=[1*cm, 7*cm, 5*cm, 4.4*cm])
    fine_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor('#2c3e50')),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('GRID',          (0,0), (-1,-2), 0.5, colors.HexColor('#dfe6e9')),
        ('ROWBACKGROUNDS',(0,1), (-1,-4), [colors.white, colors.HexColor('#fafafa')]),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        # Base total row
        ('BACKGROUND',    (0,-3), (-1,-3), colors.HexColor('#eaf0fb')),
        ('FONTNAME',      (0,-3), (-1,-3), 'Helvetica-Bold'),
        # Multiplier row
        ('BACKGROUND',    (0,-2), (-1,-2), colors.HexColor('#fff3cd')),
        ('TEXTCOLOR',     (0,-2), (-1,-2), colors.HexColor('#856404')),
        # Total row
        ('BACKGROUND',    (0,-1), (-1,-1), colors.HexColor('#c0392b')),
        ('TEXTCOLOR',     (0,-1), (-1,-1), colors.white),
        ('FONTNAME',      (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,-1), (-1,-1), 11),
    ]))
    story.append(fine_table)
    story.append(Spacer(1, 0.4*cm))

    # ── EVIDENCE + QR CODE (side by side) ───────────────
    story.append(Paragraph("Evidence & Payment", section_style))

    ss_path = os.path.join(screenshot_dir, screenshot_filename) if screenshot_filename else None
    row_content = []

    if ss_path and os.path.exists(ss_path):
        ev_img = RLImage(ss_path, width=10.5*cm, height=6*cm)
        row_content.append(ev_img)
    else:
        row_content.append(Paragraph("No screenshot", ParagraphStyle('ns', fontSize=9)))

    qr_img = RLImage(qr_path, width=4.5*cm, height=4.5*cm)
    pay_txt = Paragraph(
        f"<b>Scan to Pay Online</b><br/><br/>"
        f"Amount: <b>Rs. {total_fine:,}</b><br/><br/>"
        f"Ref: RX-{violation_id:06d}<br/><br/>"
        f"Due: 60 days<br/><br/>"
        f"<font size='7'>{payment_url[:40]}</font>",
        ParagraphStyle('pay', fontSize=9, fontName='Helvetica',
                       alignment=TA_CENTER, leading=14)
    )
    qr_block = Table([[qr_img], [pay_txt]], colWidths=[5.9*cm])
    qr_block.setStyle(TableStyle([
        ('ALIGN',   (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',  (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),
    ]))
    row_content.append(qr_block)

    ev_row = Table([row_content], colWidths=[11*cm, 6.4*cm])
    ev_row.setStyle(TableStyle([
        ('VALIGN',  (0,0), (-1,-1), 'TOP'),
        ('GRID',    (0,0), (-1,-1), 0.5, colors.HexColor('#dfe6e9')),
        ('TOPPADDING',   (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 6),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
    ]))
    story.append(ev_row)
    story.append(Spacer(1, 0.3*cm))

    # ── PAYMENT INSTRUCTIONS ─────────────────────────────
    pay_data = [
        [Paragraph("<b>PAYMENT INSTRUCTIONS</b>", ParagraphStyle('pi', fontSize=10,
                   fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER))],
        [Paragraph(
            "1. Pay online at <b>parivahan.gov.in</b> using the QR code above or Challan Reference Number<br/>"
            "2. Pay at any <b>Traffic Police Counter</b> or <b>e-Seva Kendra</b><br/>"
            "3. Non-payment within 60 days will result in <b>court summons</b> and additional penalties<br/>"
            "4. For disputes: <b>1800-XXX-XXXX</b> (Toll Free) | trafficguard@traffic.gov.in",
            ParagraphStyle('pitext', fontSize=8.5, fontName='Helvetica', leading=14)
        )],
    ]
    pay_table = Table(pay_data, colWidths=[17.4*cm])
    pay_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), colors.HexColor('#27ae60')),
        ('BACKGROUND',    (0,1), (-1,1), colors.HexColor('#eafaf1')),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#a9dfbf')),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
    ]))
    story.append(pay_table)
    story.append(Spacer(1, 0.2*cm))

    # ── FOOTER ───────────────────────────────────────────
    story.append(Paragraph(
        f"This is a computer-generated challan issued by TrafficGuard Pro Automated Enforcement System. "
        f"Generated on {datetime.now().strftime('%d %b %Y at %H:%M:%S')}  |  "
        f"Challan ID: RX-{violation_id:06d}",
        foot_style
    ))

    doc.build(story)

    # Clean up QR temp file
    try: os.unlink(qr_path)
    except: pass

    return challan_filename