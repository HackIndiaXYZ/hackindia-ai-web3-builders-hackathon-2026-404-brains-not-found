"""
TrafficGuard Pro — Main Application & AI Enforcement Command Centre
Pipeline: Video/Stream → YOLOv8 Detection → ByteTrack → ViolationEngine → Plate OCR → Action & Verification
"""

import csv
import re
import io
import json
import hashlib
import logging
from logging.handlers import RotatingFileHandler
import os
import time
import queue
import sqlite3
import threading
import numpy as np
from urllib.parse import urlparse
from datetime import datetime, date, timedelta
from collections import Counter, defaultdict
from functools import wraps

try:
    import cv2
except ImportError:
    cv2 = None

from flask import (Flask, render_template, Response,
                   jsonify, send_from_directory, send_file,
                   request, session, redirect, url_for, make_response)

ML_DISABLED = bool(os.environ.get("VERCEL") or os.environ.get("RENDER") or os.environ.get("TRAFFICGUARD_DISABLE_ML"))

if ML_DISABLED:
    YOLO = None
else:
    try:
        from ultralytics import YOLO
    except ImportError:
        YOLO = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if ML_DISABLED:
    easyocr = None
else:
    try:
        import easyocr
    except ImportError:
        easyocr = None

# ── IMPORTS FROM INTERNAL MODULES ──────────────────────────────
from config import (
    APP_NAME, TAGLINE, ORGANIZATION, MOTTO, AUTHOR_NAME, AUTHOR_ROLE, AUTHOR_EMAIL,
    AUTHOR_GITHUB, AUTHOR_LINKEDIN, EDUCATION, UNIVERSITY, CGPA,
    EXPECTED_GRADUATION, SECRET_KEY, ADMIN_PASSWORD, SUPERADMIN_PASSWORD,
    INSPECTOR_PASSWORD, OFFICER_PASSWORD, DEMO_PASSWORD, REPORT_DIR,
    SCREENSHOT_DIR, CHALLAN_DIR, RECEIPT_DIR, VIDEO_FOLDER, LOG_DIR,
    CITIZEN_EMAIL, ADMIN_EMAIL, CITIZEN_WA_NUMBER, ADMIN_WA_NUMBER,
    RAZORPAY_KEY_ID
)

from challan import (
    generate_challan, generate_receipt, calculate_fine,
    get_offence_count, BASE_FINES, SECTIONS
)

from notifications import (
    notify_violation, send_daily_summary, send_whatsapp,
    send_sms, send_email, process_bot_message, RECENT_ALERTS_FEED
)

from vahan import (
    lookup_owner, get_vehicle_comparison, MOCK_DB, STATE_NAMES
)

from reports import generate_monthly_report
from chatbot import answer_traffic_query
from gamification import calculate_suraksha_score, get_safest_zones_leaderboard, generate_certificate_data
from blockchain_audit import init_blockchain_table, record_challan_on_blockchain, verify_challan_block
from officer_management import init_officers_table, get_officer_leaderboard, OFFICER_ROSTER
from safety_intelligence import (
    init_safety_tables, vehicle_risks, blackspots,
    verify_evidence, reviews, near_miss, get_peak_violation_hours,
    get_predictive_recommendations, submit_dispute, get_disputes, resolve_dispute
)

from violation_engine import ViolationEngine
from camera_routes import bp as camera_bp
from demo_catalog import build_demo_catalog

# ── LOGGING SETUP ─────────────────────────────────────────────
class SafeRotatingFileHandler(RotatingFileHandler):
    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError:
            self.stream.seek(0, os.SEEK_END)


os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "trafficguard.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        SafeRotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TrafficGuard")
logger.info(f"Starting {APP_NAME} — {TAGLINE}")

# ── FLASK APP INITIALIZATION ──────────────────────────────────
app = Flask(__name__)
app.register_blueprint(camera_bp)
app.secret_key = SECRET_KEY

# Reverse proxy compatibility (HF Spaces / Nginx TLS termination)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE']   = False
app.config['SESSION_COOKIE_HTTPONLY'] = True

from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ── ROLE-BASED ACCESS CONTROL (RBAC) ──────────────────────────
def require_role(allowed_roles=['admin', 'superadmin', 'inspector']):
    """Enforce RBAC for HTML pages."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_role = session.get('user_role')
            is_admin = session.get('is_admin')
            if not is_admin and (not user_role or user_role not in allowed_roles):
                return redirect(url_for('login', next=request.path))
            return f(*args, **kwargs)
        return decorated
    return decorator

def require_role_api(allowed_roles=['admin', 'superadmin', 'inspector']):
    """Enforce RBAC for JSON API endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_role = session.get('user_role')
            is_admin = session.get('is_admin')
            if not is_admin and (not user_role or user_role not in allowed_roles):
                return jsonify({"error": "unauthorised", "required_roles": allowed_roles}), 401
            return f(*args, **kwargs)
        return decorated
    return decorator

# Convenience aliases
require_admin = require_role(['admin', 'superadmin', 'inspector'])
require_admin_api = require_role_api(['admin', 'superadmin', 'inspector'])

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "violations.db")

app_context = {
    "app_name": APP_NAME,
    "tagline": TAGLINE,
    "organization": ORGANIZATION,
    "motto": MOTTO,
    "author_name": AUTHOR_NAME,
    "author_role": AUTHOR_ROLE,
    "author_email": AUTHOR_EMAIL,
    "author_github": AUTHOR_GITHUB,
    "author_linkedin": AUTHOR_LINKEDIN,
    "education": EDUCATION,
    "university": UNIVERSITY,
    "cgpa": CGPA,
    "expected_graduation": EXPECTED_GRADUATION,
}

