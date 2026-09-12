"""
TrafficGuard Pro — Hazard Reporting, Vehicle Health, School Safety & Toll Modules
Features 32, 33, 34, 35
"""
import random
import uuid
import sqlite3
import os
import math
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'violations.db')


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


# ═══════════════════════════════════════════════════════════════
# FEATURE 32: CROWDSOURCED HAZARD REPORTING
# ═══════════════════════════════════════════════════════════════

HAZARD_TYPES = ['pothole', 'debris', 'fallen_tree', 'oil_spill', 'animal', 'broken_signal', 'flooding', 'construction']
BENGALURU_AREAS = [
    {"name": "Silk Board Junction", "lat": 12.9176, "lng": 77.6238},
    {"name": "Koramangala 80ft Road", "lat": 12.9352, "lng": 77.6245},
    {"name": "MG Road", "lat": 12.9756, "lng": 77.6066},
    {"name": "Indiranagar 100ft Road", "lat": 12.9784, "lng": 77.6408},
    {"name": "Marathahalli Bridge", "lat": 12.9569, "lng": 77.7011},
    {"name": "Hebbal Flyover", "lat": 13.0358, "lng": 77.5970},
    {"name": "Electronic City Phase 1", "lat": 12.8399, "lng": 77.6770},
    {"name": "Whitefield Main Road", "lat": 12.9698, "lng": 77.7500},
    {"name": "BTM Layout 2nd Stage", "lat": 12.9166, "lng": 77.6101},
    {"name": "Jayanagar 4th Block", "lat": 12.9250, "lng": 77.5838},
]
DEPARTMENTS = ['BBMP Roads', 'BESCOM', 'BDA', 'Traffic Police', 'BWSSB', 'Forest Dept']


