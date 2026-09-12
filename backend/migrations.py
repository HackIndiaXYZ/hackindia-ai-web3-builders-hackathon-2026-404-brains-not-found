"""
TrafficGuard Pro — Complete Database Migration Script
Creates all 53 tables across all 35 features with proper indexes.
Run: python migrations.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'violations.db')
conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")
c = conn.cursor()

# ─── CORE TABLES ──────────────────────────────────────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS cameras (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE,
    latitude REAL,
    longitude REAL,
    rtsp_url TEXT,
    sector TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS trajectories (
    id TEXT PRIMARY KEY,
    plate_text TEXT,
    camera_start_id TEXT,
    time_start TIMESTAMP,
    camera_end_id TEXT,
    time_end TIMESTAMP,
    distance_km REAL,
    FOREIGN KEY(camera_start_id) REFERENCES cameras(id),
    FOREIGN KEY(camera_end_id) REFERENCES cameras(id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS trajectory_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trajectory_id TEXT,
    camera_id TEXT,
    plate_text TEXT,
    latitude REAL,
    longitude REAL,
    timestamp TIMESTAMP,
    FOREIGN KEY(trajectory_id) REFERENCES trajectories(id),
    FOREIGN KEY(camera_id) REFERENCES cameras(id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS blacklist (
    plate_text TEXT PRIMARY KEY,
    reason TEXT,
    severity TEXT DEFAULT 'medium',
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS heatmap_cells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_lat REAL,
    grid_lng REAL,
    vehicle_count INTEGER DEFAULT 0,
    accident_count INTEGER DEFAULT 0,
    timestamp_hour TIMESTAMP
)''')

# ─── FEATURE 21: AMBULANCE AUTO-ROUTE CLEAR ───────────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS emergency_vehicles (
    emergency_id TEXT PRIMARY KEY,
    ambulance_id TEXT,
    license_plate TEXT,
    hospital_code TEXT,
    status TEXT DEFAULT 'active',
    route TEXT,
    eta INTEGER,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS emergency_routes (
    route_id TEXT PRIMARY KEY,
    ambulance_id TEXT,
    start_lat REAL,
    start_lng REAL,
    end_lat REAL,
    end_lng REAL,
    waypoints TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    saved_minutes REAL DEFAULT 0
)''')

c.execute('''CREATE TABLE IF NOT EXISTS emergency_alerts (
    alert_id TEXT PRIMARY KEY,
    ambulance_id TEXT,
    vehicle_plate TEXT,
    alert_type TEXT,
    action_taken TEXT,
    response_time_seconds REAL,
    saved_minutes REAL,
    fine_issued INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS traffic_light_overrides (
    override_id TEXT PRIMARY KEY,
    intersection_id TEXT,
    ambulance_id TEXT,
    original_phase TEXT,
    new_phase TEXT DEFAULT 'GREEN',
    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reverted_at TIMESTAMP,
    status TEXT DEFAULT 'active'
)''')

# ─── FEATURE 22: ACCIDENT DETECTION & AUTO-DISPATCH ──────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS accident_records (
    accident_id TEXT PRIMARY KEY,
    camera_id TEXT,
    location_lat REAL,
    location_lng REAL,
    location_name TEXT,
    severity TEXT DEFAULT 'moderate',
    vehicle_count INTEGER DEFAULT 2,
    victim_count INTEGER DEFAULT 0,
    detection_confidence REAL,
    video_path TEXT,
    frame_path TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active'
)''')

c.execute('''CREATE TABLE IF NOT EXISTS accident_dispatches (
    dispatch_id TEXT PRIMARY KEY,
    accident_id TEXT,
    service_type TEXT,
    service_name TEXT,
    eta_minutes INTEGER,
    contact_number TEXT,
    dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    arrived_at TIMESTAMP,
    status TEXT DEFAULT 'dispatched',
    FOREIGN KEY(accident_id) REFERENCES accident_records(accident_id)
)''')

# ─── FEATURE 23: EMISSION & AIR QUALITY MONITORING ───────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS emission_data (
    reading_id TEXT PRIMARY KEY,
    vehicle_plate TEXT,
    emission_level REAL DEFAULT 0,
    smoke_color TEXT DEFAULT 'clear',
    pm25_level REAL,
    co2_level REAL,
    nox_level REAL,
    vehicle_type TEXT,
    fuel_type TEXT DEFAULT 'petrol',
    bs_standard TEXT DEFAULT 'BS-VI',
    compliant INTEGER DEFAULT 1,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location_lat REAL,
    location_lng REAL,
    camera_id TEXT,
    fine_issued INTEGER DEFAULT 0,
    fine_amount REAL DEFAULT 0
)''')

c.execute('''CREATE TABLE IF NOT EXISTS pollution_hotspots (
    hotspot_id TEXT PRIMARY KEY,
    area_name TEXT,
    latitude REAL,
    longitude REAL,
    avg_emission_level REAL,
    peak_hour INTEGER,
    vehicle_types_present TEXT,
    aqi_index REAL,
    health_advisory TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS vehicle_emission_score (
    plate_text TEXT PRIMARY KEY,
    avg_emission_score REAL DEFAULT 0,
    total_readings INTEGER DEFAULT 0,
    maintenance_status TEXT DEFAULT 'good',
    last_fine_date TIMESTAMP,
    last_service_date TIMESTAMP,
    bs_standard TEXT DEFAULT 'BS-VI',
    fuel_type TEXT DEFAULT 'petrol',
    vehicle_age_years INTEGER DEFAULT 0
)''')

c.execute('''CREATE TABLE IF NOT EXISTS eco_rewards (
    reward_id TEXT PRIMARY KEY,
    plate_text TEXT,
    green_points INTEGER DEFAULT 0,
    cashback_amount REAL DEFAULT 0,
    electric_vehicle_status INTEGER DEFAULT 0,
    fine_discount_percent REAL DEFAULT 0,
    last_reward_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_co2_saved_kg REAL DEFAULT 0
)''')

# ─── FEATURE 24: DRUNK DRIVING DETECTION ─────────────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS drunk_driving_alerts (
    alert_id TEXT PRIMARY KEY,
    vehicle_plate TEXT,
    driver_description TEXT,
    eye_blink_rate REAL,
    lane_deviation_count INTEGER DEFAULT 0,
    speed_variance REAL,
    detection_method TEXT,
    confidence_score REAL,
    time_of_day INTEGER,
    action_taken TEXT,
    officer_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location_lat REAL,
    location_lng REAL,
    location_name TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS driver_behavior_profile (
    profile_id TEXT PRIMARY KEY,
    plate_text TEXT UNIQUE,
    avg_eye_blink_rate REAL DEFAULT 15,
    lane_changes_per_km REAL DEFAULT 0.5,
    speed_variance REAL DEFAULT 5,
    reaction_time_ms REAL DEFAULT 350,
    night_driving_incidents INTEGER DEFAULT 0,
    total_observations INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS drunk_driving_offenders (
    offender_id TEXT PRIMARY KEY,
    plate_text TEXT,
    offense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fine_amount REAL DEFAULT 10000,
    bac_level REAL,
    license_status TEXT DEFAULT 'suspended',
    suspension_days INTEGER DEFAULT 90,
    rehabilitation_status TEXT DEFAULT 'pending',
    court_date TIMESTAMP,
    officer_id TEXT
)''')

# ─── FEATURE 25: AUTOMATED PARKING ENFORCEMENT ───────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS parking_zones (
    zone_id TEXT PRIMARY KEY,
    zone_name TEXT,
    zone_type TEXT DEFAULT 'no_parking',
    latitude REAL,
    longitude REAL,
    radius_meters REAL DEFAULT 100,
    start_time TEXT DEFAULT '00:00',
    end_time TEXT DEFAULT '23:59',
    days_active TEXT DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat,Sun',
    fine_amount REAL DEFAULT 500,
    tow_threshold_minutes INTEGER DEFAULT 120,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS parking_violations (
    violation_id TEXT PRIMARY KEY,
    vehicle_plate TEXT,
    zone_id TEXT,
    zone_name TEXT,
    violation_type TEXT DEFAULT 'illegal_parking',
    entry_time TIMESTAMP,
    detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_minutes REAL DEFAULT 0,
    fine_amount REAL DEFAULT 500,
    fine_issued INTEGER DEFAULT 1,
    sms_sent INTEGER DEFAULT 0,
    tow_requested INTEGER DEFAULT 0,
    payment_status TEXT DEFAULT 'unpaid',
    payment_date TIMESTAMP,
    FOREIGN KEY(zone_id) REFERENCES parking_zones(zone_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS towing_records (
    tow_id TEXT PRIMARY KEY,
    violation_id TEXT,
    vehicle_plate TEXT,
    towing_service TEXT,
    driver_name TEXT,
    contact_number TEXT,
    towing_charge REAL DEFAULT 5000,
    storage_charge_per_day REAL DEFAULT 200,
    total_days INTEGER DEFAULT 0,
    towing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    release_date TIMESTAMP,
    tow_yard_address TEXT,
    status TEXT DEFAULT 'towed',
    FOREIGN KEY(violation_id) REFERENCES parking_violations(violation_id)
)''')

# ─── FEATURE 26: DRIVER BEHAVIOR RISK SCORING ────────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS driver_risk_profile (
    driver_id TEXT PRIMARY KEY,
    plate_text TEXT UNIQUE,
    owner_name TEXT,
    risk_score REAL DEFAULT 10,
    category TEXT DEFAULT 'green',
    violation_count INTEGER DEFAULT 0,
    severity_score REAL DEFAULT 0,
    recency_score REAL DEFAULT 0,
    behavior_score REAL DEFAULT 0,
    insurance_premium_multiplier REAL DEFAULT 1.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS driver_behavior_history (
    behavior_id TEXT PRIMARY KEY,
    driver_id TEXT,
    plate_text TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    behavior_type TEXT,
    risk_points REAL DEFAULT 0,
    description TEXT,
    location_lat REAL,
    location_lng REAL,
    location_name TEXT,
    FOREIGN KEY(driver_id) REFERENCES driver_risk_profile(driver_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS driver_training_records (
    training_id TEXT PRIMARY KEY,
    driver_id TEXT,
    plate_text TEXT,
    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    training_type TEXT,
    provider TEXT,
    pass_fail TEXT DEFAULT 'PENDING',
    score REAL DEFAULT 0,
    score_improvement REAL DEFAULT 0,
    certificate_issued INTEGER DEFAULT 0,
    FOREIGN KEY(driver_id) REFERENCES driver_risk_profile(driver_id)
)''')

# ─── FEATURE 27: PEDESTRIAN SAFETY & NEAR-MISS ───────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS pedestrian_detections (
    detection_id TEXT PRIMARY KEY,
    camera_id TEXT,
    location_lat REAL,
    location_lng REAL,
    location_name TEXT,
    pedestrian_count INTEGER DEFAULT 1,
    child_count INTEGER DEFAULT 0,
    elderly_count INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    zone_type TEXT DEFAULT 'normal'
)''')

c.execute('''CREATE TABLE IF NOT EXISTS near_miss_incidents (
    incident_id TEXT PRIMARY KEY,
    vehicle_plate TEXT,
    camera_id TEXT,
    pedestrian_count INTEGER DEFAULT 1,
    min_distance_cm REAL,
    danger_level TEXT DEFAULT 'medium',
    vehicle_speed_kmh REAL,
    braking_event INTEGER DEFAULT 0,
    alert_sent INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location_lat REAL,
    location_lng REAL,
    location_name TEXT,
    zone_type TEXT DEFAULT 'normal'
)''')

c.execute('''CREATE TABLE IF NOT EXISTS pedestrian_hotspots (
    hotspot_id TEXT PRIMARY KEY,
    area_name TEXT,
    latitude REAL,
    longitude REAL,
    incident_count INTEGER DEFAULT 0,
    child_count INTEGER DEFAULT 0,
    elderly_count INTEGER DEFAULT 0,
    peak_hour INTEGER,
    risk_score REAL DEFAULT 50,
    recommended_action TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# ─── FEATURE 28: PREDICTIVE ACCIDENT RISK ZONES ──────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS accident_predictions (
    prediction_id TEXT PRIMARY KEY,
    location_lat REAL,
    location_lng REAL,
    location_name TEXT,
    risk_score REAL DEFAULT 50,
    risk_zone TEXT DEFAULT 'yellow',
    predicted_time_window TEXT,
    weather_factor TEXT DEFAULT 'clear',
    traffic_density_factor REAL DEFAULT 0.5,
    historical_accident_count INTEGER DEFAULT 0,
    action_taken TEXT,
    accuracy REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS risk_zone_history (
    history_id TEXT PRIMARY KEY,
    prediction_id TEXT,
    location_name TEXT,
    prediction_accuracy REAL DEFAULT 0,
    interventions_used TEXT,
    accidents_prevented INTEGER DEFAULT 0,
    police_deployed INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(prediction_id) REFERENCES accident_predictions(prediction_id)
)''')

# ─── FEATURE 30: REAL-TIME INSURANCE CLAIM FILING ────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS insurance_claims (
    claim_id TEXT PRIMARY KEY,
    violation_id INTEGER,
    accident_id TEXT,
    vehicle_plate TEXT,
    owner_name TEXT,
    claim_type TEXT DEFAULT 'accident',
    claim_amount REAL DEFAULT 0,
    severity_assessment TEXT DEFAULT 'minor',
    evidence_video TEXT,
    evidence_photos TEXT,
    gps_coordinates TEXT,
    risk_score_at_time REAL DEFAULT 50,
    approval_status TEXT DEFAULT 'pending',
    approved_by TEXT,
    payout_amount REAL DEFAULT 0,
    payout_date TIMESTAMP,
    fraud_score REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS premium_calculation (
    calc_id TEXT PRIMARY KEY,
    vehicle_plate TEXT UNIQUE,
    owner_name TEXT,
    base_premium REAL DEFAULT 10000,
    risk_multiplier REAL DEFAULT 1.0,
    violation_surcharge REAL DEFAULT 0,
    safe_driver_discount REAL DEFAULT 0,
    ev_discount REAL DEFAULT 0,
    final_premium REAL DEFAULT 10000,
    discount_percentage REAL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS fraud_detection (
    fraud_id TEXT PRIMARY KEY,
    claim_id TEXT,
    fraud_score REAL DEFAULT 0,
    fraud_indicators TEXT,
    staged_accident_probability REAL DEFAULT 0,
    manually_reviewed INTEGER DEFAULT 0,
    reviewed_by TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(claim_id) REFERENCES insurance_claims(claim_id)
)''')

# ─── FEATURE 31: EV CHARGING STATION ROUTING ────────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS charging_stations (
    station_id TEXT PRIMARY KEY,
    station_name TEXT,
    operator TEXT,
    location_lat REAL,
    location_lng REAL,
    address TEXT,
    total_spots INTEGER DEFAULT 4,
    available_spots INTEGER DEFAULT 2,
    charging_speed_kw REAL DEFAULT 7.2,
    charger_type TEXT DEFAULT 'Type-2',
    pricing_per_hour REAL DEFAULT 8,
    network_id TEXT,
    amenities TEXT,
    status TEXT DEFAULT 'operational',
    rating REAL DEFAULT 4.2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS ev_routes (
    route_id TEXT PRIMARY KEY,
    vehicle_plate TEXT,
    start_lat REAL,
    start_lng REAL,
    end_lat REAL,
    end_lng REAL,
    battery_percent_start REAL DEFAULT 80,
    battery_percent_end REAL DEFAULT 20,
    recommended_station_id TEXT,
    detour_minutes REAL DEFAULT 3,
    total_range_km REAL DEFAULT 300,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(recommended_station_id) REFERENCES charging_stations(station_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS charging_reservations (
    reservation_id TEXT PRIMARY KEY,
    vehicle_plate TEXT,
    station_id TEXT,
    reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    charge_start_time TIMESTAMP,
    charge_end_time TIMESTAMP,
    charging_duration_minutes INTEGER DEFAULT 60,
    status TEXT DEFAULT 'active',
    amount_paid REAL DEFAULT 0,
    units_charged REAL DEFAULT 0,
    FOREIGN KEY(station_id) REFERENCES charging_stations(station_id)
)''')

# ─── FEATURE 32: CROWDSOURCED HAZARD REPORTING ───────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS hazard_reports (
    report_id TEXT PRIMARY KEY,
    hazard_type TEXT DEFAULT 'pothole',
    location_lat REAL,
    location_lng REAL,
    location_name TEXT,
    severity INTEGER DEFAULT 3,
    reporter_id TEXT,
    reporter_phone TEXT,
    photo_path TEXT,
    video_path TEXT,
    description TEXT,
    verification_count INTEGER DEFAULT 0,
    ai_verified INTEGER DEFAULT 0,
    ai_confidence REAL DEFAULT 0,
    status TEXT DEFAULT 'reported',
    priority_level TEXT DEFAULT 'medium',
    assigned_department TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS government_work_orders (
    order_id TEXT PRIMARY KEY,
    hazard_report_id TEXT,
    municipality_dept TEXT,
    assigned_contractor TEXT,
    work_type TEXT,
    priority TEXT DEFAULT 'medium',
    deadline TIMESTAMP,
    status TEXT DEFAULT 'pending',
    completion_date TIMESTAMP,
    completion_notes TEXT,
    cost_estimate REAL DEFAULT 0,
    actual_cost REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(hazard_report_id) REFERENCES hazard_reports(report_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS citizen_rewards (
    citizen_id TEXT PRIMARY KEY,
    phone_number TEXT UNIQUE,
    name TEXT,
    total_points INTEGER DEFAULT 0,
    vouchers_redeemed INTEGER DEFAULT 0,
    total_reports INTEGER DEFAULT 0,
    verified_reports INTEGER DEFAULT 0,
    rank INTEGER DEFAULT 0,
    last_reward_date TIMESTAMP
)''')

# ─── FEATURE 33: VEHICLE MAINTENANCE HEALTH CHECK ────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS vehicle_health_status (
    health_id TEXT PRIMARY KEY,
    vehicle_plate TEXT UNIQUE,
    headlights_status TEXT DEFAULT 'ok',
    brake_lights_status TEXT DEFAULT 'ok',
    indicators_status TEXT DEFAULT 'ok',
    windshield_status TEXT DEFAULT 'ok',
    wipers_status TEXT DEFAULT 'ok',
    tires_status TEXT DEFAULT 'ok',
    engine_status TEXT DEFAULT 'ok',
    suspension_status TEXT DEFAULT 'ok',
    exhaust_status TEXT DEFAULT 'ok',
    overall_score REAL DEFAULT 100,
    maintenance_required INTEGER DEFAULT 0,
    last_inspection TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_service_date TIMESTAMP,
    next_service_due TIMESTAMP,
    fine_issued INTEGER DEFAULT 0,
    certificate_url TEXT,
    certificate_valid_until TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS faulty_vehicle_reports (
    report_id TEXT PRIMARY KEY,
    vehicle_plate TEXT,
    fault_type TEXT,
    severity TEXT DEFAULT 'medium',
    detected_by TEXT DEFAULT 'ai_camera',
    camera_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location_lat REAL,
    location_lng REAL,
    location_name TEXT,
    sms_sent INTEGER DEFAULT 0,
    fine_issued INTEGER DEFAULT 0,
    fine_amount REAL DEFAULT 0,
    resolved INTEGER DEFAULT 0,
    resolved_at TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS service_center_leads (
    lead_id TEXT PRIMARY KEY,
    vehicle_plate TEXT,
    owner_phone TEXT,
    service_requirement TEXT,
    fault_types TEXT,
    contacted_centers TEXT,
    nearest_center TEXT,
    center_address TEXT,
    appointment_date TIMESTAMP,
    status TEXT DEFAULT 'pending',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# ─── FEATURE 34: SCHOOL ZONE & CHILD SAFETY ──────────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS schools (
    school_id TEXT PRIMARY KEY,
    school_name TEXT,
    school_type TEXT DEFAULT 'secondary',
    location_lat REAL,
    location_lng REAL,
    address TEXT,
    zone_radius_m INTEGER DEFAULT 500,
    school_timings_start TEXT DEFAULT '08:00',
    school_timings_end TEXT DEFAULT '14:30',
    afternoon_session_end TEXT DEFAULT '18:00',
    student_count INTEGER DEFAULT 500,
    camera_count INTEGER DEFAULT 2,
    extra_police_deployed INTEGER DEFAULT 0
)''')

c.execute('''CREATE TABLE IF NOT EXISTS school_zone_violations (
    violation_id TEXT PRIMARY KEY,
    vehicle_plate TEXT,
    school_id TEXT,
    school_name TEXT,
    violation_type TEXT DEFAULT 'speeding',
    detected_speed_kmh REAL,
    allowed_speed_kmh REAL DEFAULT 20,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location_lat REAL,
    location_lng REAL,
    fine_amount REAL DEFAULT 5000,
    challan_issued INTEGER DEFAULT 0,
    school_hours INTEGER DEFAULT 1,
    FOREIGN KEY(school_id) REFERENCES schools(school_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS school_bus_tracking (
    bus_id TEXT PRIMARY KEY,
    school_id TEXT,
    bus_number TEXT,
    driver_name TEXT,
    driver_phone TEXT,
    route_name TEXT,
    capacity INTEGER DEFAULT 40,
    student_count_today INTEGER DEFAULT 0,
    current_location_lat REAL,
    current_location_lng REAL,
    current_address TEXT,
    speed_kmh REAL DEFAULT 0,
    status TEXT DEFAULT 'parked',
    next_stop TEXT,
    eta_minutes INTEGER DEFAULT 0,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(school_id) REFERENCES schools(school_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS parent_alerts (
    alert_id TEXT PRIMARY KEY,
    bus_id TEXT,
    school_id TEXT,
    alert_type TEXT DEFAULT 'bus_departed',
    message TEXT,
    parent_count INTEGER DEFAULT 0,
    sms_sent INTEGER DEFAULT 0,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(bus_id) REFERENCES school_bus_tracking(bus_id)
)''')

# ─── FEATURE 35: TOLL PLAZA AUTOMATION ───────────────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS toll_plazas (
    plaza_id TEXT PRIMARY KEY,
    plaza_name TEXT,
    highway TEXT,
    location_lat REAL,
    location_lng REAL,
    direction TEXT DEFAULT 'both',
    lanes INTEGER DEFAULT 4,
    status TEXT DEFAULT 'operational',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS toll_transactions (
    transaction_id TEXT PRIMARY KEY,
    vehicle_plate TEXT,
    plaza_id TEXT,
    vehicle_category TEXT DEFAULT 'car',
    toll_amount REAL DEFAULT 15,
    dynamic_multiplier REAL DEFAULT 1.0,
    final_amount REAL DEFAULT 15,
    payment_method TEXT DEFAULT 'auto_deduct',
    payment_status TEXT DEFAULT 'paid',
    exemption_type TEXT,
    vehicle_speed_kmh REAL DEFAULT 60,
    ocr_confidence REAL DEFAULT 97.4,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    receipt_sent INTEGER DEFAULT 0,
    FOREIGN KEY(plaza_id) REFERENCES toll_plazas(plaza_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS toll_plaza_earnings (
    earning_id TEXT PRIMARY KEY,
    plaza_id TEXT,
    date TEXT,
    daily_revenue REAL DEFAULT 0,
    weekly_revenue REAL DEFAULT 0,
    monthly_revenue REAL DEFAULT 0,
    total_vehicles INTEGER DEFAULT 0,
    exempted_vehicles INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(plaza_id) REFERENCES toll_plazas(plaza_id)
)''')

# ─── FEATURE 29: V2I / TRAFFIC SIGNAL INTELLIGENCE ───────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS traffic_signals (
    signal_id TEXT PRIMARY KEY,
    intersection_name TEXT,
    location_lat REAL,
    location_lng REAL,
    current_phase TEXT DEFAULT 'RED',
    green_duration_sec INTEGER DEFAULT 45,
    red_duration_sec INTEGER DEFAULT 60,
    yellow_duration_sec INTEGER DEFAULT 5,
    vehicle_count_ns INTEGER DEFAULT 0,
    vehicle_count_ew INTEGER DEFAULT 0,
    ai_optimized INTEGER DEFAULT 0,
    emergency_override INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE IF NOT EXISTS signal_optimization_log (
    log_id TEXT PRIMARY KEY,
    signal_id TEXT,
    original_green_sec INTEGER,
    new_green_sec INTEGER,
    vehicle_count INTEGER,
    optimization_reason TEXT,
    time_saved_sec INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(signal_id) REFERENCES traffic_signals(signal_id)
)''')

# ─── AI DATASET GENERATOR TRACKING ───────────────────────────────────────────

c.execute('''CREATE TABLE IF NOT EXISTS ai_dataset_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT,
    event_data TEXT,
    confidence REAL DEFAULT 95.0,
    camera_id TEXT,
    location_name TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    displayed INTEGER DEFAULT 0
)''')

# ─── INDEXES FOR PERFORMANCE ──────────────────────────────────────────────────

indexes = [
    ("idx_traj_plate", "trajectories(plate_text)"),
    ("idx_traj_points_plate", "trajectory_points(plate_text)"),
    ("idx_traj_points_ts", "trajectory_points(timestamp)"),
    ("idx_emergency_status", "emergency_vehicles(status)"),
    ("idx_emergency_routes_amb", "emergency_routes(ambulance_id)"),
    ("idx_emission_plate", "emission_data(vehicle_plate)"),
    ("idx_emission_ts", "emission_data(timestamp)"),
    ("idx_drunk_plate", "drunk_driving_alerts(vehicle_plate)"),
    ("idx_drunk_ts", "drunk_driving_alerts(timestamp)"),
    ("idx_parking_viol_plate", "parking_violations(vehicle_plate)"),
    ("idx_parking_viol_status", "parking_violations(payment_status)"),
    ("idx_risk_plate", "driver_risk_profile(plate_text)"),
    ("idx_risk_score", "driver_risk_profile(risk_score)"),
    ("idx_risk_category", "driver_risk_profile(category)"),
    ("idx_ped_detect_ts", "pedestrian_detections(timestamp)"),
    ("idx_near_miss_plate", "near_miss_incidents(vehicle_plate)"),
    ("idx_near_miss_ts", "near_miss_incidents(timestamp)"),
    ("idx_accident_pred_ts", "accident_predictions(created_at)"),
    ("idx_accident_pred_risk", "accident_predictions(risk_score)"),
    ("idx_insurance_plate", "insurance_claims(vehicle_plate)"),
    ("idx_insurance_status", "insurance_claims(approval_status)"),
    ("idx_ev_station_lat", "charging_stations(location_lat)"),
    ("idx_ev_station_lng", "charging_stations(location_lng)"),
    ("idx_hazard_type", "hazard_reports(hazard_type)"),
    ("idx_hazard_status", "hazard_reports(status)"),
    ("idx_hazard_ts", "hazard_reports(created_at)"),
    ("idx_vehicle_health_plate", "vehicle_health_status(vehicle_plate)"),
    ("idx_school_zone_viol_plate", "school_zone_violations(vehicle_plate)"),
    ("idx_school_zone_viol_ts", "school_zone_violations(timestamp)"),
    ("idx_bus_school", "school_bus_tracking(school_id)"),
    ("idx_toll_plate", "toll_transactions(vehicle_plate)"),
    ("idx_toll_ts", "toll_transactions(timestamp)"),
    ("idx_toll_status", "toll_transactions(payment_status)"),
    ("idx_signal_intersection", "traffic_signals(intersection_name)"),
    ("idx_ai_events_type", "ai_dataset_events(event_type)"),
    ("idx_ai_events_ts", "ai_dataset_events(generated_at)"),
]

for idx_name, idx_target in indexes:
    c.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_target}")

conn.commit()
conn.close()
print("All 53 database tables and indexes created successfully.")
print("Run seed_advanced.py to populate with realistic demo data.")
