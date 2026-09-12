"""
TrafficGuard Pro — Emission, Drunk Driving, Parking, Driver Risk,
Pedestrian, Accident Prediction, V2I, Insurance, EV Charging Modules
Features 23-31 — All in one consolidated module for reliability
"""
import random, uuid, sqlite3, os, math, hashlib
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'violations.db')

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

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

CAMERAS = ["CAM-01","CAM-02","CAM-03","CAM-04","CAM-05","CAM-06","CAM-07","CAM-08","CAM-09","CAM-10"]
INDIAN_PLATES = [
    "KA03MX4521","MH12AB3456","DL09WR6392","TN05AT7024","KL07CD5678",
    "UP32GH8901","RJ14XY2345","GJ01BC7890","TS09QR1234","KA01HJ9876",
    "MH04CD1234","DL08PQ5678","KL09CA1671","MH14GE9533","KL5ER9012",
    "KL11AB1234","HB08H8993","GJ18BQ2145","AP29BQ7821","HR26DQ9034"
]

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 23 — EMISSION & AIR QUALITY MONITORING
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_vehicle_emission(plate_text, vehicle_type='motorcycle', camera_id=None):
    """Simulate AI smoke color detection and emission analysis."""
    if not camera_id:
        camera_id = random.choice(CAMERAS)
    smoke_colors = ['clear', 'clear', 'clear', 'black', 'white', 'blue']
    smoke = random.choices(smoke_colors, weights=[55, 15, 10, 10, 6, 4])[0]
    emission_level = {'clear': random.uniform(5,25), 'black': random.uniform(70,95),
                      'white': random.uniform(45,70), 'blue': random.uniform(55,80)}.get(smoke, 15)
    pm25 = round(emission_level * 0.8 + random.uniform(-5, 5), 1)
    co2 = round(emission_level * 2.1 + random.uniform(-10, 10), 1)
    nox = round(emission_level * 0.15 + random.uniform(-2, 2), 2)
    fine = 0
    if smoke == 'black' and emission_level > 65:
        fine = 5000
    elif smoke in ['white', 'blue'] and emission_level > 55:
        fine = 3000
    compliant = 1 if smoke == 'clear' else 0
    area = random.choice(BENGALURU_AREAS)
    reading_id = f"EM-{str(uuid.uuid4())[:10].upper()}"
    conn = _get_conn()
    try:
        conn.execute("""INSERT OR IGNORE INTO emission_data
            (reading_id, vehicle_plate, emission_level, smoke_color, pm25_level,
             co2_level, nox_level, vehicle_type, bs_standard, compliant,
             timestamp, location_lat, location_lng, camera_id, fine_issued, fine_amount)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (reading_id, plate_text, round(emission_level,1), smoke, pm25, co2, nox,
             vehicle_type, 'BS-VI' if compliant else 'PRE-BS-VI', compliant,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             area['lat'], area['lng'], camera_id, 1 if fine > 0 else 0, fine))
        conn.execute("""INSERT OR REPLACE INTO vehicle_emission_score
            (plate_text, avg_emission_score, total_readings, maintenance_status, bs_standard)
            VALUES (?,?,1,?,?)""",
            (plate_text, round(emission_level,1),
             'urgent' if smoke == 'black' else 'good' if smoke == 'clear' else 'required',
             'BS-VI' if compliant else 'PRE-BS-VI'))
        conn.commit()
    finally:
        conn.close()
    return {
        "reading_id": reading_id, "plate_text": plate_text,
        "smoke_color": smoke, "emission_level": round(emission_level, 1),
        "pm25_level": pm25, "co2_level": co2, "nox_level": nox,
        "bs_vi_compliant": bool(compliant), "fine_amount": fine,
        "maintenance_urgency": 'immediate' if smoke == 'black' else 'within_7_days' if smoke in ['white','blue'] else 'none',
        "aqi_contribution": round(pm25 * 1.2, 1)
    }

def get_pollution_hotspots():
    """Return top pollution hotspot data."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM pollution_hotspots ORDER BY avg_emission_level DESC LIMIT 5").fetchall()
        if rows:
            return [dict(r) for r in rows]
    finally:
        conn.close()
    return [
        {"hotspot_id": f"PH-{i+1:03d}", "area_name": a['name'],
         "latitude": a['lat'], "longitude": a['lng'],
         "avg_emission_level": round(random.uniform(55,85),1),
         "peak_hour": random.choice([8,9,18,19]),
         "aqi_index": round(random.uniform(100,300),0),
         "health_advisory": random.choice(["Wear mask","Avoid outdoor exercise","Hazardous - stay indoors"])}
        for i, a in enumerate(random.sample(BENGALURU_AREAS, 5))
    ]

def create_pollution_heatmap_data():
    """Return heatmap points for Leaflet."""
    return [{"lat": a['lat']+random.uniform(-0.01,0.01),
             "lng": a['lng']+random.uniform(-0.01,0.01),
             "intensity": round(random.uniform(0.3,1.0),2)}
            for a in BENGALURU_AREAS for _ in range(3)]

def reward_ev_vehicle(plate_text):
    """Award green points and cashback to EV owners."""
    points = random.randint(50, 200)
    cashback = round(points * 2.5, 0)
    conn = _get_conn()
    try:
        conn.execute("""INSERT OR REPLACE INTO eco_rewards
            (reward_id, plate_text, green_points, cashback_amount,
             electric_vehicle_status, fine_discount_percent, last_reward_date, total_co2_saved_kg)
            VALUES (?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4())[:12], plate_text, points, cashback,
             1, 50.0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), round(random.uniform(12,45),2)))
        conn.commit()
    finally:
        conn.close()
    return {"plate_text": plate_text, "green_points": points, "cashback": cashback,
            "fine_discount": "50%", "ev_certificate": "GREEN_DRIVER_2026"}

def get_emission_stats():
    """Return emission monitoring statistics."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM emission_data").fetchone()[0]
        compliant = conn.execute("SELECT COUNT(*) FROM emission_data WHERE compliant=1").fetchone()[0]
        fines = conn.execute("SELECT SUM(fine_amount) FROM emission_data WHERE fine_issued=1").fetchone()[0] or 0
        return {
            "total_readings": total or random.randint(200,500),
            "bs_vi_compliance_rate": round((compliant/max(total,1))*100, 1) if total else 87.3,
            "avg_aqi": round(random.uniform(120,180), 0),
            "fines_collected_today": round(fines, 0),
            "ev_count": random.randint(15,40),
            "black_smoke_detections": random.randint(8,25),
            "maintenance_alerts_sent": random.randint(12,35)
        }
    finally:
        conn.close()

