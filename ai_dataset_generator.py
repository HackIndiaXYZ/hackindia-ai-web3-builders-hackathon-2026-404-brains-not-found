"""
TrafficGuard Pro — AI Real-Time Dataset Generator
Continuously generates realistic Indian traffic data using probabilistic models.
Powers the live data feed on the website.
"""
import random, uuid, threading, time, sqlite3, os, json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'violations.db')

PLATES = [
    "KA03MX4521","MH12AB3456","DL09WR6392","TN05AT7024","KL07CD5678",
    "UP32GH8901","RJ14XY2345","GJ01BC7890","TS09QR1234","KA01HJ9876",
    "MH04CD1234","DL08PQ5678","KL09CA1671","MH14GE9533","KL5ER9012",
    "KL11AB1234","HB08H8993","GJ18BQ2145","AP29BQ7821","HR26DQ9034",
    "PB10CD5432","WB25EF7890","MP09GH1234","CG07IJ5678","OD15KL9012",
]
LOCATIONS = [
    ("Silk Board Junction","CAM-01",12.9176,77.6238),
    ("Koramangala 80ft Road","CAM-02",12.9352,77.6245),
    ("MG Road Metro","CAM-03",12.9756,77.6066),
    ("Indiranagar 100ft Road","CAM-04",12.9784,77.6408),
    ("Marathahalli Bridge","CAM-05",12.9569,77.7011),
    ("Hebbal Flyover","CAM-06",13.0358,77.5970),
    ("Electronic City","CAM-07",12.8399,77.6770),
    ("Whitefield ITPL Gate","CAM-08",12.9698,77.7500),
    ("BTM Layout","CAM-09",12.9166,77.6101),
    ("Jayanagar 4th Block","CAM-10",12.9250,77.5838),
]

EVENT_TYPES = [
    "violation_detected", "violation_detected", "violation_detected",
    "ambulance_detected", "accident_detected", "emission_alert",
    "drunk_driving_alert", "parking_violation", "near_miss_detected",
    "toll_processed", "ev_charging_started", "hazard_reported",
    "school_zone_violation", "risk_score_updated", "signal_optimized",
    "insurance_claim_filed", "blacklist_alert"
]

VIOLATIONS_POOL = [
    ("NO HELMET", 1000), ("TRIPLE RIDING", 1000), ("WRONG WAY", 5000),
    ("OVERSPEEDING", 2000), ("NO HELMET + TRIPLE RIDING", 2000)
]