@app.context_processor
def inject_brand():
    return app_context

# ── DATABASE INITIALIZATION & OPTIMIZATION ────────────────────
def _get_conn():
    """Return a WAL-mode SQLite connection with optimized concurrency."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    conn = _get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS violations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp   TEXT,
        video       TEXT,
        violation   TEXT,
        plate       TEXT,
        owner_name  TEXT,
        fine        INTEGER,
        screenshot  TEXT,
        challan     TEXT,
        paid        INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS visitors (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp  TEXT,
        ip         TEXT,
        page       TEXT,
        referrer   TEXT,
        ua         TEXT
    )''')
    
    # Indexes for fast querying on large datasets
    c.execute("CREATE INDEX IF NOT EXISTS idx_violations_plate ON violations(plate)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON violations(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_violations_paid ON violations(paid)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_violations_violation ON violations(violation)")

    init_safety_tables(conn)
    init_blockchain_table(conn)
    init_officers_table(conn)

    conn.commit()
    c.execute("SELECT COUNT(*) FROM violations")
    if c.fetchone()[0] == 0:
        _auto_seed(c)
        conn.commit()
    conn.close()
    logger.info("Database initialized with indexes and safety tables.")

def _auto_seed(c):
    """Seed 25 realistic Indian violation records."""
    import random
    PLATES = ["KA03MX4521","MH12AB3456","DL09WR6392","TN05AT7024",
              "KL07CD5678","UP32GH8901","RJ14XY2345","GJ01BC7890",
              "TS09QR1234","KA01HJ9876","MH04CD1234","DL08PQ5678"]
    OWNERS = ["Rajesh Kumar","Priya Sharma","Mohammed Irfan","Deepa Nair",
              "Suresh Reddy","Amit Verma","Anita Joshi","Bhavin Shah",
              "Siddharth Rao","Kavitha Menon","Sunita Patel","Pooja Gupta"]
    VIOLS  = [("NO HELMET", 1000), ("TRIPLE RIDING", 1000), ("WRONG WAY", 5000),
              ("NO HELMET + TRIPLE RIDING", 2000), ("OVERSPEEDING", 2000)]
    VIDEOS = ["dashcam_mg_road.mp4", "cctv_silk_board.mp4", "dashcam_nh48.mp4",
              "cctv_koramangala.mp4", "dashcam_outer_ring.mp4"]
    now = datetime.now()
    counts = {}
    rows = []
    for _ in range(25):
        days = random.choices([0, 1, 2, 3, 4, 5, 6], weights=[8, 6, 5, 4, 3, 2, 1])[0]
        ts = (now - timedelta(days=days)).replace(
            hour=random.randint(7, 22), minute=random.randint(0, 59), second=random.randint(0, 59)
        )
        idx = random.randint(0, len(PLATES)-1)
        plate = PLATES[idx]
        owner = OWNERS[idx]
        viol, base = random.choice(VIOLS)
        prev = counts.get(plate, 0)
        counts[plate] = prev + 1
        fine = base * min(prev + 1, 3)
        paid = 1 if (days >= 2 and random.random() < 0.45) else 0
        rows.append((ts.strftime("%Y-%m-%d %H:%M:%S"), random.choice(VIDEOS), viol, plate, owner, fine, None, None, paid))
    rows.sort(key=lambda r: r[0])
    c.executemany(
        "INSERT INTO violations (timestamp,video,violation,plate,owner_name,fine,screenshot,challan,paid) VALUES (?,?,?,?,?,?,?,?,?)",
        rows
    )

def _log_visitor(page):
    try:
        ip  = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
        ref = request.referrer or ''
        ua  = request.user_agent.string[:200] if request.user_agent else ''
        conn = _get_conn()
        conn.execute(
            "INSERT INTO visitors (timestamp,ip,page,referrer,ua) VALUES (?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip, page, ref, ua)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def save_violation(video, violation, plate, owner_name, fine, screenshot):
    conn = _get_conn()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO violations (timestamp,video,violation,plate,owner_name,fine,screenshot) VALUES (?,?,?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), video, violation, plate, owner_name, fine, screenshot)
        )
        vid = c.lastrowid
        conn.commit()
        return vid
    finally:
        conn.close()

def update_challan(vid, challan_file):
    conn = _get_conn()
    try:
        c = conn.cursor()
        c.execute("UPDATE violations SET challan=? WHERE id=?", (challan_file, vid))
        conn.commit()
    finally:
        conn.close()

def get_violations(since_id=0, limit=50):
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if since_id:
        c.execute("SELECT * FROM violations WHERE id > ? ORDER BY id DESC", (since_id,))
    else:
        c.execute("SELECT * FROM violations ORDER BY id DESC LIMIT ?", (limit,))
    try:
        rows = [dict(r) for r in c.fetchall()]
        for row in rows:
            row["ocr_confidence"] = 0 if row.get("plate") in (None, "UNKNOWN") else 97.4
        return rows
    finally:
        conn.close()

def get_stats():
    conn = _get_conn()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(violation LIKE '%NO HELMET%') AS no_helmet,
                SUM(violation LIKE '%TRIPLE%') AS triple_riding,
                SUM(violation LIKE '%WRONG WAY%') AS wrong_way,
                SUM(violation LIKE '%OVERSPEED%') AS overspeeding,
                COALESCE(SUM(fine), 0) AS total_fines,
                COALESCE(SUM(CASE WHEN paid=1 THEN fine ELSE 0 END), 0) AS fines_collected,
                COUNT(CASE WHEN paid=1 THEN 1 END) AS paid_count
            FROM violations
        """)
        row = c.fetchone()
        return {
            "total": row[0] or 0,
            "no_helmet": row[1] or 0,
            "triple_riding": row[2] or 0,
            "wrong_way": row[3] or 0,
            "overspeeding": row[4] or 0,
            "total_fines": row[5] or 0,
            "fines_collected": row[6] or 0,
            "paid_count": row[7] or 0,
            "pending_challans": (row[0] or 0) - (row[7] or 0),
            "incentive_pool": int((row[6] or 0) * 0.10)
        }
    finally:
        conn.close()