def get_weekly_air_quality_report():
    """Return 7-day AQI trend for Chart.js."""
    labels = [(datetime.now()-timedelta(days=i)).strftime("%d %b") for i in range(6,-1,-1)]
    data = [round(random.uniform(95,220),0) for _ in range(7)]
    return {"labels": labels, "data": data,
            "categories": ["Good","Satisfactory","Moderate","Poor","Very Poor","Severe"],
            "current_aqi": data[-1]}

def seed_emission_data():
    """Seed historical emission readings."""
    conn = _get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM emission_data").fetchone()[0] > 0:
            return
        for _ in range(80):
            plate = random.choice(INDIAN_PLATES)
            area = random.choice(BENGALURU_AREAS)
            smoke = random.choices(['clear','black','white','blue'], weights=[60,20,12,8])[0]
            level = random.uniform(10,90)
            ts = (datetime.now()-timedelta(hours=random.randint(0,168))).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""INSERT OR IGNORE INTO emission_data
                (reading_id, vehicle_plate, emission_level, smoke_color, pm25_level,
                 co2_level, nox_level, vehicle_type, bs_standard, compliant,
                 timestamp, location_lat, location_lng, camera_id, fine_issued, fine_amount)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4())[:12], plate, round(level,1), smoke,
                 round(level*0.8,1), round(level*2.1,1), round(level*0.15,2),
                 random.choice(['motorcycle','car','truck']),
                 'BS-VI' if smoke=='clear' else 'PRE-BS-VI', 1 if smoke=='clear' else 0,
                 ts, area['lat'], area['lng'], random.choice(CAMERAS),
                 1 if (smoke!='clear' and level>55) else 0,
                 5000 if smoke=='black' else (3000 if smoke in ['white','blue'] else 0)))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 24 — DRUNK DRIVING DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

NIGHTLIFE_AREAS = [
    {"name": "Koramangala Bar District", "lat": 12.9352, "lng": 77.6245},
    {"name": "Indiranagar 12th Main", "lat": 12.9784, "lng": 77.6408},
    {"name": "MG Road Pub Zone", "lat": 12.9756, "lng": 77.6066},
    {"name": "Church Street", "lat": 12.9738, "lng": 77.6080},
    {"name": "Brigade Road Night Market", "lat": 12.9710, "lng": 77.6073},
]

def analyze_vehicle_for_impairment(plate_text, camera_id=None, time_hour=None):
    """Multi-modal drunk driving detection simulation."""
    if not camera_id: camera_id = random.choice(CAMERAS)
    if time_hour is None: time_hour = datetime.now().hour
    # Time-of-day factor: 10PM-4AM = much higher detection rate
    time_risk = 2.5 if (time_hour >= 22 or time_hour <= 4) else 1.0
    eye_blink_rate = round(random.gauss(14, 4) / time_risk, 1)  # Normal=15/min, drunk<2
    lane_deviations = random.randint(0, 5) if time_risk > 1.5 else random.randint(0, 2)
    speed_variance = round(random.uniform(2, 20) * time_risk, 1)
    methods = []
    confidence = 0.0
    if eye_blink_rate < 5:
        methods.append("eye_blink_analysis"); confidence += 35
    if lane_deviations >= 3:
        methods.append("lane_deviation_tracking"); confidence += 30
    if speed_variance > 15:
        methods.append("speed_variance_analysis"); confidence += 25
    if time_risk > 1.5:
        methods.append("time_of_day_factor"); confidence += 10
    confidence = min(confidence, 98)
    area = random.choice(NIGHTLIFE_AREAS) if time_risk > 1.5 else random.choice(BENGALURU_AREAS)
    detected = confidence >= 65
    if detected:
        alert_id = f"DD-{str(uuid.uuid4())[:10].upper()}"
        conn = _get_conn()
        try:
            conn.execute("""INSERT OR IGNORE INTO drunk_driving_alerts
                (alert_id, vehicle_plate, eye_blink_rate, lane_deviation_count,
                 speed_variance, detection_method, confidence_score,
                 time_of_day, action_taken, timestamp, location_lat, location_lng, location_name)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (alert_id, plate_text, eye_blink_rate, lane_deviations, speed_variance,
                 ",".join(methods), round(confidence,1), time_hour,
                 "police_alert_dispatched" if confidence > 80 else "driver_sms_sent",
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 area['lat'], area['lng'], area['name']))
            conn.commit()
        finally:
            conn.close()
    return {
        "plate_text": plate_text, "impairment_detected": detected,
        "confidence": round(confidence, 1), "methods_triggered": methods,
        "eye_blink_rate": eye_blink_rate, "lane_deviations": lane_deviations,
        "speed_variance": speed_variance, "bac_estimate": round(confidence/200, 2),
        "action_recommended": "immediate_stop" if confidence > 80 else "advisory_sms" if detected else "none",
        "fine_if_confirmed": 10000, "license_suspension_days": 90 if confidence > 80 else 0
    }

def get_drunk_driving_heatmap():
    """Return heatmap data clustered near nightlife."""
    return [{"lat": a['lat']+random.uniform(-0.005,0.005),
             "lng": a['lng']+random.uniform(-0.005,0.005),
             "count": random.randint(3,15)}
            for a in NIGHTLIFE_AREAS for _ in range(4)]

def get_drunk_driving_stats():
    """Return drunk driving detection statistics."""
    conn = _get_conn()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        total = conn.execute("SELECT COUNT(*) FROM drunk_driving_alerts").fetchone()[0]
        today_alerts = conn.execute(
            "SELECT COUNT(*) FROM drunk_driving_alerts WHERE timestamp LIKE ?",
            (f"{today}%",)).fetchone()[0]
        high_risk_hours = {str(h): random.randint(0, 5 if (h>=22 or h<=4) else 1) for h in range(24)}
        return {
            "today_alerts": today_alerts or random.randint(2,8),
            "this_month_alerts": total or random.randint(45,120),
            "fines_collected": (total or 45) * 10000,
            "high_risk_hours": high_risk_hours,
            "peak_risk_hour": "23:00 - 02:00",
            "licenses_suspended": random.randint(8,25)
        }
    finally:
        conn.close()

def get_offender_list(limit=20):
    """Get drunk driving offender list."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM drunk_driving_offenders ORDER BY offense_date DESC LIMIT ?",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def alert_police_for_impaired_driver(alert_id, plate_text, location_name="Unknown"):
    """Dispatch police to intercept impaired driver."""
    return {
        "alert_id": alert_id, "plate_text": plate_text,
        "police_dispatched": True,
        "unit": f"Traffic Police Unit {random.randint(1,20)}",
        "eta_minutes": random.randint(3, 8),
        "location": location_name,
        "message": f"Police unit dispatched to intercept vehicle {plate_text}. ETA: {random.randint(3,8)} minutes."
    }

def seed_drunk_driving_data():
    """Seed demo data."""
    conn = _get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM drunk_driving_alerts").fetchone()[0] > 0:
            return
        for _ in range(30):
            plate = random.choice(INDIAN_PLATES)
            area = random.choice(NIGHTLIFE_AREAS)
            hour = random.choices(list(range(24)), weights=[
                5,3,2,2,2,1,1,1,1,1,1,1,1,1,1,2,3,4,5,6,7,8,9,7])[0]
            conf = round(random.uniform(65, 97), 1)
            ts = (datetime.now()-timedelta(days=random.randint(0,30),
                  hours=random.randint(0,23))).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""INSERT OR IGNORE INTO drunk_driving_alerts
                (alert_id, vehicle_plate, eye_blink_rate, lane_deviation_count,
                 speed_variance, detection_method, confidence_score, time_of_day,
                 action_taken, timestamp, location_lat, location_lng, location_name)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4())[:12], plate, round(random.uniform(1,5),1),
                 random.randint(2,6), round(random.uniform(10,25),1),
                 "eye_blink_analysis,lane_deviation_tracking", conf, hour,
                 "police_alert_dispatched", ts, area['lat'], area['lng'], area['name']))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 25 — AUTOMATED PARKING ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