_stop_event = threading.Event()
_generator_thread = None


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def generate_single_event():
    """Generate one realistic traffic event."""
    hour = datetime.now().hour
    # Weight events by time of day
    if 8 <= hour <= 10 or 17 <= hour <= 20:  # Rush hour
        weights = [50,5,8,3,10,8,2,6,3,2,1,1,4,2,4,3,1]
    elif 22 <= hour or hour <= 4:  # Night
        weights = [30,5,5,4,12,5,8,8,3,3,2,1,1,4,4,5,2]
    else:  # Normal
        weights = [40,6,6,4,8,8,4,6,4,4,2,2,3,3,4,4,2]

    event_type = random.choices(EVENT_TYPES, weights=weights[:len(EVENT_TYPES)])[0]
    plate = random.choice(PLATES)
    loc_name, cam_id, lat, lng = random.choice(LOCATIONS)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event_id = f"EVT-{str(uuid.uuid4())[:10].upper()}"

    if event_type == "violation_detected":
        viol, fine = random.choice(VIOLATIONS_POOL)
        data = {
            "plate": plate, "violation": viol, "fine": fine,
            "camera": cam_id, "location": loc_name,
            "confidence": round(random.uniform(94, 99.5), 1),
            "icon": "🚫", "severity": "high" if fine >= 5000 else "medium"
        }
    elif event_type == "ambulance_detected":
        data = {
            "ambulance_id": f"AMB-KA-{random.randint(100,999)}",
            "plate": f"KA{random.randint(1,50):02d}G{random.randint(1000,9999)}",
            "hospital": random.choice(["Manipal Hospital","Fortis","Apollo","Narayana Health"]),
            "signals_cleared": random.randint(4,8), "eta_minutes": random.randint(8,20),
            "saved_minutes": round(random.uniform(12,20),1),
            "icon": "🚑", "severity": "emergency"
        }
    elif event_type == "accident_detected":
        data = {
            "plate": plate, "severity": random.choice(["minor","moderate","severe"]),
            "vehicle_count": random.randint(2,4),
            "location": loc_name, "services_dispatched": random.randint(2,4),
            "response_time_sec": round(random.uniform(8,12),1),
            "icon": "💥", "severity_level": "critical"
        }
    elif event_type == "emission_alert":
        smoke = random.choice(["black","white","blue"])
        data = {
            "plate": plate, "smoke_color": smoke,
            "emission_level": round(random.uniform(65,95),1),
            "fine": 5000 if smoke=="black" else 3000,
            "maintenance": "required", "icon": "💨", "severity": "medium"
        }
    elif event_type == "drunk_driving_alert":
        conf = round(random.uniform(65,97),1)
        data = {
            "plate": plate, "confidence": conf,
            "eye_blink_rate": round(random.uniform(1,5),1),
            "lane_deviations": random.randint(2,6),
            "action": "police_dispatched" if conf>80 else "sms_sent",
            "fine": 10000, "icon": "🍺", "severity": "high"
        }
    elif event_type == "parking_violation":
        duration = random.randint(30,180)
        data = {
            "plate": plate, "zone": random.choice(["No-Parking Zone","Hospital Zone","School Zone"]),
            "duration_minutes": duration, "fine": random.choice([500,1000,2000,5000]),
            "tow_requested": duration > 120,
            "icon": "🚗", "severity": "low"
        }
    elif event_type == "near_miss_detected":
        dist = random.randint(80,400)
        data = {
            "plate": plate, "distance_cm": dist,
            "danger": "CRITICAL" if dist<200 else "HIGH",
            "pedestrian_count": random.randint(1,3),
            "speed_kmh": round(random.uniform(30,65),1),
            "icon": "⚠️", "severity": "high"
        }
    elif event_type == "toll_processed":
        cat = random.choice(["car","two_wheeler","suv","truck","bus"])
        rates = {"car":15,"two_wheeler":5,"suv":25,"truck":50,"bus":30}
        data = {
            "plate": plate, "vehicle_category": cat,
            "toll_amount": rates.get(cat,15),
            "processing_time_sec": 0, "wait_time_saved_sec": 300,
            "plaza": random.choice(["Hosur Road Toll","Tumkur Road Toll","Mysore Road Toll"]),
            "icon": "🏎️", "severity": "info"
        }
    elif event_type == "ev_charging_started":
        data = {
            "plate": plate, "station": random.choice(["Tata Power Koramangala","ChargeZone ITPL","Ather Grid HSR"]),
            "charging_speed_kw": random.choice([7.2,22,50,150]),
            "battery_start_pct": random.randint(15,40),
            "green_points_earned": random.randint(50,200),
            "icon": "⚡", "severity": "info"
        }
    elif event_type == "hazard_reported":
        data = {
            "hazard_type": random.choice(["pothole","debris","fallen_tree","oil_spill"]),
            "location": loc_name, "severity": random.randint(1,5),
            "ai_verified": random.random() > 0.3,
            "department": random.choice(["BBMP Roads","BDA","BESCOM"]),
            "icon": "🚧", "severity_level": "medium"
        }
    elif event_type == "school_zone_violation":
        data = {
            "plate": plate, "school": random.choice(["DPS Whitefield","Bishop Cotton","National Public School"]),
            "detected_speed": random.randint(35,65), "speed_limit": 20,
            "fine": 5000, "school_hours": True,
            "icon": "🏫", "severity": "high"
        }
    elif event_type == "risk_score_updated":
        score = round(random.uniform(10,95),1)
        data = {
            "plate": plate, "risk_score": score,
            "category": "red" if score>80 else "orange" if score>60 else "yellow" if score>30 else "green",
            "insurance_impact": f"+{int((score-30)*2)}%" if score>30 else f"-{int((30-score)*0.5)}%",
            "icon": "📊", "severity": "info"
        }
    elif event_type == "signal_optimized":
        data = {
            "intersection": loc_name, "old_green_sec": random.randint(30,60),
            "new_green_sec": random.randint(35,90),
            "vehicles_benefited": random.randint(50,200),
            "time_saved_sec": random.randint(8,25),
            "icon": "🚦", "severity": "info"
        }
    elif event_type == "insurance_claim_filed":
        data = {
            "plate": plate, "claim_type": random.choice(["accident","violation"]),
            "claim_amount": random.randint(5000,150000),
            "fraud_score": round(random.uniform(5,45),1),
            "auto_approved": random.random() > 0.5,
            "icon": "📋", "severity": "info"
        }
    else:  # blacklist_alert
        data = {
            "plate": plate, "reason": random.choice(["Stolen vehicle","Wanted criminal","Outstanding fines","Insurance fraud"]),
            "severity": random.choice(["CRITICAL","HIGH","MEDIUM"]),
            "alert_sent_to": "Nearest Police Station",
            "icon": "🚨", "severity_level": "critical"
        }

    data.update({"event_id": event_id, "event_type": event_type,
                 "timestamp": ts, "camera_id": cam_id, "location_name": loc_name,
                 "lat": lat + random.uniform(-0.001,0.001),
                 "lng": lng + random.uniform(-0.001,0.001)})
    return data