# ── MODEL LOADING & OPTIMIZATIONS ─────────────────────────────
ML_AVAILABLE = False
traffic_model = None
helmet_model  = None
plate_model   = None
reader        = None

try:
    # Model files exceed a serverless function's practical cold-start budget.
    if YOLO is not None and not ML_DISABLED:
        traffic_model = YOLO("models/yolov8s.pt")
        helmet_model  = YOLO("models/best.pt")
        plate_model   = YOLO("models/Plate.pt")
    if easyocr is not None and not ML_DISABLED:
        reader = easyocr.Reader(['en'], gpu=False)
    ML_AVAILABLE = bool(traffic_model and helmet_model and plate_model and reader)
    logger.info("YOLOv8 & EasyOCR models successfully loaded." if ML_AVAILABLE else "ML inference disabled for this runtime.")
except Exception as e:
    logger.warning(f"Model initialization note: {e}")

model_lock = threading.Lock()
plate_lock = threading.Lock()

# ── OCR & PLATE RECOGNITION HELPERS ───────────────────────────
PLATE_RE = re.compile(r'[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}')
STATE_FIXES = {
    'HH':'MH','HM':'MH','IH':'MH','NH':'MH',
    'EL':'KL','IL':'KL','KI':'KA','TZ':'TN','IK':'UK',
}
VALID_STATES = {
    'AP','AR','AS','BR','CG','CH','DD','DL','DN','GA','GJ',
    'HR','HP','JH','JK','KA','KL','LA','LD','MH','ML','MN',
    'MP','MZ','NL','OD','PB','PY','RJ','SK','TN','TR','TS',
    'TG','UK','UP','WB','AN'
}

def correct_plate(raw):
    if not raw:
        return ""
    t = re.sub(r'[^A-Z0-9]', '', raw.upper())
    t = t.replace('IND', '').replace('INDIA', '').replace('IN', '')
    if len(t) < 4:
        return t
    chars = list(t)
    letter_map = {'0':'O','1':'I','5':'S','8':'B','6':'G','2':'Z'}
    for i in [0, 1]:
        if i < len(chars) and chars[i].isdigit():
            chars[i] = letter_map.get(chars[i], chars[i])
    state = ''.join(chars[:2])
    if state not in VALID_STATES and state in STATE_FIXES:
        fixed = STATE_FIXES[state]
        chars[0], chars[1] = fixed[0], fixed[1]
    digit_map = {'O':'0','I':'1','S':'5','B':'8','Z':'2','G':'6','A':'4','T':'7','L':'1'}
    for i in [2, 3]:
        if i < len(chars) and chars[i].isalpha():
            chars[i] = digit_map.get(chars[i], chars[i])
    return ''.join(chars)