PARKING_ZONES_DATA = [
    {"id":"PZ-01","name":"Manipal Hospital No-Parking Zone","type":"no_parking","lat":12.9411,"lng":77.7027,"fine":1000},
    {"id":"PZ-02","name":"DPS School Entrance","type":"school","lat":12.9698,"lng":77.7499,"fine":2000},
    {"id":"PZ-03","name":"Koramangala Bus Stop","type":"no_parking","lat":12.9352,"lng":77.6245,"fine":500},
    {"id":"PZ-04","name":"MG Road Disabled Zone","type":"disabled","lat":12.9756,"lng":77.6066,"fine":5000},
    {"id":"PZ-05","name":"Commercial Street Market","type":"no_parking","lat":12.9815,"lng":77.5996,"fine":500},
    {"id":"PZ-06","name":"Indiranagar Metro Station","type":"no_parking","lat":12.9784,"lng":77.6408,"fine":1000},
    {"id":"PZ-07","name":"Electronic City Street Cleaning Zone","type":"street_cleaning","lat":12.8399,"lng":77.6770,"fine":2000},
    {"id":"PZ-08","name":"Whitefield IT Park Gate","type":"no_parking","lat":12.9698,"lng":77.7500,"fine":1000},
]

TOWING_SERVICES = [
    {"name":"KA Rapid Towing","phone":"+91 98450 12345","eta":25},
    {"name":"Bengaluru Vehicle Recovery","phone":"+91 98765 43210","eta":30},
    {"name":"City Tow Services","phone":"+91 80 4567 8901","eta":35},
]

def seed_parking_zones():
    """Seed parking zones and sample violations."""
    conn = _get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM parking_zones").fetchone()[0] > 0:
            return
        for z in PARKING_ZONES_DATA:
            conn.execute("""INSERT OR IGNORE INTO parking_zones
                (zone_id, zone_name, zone_type, latitude, longitude, fine_amount)
                VALUES (?,?,?,?,?,?)""",
                (z['id'],z['name'],z['type'],z['lat'],z['lng'],z['fine']))
        for _ in range(40):
            zone = random.choice(PARKING_ZONES_DATA)
            plate = random.choice(INDIAN_PLATES)
            duration = random.randint(10, 180)
            ts = (datetime.now()-timedelta(minutes=random.randint(0, duration))).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""INSERT OR IGNORE INTO parking_violations
                (violation_id, vehicle_plate, zone_id, zone_name, violation_type,
                 detection_time, duration_minutes, fine_amount, fine_issued,
                 tow_requested, payment_status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4())[:12], plate, zone['id'], zone['name'],
                 'illegal_parking', ts, duration, zone['fine'], 1,
                 1 if duration > 120 else 0,
                 random.choice(['paid','unpaid','unpaid'])))
        conn.commit()
    finally:
        conn.close()

def detect_parking_violation(plate_text, zone_id=None, camera_id=None):
    """Simulate parking violation detection."""
    zone = next((z for z in PARKING_ZONES_DATA if z['id']==zone_id), random.choice(PARKING_ZONES_DATA))
    duration = random.randint(5, 180)
    fine = zone['fine']
    if zone['type'] == 'disabled': fine = 5000
    tow = duration > 120
    vid = f"PKV-{str(uuid.uuid4())[:10].upper()}"
    conn = _get_conn()
    try:
        conn.execute("""INSERT OR IGNORE INTO parking_violations
            (violation_id, vehicle_plate, zone_id, zone_name, violation_type,
             detection_time, duration_minutes, fine_amount, fine_issued,
             sms_sent, tow_requested, payment_status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (vid, plate_text, zone['id'], zone['name'], 'illegal_parking',
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), duration, fine, 1, 1, 1 if tow else 0, 'unpaid'))
        conn.commit()
    finally:
        conn.close()
    return {"violation_id": vid, "plate_text": plate_text, "zone": zone['name'],
            "zone_type": zone['type'], "duration_minutes": duration, "fine_amount": fine,
            "tow_recommended": tow, "sms_sent": True,
            "message": f"Vehicle {plate_text} in {zone['name']} for {duration} min. Fine: ₹{fine}"}

def request_towing(violation_id):
    """Request towing service."""
    svc = random.choice(TOWING_SERVICES)
    tow_id = f"TOW-{str(uuid.uuid4())[:10].upper()}"
    conn = _get_conn()
    try:
        conn.execute("""INSERT OR IGNORE INTO towing_records
            (tow_id, violation_id, towing_service, driver_name, contact_number,
             towing_charge, storage_charge_per_day, towing_date, status)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (tow_id, violation_id, svc['name'],
             random.choice(["Ravi Driver","Kumar Tow","Suresh Recovery"]),
             svc['phone'], 5000, 200,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'dispatched'))
        conn.commit()
    finally:
        conn.close()
    return {"tow_id": tow_id, "service": svc['name'], "eta_minutes": svc['eta'],
            "phone": svc['phone'], "towing_charge": 5000, "storage_per_day": 200}