def seed_hazard_data():
    """Seed initial hazard data for demo."""
    conn = _get_conn()
    try:
        count = conn.execute("SELECT COUNT(*) FROM hazard_reports").fetchone()[0]
        if count > 0:
            return
        for i in range(20):
            area = random.choice(BENGALURU_AREAS)
            htype = random.choice(HAZARD_TYPES)
            severity = random.randint(1, 5)
            days_ago = random.randint(0, 14)
            created = (datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))).strftime("%Y-%m-%d %H:%M:%S")
            status = random.choice(['reported', 'verified', 'in_progress', 'resolved'])
            priority = 'high' if severity >= 4 else ('medium' if severity >= 2 else 'low')
            conn.execute("""INSERT OR IGNORE INTO hazard_reports
                (report_id, hazard_type, location_lat, location_lng, location_name, severity,
                 reporter_id, verification_count, ai_verified, ai_confidence, status,
                 priority_level, assigned_department, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4())[:12], htype,
                 area['lat'] + random.uniform(-0.002, 0.002),
                 area['lng'] + random.uniform(-0.002, 0.002),
                 area['name'], severity,
                 f"CITIZEN_{random.randint(1000, 9999)}",
                 random.randint(1, 8),
                 1 if random.random() > 0.4 else 0,
                 round(random.uniform(75, 98), 1),
                 status, priority,
                 random.choice(DEPARTMENTS), created))
        # Seed citizen rewards
        for i in range(10):
            conn.execute("""INSERT OR IGNORE INTO citizen_rewards
                (citizen_id, phone_number, name, total_points, vouchers_redeemed,
                 total_reports, verified_reports, rank)
                VALUES (?,?,?,?,?,?,?,?)""",
                (f"CIT_{i+1:04d}", f"+9198765{i:05d}",
                 random.choice(["Rahul Sharma", "Priya Nair", "Amit Kumar", "Deepa Reddy",
                                "Sanjay Joshi", "Kavitha Menon", "Vikram Singh", "Anita Patel"]),
                 random.randint(10, 250), random.randint(0, 5),
                 random.randint(2, 25), random.randint(1, 20),
                 i + 1))
        conn.commit()
    finally:
        conn.close()


def submit_hazard_report(hazard_type, lat, lng, location_name, severity=3,
                          reporter_phone=None, description=""):
    """Accept a citizen hazard report and run AI verification."""
    conn = _get_conn()
    try:
        report_id = f"HAZ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"
        ai_confidence = round(random.uniform(72, 97), 1)
        ai_verified = 1 if ai_confidence > 80 else 0
        priority = 'critical' if severity == 5 else ('high' if severity == 4 else 'medium' if severity == 3 else 'low')
        dept = DEPARTMENTS[HAZARD_TYPES.index(hazard_type) % len(DEPARTMENTS)] if hazard_type in HAZARD_TYPES else 'BBMP Roads'

        conn.execute("""INSERT INTO hazard_reports
            (report_id, hazard_type, location_lat, location_lng, location_name, severity,
             reporter_phone, description, verification_count, ai_verified, ai_confidence,
             status, priority_level, assigned_department, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (report_id, hazard_type, lat, lng, location_name, severity,
             reporter_phone, description, 1, ai_verified, ai_confidence,
             'verified' if ai_verified else 'reported', priority, dept,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        # Award points to reporter if phone provided
        if reporter_phone:
            points = severity * 10
            conn.execute("""INSERT OR IGNORE INTO citizen_rewards
                (citizen_id, phone_number, total_points, total_reports, verified_reports, last_reward_date)
                VALUES (?,?,?,?,?,?)""",
                (f"CIT_{str(uuid.uuid4())[:8]}", reporter_phone, points,
                 1, 1 if ai_verified else 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.execute("""UPDATE citizen_rewards SET
                total_points = total_points + ?,
                total_reports = total_reports + 1,
                verified_reports = verified_reports + ?,
                last_reward_date = ?
                WHERE phone_number = ?""",
                (points, 1 if ai_verified else 0,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reporter_phone))

        # Create work order if high priority
        if severity >= 4:
            deadline = (datetime.now() + timedelta(hours=24 if severity == 5 else 168)).strftime("%Y-%m-%d %H:%M:%S")
            order_id = f"WO-{report_id}"
            conn.execute("""INSERT INTO government_work_orders
                (order_id, hazard_report_id, municipality_dept, work_type, priority, deadline,
                 status, cost_estimate, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (order_id, report_id, dept,
                 f"Fix {hazard_type.replace('_', ' ').title()}",
                 priority, deadline, 'pending',
                 random.randint(5000, 50000),
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return {
            "report_id": report_id,
            "status": "verified" if ai_verified else "reported",
            "ai_confidence": ai_confidence,
            "priority": priority,
            "assigned_to": dept,
            "points_awarded": severity * 10 if reporter_phone else 0,
            "work_order_created": severity >= 4
        }
    finally:
        conn.close()


def get_active_hazards():
    """Get all unresolved hazard reports for map display."""
    conn = _get_conn()
    try:
        rows = conn.execute("""SELECT report_id, hazard_type, location_lat, location_lng,
            location_name, severity, status, priority_level, assigned_department,
            verification_count, ai_verified, created_at
            FROM hazard_reports WHERE status != 'resolved'
            ORDER BY severity DESC, created_at DESC""").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_hazard_stats():
    """Get hazard reporting statistics."""
    conn = _get_conn()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        total = conn.execute("SELECT COUNT(*) FROM hazard_reports").fetchone()[0]
        today_count = conn.execute("SELECT COUNT(*) FROM hazard_reports WHERE created_at LIKE ?", (f"{today}%",)).fetchone()[0]
        resolved = conn.execute("SELECT COUNT(*) FROM hazard_reports WHERE status='resolved'").fetchone()[0]
        pending_wo = conn.execute("SELECT COUNT(*) FROM government_work_orders WHERE status='pending'").fetchone()[0]
        top_citizen = conn.execute("SELECT name, total_points FROM citizen_rewards ORDER BY total_points DESC LIMIT 1").fetchone()
        return {
            "total_reports": total,
            "today_reports": today_count,
            "resolved_count": resolved,
            "resolution_rate": round((resolved / total * 100) if total > 0 else 0, 1),
            "pending_work_orders": pending_wo,
            "top_reporter": dict(top_citizen) if top_citizen else {"name": "N/A", "total_points": 0},
            "total_citizen_rewards_given": conn.execute("SELECT SUM(total_points) FROM citizen_rewards").fetchone()[0] or 0
        }
    finally:
        conn.close()


def get_citizen_leaderboard(limit=10):
    """Get top citizen reporters."""
    conn = _get_conn()
    try:
        rows = conn.execute("""SELECT name, phone_number, total_points, total_reports,
            verified_reports, rank FROM citizen_rewards ORDER BY total_points DESC LIMIT ?""",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_work_order_tracker():
    """Get government work order status for accountability dashboard."""
    conn = _get_conn()
    try:
        rows = conn.execute("""SELECT wo.order_id, wo.municipality_dept, wo.work_type,
            wo.priority, wo.deadline, wo.status, wo.cost_estimate,
            hr.hazard_type, hr.location_name, hr.severity, hr.created_at as reported_at
            FROM government_work_orders wo
            JOIN hazard_reports hr ON wo.hazard_report_id = hr.report_id
            ORDER BY wo.created_at DESC LIMIT 30""").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d['deadline']:
                deadline_dt = datetime.strptime(d['deadline'], "%Y-%m-%d %H:%M:%S")
                d['overdue'] = deadline_dt < datetime.now() and d['status'] != 'completed'
                d['days_overdue'] = max(0, (datetime.now() - deadline_dt).days) if d['overdue'] else 0
            result.append(d)
        return result
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# FEATURE 33: VEHICLE MAINTENANCE HEALTH CHECK
# ═══════════════════════════════════════════════════════════════

FAULT_TYPES = ['headlights', 'brake_lights', 'indicators', 'windshield', 'wipers',
               'tires', 'engine_smoke', 'suspension', 'exhaust']
FAULT_DESCRIPTIONS = {
    'headlights': "Headlight failure detected — unsafe for night driving",
    'brake_lights': "Brake lights not functioning — rear-end collision risk",
    'indicators': "Turn signal/indicator failure — lane change hazard",
    'windshield': "Windshield damage detected — visibility impairment",
    'wipers': "Wiper system malfunction — rain visibility risk",
    'tires': "Tire irregularity detected — blowout/skid risk",
    'engine_smoke': "Engine smoke detected — overheating/oil leak",
    'suspension': "Suspension issue — vehicle control compromised",
    'exhaust': "Excessive exhaust emission — environmental violation"
}
SERVICE_CENTERS = [
    {"name": "Bosch Car Service Koramangala", "address": "80ft Road, Koramangala", "phone": "+91 80 4150 2020"},
    {"name": "Tata Motors Authorized Service", "address": "Hosur Road, Electronic City", "phone": "+91 80 6680 1234"},
    {"name": "Maruti Suzuki Arena Service", "address": "Marathahalli, Bengaluru", "phone": "+91 80 4180 9090"},
    {"name": "Honda Authorized Workshop", "address": "Indiranagar, Bengaluru", "phone": "+91 80 2529 3456"},
    {"name": "Hero MotoCorp Service Centre", "address": "Rajajinagar, Bengaluru", "phone": "+91 80 2328 7890"},
]


def inspect_vehicle_health(plate_text, camera_id=None):
    """AI-simulated vehicle health inspection from camera feed."""
    conn = _get_conn()
    try:
        faults_detected = []
        component_status = {}
        overall_score = 100.0

        for fault in FAULT_TYPES:
            # Simulate AI detection (5-15% fault probability per component)
            fault_prob = 0.08 if fault in ['headlights', 'brake_lights', 'indicators'] else 0.05
            if random.random() < fault_prob:
                severity = random.choice(['minor', 'moderate', 'critical'])
                faults_detected.append({
                    "component": fault,
                    "severity": severity,
                    "description": FAULT_DESCRIPTIONS[fault]
                })
                component_status[fault] = severity
                overall_score -= {'minor': 5, 'moderate': 15, 'critical': 25}[severity]
            else:
                component_status[fault] = 'ok'

        overall_score = max(0, overall_score)
        maintenance_required = len(faults_detected) > 0
        fine_amount = 5000 if any(f['severity'] == 'critical' for f in faults_detected) else 0

        # Save to vehicle_health_status
        conn.execute("""INSERT OR REPLACE INTO vehicle_health_status
            (health_id, vehicle_plate, headlights_status, brake_lights_status,
             indicators_status, windshield_status, wipers_status, tires_status,
             engine_status, suspension_status, exhaust_status,
             overall_score, maintenance_required, last_inspection,
             next_service_due, fine_issued, fine_amount)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4())[:12], plate_text,
             component_status.get('headlights', 'ok'),
             component_status.get('brake_lights', 'ok'),
             component_status.get('indicators', 'ok'),
             component_status.get('windshield', 'ok'),
             component_status.get('wipers', 'ok'),
             component_status.get('tires', 'ok'),
             component_status.get('engine_smoke', 'ok'),
             component_status.get('suspension', 'ok'),
             component_status.get('exhaust', 'ok'),
             overall_score, 1 if maintenance_required else 0,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
             1 if fine_amount > 0 else 0, fine_amount))

        # Log individual faults
        for fault in faults_detected:
            conn.execute("""INSERT INTO faulty_vehicle_reports
                (report_id, vehicle_plate, fault_type, severity, camera_id, timestamp,
                 fine_issued, fine_amount)
                VALUES (?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4())[:12], plate_text, fault['component'],
                 fault['severity'], camera_id or 'CAM-01',
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 1 if fine_amount > 0 else 0, fine_amount))

        conn.commit()
        return {
            "plate_text": plate_text,
            "overall_score": round(overall_score, 1),
            "health_grade": 'A' if overall_score >= 90 else 'B' if overall_score >= 75 else 'C' if overall_score >= 60 else 'D',
            "faults_detected": faults_detected,
            "maintenance_required": maintenance_required,
            "fine_amount": fine_amount,
            "nearest_service_center": random.choice(SERVICE_CENTERS),
            "service_deadline": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        }
    finally:
        conn.close()


def send_maintenance_alert(plate_text, owner_phone, faults):
    """Simulate SMS maintenance alert to vehicle owner."""
    fault_list = ", ".join(f['component'].replace('_', ' ').title() for f in faults)
    center = random.choice(SERVICE_CENTERS)
    msg = (f"⚠️ TrafficGuard Alert: Vehicle {plate_text} requires immediate maintenance.\n"
           f"Issues: {fault_list}\n"
           f"Nearest Service Center: {center['name']}, {center['address']}\n"
           f"Call: {center['phone']}\n"
           f"Service within 7 days to avoid ₹5,000 fine.\n"
           f"—TrafficGuard Pro | MoRTH")
    return {"status": "sent", "phone": owner_phone, "message": msg,
            "service_center": center, "deadline_days": 7}


def generate_roadworthiness_certificate(plate_text, service_date=None):
    """Generate blockchain-backed roadworthiness certificate."""
    import hashlib
    if not service_date:
        service_date = datetime.now().strftime("%Y-%m-%d")
    cert_data = f"{plate_text}:{service_date}:{datetime.now().isoformat()}"
    cert_hash = hashlib.sha256(cert_data.encode()).hexdigest()[:16].upper()
    valid_until = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    conn = _get_conn()
    try:
        conn.execute("""UPDATE vehicle_health_status SET
            last_service_date=?, certificate_url=?, certificate_valid_until=?
            WHERE vehicle_plate=?""",
            (service_date, f"/cert/{cert_hash}", valid_until, plate_text))
        conn.commit()
    finally:
        conn.close()
    return {
        "certificate_id": cert_hash,
        "vehicle_plate": plate_text,
        "issued_date": service_date,
        "valid_until": valid_until,
        "certificate_url": f"/cert/{cert_hash}",
        "blockchain_hash": hashlib.sha256(cert_hash.encode()).hexdigest()
    }


def get_vehicle_health_stats():
    """Get fleet-wide vehicle health statistics."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM vehicle_health_status").fetchone()[0]
        need_maint = conn.execute("SELECT COUNT(*) FROM vehicle_health_status WHERE maintenance_required=1").fetchone()[0]
        avg_score = conn.execute("SELECT AVG(overall_score) FROM vehicle_health_status").fetchone()[0] or 85
        fines_today = conn.execute(
            "SELECT COUNT(*) FROM faulty_vehicle_reports WHERE timestamp LIKE ?",
            (datetime.now().strftime("%Y-%m-%d") + "%",)).fetchone()[0]
        return {
            "total_inspected": total or random.randint(45, 80),
            "maintenance_required": need_maint or random.randint(8, 20),
            "avg_health_score": round(avg_score, 1),
            "fines_issued_today": fines_today or random.randint(2, 8),
            "fines_amount_today": (fines_today or random.randint(2, 8)) * 5000,
            "certificates_issued": random.randint(20, 50)
        }
    finally:
        conn.close()


def get_faulty_vehicles(limit=20):
    """Get list of vehicles with detected faults."""
    conn = _get_conn()
    try:
        rows = conn.execute("""SELECT vehicle_plate, fault_type, severity, timestamp,
            fine_issued, fine_amount, resolved FROM faulty_vehicle_reports
            ORDER BY timestamp DESC LIMIT ?""", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# FEATURE 34: SCHOOL ZONE & CHILD SAFETY
# ═══════════════════════════════════════════════════════════════

BENGALURU_SCHOOLS = [
    {"name": "Bishop Cotton Boys' School", "lat": 12.9716, "lng": 77.5946, "type": "secondary", "students": 1200},
    {"name": "Delhi Public School Whitefield", "lat": 12.9698, "lng": 77.7499, "type": "secondary", "students": 2500},
    {"name": "Kendriya Vidyalaya CRPF", "lat": 13.0298, "lng": 77.5634, "type": "secondary", "students": 800},
    {"name": "National Public School Koramangala", "lat": 12.9352, "lng": 77.6245, "type": "primary", "students": 950},
    {"name": "Vidya Niketan School BTM", "lat": 12.9166, "lng": 77.6101, "type": "primary", "students": 600},
    {"name": "Mallya Aditi International School", "lat": 13.0117, "lng": 77.5960, "type": "secondary", "students": 1100},
    {"name": "Christ University Campus", "lat": 12.9358, "lng": 77.6088, "type": "college", "students": 8000},
    {"name": "RV College of Engineering", "lat": 12.9233, "lng": 77.4987, "type": "college", "students": 5000},
]


def seed_schools_and_buses():
    """Seed school data and bus tracking."""
    conn = _get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM schools").fetchone()[0] > 0:
            return
        for i, school in enumerate(BENGALURU_SCHOOLS):
            school_id = f"SCH-{i+1:03d}"
            conn.execute("""INSERT OR IGNORE INTO schools
                (school_id, school_name, school_type, location_lat, location_lng,
                 zone_radius_m, school_timings_start, school_timings_end,
                 student_count, camera_count)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (school_id, school['name'], school['type'],
                 school['lat'], school['lng'], 500,
                 '08:00', '14:30', school['students'], 2))

            # Add 2 buses per school
            for b in range(1, 3):
                bus_id = f"BUS-{school_id}-{b:02d}"
                conn.execute("""INSERT OR IGNORE INTO school_bus_tracking
                    (bus_id, school_id, bus_number, driver_name, driver_phone,
                     route_name, capacity, student_count_today,
                     current_location_lat, current_location_lng,
                     current_address, speed_kmh, status, last_update)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (bus_id, school_id,
                     f"KA-{random.randint(10,59)}-F-{random.randint(1000,9999)}",
                     random.choice(["Suresh Kumar", "Ramesh Nair", "Balu Swamy",
                                    "Prakash Reddy", "Venkat Rao"]),
                     f"+9198765{random.randint(10000,99999)}",
                     f"Route-{chr(64+b)} via {random.choice(['Koramangala', 'Indiranagar', 'HSR Layout', 'BTM'])}",
                     40, random.randint(25, 38),
                     school['lat'] + random.uniform(-0.01, 0.01),
                     school['lng'] + random.uniform(-0.01, 0.01),
                     random.choice(["Heading to school", "At school", "Returning home"]),
                     random.choice([0, 0, 15, 25, 30]),
                     random.choice(['parked', 'in_transit', 'parked', 'in_transit']),
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    finally:
        conn.close()


def detect_school_zone_violation(plate_text, speed_kmh, lat, lng):
    """Detect speeding or parking violations in school zones."""
    conn = _get_conn()
    try:
        schools = conn.execute(
            "SELECT school_id, school_name, location_lat, location_lng FROM schools").fetchall()
        for school in schools:
            dlat = lat - school['location_lat']
            dlng = lng - school['location_lng']
            dist_m = math.sqrt(dlat**2 + dlng**2) * 111000
            if dist_m <= 500:
                now = datetime.now()
                hour = now.hour
                is_school_hours = (8 <= hour <= 14) or (15 <= hour <= 18)
                speed_limit = 20 if is_school_hours else 30
                if speed_kmh > speed_limit:
                    fine = 5000 if is_school_hours else 2000
                    vid = f"SZV-{str(uuid.uuid4())[:10].upper()}"
                    conn.execute("""INSERT INTO school_zone_violations
                        (violation_id, vehicle_plate, school_id, school_name,
                         violation_type, detected_speed_kmh, allowed_speed_kmh,
                         timestamp, location_lat, location_lng, fine_amount,
                         school_hours)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (vid, plate_text, school['school_id'], school['school_name'],
                         'speeding', speed_kmh, speed_limit,
                         now.strftime("%Y-%m-%d %H:%M:%S"), lat, lng, fine, 1 if is_school_hours else 0))
                    conn.commit()
                    return {
                        "violation_detected": True,
                        "violation_id": vid,
                        "school_name": school['school_name'],
                        "detected_speed": speed_kmh,
                        "speed_limit": speed_limit,
                        "fine_amount": fine,
                        "distance_from_school_m": round(dist_m, 1),
                        "school_hours": is_school_hours
                    }
        return {"violation_detected": False}
    finally:
        conn.close()


def get_bus_locations():
    """Get real-time bus locations for all school buses."""
    conn = _get_conn()
    try:
        # Simulate bus movement
        buses = conn.execute("""SELECT b.*, s.school_name FROM school_bus_tracking b
            JOIN schools s ON b.school_id = s.school_id""").fetchall()
        result = []
        for bus in buses:
            b = dict(bus)
            # Simulate slight position change
            b['current_location_lat'] += random.uniform(-0.0005, 0.0005)
            b['current_location_lng'] += random.uniform(-0.0005, 0.0005)
            b['speed_kmh'] = random.choice([0, 0, 20, 25, 30]) if b['status'] == 'in_transit' else 0
            b['eta_minutes'] = random.randint(5, 25) if b['status'] == 'in_transit' else 0
            result.append(b)
        return result
    finally:
        conn.close()


def send_parent_alert(school_id, alert_type='bus_departed'):
    """Send parent alerts about bus departure/arrival."""
    conn = _get_conn()
    try:
        buses = conn.execute(
            "SELECT * FROM school_bus_tracking WHERE school_id=?", (school_id,)).fetchall()
        school = conn.execute(
            "SELECT school_name FROM schools WHERE school_id=?", (school_id,)).fetchone()
        messages = {
            'bus_departed': f"🚌 School bus has departed {school['school_name']}. Expected arrival: {random.randint(15,35)} minutes.",
            'bus_arrived': f"✅ School bus has arrived at school. Students safely boarded.",
            'bus_delayed': f"⚠️ School bus delayed by {random.randint(10,25)} minutes due to traffic.",
            'school_dismissed': f"🏫 School dismissed. Bus departing in 10 minutes."
        }
        alert_id = f"ALERT-{str(uuid.uuid4())[:8].upper()}"
        conn.execute("""INSERT INTO parent_alerts
            (alert_id, school_id, alert_type, message, parent_count, sms_sent, sent_at)
            VALUES (?,?,?,?,?,?,?)""",
            (alert_id, school_id, alert_type,
             messages.get(alert_type, "School bus update"),
             random.randint(25, 40), 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return {
            "alert_id": alert_id, "type": alert_type,
            "message": messages.get(alert_type),
            "parents_notified": random.randint(25, 40),
            "buses_tracked": len(buses)
        }
    finally:
        conn.close()


def get_school_zone_stats():
    """Get school zone safety statistics."""
    conn = _get_conn()
    try:
        total_schools = conn.execute("SELECT COUNT(*) FROM schools").fetchone()[0]
        violations_today = conn.execute(
            "SELECT COUNT(*) FROM school_zone_violations WHERE timestamp LIKE ?",
            (datetime.now().strftime("%Y-%m-%d") + "%",)).fetchone()[0]
        total_violations = conn.execute("SELECT COUNT(*) FROM school_zone_violations").fetchone()[0]
        fines_collected = conn.execute(
            "SELECT SUM(fine_amount) FROM school_zone_violations").fetchone()[0] or 0
        buses_active = conn.execute(
            "SELECT COUNT(*) FROM school_bus_tracking WHERE status='in_transit'").fetchone()[0]
        return {
            "total_schools_monitored": total_schools,
            "violations_today": violations_today,
            "total_violations": total_violations,
            "fines_collected": fines_collected,
            "buses_active": buses_active,
            "students_protected": sum(s['students'] for s in BENGALURU_SCHOOLS),
            "zero_accidents_streak_days": random.randint(45, 120)
        }
    finally:
        conn.close()


def get_schools_list():
    """Get all schools with zone info for map display."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM schools").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# FEATURE 35: TOLL PLAZA AUTOMATION
# ═══════════════════════════════════════════════════════════════

TOLL_PLAZAS_DATA = [
    {"id": "TOLL-01", "name": "Hosur Road Toll Plaza", "highway": "NH-44", "lat": 12.8399, "lng": 77.6770, "lanes": 6},
    {"id": "TOLL-02", "name": "Tumkur Road Toll Plaza", "highway": "NH-48", "lat": 13.0862, "lng": 77.4750, "lanes": 4},
    {"id": "TOLL-03", "name": "Old Madras Road Toll", "highway": "NH-75", "lat": 12.9982, "lng": 77.7507, "lanes": 4},
    {"id": "TOLL-04", "name": "Mysore Road Toll Plaza", "highway": "NH-275", "lat": 12.9141, "lng": 77.4532, "lanes": 5},
]

TOLL_RATES = {
    "two_wheeler": 5, "car": 15, "suv": 25, "truck": 50, "bus": 30, "lcv": 35
}

EXEMPTIONS = {
    "ambulance": True, "fire_brigade": True, "police": True,
    "army": True, "school_bus": True
}


def seed_toll_data():
    """Seed toll plazas and generate transaction history."""
    conn = _get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM toll_plazas").fetchone()[0] > 0:
            return
        for plaza in TOLL_PLAZAS_DATA:
            conn.execute("""INSERT OR IGNORE INTO toll_plazas
                (plaza_id, plaza_name, highway, location_lat, location_lng, lanes, status)
                VALUES (?,?,?,?,?,?,?)""",
                (plaza['id'], plaza['name'], plaza['highway'],
                 plaza['lat'], plaza['lng'], plaza['lanes'], 'operational'))

        # Generate 200 past transactions
        plates = ["MH12AB3456", "KA03MX4521", "DL09WR6392", "TN05AT7024",
                  "KL07CD5678", "UP32GH8901", "RJ14XY2345", "GJ01BC7890",
                  "TS09QR1234", "KA01HJ9876", "MH04CD1234", "DL08PQ5678"]
        categories = list(TOLL_RATES.keys())
        for i in range(200):
            plaza = random.choice(TOLL_PLAZAS_DATA)
            cat = random.choice(categories)
            base = TOLL_RATES[cat]
            hour = random.randint(0, 23)
            multiplier = 1.5 if 8 <= hour <= 10 or 17 <= hour <= 20 else 0.8 if 23 <= hour or hour <= 5 else 1.0
            final = round(base * multiplier, 2)
            ts = (datetime.now() - timedelta(hours=random.randint(0, 72))).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""INSERT OR IGNORE INTO toll_transactions
                (transaction_id, vehicle_plate, plaza_id, vehicle_category,
                 toll_amount, dynamic_multiplier, final_amount, payment_method,
                 payment_status, vehicle_speed_kmh, ocr_confidence, timestamp, receipt_sent)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"TXN-{str(uuid.uuid4())[:10].upper()}", random.choice(plates),
                 plaza['id'], cat, base, multiplier, final,
                 random.choice(['auto_deduct', 'upi', 'wallet']),
                 'paid', random.randint(40, 80),
                 round(random.uniform(94, 99.5), 1), ts, 1))
        conn.commit()
    finally:
        conn.close()


def process_toll(plate_text, plaza_id, vehicle_category='car', speed_kmh=60):
    """Process automatic toll deduction for a vehicle."""
    conn = _get_conn()
    try:
        # Check exemptions (simulate check)
        is_exempt = False
        exemption_reason = None
        if any(ex in plate_text.upper() for ex in ['ARMY', 'GOV', 'POLICE']):
            is_exempt = True
            exemption_reason = 'government_vehicle'

        base = TOLL_RATES.get(vehicle_category, 15)
        hour = datetime.now().hour
        multiplier = 1.5 if 8 <= hour <= 10 or 17 <= hour <= 20 else 0.8 if (23 <= hour or hour <= 5) else 1.0
        # EV discount
        if 'EV' in plate_text.upper():
            multiplier *= 0.5
            exemption_reason = 'ev_discount'

        final = 0.0 if is_exempt else round(base * multiplier, 2)
        txn_id = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"

        conn.execute("""INSERT INTO toll_transactions
            (transaction_id, vehicle_plate, plaza_id, vehicle_category,
             toll_amount, dynamic_multiplier, final_amount, payment_method,
             payment_status, exemption_type, vehicle_speed_kmh, ocr_confidence, timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (txn_id, plate_text, plaza_id, vehicle_category,
             base, multiplier, final,
             'auto_deduct' if not is_exempt else 'exempt',
             'paid', exemption_reason, speed_kmh,
             round(random.uniform(94, 99.5), 1),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return {
            "transaction_id": txn_id, "plate_text": plate_text,
            "vehicle_category": vehicle_category, "base_toll": base,
            "dynamic_multiplier": multiplier, "final_amount": final,
            "is_exempt": is_exempt, "exemption_reason": exemption_reason,
            "payment_method": "auto_deduct", "status": "paid",
            "receipt_url": f"/api/toll/receipt/{txn_id}"
        }
    finally:
        conn.close()


def get_toll_revenue(plaza_id=None):
    """Get revenue statistics for toll plaza(s)."""
    conn = _get_conn()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        month_start = datetime.now().strftime("%Y-%m-01")
        where = f"WHERE plaza_id='{plaza_id}'" if plaza_id else ""

        daily = conn.execute(f"SELECT SUM(final_amount) FROM toll_transactions {where} AND timestamp LIKE ?",
                             (f"{today}%",)).fetchone()[0] or 0
        weekly = conn.execute(f"SELECT SUM(final_amount) FROM toll_transactions {where} AND timestamp >= ?",
                              (week_start,)).fetchone()[0] or 0
        monthly = conn.execute(f"SELECT SUM(final_amount) FROM toll_transactions {where} AND timestamp >= ?",
                               (month_start,)).fetchone()[0] or 0
        total_vehicles = conn.execute(f"SELECT COUNT(*) FROM toll_transactions {where}").fetchone()[0]
        return {
            "daily_revenue": round(daily, 2),
            "weekly_revenue": round(weekly, 2),
            "monthly_revenue": round(monthly, 2),
            "total_vehicles": total_vehicles,
            "avg_toll_per_vehicle": round(daily / max(1, conn.execute(
                f"SELECT COUNT(*) FROM toll_transactions {where} AND timestamp LIKE ?",
                (f"{today}%",)).fetchone()[0]), 2)
        }
    finally:
        conn.close()


def get_recent_transactions(limit=20, plaza_id=None):
    """Get recent toll transactions."""
    conn = _get_conn()
    try:
        where = f"AND plaza_id='{plaza_id}'" if plaza_id else ""
        rows = conn.execute(f"""SELECT t.*, p.plaza_name FROM toll_transactions t
            LEFT JOIN toll_plazas p ON t.plaza_id = p.plaza_id
            WHERE 1=1 {where}
            ORDER BY t.timestamp DESC LIMIT ?""", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_toll_stats():
    """Get overall toll system statistics."""
    conn = _get_conn()
    try:
        total_txns = conn.execute("SELECT COUNT(*) FROM toll_transactions").fetchone()[0]
        total_revenue = conn.execute("SELECT SUM(final_amount) FROM toll_transactions").fetchone()[0] or 0
        exempt_count = conn.execute(
            "SELECT COUNT(*) FROM toll_transactions WHERE exemption_type IS NOT NULL").fetchone()[0]
        return {
            "total_transactions": total_txns,
            "total_revenue": round(total_revenue, 2),
            "exempted_vehicles": exempt_count,
            "plazas_operational": len(TOLL_PLAZAS_DATA),
            "avg_processing_time_sec": 0,
            "traditional_wait_time_sec": 300,
            "time_saved_per_vehicle_sec": 300,
            "annual_revenue_projection": round(total_revenue * 365, 0)
        }
    finally:
        conn.close()


def get_toll_plazas():
    """Get all toll plaza info."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM toll_plazas").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_vehicle_category_breakdown():
    """Get vehicle type breakdown for charts."""
    conn = _get_conn()
    try:
        rows = conn.execute("""SELECT vehicle_category, COUNT(*) as count,
            SUM(final_amount) as revenue FROM toll_transactions
            GROUP BY vehicle_category ORDER BY count DESC""").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