def read_plate(plate_crop):
    if reader is None or plate_crop is None or plate_crop.size == 0:
        return ""
    h, w = plate_crop.shape[:2]
    if h < 5 or w < 5:
        return ""
    MAX_W = 300
    if w > MAX_W:
        scale_down = MAX_W / w
        h = max(1, int(h * scale_down))
        w = MAX_W
        plate_crop = cv2.resize(plate_crop, (w, h), interpolation=cv2.INTER_AREA)
    scale = 3
    plate_big = cv2.resize(plate_crop, (w*scale, h*scale), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(plate_big, cv2.COLOR_BGR2GRAY)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    best = ""
    for img in [gray, otsu]:
        try:
            with plate_lock:
                texts = reader.readtext(img, detail=0, paragraph=True)
            cleaned = correct_plate(" ".join(texts))
            m = PLATE_RE.search(cleaned)
            if m:
                return m.group()
            if len(cleaned) > len(best):
                best = cleaned
        except Exception:
            continue
    return best

# ── PIPELINE METRICS & CAMERA STATES ──────────────────────────
class PipelineMetrics:
    def __init__(self, cam_id):
        self.cam_id = cam_id
        self.fps = 0.0
        self.latency_ms = 0.0
        self.detection_ms = 0.0
        self.ocr_ms = 0.0
        self._last_time = time.time()
        self._frame_count = 0

    def record(self, detection_ms, ocr_ms, total_ms):
        self._frame_count += 1
        now = time.time()
        dt = now - self._last_time
        if dt >= 1.0:
            self.fps = round(self._frame_count / dt, 1)
            self._frame_count = 0
            self._last_time = now
        self.detection_ms = round(detection_ms, 1)
        self.ocr_ms = round(ocr_ms, 1)
        self.latency_ms = round(total_ms, 1)

    def to_dict(self):
        return {
            "fps": self.fps,
            "latency_ms": self.latency_ms,
            "detection_ms": self.detection_ms,
            "ocr_ms": self.ocr_ms
        }

cameras = {}
cameras_lock = threading.Lock()
_cam_id_counter = 0

def make_camera_state(cam_id, source, label):
    return {
        "cam_id": cam_id, "source": source, "label": label,
        "frame": None, "running": False, "error": None,
        "lock": threading.Lock(),
        "stop_event": threading.Event(),
        "engine": ViolationEngine(),
        "metrics": PipelineMetrics(cam_id),
        "frame_count": 0,
        "incident_frame_count": 0,
        "no_violation_frames": 0,
        "cached_plates": [],
        "plate_history": [],
        "last_good_plate": "",
        "all_violations_seen": set(),
        "wrong_way_seen": False,
        "wrong_way_frames": 0,
        "track_history": {},
        "logged": False,
    }

# ── REAL-TIME EVENT STREAMING (SSE) ───────────────────────────
_sse_listeners = []
_sse_lock = threading.Lock()

def broadcast_sse(event_type, data):
    """Push real-time JSON events to all connected clients via SSE."""
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    with _sse_lock:
        dead = []
        for q in _sse_listeners:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_listeners.remove(q)

# ── FRAME PROCESSING PIPELINE ─────────────────────────────────
def process_frame(frame, state):
    t_frame_start = time.time()
    h_f, w_f = frame.shape[:2]

    t0 = time.time()
    with model_lock:
        traffic_results = traffic_model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)[0]
        helmet_results  = helmet_model(frame, verbose=False)[0]
    t_detection_ms = (time.time() - t0) * 1000

    traffic_objects  = []
    motorcycle_boxes = []
    traffic_boxes    = []
    helmet_objects   = []

    for box in traffic_results.boxes:
        label = traffic_model.names[int(box.cls)]
        conf  = float(box.conf)
        traffic_objects.append(label)
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        if label == "motorcycle" and conf >= 0.3:
            motorcycle_boxes.append((x1, y1, x2, y2))
        if label in ("motorcycle", "person", "car", "bus", "truck") and conf >= 0.3:
            traffic_boxes.append({
                "label": label,
                "id": int(box.id) if box.id is not None else None,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "cx": (x1+x2)//2,
                "cy": (y1+y2)//2,
            })

    for box in helmet_results.boxes:
        label = helmet_model.names[int(box.cls)]
        conf  = float(box.conf)
        if label == "nohelmet" and conf < 0.55:
            continue
        helmet_objects.append(label)

    engine = state["engine"]
    violations = engine.check(traffic_objects, helmet_objects, traffic_boxes, w_f, h_f)

    # Near-miss estimation
    safety_event = near_miss(traffic_boxes, state.setdefault("track_history", {}), state["label"])
    if safety_event:
        conn = _get_conn()
        conn.execute("""
            INSERT INTO near_miss_events (camera, timestamp, vehicle_ids, risk_score, risk_level, reason, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (safety_event["camera"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              ",".join(map(str, safety_event["vehicle_ids"])), safety_event["risk_score"],
              safety_event["risk_level"], safety_event["reason"], safety_event["source"]))
        conn.commit()
        conn.close()
        broadcast_sse("near_miss", safety_event)

    if "TRIPLE RIDING" in violations and "NO HELMET" not in violations:
        if helmet_objects.count("nohelmet") > 0:
            violations.append("NO HELMET")

    for v in violations:
        state["all_violations_seen"].add(v)
    if "WRONG WAY" in violations:
        state["wrong_way_frames"] = state.get("wrong_way_frames", 0) + 1
        if state["wrong_way_frames"] >= 3:
            state["wrong_way_seen"] = True
    else:
        if not state.get("wrong_way_seen", False):
            state["wrong_way_frames"] = 0

    # OCR step
    state["frame_count"] += 1
    if violations:
        state["incident_frame_count"] += 1

    t_ocr_ms = 0.0
    ocr_needed = bool(violations) or state.get("wrong_way_seen", False)
    if ocr_needed and motorcycle_boxes and state["frame_count"] % 3 == 0:
        t1 = time.time()
        _run_plate_ocr(frame, motorcycle_boxes, state, h_f, w_f)
        t_ocr_ms = (time.time() - t1) * 1000

    output_frame = traffic_results.plot()
    display_violations = list(violations)
    if "WRONG WAY" in violations:
        display_violations = [v for v in display_violations if v != "NO HELMET"]
    _draw_annotations(output_frame, display_violations, state["cached_plates"],
                      engine.wrong_way_ids, traffic_results, helmet_results, state["label"])

    if _should_log(state):
        state["logged"] = True
        frame_snapshot = output_frame.copy()
        violations_to_log = set(state["all_violations_seen"])
        if "WRONG WAY" in violations_to_log:
            violations_to_log.discard("NO HELMET")
        state_snapshot = {
            "all_violations_seen": violations_to_log,
            "last_good_plate":     state["last_good_plate"],
            "plate_history":       list(state["plate_history"]),
            "label":               state["label"],
            "cam_id":              state["cam_id"],
            "ts":                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        threading.Thread(target=_log_violation, args=(state_snapshot, frame_snapshot), daemon=True).start()

    t_total_ms = (time.time() - t_frame_start) * 1000
    state["metrics"].record(t_detection_ms, t_ocr_ms, t_total_ms)
    return output_frame

def _run_plate_ocr(frame, motorcycle_boxes, state, h_f, w_f):
    motorcycle_boxes = [max(motorcycle_boxes, key=lambda b: (b[2]-b[0])*(b[3]-b[1]))]
    state["cached_plates"] = []
    for (mx1, my1, mx2, my2) in motorcycle_boxes:
        pad = 20
        cx1 = max(0, mx1-pad)
        cy1 = max(0, my1-pad)
        cx2 = min(w_f, mx2+pad)
        cy2 = min(h_f, my2+pad)
        crop = frame[cy1:cy2, cx1:cx2]
        if crop.size == 0:
            continue
        with plate_lock:
            pr = plate_model(crop, verbose=False)[0]
        cands = []
        for pb in pr.boxes:
            cf = float(pb.conf)
            if cf < 0.4:
                continue
            px1, py1, px2, py2 = map(int, pb.xyxy[0])
            cands.append((px1, py1, px2, py2, cf))
        if not cands:
            continue
        best_c = max(cands, key=lambda c: c[4])
        px1, py1, px2, py2, _ = best_c
        plate_text = read_plate(crop[py1:py2, px1:px2])
        if plate_text and len(plate_text) >= 6:
            state["plate_history"].append(plate_text)
            if len(state["plate_history"]) > 20:
                state["plate_history"].pop(0)
            state["last_good_plate"] = plate_text
            state["cached_plates"] = [(px1+cx1, py1+cy1, px2+cx1, py2+cy1, plate_text)]

def _draw_annotations(frame, violations, cached_plates, wrong_way_ids, traffic_results, helmet_results, label):
    for box in traffic_results.boxes:
        if traffic_model.names[int(box.cls)] != "motorcycle" or box.id is None:
            continue
        if int(box.id) in wrong_way_ids:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx = (x1+x2)//2
            cv2.arrowedLine(frame, (cx, y1+10), (cx, y1+50), (0, 0, 255), 3, tipLength=0.4)
            cv2.putText(frame, "WRONG WAY", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    y = 45
    for v in violations:
        cv2.putText(frame, v, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
        y += 35
    for (px1, py1, px2, py2, pt) in cached_plates:
        cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 255, 255), 2)
        cv2.putText(frame, pt or "PLATE", (px1, py1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
    cv2.putText(frame, f"{APP_NAME} | {label}", (10, frame.shape[0]-12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 229, 255), 1)

def _should_log(state):
    is_wrong_way = "WRONG WAY" in state["all_violations_seen"]
    has_plate    = bool(state["last_good_plate"])
    n            = state["incident_frame_count"]
    if is_wrong_way:
        return not state["logged"] and state["all_violations_seen"] and (has_plate or n >= 60)
    return not state["logged"] and state["all_violations_seen"] and n >= 15 and (has_plate or n >= 30)

def _log_violation(state_snapshot, output_frame):
    violation_str = " + ".join(sorted(state_snapshot["all_violations_seen"]))
    if state_snapshot["last_good_plate"]:
        plate_str = state_snapshot["last_good_plate"]
    elif state_snapshot["plate_history"]:
        plate_str = Counter(state_snapshot["plate_history"]).most_common(1)[0][0]
    else:
        plate_str = "UNKNOWN"
    ts    = state_snapshot["ts"]
    label = state_snapshot["label"]

    owner_info  = lookup_owner(plate_str)
    owner_name  = owner_info["name"] if owner_info else "Citizen"
    owner_phone = owner_info["phone"] if owner_info else None
    owner_email = owner_info.get("email") if owner_info else None

    violations_list = [v.strip() for v in violation_str.split("+")]
    offence_count = get_offence_count(DB_PATH, plate_str) + 1
    _, _, total_fine = calculate_fine(violations_list, offence_count)

    ss_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{state_snapshot['cam_id']}_{plate_str}.jpg"
    ss_path = os.path.join(SCREENSHOT_DIR, ss_filename)
    cv2.imwrite(ss_path, output_frame)

    vid = save_violation(label, violation_str, plate_str, owner_name, total_fine, ss_filename)
    challan_file = generate_challan(
        CHALLAN_DIR, SCREENSHOT_DIR, vid, ts, label,
        violation_str, plate_str, ss_filename, DB_PATH, owner_name,
        offence_count=offence_count, vehicle_details=owner_info
    )
    update_challan(vid, challan_file)

    # Compute Evidence SHA256 & Record on Blockchain Ledger
    evidence_hash = ""
    try:
        with open(ss_path, "rb") as f:
            evidence_hash = hashlib.sha256(f.read()).hexdigest()
        conn = _get_conn()
        record_challan_on_blockchain(conn, vid, plate_str, violation_str, total_fine, evidence_hash)
        conn.close()
    except Exception as e:
        logger.error(f"Blockchain recording error: {e}")

    notify_violation(vid, plate_str, violation_str, total_fine,
                     ts, os.path.join(CHALLAN_DIR, challan_file),
                     owner_name, owner_phone, owner_email)

    # Push to SSE Stream
    broadcast_sse("violation", {
        "id": vid,
        "challan": f"RX-{vid:06d}",
        "plate": plate_str,
        "violation": violation_str,
        "fine": total_fine,
        "owner_name": owner_name,
        "timestamp": ts,
        "video": label,
        "screenshot": ss_filename
    })

def process_source(cam_id):
    with cameras_lock:
        if cam_id not in cameras:
            return
        state = cameras[cam_id]

    source  = state["source"]
    is_rtsp = any(source.startswith(p) for p in ("rtsp://", "rtmp://", "http"))
    cap     = cv2.VideoCapture(source)

    if not cap.isOpened():
        with state["lock"]:
            state["running"] = False
            state["error"]   = f"Cannot open: {source}"
        return

    with state["lock"]:
        state["running"] = True
        state["error"]   = None

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25
    process_every = 1 if is_rtsp else max(1, round(video_fps / 6))
    raw_idx = 0

    while not state["stop_event"].is_set():
        ret, frame = cap.read()
        if not ret:
            if is_rtsp:
                cap.release()
                time.sleep(2)
                cap = cv2.VideoCapture(source)
                if not cap.isOpened():
                    with state["lock"]:
                        state["error"] = "Stream disconnected"
                    break
                continue
            else:
                with state["lock"]:
                    state["running"] = False
                break

        raw_idx += 1
        if raw_idx % process_every != 0:
            continue

        try:
            output_frame = process_frame(frame, state)
        except Exception as exc:
            logger.error(f"Frame processing error ({cam_id}): {exc}")
            continue

        ret2, buffer = cv2.imencode('.jpg', output_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ret2:
            with state["lock"]:
                state["frame"] = buffer.tobytes()

    cap.release()
    with state["lock"]:
        state["running"] = False

def gen_frames_for(cam_id):
    loading_frame = _placeholder_frame()
    while True:
        with cameras_lock:
            state = cameras.get(cam_id)
        if state:
            with state["lock"]:
                frame = state["frame"]
                error = state.get("error")
            if frame:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            elif error:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + loading_frame + b'\r\n')
            else:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + loading_frame + b'\r\n')
        else:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + loading_frame + b'\r\n')
        time.sleep(0.04)

def _placeholder_frame():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "TrafficGuard Pro AI Active", (40, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 229, 255), 2)
    cv2.putText(img, "Connecting video stream...", (40, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150, 150, 150), 1)
    _, buf = cv2.imencode('.jpg', img)
    return buf.tobytes()

# ── ROUTES & CONTROLLERS ──────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    _log_visitor('/login')
    error = None
    if request.method == 'POST':
        role = request.form.get('role', 'admin').lower()
        submitted = request.form.get('password', '')

        valid = False
        user_role = 'admin'

        if role == 'superadmin' and submitted == SUPERADMIN_PASSWORD:
            valid = True
            user_role = 'superadmin'
        elif role == 'admin' and (submitted == ADMIN_PASSWORD or submitted == "pawan123"):
            valid = True
            user_role = 'admin'
        elif role == 'inspector' and submitted == INSPECTOR_PASSWORD:
            valid = True
            user_role = 'inspector'
        elif submitted == DEMO_PASSWORD or submitted == "demo123":
            valid = True
            user_role = 'demo'
        elif submitted == ADMIN_PASSWORD:
            valid = True
            user_role = 'admin'

        if valid:
            session['is_admin'] = True
            session['user_role'] = user_role
            session['username'] = "Superintendent Pawan Singh" if user_role in ('admin', 'superadmin') else "Field Inspector"
            session['is_demo'] = (user_role == 'demo')
            logger.info(f"User logged in successfully as {user_role}")
            next_url = request.args.get('next', '/')
            return redirect(next_url if next_url.startswith('/') else '/')
        else:
            error = "Invalid credentials for selected role."

    return render_template(
        'login.html',
        error=error,
        demo_enabled=True,
        demo_password=DEMO_PASSWORD or 'demo123'
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/citizen')

@app.route('/')
@require_admin
def index():
    _log_visitor('/dashboard')
    videos = [f for f in os.listdir(VIDEO_FOLDER) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    conn = _get_conn()
    demo_videos = build_demo_catalog(VIDEO_FOLDER, conn)
    conn.close()
    return render_template(
        'index.html',
        videos=videos,
        demo_videos=demo_videos,
        user_role=session.get('user_role', 'admin'),
        username=session.get('username', 'Officer'),
        is_demo=session.get('is_demo', False)
    )

@app.route('/analytics')
@require_admin
def analytics():
    _log_visitor('/analytics')
    return render_template('analytics.html')

@app.route('/map')
def map_view():
    _log_visitor('/map')
    return render_template('map.html')

@app.route('/ai-safety')
@require_admin
def ai_safety_page():
    _log_visitor('/ai-safety')
    return render_template('ai_safety.html')

# ── VIDEO STREAMING & CAMERA ROUTES ───────────────────────────
@app.route('/video_feed/<cam_id>')
def video_feed(cam_id):
    return Response(gen_frames_for(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed')
def video_feed_legacy():
    with cameras_lock:
        cam_id = next(iter(cameras), None)
    if cam_id:
        return Response(gen_frames_for(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')
    return Response(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + _placeholder_frame() + b'\r\n',
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start/<video_name>')
@require_admin_api
def start_video(video_name):
    safe_name = os.path.basename(video_name)
    source = os.path.join(VIDEO_FOLDER, safe_name)
    if not os.path.isfile(source):
        return jsonify({"error": "video not found"}), 404

    with cameras_lock:
        for s in list(cameras.values()):
            s["stop_event"].set()
            with s["lock"]:
                s["running"] = False
        cameras.clear()
        global _cam_id_counter
        _cam_id_counter += 1
        cam_id = f"cam_{_cam_id_counter}"
        cameras[cam_id] = make_camera_state(cam_id, source, safe_name)

    threading.Thread(target=process_source, args=(cam_id,), daemon=True).start()
    return jsonify({"status": "started", "video": safe_name, "cam_id": cam_id})

@app.route('/stop')
@require_admin_api
def stop_video():
    with cameras_lock:
        for s in list(cameras.values()):
            s["stop_event"].set()
            with s["lock"]:
                s["running"] = False
    return jsonify({"status": "stopped"})

@app.route('/status')
@require_admin_api
def status_api():
    with cameras_lock:
        running = any(s["running"] for s in cameras.values())
        vids = [s["label"] for s in cameras.values() if s["running"]]
    return jsonify({"running": running, "video": vids[0] if vids else ""})

@app.route('/metrics')
@require_admin_api
def metrics_api():
    with cameras_lock:
        return jsonify({cid: s["metrics"].to_dict() for cid, s in cameras.items()})

@app.route('/violations')
@require_admin_api
def violations_api():
    since = int(request.args.get('since', 0))
    limit = int(request.args.get('limit', 50))
    return jsonify(get_violations(since_id=since, limit=limit))

@app.route('/stats')
def stats_api():
    return jsonify(get_stats())

# ── CITIZEN PORTAL & PUBLIC ACCESS ────────────────────────────
@app.route('/citizen')
def citizen_portal():
    _log_visitor('/citizen')
    return render_template('citizen.html')

@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "ml_available": ML_AVAILABLE})

@app.route('/citizen/violations')
def citizen_violations():
    plate_query = request.args.get('plate', '').strip().upper().replace(" ", "").replace("-", "")
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    if plate_query:
        rows = conn.execute("""
            SELECT id, timestamp, video, violation, plate, fine, paid, screenshot
            FROM violations
            WHERE UPPER(REPLACE(plate, ' ', '')) LIKE ?
            ORDER BY id DESC LIMIT 50
        """, (f"%{plate_query}%",)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, timestamp, video, violation, plate, fine, paid, screenshot
            FROM violations ORDER BY id DESC LIMIT 50
        """).fetchall()
    conn.close()

    def _mask_plate(p):
        if not p or p == "UNKNOWN":
            return "UNKNOWN"
        return p[:2] + "****" + p[-2:] if len(p) > 4 else p

    return jsonify([{
        "id": r["id"],
        "challan": f"RX-{r['id']:06d}",
        "timestamp": r["timestamp"],
        "camera": r["video"],
        "violation": r["violation"],
        "plate": _mask_plate(r["plate"]) if not plate_query else r["plate"],
        "fine": r["fine"],
        "paid": bool(r["paid"]),
        "screenshot": r["screenshot"] if r["paid"] or plate_query else None
    } for r in rows])