def get_parking_zones():
    """Return all parking zones for map."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM parking_zones").fetchall()
        return [dict(r) for r in rows] if rows else PARKING_ZONES_DATA
    finally:
        conn.close()

def get_parking_stats():
    """Get parking enforcement statistics."""
    conn = _get_conn()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        total = conn.execute("SELECT COUNT(*) FROM parking_violations").fetchone()[0]
        today_v = conn.execute("SELECT COUNT(*) FROM parking_violations WHERE detection_time LIKE ?",
            (f"{today}%",)).fetchone()[0]
        fines = conn.execute("SELECT SUM(fine_amount) FROM parking_violations WHERE fine_issued=1").fetchone()[0] or 0
        tows = conn.execute("SELECT COUNT(*) FROM towing_records WHERE towing_date LIKE ?",
            (f"{today}%",)).fetchone()[0]
        return {"today_violations": today_v or random.randint(8,25),
                "total_fines": round(fines,0), "tow_requests_today": tows or random.randint(2,8),
                "avg_violation_duration_min": random.randint(35,90), "collection_rate": "72%"}
    finally:
        conn.close()

def get_active_parking_violations(limit=20):
    """Get unpaid parking violations."""
    conn = _get_conn()
    try:
        rows = conn.execute("""SELECT * FROM parking_violations
            WHERE payment_status='unpaid' ORDER BY detection_time DESC LIMIT ?""", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 26 — DRIVER BEHAVIOR RISK SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_risk_score(plate_text, db_conn=None):
    """Compute weighted driver risk score 0-100."""
    close_conn = db_conn is None
    conn = db_conn or _get_conn()
    try:
        rows = conn.execute(
            "SELECT violation, timestamp, fine FROM violations WHERE plate=?",
            (plate_text,)).fetchall()
        if not rows:
            return {"risk_score": 10, "category": "green", "factors": [], "insurance_multiplier": 0.8}
        count = len(rows)
        severity_score = sum(1.5 if r['fine']>=5000 else 1.0 if r['fine']>=1000 else 0.5 for r in rows)
        now = datetime.now()
        recency_score = 0
        for r in rows:
            try:
                ts = datetime.strptime(r['timestamp'][:19], "%Y-%m-%d %H:%M:%S")
                days = (now - ts).days
                recency_score += max(0, 30 - days) / 30
            except: pass
        risk_score = min(100, (count*10*0.4) + (severity_score*6*0.3) + (recency_score*15*0.2) + (count*2*0.1))
        category = get_risk_category(risk_score)
        multiplier = {"green": 0.8, "yellow": 1.0, "orange": 1.5, "red": 2.5}[category]
        factors = []
        if count >= 3: factors.append(f"Habitual offender ({count} violations)")
        if severity_score > count: factors.append("High-severity violations detected")
        if recency_score > 0.5: factors.append("Recent violations increase risk")
        conn2 = _get_conn()
        conn2.execute("""INSERT OR REPLACE INTO driver_risk_profile
            (driver_id, plate_text, risk_score, category, violation_count,
             severity_score, recency_score, insurance_premium_multiplier, last_updated)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4())[:12], plate_text, round(risk_score,1), category,
             count, round(severity_score,1), round(recency_score,1), multiplier,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn2.commit(); conn2.close()
        return {"plate_text": plate_text, "risk_score": round(risk_score,1), "category": category,
                "factors": factors or ["Clean driving record"],
                "insurance_multiplier": multiplier, "violation_count": count}
    finally:
        if close_conn: conn.close()

def get_risk_category(score):
    if score <= 30: return "green"
    elif score <= 60: return "yellow"
    elif score <= 80: return "orange"
    else: return "red"

def sync_risk_scores_from_violations():
    """Bulk recalculate all risk profiles."""
    conn = _get_conn()
    try:
        plates = [r[0] for r in conn.execute(
            "SELECT DISTINCT plate FROM violations WHERE plate IS NOT NULL AND plate!='UNKNOWN'").fetchall()]
        for plate in plates:
            calculate_risk_score(plate)
        return {"updated": len(plates), "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    finally:
        conn.close()

def get_all_risk_profiles(limit=50):
    """Get all driver risk profiles."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM driver_risk_profile ORDER BY risk_score DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_risk_distribution():
    """Get risk category distribution for pie chart."""
    conn = _get_conn()
    try:
        dist = {"green": 0, "yellow": 0, "orange": 0, "red": 0}
        for cat in dist:
            dist[cat] = conn.execute(
                "SELECT COUNT(*) FROM driver_risk_profile WHERE category=?", (cat,)).fetchone()[0]
        if sum(dist.values()) == 0:
            dist = {"green": 65, "yellow": 20, "orange": 10, "red": 5}
        return dist
    finally:
        conn.close()

def calculate_insurance_premium(plate_text, base_premium=12000):
    """Calculate dynamic insurance premium."""
    profile = calculate_risk_score(plate_text)
    multiplier = profile['insurance_multiplier']
    discount = max(0, (1 - multiplier) * 100)
    surcharge = max(0, (multiplier - 1) * 100)
    final = round(base_premium * multiplier, 0)
    conn = _get_conn()
    try:
        conn.execute("""INSERT OR REPLACE INTO premium_calculation
            (calc_id, vehicle_plate, base_premium, risk_multiplier,
             violation_surcharge, safe_driver_discount, final_premium,
             discount_percentage, last_updated)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4())[:12], plate_text, base_premium, multiplier,
             surcharge, discount, final, discount,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    finally:
        conn.close()
    return {"plate_text": plate_text, "base_premium": base_premium,
            "final_premium": final, "risk_multiplier": multiplier,
            "safe_driver_discount": f"{discount:.0f}%",
            "violation_surcharge": f"{surcharge:.0f}%",
            "risk_category": profile['category'],
            "annual_savings": base_premium - final if final < base_premium else 0}

def get_risk_stats():
    """Get risk scoring statistics."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM driver_risk_profile").fetchone()[0]
        high_risk = conn.execute(
            "SELECT COUNT(*) FROM driver_risk_profile WHERE category IN ('orange','red')").fetchone()[0]
        avg = conn.execute("SELECT AVG(risk_score) FROM driver_risk_profile").fetchone()[0] or 28.5
        return {"total_profiles": total or random.randint(80,200),
                "avg_fleet_risk": round(avg, 1),
                "high_risk_count": high_risk or random.randint(15,40),
                "training_required_count": high_risk or random.randint(10,30),
                "insurance_savings_potential_pct": 15}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 27 — PEDESTRIAN SAFETY & NEAR-MISS DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_pedestrian_detection(camera_id=None):
    """Simulate pedestrian detection from camera feed."""
    if not camera_id: camera_id = random.choice(CAMERAS)
    area = random.choice(BENGALURU_AREAS)
    count = random.randint(1, 12)
    children = random.randint(0, max(0, count//3))
    elderly = random.randint(0, max(0, count//5))
    zone = random.choice(['school_zone','market','crosswalk','residential','normal'])
    pid = str(uuid.uuid4())[:12]
    conn = _get_conn()
    try:
        conn.execute("""INSERT OR IGNORE INTO pedestrian_detections
            (detection_id, camera_id, location_lat, location_lng, location_name,
             pedestrian_count, child_count, elderly_count, timestamp, zone_type)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (pid, camera_id, area['lat']+random.uniform(-0.002,0.002),
             area['lng']+random.uniform(-0.002,0.002), area['name'],
             count, children, elderly, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), zone))
        conn.commit()
    finally:
        conn.close()
    return {"detection_id": pid, "pedestrian_count": count, "child_count": children,
            "elderly_count": elderly, "zone_type": zone, "location_name": area['name'],
            "vulnerability_score": round((children*2 + elderly*1.5)/max(count,1)*100, 1)}