def save_event(event_data):
    """Save generated event to ai_dataset_events table."""
    try:
        conn = _get_conn()
        conn.execute("""INSERT OR IGNORE INTO ai_dataset_events
            (event_id, event_type, event_data, confidence, camera_id, location_name, generated_at)
            VALUES (?,?,?,?,?,?,?)""",
            (event_data['event_id'], event_data['event_type'],
             json.dumps(event_data), event_data.get('confidence', 95.0),
             event_data.get('camera_id', 'CAM-01'),
             event_data.get('location_name', 'Unknown'),
             event_data['timestamp']))
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_recent_events(limit=20, event_type=None):
    """Get recent AI-generated events for dashboard."""
    try:
        conn = _get_conn()
        if event_type:
            rows = conn.execute(
                "SELECT * FROM ai_dataset_events WHERE event_type=? ORDER BY generated_at DESC LIMIT ?",
                (event_type, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ai_dataset_events ORDER BY generated_at DESC LIMIT ?",
                (limit,)).fetchall()
        conn.close()
        result = []
        for r in rows:
            try:
                d = json.loads(r[2])  # event_data column
                result.append(d)
            except Exception:
                pass
        return result
    except Exception:
        return [generate_single_event() for _ in range(limit)]


def get_live_feed_data(limit=15):
    """Get mixed live feed for dashboard ticker."""
    events = get_recent_events(limit=limit)
    if len(events) < limit:
        events.extend([generate_single_event() for _ in range(limit - len(events))])
    return events[:limit]


def get_realtime_kpis():
    """Return live KPI metrics for dashboard counters."""
    hour = datetime.now().hour
    base_violations = 120 + (80 if 8<=hour<=10 or 17<=hour<=20 else 20)
    return {
        "violations_today": random.randint(base_violations-20, base_violations+20),
        "fines_collected_today": random.randint(150000, 400000),
        "cameras_active": random.randint(8, 10),
        "challans_issued_today": random.randint(80, 180),
        "ambulances_cleared_today": random.randint(3, 8),
        "accidents_detected_today": random.randint(1, 5),
        "near_misses_today": random.randint(8, 20),
        "ev_sessions_today": random.randint(25, 80),
        "toll_transactions_today": random.randint(800, 2500),
        "hazards_reported_today": random.randint(2, 12),
        "school_zone_violations_today": random.randint(3, 15),
        "drunk_driving_alerts_today": random.randint(2, 8),
        "lives_saved_estimate": round(random.uniform(0.5, 2.5), 1),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_city_stats():
    """Return city-wide traffic statistics."""
    return {
        "total_violations_recorded": random.randint(8500, 12000),
        "total_fines_collected": random.randint(15000000, 25000000),
        "total_challans_issued": random.randint(6000, 9000),
        "payment_rate_pct": round(random.uniform(68, 82), 1),
        "cameras_deployed": 10,
        "coverage_area_km2": 720,
        "total_vehicles_monitored_today": random.randint(45000, 80000),
        "avg_detection_confidence_pct": 97.4,
        "uptime_pct": 99.2,
        "city": "Bengaluru, Karnataka",
        "deployment_date": "2026-01-15"
    }


def _generator_loop(interval_seconds=8):
    """Background thread: generates events every N seconds."""
    while not _stop_event.is_set():
        try:
            event = generate_single_event()
            save_event(event)
        except Exception:
            pass
        _stop_event.wait(interval_seconds)


def start_generator(interval_seconds=8):
    """Start the background AI dataset generator thread."""
    global _generator_thread, _stop_event
    _stop_event.clear()
    _generator_thread = threading.Thread(
        target=_generator_loop, args=(interval_seconds,), daemon=True)
    _generator_thread.start()
    return {"status": "started", "interval_seconds": interval_seconds}


def stop_generator():
    """Stop the background generator."""
    global _stop_event
    _stop_event.set()
    return {"status": "stopped"}