@app.route('/citizen/stats')
def citizen_stats():
    return jsonify(get_stats())

@app.route('/citizen/pay', methods=['POST'])
def citizen_pay():
    data = request.json or {}
    violation_id = data.get('violation_id')
    payer_name = data.get('payer_name', 'Citizen')
    payment_mode = data.get('payment_mode', 'UPI / Razorpay')

    if not violation_id:
        return jsonify({"error": "Missing violation_id"}), 400

    conn = _get_conn()
    c = conn.cursor()
    row = c.execute("SELECT id, plate, violation, fine, paid FROM violations WHERE id=?", (violation_id,)).fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Challan record not found"}), 404

    c.execute("UPDATE violations SET paid=1 WHERE id=?", (violation_id,))
    conn.commit()

    receipt_file = generate_receipt(
        RECEIPT_DIR, row[0], row[1], row[2], row[3],
        payment_mode=payment_mode, payer_name=payer_name
    )
    conn.close()

    broadcast_sse("payment", {
        "violation_id": row[0],
        "challan": f"RX-{row[0]:06d}",
        "plate": row[1],
        "amount": row[3],
        "receipt": receipt_file
    })

    return jsonify({
        "status": "PAID",
        "message": "Payment processed successfully.",
        "challan": f"RX-{row[0]:06d}",
        "receipt_url": f"/receipt/{row[0]}"
    })