def detect_near_miss(plate_text, camera_id=None):
    """Simulate vehicle-pedestrian near miss detection."""
    if not camera_id: camera_id = random.choice(CAMERAS)
    area = random.choice(BENGALURU_AREAS)
    distance = random.randint(80, 800)
    danger = 'CRITICAL' if distance < 200 else 'HIGH' if distance < 400 else 'MEDIUM'
    speed = round(random.uniform(20, 65), 1)
    incident_id = f"NM-{str(uuid.uuid4())[:10].upper()}"
    conn = _get_conn()
    try:
        conn.execute("""INSERT OR IGNORE INTO near_miss_incidents
            (incident_id, vehicle_plate, camera_id, pedestrian_count,
             min_distance_cm, danger_level, vehicle_speed_kmh, braking_event,
             alert_sent, timestamp, location_lat, location_lng, location_name)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (incident_id, plate_text, camera_id, random.randint(1,3),
             distance, danger, speed, 1 if distance < 300 else 0, 1,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             area['lat'], area['lng'], area['name']))
        conn.commit()
    finally:
        conn.close()
    return {"incident_id": incident_id, "plate_text": plate_text, "danger_level": danger,
            "min_distance_cm": distance, "vehicle_speed_kmh": speed, "location": area['name'],
            "action": "brake_alert_sent" if distance < 300 else "warning_logged"}

def seed_pedestrian_data():
    """Seed pedestrian hotspot data."""
    conn = _get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM pedestrian_hotspots").fetchone()[0] > 0:
            return
        hotspots = [
            ("Silk Board Junction Crosswalk", 12.9176, 77.6238, 45, 8, 5, 9),
            ("DPS Whitefield School Gate", 12.9698, 77.7499, 38, 15, 2, 8),
            ("Koramangala Market Crossing", 12.9352, 77.6245, 29, 3, 7, 18),
            ("MG Road Pedestrian Zone", 12.9756, 77.6066, 22, 1, 6, 17),
            ("Indiranagar Market", 12.9784, 77.6408, 18, 2, 8, 19),
        ]
        for name, lat, lng, incidents, children, elderly, peak in hotspots:
            conn.execute("""INSERT OR IGNORE INTO pedestrian_hotspots
                (hotspot_id, area_name, latitude, longitude, incident_count,
                 child_count, elderly_count, peak_hour, risk_score, recommended_action)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4())[:12], name, lat, lng, incidents, children, elderly, peak,
                 min(100, incidents*2), "Deploy traffic marshal + extend crossing time"))
        for _ in range(50):
            area = random.choice(BENGALURU_AREAS)
            plate = random.choice(INDIAN_PLATES)
            dist = random.randint(80, 800)
            ts = (datetime.now()-timedelta(hours=random.randint(0,72))).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""INSERT OR IGNORE INTO near_miss_incidents
                (incident_id, vehicle_plate, camera_id, pedestrian_count, min_distance_cm,
                 danger_level, vehicle_speed_kmh, braking_event, alert_sent,
                 timestamp, location_lat, location_lng, location_name)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4())[:12], plate, random.choice(CAMERAS), random.randint(1,4),
                 dist, 'CRITICAL' if dist<200 else 'HIGH' if dist<400 else 'MEDIUM',
                 round(random.uniform(20,65),1), 1 if dist<300 else 0, 1, ts,
                 area['lat'], area['lng'], area['name']))
        conn.commit()
    finally:
        conn.close()

def get_pedestrian_hotspots():
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM pedestrian_hotspots ORDER BY incident_count DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_near_miss_stats():
    conn = _get_conn()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        total = conn.execute("SELECT COUNT(*) FROM near_miss_incidents").fetchone()[0]
        crit = conn.execute("SELECT COUNT(*) FROM near_miss_incidents WHERE danger_level='CRITICAL'").fetchone()[0]
        today_c = conn.execute("SELECT COUNT(*) FROM near_miss_incidents WHERE timestamp LIKE ?",
            (f"{today}%",)).fetchone()[0]
        return {"today_incidents": today_c or random.randint(3,12),
                "critical_count": crit or random.randint(2,8),
                "total_incidents": total or random.randint(80,200),
                "children_endangered": random.randint(8,25),
                "alerts_sent_today": today_c or random.randint(5,15)}
    finally:
        conn.close()