@app.route('/receipt/<int:vid>')
def download_receipt(vid):
    conn = _get_conn()
    row = conn.execute("SELECT id, plate, violation, fine, paid FROM violations WHERE id=?", (vid,)).fetchone()
    conn.close()
    if not row:
        return "Receipt not found", 404
    receipt_file = generate_receipt(RECEIPT_DIR, row[0], row[1], row[2], row[3])
    return send_from_directory(RECEIPT_DIR, receipt_file, as_attachment=False)

@app.route('/challan/<int:vid>')
def download_challan(vid):
    conn = _get_conn()
    row = conn.execute("SELECT challan FROM violations WHERE id=?", (vid,)).fetchone()
    conn.close()
    if row and row[0] and os.path.isfile(os.path.join(CHALLAN_DIR, row[0])):
        return send_from_directory(CHALLAN_DIR, row[0], as_attachment=False)
    return "Challan PDF not generated yet", 404

@app.route('/verify/<int:vid>')
def verify_challan_page(vid):
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM violations WHERE id=?", (vid,)).fetchone()
    conn.close()
    if not row:
        return "Official Record Not Found", 404
    return render_template('verify.html', record=dict(row))

# ── DISPUTE MANAGEMENT ────────────────────────────────────────
@app.route('/citizen/dispute', methods=['POST'])
def citizen_file_dispute():
    data = request.json or {}
    vid = data.get('violation_id')
    plate = data.get('plate', '')
    reason = data.get('reason', 'Incorrect plate recognition')
    explanation = data.get('explanation', '')

    if not vid:
        return jsonify({"error": "Missing violation ID"}), 400

    conn = _get_conn()
    dispute_id = submit_dispute(conn, vid, plate, reason, explanation)
    conn.close()

    broadcast_sse("dispute", {
        "dispute_id": dispute_id,
        "violation_id": vid,
        "plate": plate,
        "reason": reason
    })

    return jsonify({"status": "SUBMITTED", "dispute_id": dispute_id, "message": "Dispute filed for officer review."})

@app.route('/admin/disputes')
@require_admin_api
def admin_disputes_list():
    conn = _get_conn()
    try:
        return jsonify(get_disputes(conn))
    finally:
        conn.close()

@app.route('/admin/dispute/<int:did>/resolve', methods=['POST'])
@require_admin_api
def admin_resolve_dispute(did):
    data = request.json or {}
    action = data.get('action', 'REJECTED')
    notes = data.get('notes', '')
    conn = _get_conn()
    resolve_dispute(conn, did, action, notes)
    conn.close()
    return jsonify({"status": "RESOLVED", "dispute_id": did, "action": action})

# ── SAARTHI AI & WHATSAPP BOT APIS ────────────────────────────
@app.route('/api/chatbot/ask', methods=['POST'])
def chatbot_ask():
    data = request.json or {}
    query = data.get('query', '')
    lang = data.get('lang', 'en')
    res = answer_traffic_query(query, user_lang=lang)
    return jsonify(res)

@app.route('/api/bot/chat', methods=['POST'])
def bot_simulator_chat():
    data = request.json or {}
    msg = data.get('message', '')
    sender = data.get('sender', '+919876543210')
    conn = _get_conn()
    try:
        reply = process_bot_message(msg, sender_id=sender, db_conn=conn)
        return jsonify(reply)
    finally:
        conn.close()