def get_recent_near_misses(limit=15):
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM near_miss_incidents ORDER BY timestamp DESC LIMIT ?",
            (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 28 — PREDICTIVE ACCIDENT RISK ZONES
# ═══════════════════════════════════════════════════════════════════════════════

RISK_LOCATIONS = [
    {"name": "Silk Board Junction", "lat": 12.9176, "lng": 77.6238, "base_risk": 85},
    {"name": "Hosur Road – Electronic City", "lat": 12.8399, "lng": 77.6770, "base_risk": 72},
    {"name": "Outer Ring Road Marathahalli", "lat": 12.9569, "lng": 77.7011, "base_risk": 68},
    {"name": "Tumkur Road Peenya", "lat": 13.0358, "lng": 77.5240, "base_risk": 61},
    {"name": "Old Madras Road KR Puram", "lat": 12.9982, "lng": 77.7507, "base_risk": 58},
    {"name": "Mysore Road Kengeri", "lat": 12.9141, "lng": 77.4532, "base_risk": 55},
    {"name": "Bellary Road Hebbal", "lat": 13.0358, "lng": 77.5970, "base_risk": 48},
    {"name": "Airport Road Hebbal", "lat": 13.0362, "lng": 77.5973, "base_risk": 42},
]

def seed_risk_predictions():
    conn = _get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM accident_predictions").fetchone()[0] > 0:
            return
        for loc in RISK_LOCATIONS:
            risk = min(100, loc['base_risk'] + random.randint(-10, 10))
            zone = 'red' if risk>75 else 'orange' if risk>50 else 'yellow' if risk>25 else 'green'
            conn.execute("""INSERT OR IGNORE INTO accident_predictions
                (prediction_id, location_lat, location_lng, location_name, risk_score,
                 risk_zone, predicted_time_window, weather_factor,
                 traffic_density_factor, historical_accident_count, action_taken,
                 accuracy, created_at, valid_until)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4())[:12], loc['lat'], loc['lng'], loc['name'],
                 risk, zone, "Next 2 hours", random.choice(['clear','rain','fog']),
                 round(random.uniform(0.4,0.9),2), random.randint(5,45),
                 "Police deployed" if risk>75 else "Monitoring",
                 round(random.uniform(82,96),1),
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 (datetime.now()+timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    finally:
        conn.close()

def predict_accident_risk(lat, lng, time_hour=None, weather='clear', traffic_density=0.5):
    """ML-simulated accident risk prediction."""
    if time_hour is None: time_hour = datetime.now().hour
    # Find nearest known location
    nearest = min(RISK_LOCATIONS, key=lambda l: math.sqrt((l['lat']-lat)**2+(l['lng']-lng)**2))
    base_risk = nearest['base_risk']
    time_factor = 1.4 if 8<=time_hour<=10 or 17<=time_hour<=20 else 1.2 if 22<=time_hour or time_hour<=5 else 1.0
    weather_factor = {'rain':1.3,'fog':1.5,'clear':1.0,'hail':1.8}.get(weather, 1.0)
    risk = min(100, base_risk * time_factor * weather_factor * (0.5 + traffic_density))
    zone = 'red' if risk>75 else 'orange' if risk>50 else 'yellow' if risk>25 else 'green'
    actions = []
    if risk > 75: actions = ["Deploy 2 police units", "Activate speed cameras", "Alert nearest ambulance"]
    elif risk > 50: actions = ["Deploy 1 police unit", "Increase signal timing"]
    elif risk > 25: actions = ["Monitor camera feed", "Deploy advisory SMS"]
    return {"location": nearest['name'], "risk_score": round(risk,1), "risk_zone": zone,
            "contributing_factors": [f"Time of day: {time_hour}:00",
                                      f"Weather: {weather}", f"Traffic density: {traffic_density:.0%}"],
            "recommended_actions": actions, "confidence": round(random.uniform(82,96),1)}

def get_risk_zones():
    conn = _get_conn()
    try:
        rows = conn.execute("""SELECT * FROM accident_predictions
            ORDER BY risk_score DESC""").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_risk_heatmap_data():
    return [{"lat": l['lat']+random.uniform(-0.005,0.005),
             "lng": l['lng']+random.uniform(-0.005,0.005),
             "intensity": l['base_risk']/100}
            for l in RISK_LOCATIONS for _ in range(3)]

def get_prediction_stats():
    conn = _get_conn()
    try:
        high = conn.execute("SELECT COUNT(*) FROM accident_predictions WHERE risk_score>75").fetchone()[0]
        medium = conn.execute("SELECT COUNT(*) FROM accident_predictions WHERE risk_score>50 AND risk_score<=75").fetchone()[0]
        acc = conn.execute("SELECT AVG(accuracy) FROM accident_predictions").fetchone()[0] or 88.5
        return {"high_risk_zones": high or 2, "medium_risk_zones": medium or 3,
                "accidents_prevented_this_month": random.randint(8,25),
                "model_accuracy_pct": round(acc,1)}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 29 — V2I / SMART TRAFFIC SIGNALS
# ═══════════════════════════════════════════════════════════════════════════════

SIGNAL_LOCATIONS = [
    {"id":"SIG-01","name":"Silk Board Junction","lat":12.9176,"lng":77.6238},
    {"id":"SIG-02","name":"Koramangala 80ft Road","lat":12.9352,"lng":77.6245},
    {"id":"SIG-03","name":"MG Road Metro","lat":12.9756,"lng":77.6066},
    {"id":"SIG-04","name":"Brigade Road","lat":12.9738,"lng":77.6080},
    {"id":"SIG-05","name":"Indiranagar 100ft Road","lat":12.9784,"lng":77.6408},
    {"id":"SIG-06","name":"Whitefield ITPL","lat":12.9698,"lng":77.7500},
    {"id":"SIG-07","name":"Hebbal Flyover","lat":13.0358,"lng":77.5970},
    {"id":"SIG-08","name":"Electronic City Signal","lat":12.8399,"lng":77.6770},
]

def seed_traffic_signals():
    conn = _get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM traffic_signals").fetchone()[0] > 0:
            return
        for s in SIGNAL_LOCATIONS:
            vc_ns = random.randint(20, 120)
            vc_ew = random.randint(15, 100)
            green = max(30, min(90, int(45 * vc_ns / max(vc_ns+vc_ew, 1) * 2)))
            conn.execute("""INSERT OR IGNORE INTO traffic_signals
                (signal_id, intersection_name, location_lat, location_lng,
                 current_phase, green_duration_sec, red_duration_sec, yellow_duration_sec,
                 vehicle_count_ns, vehicle_count_ew, ai_optimized, last_updated)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (s['id'], s['name'], s['lat'], s['lng'],
                 random.choice(['GREEN','RED','YELLOW']), green, 60-green+15, 5,
                 vc_ns, vc_ew, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    finally:
        conn.close()

def get_all_signals():
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM traffic_signals").fetchall()
        if rows: return [dict(r) for r in rows]
    finally:
        conn.close()
    return [{"signal_id": s['id'], "intersection_name": s['name'],
             "location_lat": s['lat'], "location_lng": s['lng'],
             "current_phase": random.choice(['GREEN','RED']),
             "green_duration_sec": random.randint(30,90),
             "vehicle_count_ns": random.randint(20,120),
             "vehicle_count_ew": random.randint(15,100),
             "ai_optimized": 1} for s in SIGNAL_LOCATIONS]

def optimize_signal_timing(signal_id):
    """AI-optimize signal green time based on vehicle counts."""
    conn = _get_conn()
    try:
        sig = conn.execute("SELECT * FROM traffic_signals WHERE signal_id=?", (signal_id,)).fetchone()
        if not sig:
            return {"error": "Signal not found"}
        sig = dict(sig)
        vc_ns = sig['vehicle_count_ns'] + random.randint(-10,10)
        vc_ew = sig['vehicle_count_ew'] + random.randint(-10,10)
        total = max(vc_ns + vc_ew, 1)
        new_green = max(20, min(90, int(90 * vc_ns / total)))
        old_green = sig['green_duration_sec']
        saved = abs(new_green - old_green) * 0.4
        conn.execute("UPDATE traffic_signals SET green_duration_sec=?, vehicle_count_ns=?, vehicle_count_ew=?, ai_optimized=1, last_updated=? WHERE signal_id=?",
            (new_green, vc_ns, vc_ew, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), signal_id))
        conn.execute("""INSERT INTO signal_optimization_log
            (log_id, signal_id, original_green_sec, new_green_sec,
             vehicle_count, optimization_reason, time_saved_sec, timestamp)
            VALUES (?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4())[:12], signal_id, old_green, new_green,
             total, f"NS:{vc_ns} EW:{vc_ew} — balance optimized",
             int(saved), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return {"signal_id": signal_id, "old_green_sec": old_green, "new_green_sec": new_green,
                "vehicle_count_ns": vc_ns, "vehicle_count_ew": vc_ew,
                "estimated_time_saved_sec": int(saved),
                "reason": f"Balanced for {vc_ns} NS vs {vc_ew} EW vehicles"}
    finally:
        conn.close()

def get_v2i_stats():
    conn = _get_conn()
    try:
        optimized = conn.execute("SELECT COUNT(*) FROM signal_optimization_log WHERE timestamp LIKE ?",
            (datetime.now().strftime("%Y-%m-%d")+"%",)).fetchone()[0]
        saved = conn.execute("SELECT AVG(time_saved_sec) FROM signal_optimization_log").fetchone()[0] or 18
        return {"total_signals": len(SIGNAL_LOCATIONS), "optimized_today": optimized or random.randint(15,30),
                "avg_time_saved_per_vehicle_sec": round(saved,1),
                "emergency_overrides_today": random.randint(1,5),
                "efficiency_improvement_pct": 24, "co2_reduction_pct": 12}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 30 — REAL-TIME INSURANCE CLAIM FILING
# ═══════════════════════════════════════════════════════════════════════════════

def auto_generate_claim(violation_id=None, accident_id=None, plate_text=None, claim_type='violation'):
    """Auto-generate insurance claim with evidence."""
    if not plate_text: plate_text = random.choice(INDIAN_PLATES)
    claim_id = f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"
    amount = random.randint(15000, 200000) if claim_type == 'accident' else random.randint(1000, 10000)
    fraud = assess_fraud_risk_score(plate_text, amount, claim_type)
    conn = _get_conn()
    try:
        conn.execute("""INSERT OR IGNORE INTO insurance_claims
            (claim_id, violation_id, accident_id, vehicle_plate, claim_type,
             claim_amount, severity_assessment, risk_score_at_time,
             approval_status, fraud_score, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (claim_id, violation_id, accident_id, plate_text, claim_type,
             amount, random.choice(['minor','moderate','severe']),
             round(random.uniform(10,80),1),
             'pending', round(fraud,1), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.execute("""INSERT OR IGNORE INTO fraud_detection
            (fraud_id, claim_id, fraud_score, fraud_indicators,
             staged_accident_probability, status, created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (str(uuid.uuid4())[:12], claim_id, round(fraud,1),
             "Multiple claims in 30 days" if fraud>60 else "Normal pattern",
             round(fraud*0.6,1), 'flagged' if fraud>60 else 'clear',
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    finally:
        conn.close()
    return {"claim_id": claim_id, "plate_text": plate_text, "claim_amount": amount,
            "fraud_score": round(fraud,1), "status": "pending",
            "auto_approval_eligible": fraud < 30,
            "expected_approval_hours": 2 if fraud < 30 else 24}

def assess_fraud_risk_score(plate_text, amount, claim_type):
    """Score fraud risk 0-100."""
    conn = _get_conn()
    try:
        past_claims = conn.execute(
            "SELECT COUNT(*) FROM insurance_claims WHERE vehicle_plate=?", (plate_text,)).fetchone()[0]
        base = min(50, past_claims * 15) + (20 if amount > 100000 else 0) + random.uniform(0, 20)
        return min(95, base)
    finally:
        conn.close()

def approve_claim(claim_id, approver='AI_SYSTEM'):
    """Approve an insurance claim and calculate payout."""
    conn = _get_conn()
    try:
        claim = conn.execute("SELECT * FROM insurance_claims WHERE claim_id=?", (claim_id,)).fetchone()
        if not claim: return {"error": "Claim not found"}
        claim = dict(claim)
        payout = round(claim['claim_amount'] * random.uniform(0.80, 0.95), 0)
        conn.execute("""UPDATE insurance_claims SET approval_status='approved',
            approved_by=?, payout_amount=?, payout_date=? WHERE claim_id=?""",
            (approver, payout, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), claim_id))
        conn.commit()
        return {"claim_id": claim_id, "status": "approved", "payout": payout,
                "processing_time": "48 hours", "payment_method": "NEFT to registered account"}
    finally:
        conn.close()

def get_pending_claims(limit=20):
    conn = _get_conn()
    try:
        rows = conn.execute("""SELECT * FROM insurance_claims
            WHERE approval_status='pending' ORDER BY created_at DESC LIMIT ?""", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_insurance_stats():
    conn = _get_conn()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        total = conn.execute("SELECT COUNT(*) FROM insurance_claims").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM insurance_claims WHERE approval_status='pending'").fetchone()[0]
        payout = conn.execute("SELECT SUM(payout_amount) FROM insurance_claims WHERE approval_status='approved'").fetchone()[0] or 0
        high_fraud = conn.execute("SELECT COUNT(*) FROM fraud_detection WHERE fraud_score>60").fetchone()[0]
        return {"total_claims": total or random.randint(80,200),
                "pending_count": pending or random.randint(15,40),
                "approved_today": random.randint(3,12),
                "avg_fraud_score": round(random.uniform(18,35),1),
                "total_payout_this_month": round(payout,0),
                "fraud_prevented_amount": high_fraud * random.randint(50000,200000)}
    finally:
        conn.close()

def seed_insurance_data():
    conn = _get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM insurance_claims").fetchone()[0] > 0:
            return
        for _ in range(50):
            plate = random.choice(INDIAN_PLATES)
            ctype = random.choice(['violation','accident','accident','violation'])
            amount = random.randint(1000,150000)
            fraud = assess_fraud_risk_score(plate, amount, ctype)
            status = random.choice(['pending','approved','approved','rejected'])
            payout = round(amount*random.uniform(0.8,0.95),0) if status=='approved' else 0
            ts = (datetime.now()-timedelta(days=random.randint(0,60))).strftime("%Y-%m-%d %H:%M:%S")
            cid = f"CLM-{str(uuid.uuid4())[:14].upper()}"
            conn.execute("""INSERT OR IGNORE INTO insurance_claims
                (claim_id, vehicle_plate, claim_type, claim_amount,
                 severity_assessment, risk_score_at_time, approval_status,
                 payout_amount, fraud_score, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (cid, plate, ctype, amount, random.choice(['minor','moderate','severe']),
                 round(random.uniform(10,80),1), status, payout, round(fraud,1), ts))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 31 — EV CHARGING STATION ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

EV_STATIONS_DATA = [
    {"id":"EV-01","name":"Tata Power Charging Hub Koramangala","operator":"Tata Power","lat":12.9352,"lng":77.6245,"speed":50,"price":8.0,"spots":8},
    {"id":"EV-02","name":"ChargeZone ITPL Whitefield","operator":"ChargeZone","lat":12.9698,"lng":77.7500,"speed":150,"price":12.0,"spots":6},
    {"id":"EV-03","name":"BPCL EV Station MG Road","operator":"BPCL","lat":12.9756,"lng":77.6066,"speed":22,"price":7.5,"spots":4},
    {"id":"EV-04","name":"Exicom Charging Indiranagar","operator":"Exicom","lat":12.9784,"lng":77.6408,"speed":7.2,"price":6.0,"spots":3},
    {"id":"EV-05","name":"Ather Grid HSR Layout","operator":"Ather Energy","lat":12.9166,"lng":77.6101,"speed":5.0,"price":5.0,"spots":10},
    {"id":"EV-06","name":"Statiq Hub Electronic City","operator":"Statiq","lat":12.8399,"lng":77.6770,"speed":50,"price":9.0,"spots":5},
    {"id":"EV-07","name":"Tata Power Hebbal","operator":"Tata Power","lat":13.0358,"lng":77.5970,"speed":22,"price":8.0,"spots":4},
    {"id":"EV-08","name":"ChargeZone Marathahalli","operator":"ChargeZone","lat":12.9569,"lng":77.7011,"speed":50,"price":10.0,"spots":6},
    {"id":"EV-09","name":"BPCL Charging BTM Layout","operator":"BPCL","lat":12.9166,"lng":77.6101,"speed":7.2,"price":7.0,"spots":3},
    {"id":"EV-10","name":"Ather Grid Jayanagar","operator":"Ather Energy","lat":12.9250,"lng":77.5838,"speed":5.0,"price":5.0,"spots":8},
    {"id":"EV-11","name":"Statiq Hub Silk Board","operator":"Statiq","lat":12.9176,"lng":77.6238,"speed":150,"price":12.0,"spots":4},
    {"id":"EV-12","name":"Exicom Whitefield Phase 2","operator":"Exicom","lat":12.9680,"lng":77.7540,"speed":22,"price":8.5,"spots":5},
]

def seed_charging_stations():
    conn = _get_conn()
    try:
        if conn.execute("SELECT COUNT(*) FROM charging_stations").fetchone()[0] > 0:
            return
        for s in EV_STATIONS_DATA:
            avail = random.randint(1, s['spots'])
            conn.execute("""INSERT OR IGNORE INTO charging_stations
                (station_id, station_name, operator, location_lat, location_lng,
                 total_spots, available_spots, charging_speed_kw, pricing_per_hour,
                 status, rating)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (s['id'], s['name'], s['operator'], s['lat'], s['lng'],
                 s['spots'], avail, s['speed'], s['price'],
                 'operational', round(random.uniform(3.8,4.9),1)))
        conn.commit()
    finally:
        conn.close()

def _haversine(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2-lat1); dlng = math.radians(lng2-lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_nearby_stations(lat, lng, radius_km=10):
    """Get EV charging stations within radius."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM charging_stations WHERE status='operational'").fetchall()
        stations = [dict(r) for r in rows] if rows else EV_STATIONS_DATA
    finally:
        conn.close()
    result = []
    for s in stations:
        slat = s.get('location_lat', s.get('lat'))
        slng = s.get('location_lng', s.get('lng'))
        dist = _haversine(lat, lng, slat, slng)
        if dist <= radius_km:
            s['distance_km'] = round(dist, 2)
            s['available_spots'] = s.get('available_spots', random.randint(1,4))
            result.append(s)
    return sorted(result, key=lambda x: x['distance_km'])

def calculate_ev_range(battery_percent, vehicle_type='car'):
    """Calculate remaining range from battery percentage."""
    full_range = {'car':300,'suv':280,'bike':120,'bus':250,'scooter':80}.get(vehicle_type, 300)
    return {"battery_percent": battery_percent, "range_km": round(full_range*battery_percent/100, 1),
            "charge_needed_pct": max(0, 20-battery_percent),
            "action": "charge_now" if battery_percent < 20 else "charge_soon" if battery_percent < 40 else "ok"}

def reserve_charging_spot(station_id, plate_text, duration_minutes=60):
    """Reserve an EV charging spot."""
    res_id = f"RES-{str(uuid.uuid4())[:10].upper()}"
    start = datetime.now() + timedelta(minutes=30)
    end = start + timedelta(minutes=duration_minutes)
    conn = _get_conn()
    try:
        conn.execute("""INSERT OR IGNORE INTO charging_reservations
            (reservation_id, vehicle_plate, station_id, reserved_at,
             charge_start_time, charge_end_time, charging_duration_minutes, status)
            VALUES (?,?,?,?,?,?,?,?)""",
            (res_id, plate_text, station_id,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             start.strftime("%Y-%m-%d %H:%M:%S"),
             end.strftime("%Y-%m-%d %H:%M:%S"),
             duration_minutes, 'active'))
        conn.execute("UPDATE charging_stations SET available_spots=MAX(0,available_spots-1) WHERE station_id=?",
            (station_id,))
        conn.commit()
    finally:
        conn.close()
    return {"reservation_id": res_id, "station_id": station_id, "plate_text": plate_text,
            "start_time": start.strftime("%H:%M"), "duration_minutes": duration_minutes,
            "estimated_cost": round(duration_minutes/60*8, 2), "status": "confirmed"}

def get_station_status_map():
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM charging_stations").fetchall()
        return [dict(r) for r in rows] if rows else []
    finally:
        conn.close()

def get_ev_stats():
    conn = _get_conn()
    try:
        sessions = conn.execute("SELECT COUNT(*) FROM charging_reservations").fetchone()[0]
        return {"total_stations": len(EV_STATIONS_DATA),
                "charging_sessions_today": sessions or random.randint(25,80),
                "total_ev_vehicles_detected": random.randint(150,400),
                "green_points_awarded": random.randint(5000,15000),
                "co2_saved_kg": round(random.uniform(500,2000),1),
                "revenue_from_charging": round(random.uniform(15000,50000),0)}
    finally:
        conn.close()

def get_ev_usage_chart():
    """Return 24-hour EV usage data."""
    labels = [f"{h:02d}:00" for h in range(24)]
    data = [random.randint(2, 20) for _ in range(24)]
    return {"labels": labels, "data": data}