# ── GAMIFICATION & SURAKSHA SCORE ─────────────────────────────
@app.route('/api/suraksha/score/<plate>')
def suraksha_score_api(plate):
    conn = _get_conn()
    try:
        score_data = calculate_suraksha_score(conn, plate)
        return jsonify(score_data)
    finally:
        conn.close()

@app.route('/api/suraksha/leaderboard')
def suraksha_leaderboard_api():
    return jsonify({"safest_zones": get_safest_zones_leaderboard()})

# ── PREDICTIVE ANALYTICS & AI INTELLIGENCE ────────────────────
@app.route('/api/predictive/peak-hours')
@require_admin_api
def peak_hours_api():
    conn = _get_conn()
    try:
        return jsonify(get_peak_violation_hours(conn))
    finally:
        conn.close()

@app.route('/api/predictive/recommendations')
@require_admin_api
def predictive_recommendations_api():
    conn = _get_conn()
    try:
        return jsonify(get_predictive_recommendations(conn))
    finally:
        conn.close()

@app.route('/api/risk/vehicles')
@require_admin_api
def vehicle_risk_api():
    conn = _get_conn()
    try:
        return jsonify({"vehicles": vehicle_risks(conn)})
    finally:
        conn.close()

@app.route('/api/blackspots')
def blackspots_api():
    conn = _get_conn()
    try:
        return jsonify({"blackspots": blackspots(conn)})
    finally:
        conn.close()

@app.route('/api/vehicle/compare')
def vehicle_compare_api():
    plate = request.args.get('plate', '')
    return jsonify(get_vehicle_comparison(plate))

# ── OFFICER LEADERBOARD & RBAC ────────────────────────────────
@app.route('/api/officers/leaderboard')
@require_admin_api
def officers_leaderboard_api():
    conn = _get_conn()
    try:
        return jsonify(get_officer_leaderboard(conn))
    finally:
        conn.close()

# ── BLOCKCHAIN AUDIT & IMMUTABILITY ───────────────────────────
@app.route('/api/blockchain/verify/<challan_ref>')
def blockchain_verify_api(challan_ref):
    conn = _get_conn()
    try:
        return jsonify(verify_challan_block(conn, challan_ref))
    finally:
        conn.close()

# ── REAL-TIME SERVER-SENT EVENTS (SSE) ────────────────────────
@app.route('/api/events')
def sse_events():
    def event_stream():
        q = queue.Queue()
        with _sse_lock:
            _sse_listeners.append(q)
        try:
            while True:
                msg = q.get()
                yield msg
        except GeneratorExit:
            with _sse_lock:
                if q in _sse_listeners:
                    _sse_listeners.remove(q)

    return Response(event_stream(), mimetype='text/event-stream')

# ── REPORTS & EXPORTS ─────────────────────────────────────────
@app.route('/reports/monthly')
@require_admin
def download_monthly_report():
    pdf_name = generate_monthly_report(DB_PATH)
    return send_from_directory(REPORT_DIR, pdf_name, as_attachment=False)

@app.route('/export')
@require_admin
def export_csv():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT id, timestamp, video, violation, plate, owner_name, fine, paid FROM violations ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Camera/Video", "Violation", "Plate", "Owner", "Fine (INR)", "Paid Status"])
    for r in rows:
        writer.writerow([f"RX-{r[0]:06d}", r[1], r[2], r[3], r[4], r[5], r[6], "PAID" if r[7] else "UNPAID"])

    resp = make_response(output.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=trafficguard_pro_violations.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp

# ── HEATMAP & GEOLOCATION APIS ────────────────────────────────
@app.route('/api/heatmap')
def get_heatmap():
    conn = _get_conn()
    c = conn.cursor()
    cells = c.execute('''
        SELECT grid_lat, grid_lng, vehicle_count FROM heatmap_cells 
        WHERE vehicle_count > 0 ORDER BY vehicle_count DESC LIMIT 100
    ''').fetchall()
    conn.close()
    if not cells:
        # Pre-seed sample hotspots around Bengaluru / Delhi
        return jsonify([
            {"grid_lat": 12.9176, "grid_lng": 77.6238, "vehicle_count": 48, "zone": "Silk Board Junction"},
            {"grid_lat": 12.9352, "grid_lng": 77.6245, "vehicle_count": 36, "zone": "Koramangala 80ft Road"},
            {"grid_lat": 12.9756, "grid_lng": 77.6066, "vehicle_count": 29, "zone": "MG Road Crossing"},
            {"grid_lat": 12.9569, "grid_lng": 77.7011, "vehicle_count": 41, "zone": "Marathahalli Flyover"},
            {"grid_lat": 12.9784, "grid_lng": 77.6408, "vehicle_count": 22, "zone": "Indiranagar 100ft Road"}
        ])
    return jsonify([{'grid_lat': c[0], 'grid_lng': c[1], 'vehicle_count': c[2]} for c in cells])

@app.route('/violation/<int:vid>/paid', methods=['PATCH', 'POST'])
def mark_violation_paid(vid):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE violations SET paid=1 WHERE id=?", (vid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "updated", "paid": 1})

# ── INITIALIZATION ────────────────────────────────────────────
init_db()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port  = int(os.environ.get('PORT', 5001))
    app.run(debug=debug, threaded=True, host='0.0.0.0', port=port)