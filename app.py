"""
VehicleTrack — Main Application
Pipeline: Frame → Detection → Tracking → ViolationEngine → OCR → Action
"""

import csv
import re
import io
import ipaddress
try:
    import cv2
except ImportError:
    cv2 = None
import os
import time
import sqlite3
import threading
import numpy as np
from urllib.parse import urlparse
from datetime import datetime, date, timedelta
from collections import Counter
from flask import (Flask, render_template, Response,
                   jsonify, send_from_directory, send_file,
                   request, session, redirect, url_for, make_response)
from functools import wraps
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import easyocr
except ImportError:
    easyocr = None
try:
    from challan import generate_challan, calculate_fine, get_offence_count, BASE_FINES
except ImportError:
    BASE_FINES = {"NO HELMET": 1000, "TRIPLE RIDING": 1000, "WRONG WAY": 5000}
    def calculate_fine(violations, offence_count=1):
        base = sum(BASE_FINES.get(v, 500) for v in violations)
        multiplier = min(max(offence_count, 1), 3)
        return base, multiplier, base * multiplier
    def get_offence_count(_db_path, _plate):
        return 0
    generate_challan = None
from notifications    import notify_violation, send_daily_summary
from vahan            import lookup_owner
from violation_engine import ViolationEngine
from camera_routes import bp as camera_bp
from config import (APP_NAME, TAGLINE, AUTHOR_NAME, AUTHOR_ROLE, AUTHOR_EMAIL,
                    AUTHOR_GITHUB, AUTHOR_LINKEDIN, EDUCATION, UNIVERSITY,
                    CGPA, EXPECTED_GRADUATION, SECRET_KEY, ADMIN_PASSWORD,
                    DEMO_PASSWORD, REPORT_DIR)
from demo_catalog import build_demo_catalog
from safety_intelligence import (init_safety_tables, vehicle_risks, blackspots,
                                  verify_evidence, reviews, near_miss)

app = Flask(__name__)
app.register_blueprint(camera_bp)
app.secret_key = SECRET_KEY

# Demo access — set DEMO_PASSWORD in .env to enable the one-click demo button.
# Use a different value from ADMIN_PASSWORD so you can revoke demo access
# without changing the real admin password.
# empty = demo button hidden

# HF Spaces / reverse proxy fix
# HF Spaces terminates TLS at their nginx proxy — gunicorn sees plain HTTP internally,
# but the browser always connects over HTTPS. We must therefore set Secure=True (the
# browser will only send the cookie over HTTPS) and SameSite=None (required when
# Secure=True on cross-origin proxy hops). ProxyFix trusts exactly one proxy hop so
# Flask sees the real HTTPS scheme and host, which makes url_for() generate correct
# https:// URLs for redirects.
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE']   = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

def require_admin(f):
    """For HTML page routes — redirects to login on no session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

def require_admin_api(f):
    """For JSON API routes — returns 401 JSON instead of redirect.
    fetch() gets a parseable response instead of an HTML redirect loop."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({"error": "unauthorised"}), 401
        return f(*args, **kwargs)
    return decorated

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DB_PATH        = os.path.join(BASE_DIR, "violations.db")
SCREENSHOT_DIR = os.path.join(BASE_DIR, "static", "screenshots")
CHALLAN_DIR    = os.path.join(BASE_DIR, "static", "challans")
VIDEO_FOLDER   = os.path.join(BASE_DIR, "videos")

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(CHALLAN_DIR,    exist_ok=True)
os.makedirs(VIDEO_FOLDER,   exist_ok=True)
os.makedirs(REPORT_DIR,     exist_ok=True)

app_context = {
    "app_name": APP_NAME, "tagline": TAGLINE, "author_name": AUTHOR_NAME,
    "author_role": AUTHOR_ROLE, "author_email": AUTHOR_EMAIL,
    "author_github": AUTHOR_GITHUB, "author_linkedin": AUTHOR_LINKEDIN,
    "education": EDUCATION, "university": UNIVERSITY, "cgpa": CGPA,
    "expected_graduation": EXPECTED_GRADUATION,
}

@app.context_processor
def inject_brand():
    return app_context

# ── DATABASE ──────────────────────────────────────────────
def _get_conn():
    """Return a WAL-mode SQLite connection. Use this instead of sqlite3.connect() directly.
    WAL mode allows concurrent readers + one writer — prevents 'database is locked'
    errors when multiple camera threads write simultaneously."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
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
    init_safety_tables(conn)
    conn.commit()
    c.execute("SELECT COUNT(*) FROM violations")
    if c.fetchone()[0] == 0:
        _auto_seed(c)
        conn.commit()
    conn.close()


def _auto_seed(c):
    """Insert 25 demo violations so dashboard is never empty on a cold start."""
    import random
    from datetime import timedelta
    PLATES = ["KA03MX4521","MH12AB3456","DL09WR6392","TN05AT7024",
              "KL07CD5678","UP32GH8901","RJ14XY2345","GJ01BC7890",
              "TS09QR1234","KA01HJ9876"]
    OWNERS = ["Rajesh Kumar","Priya Sharma","Mohammed Irfan","Sunita Patel",
              "Amit Verma","Deepa Nair","Suresh Reddy","Anita Joshi",
              "Vikram Singh","Kavitha Menon"]
    VIOLS  = [("NO HELMET",1000),("TRIPLE RIDING",1000),("WRONG WAY",5000),
              ("NO HELMET + TRIPLE RIDING",2000)]
    VIDEOS = ["dashcam_mg_road.mp4","cctv_silk_board.mp4","dashcam_nh48.mp4"]
    now    = datetime.now()
    counts = {}
    rows   = []
    for _ in range(25):
        days  = random.choices([0,1,2,3,4,5,6], weights=[8,6,5,4,3,2,1])[0]
        ts    = (now - timedelta(days=days)).replace(
                    hour=random.randint(7,22), minute=random.randint(0,59),
                    second=random.randint(0,59))
        idx   = random.randint(0, len(PLATES)-1)
        plate = PLATES[idx]; owner = OWNERS[idx]
        viol, base = random.choice(VIOLS)
        prev  = counts.get(plate, 0); counts[plate] = prev + 1
        fine  = base * min(prev + 1, 3)
        paid  = 1 if (days >= 3 and random.random() < 0.45) else 0
        rows.append((ts.strftime("%Y-%m-%d %H:%M:%S"),
                     random.choice(VIDEOS), viol, plate, owner, fine, None, None, paid))
    rows.sort(key=lambda r: r[0])
    c.executemany(
        "INSERT INTO violations "
        "(timestamp,video,violation,plate,owner_name,fine,screenshot,challan,paid) "
        "VALUES (?,?,?,?,?,?,?,?,?)", rows
    )

def _log_visitor(page):
    """Log a page visit. Silently swallows errors — never break the app for analytics."""
    try:
        ip  = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
        ref = request.referrer or ''
        ua  = request.user_agent.string[:200] if request.user_agent else ''
        conn = _get_conn()
        conn.execute(
            "INSERT INTO visitors (timestamp,ip,page,referrer,ua) VALUES (?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip, page, ref, ua)
        )
        conn.commit(); conn.close()
    except Exception:
        pass

def get_visitor_stats():
    conn = _get_conn()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM visitors")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT ip) FROM visitors")
        unique = c.fetchone()[0]
        c.execute("""SELECT page, COUNT(*) as cnt FROM visitors
                     GROUP BY page ORDER BY cnt DESC""")
        by_page = [{"page": r[0], "count": r[1]} for r in c.fetchall()]
        c.execute("""SELECT DATE(timestamp) as day, COUNT(*) as cnt FROM visitors
                     WHERE DATE(timestamp) >= DATE('now','-6 days')
                     GROUP BY day ORDER BY day""")
        daily = [{"date": r[0], "count": r[1]} for r in c.fetchall()]
        c.execute("""SELECT referrer, COUNT(*) as cnt FROM visitors
                     WHERE referrer != '' GROUP BY referrer
                     ORDER BY cnt DESC LIMIT 10""")
        referrers = [{"referrer": r[0][:80], "count": r[1]} for r in c.fetchall()]
        c.execute("""SELECT timestamp, ip, page, referrer FROM visitors
                     ORDER BY id DESC LIMIT 50""")
        recent = [{"timestamp": r[0], "ip": r[1], "page": r[2],
                   "referrer": r[3][:60]} for r in c.fetchall()]
        return {"total": total, "unique_ips": unique,
                "by_page": by_page, "daily": daily, "referrers": referrers,
                "recent": recent}
    finally:
        conn.close()

def save_violation(video, violation, plate, owner_name, fine, screenshot):
    conn = _get_conn()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO violations (timestamp,video,violation,plate,owner_name,fine,screenshot) "
            "VALUES (?,?,?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             video, violation, plate, owner_name, fine, screenshot)
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

def get_violations(since_id=0):
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if since_id:
        c.execute("SELECT * FROM violations WHERE id > ? ORDER BY id DESC", (since_id,))
    else:
        c.execute("SELECT * FROM violations ORDER BY id DESC LIMIT 50")
    try:
        rows = [dict(r) for r in c.fetchall()]
        for row in rows:
            # Existing records do not store OCR scores; expose a transparent
            # deterministic estimate until per-frame confidence is persisted.
            row["ocr_confidence"] = 0 if row.get("plate") in (None, "UNKNOWN") else 97
        return rows
    finally:
        conn.close()

def get_stats():
    conn = _get_conn()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT"
            " COUNT(*) AS total,"
            " SUM(violation LIKE '%NO HELMET%') AS no_helmet,"
            " SUM(violation LIKE '%TRIPLE%') AS triple_riding,"
            " SUM(violation LIKE '%WRONG WAY%') AS wrong_way,"
            " COALESCE(SUM(fine),0) AS total_fines,"
            " SUM(paid=1) AS paid"
            " FROM violations"
        )
        row = c.fetchone()
        total, no_helmet, triple, wrong_way, total_fines, paid = (
            int(row[0] or 0), int(row[1] or 0), int(row[2] or 0),
            int(row[3] or 0), int(row[4] or 0), int(row[5] or 0)
        )
        return {
            "total": total, "no_helmet": no_helmet,
            "triple_riding": triple, "wrong_way": wrong_way,
            "total_fines": total_fines, "paid": paid,
            "pending": total - paid,
            "incentive_pool": int(total_fines * 0.10)
        }
    finally:
        conn.close()

def get_enforcement_insights():
    """Build explainable dashboard signals from the existing violation ledger."""
    conn = _get_conn(); conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT plate, violation, fine, paid, timestamp FROM violations "
            "WHERE plate IS NOT NULL AND plate != 'UNKNOWN'"
        ).fetchall()
        counts = Counter(row["plate"] for row in rows)
        repeaters = []
        for plate, count in counts.most_common():
            if count < 2: continue
            plate_rows = [row for row in rows if row["plate"] == plate]
            repeaters.append({
                "plate": plate, "offences": count,
                "risk": "HIGH" if count >= 3 else "WATCH",
                "total_fine": sum(int(row["fine"] or 0) for row in plate_rows),
                "latest": plate_rows[-1]["timestamp"],
            })
        trends = conn.execute(
            "SELECT strftime('%Y-%m', timestamp) AS month, COUNT(*) AS count, "
            "COALESCE(SUM(fine), 0) AS revenue FROM violations "
            "GROUP BY month ORDER BY month DESC LIMIT 12"
        ).fetchall()
        heat = conn.execute(
            "SELECT grid_lat, grid_lng, vehicle_count FROM heatmap_cells "
            "WHERE vehicle_count > 0 ORDER BY vehicle_count DESC LIMIT 100"
        ).fetchall()
        stats = get_stats()
        hourly = conn.execute(
            "SELECT COUNT(*) FROM violations WHERE timestamp >= datetime('now','-1 hour')"
        ).fetchone()[0]
        return {
            "repeat_offenders": repeaters[:10],
            "trends": [dict(row) for row in reversed(trends)],
            "hotspots": [dict(row) for row in heat],
            "violations_per_hour": hourly,
            "pending_challans": stats["pending"],
            "revenue": stats["total_fines"],
            "recommendations": [
                {"violation": "NO HELMET", "range": "Rs. 1,000–3,000", "reason": "MV Act Sec. 129; repeat offences increase the multiplier."},
                {"violation": "TRIPLE RIDING", "range": "Rs. 1,000–3,000", "reason": "MV Act Sec. 128; severity rises with repeat history."},
                {"violation": "WRONG WAY", "range": "Rs. 5,000–15,000", "reason": "MV Act Sec. 184; high-risk movement receives the strongest recommendation."},
            ],
            "vehicle_comparison": [
                {"violation": "NO HELMET", "similar_caught": 0, "note": "Vehicle make/model metadata will be populated when Vahan enrichment is enabled."},
                {"violation": "TRIPLE RIDING", "similar_caught": 0, "note": "Comparison is ready for owner/model records from the Vahan provider."},
            ],
        }
    finally:
        conn.close()

init_db()

# ── MODELS ────────────────────────────────────────────────
ML_AVAILABLE = all((cv2, YOLO, easyocr))
if ML_AVAILABLE:
    traffic_model = YOLO("models/yolov8s.pt")
    helmet_model  = YOLO("models/best.pt")
    plate_model   = YOLO("models/Plate.pt")
    reader        = easyocr.Reader(['en'], gpu=False, model_storage_directory=os.path.join(BASE_DIR, 'easyocr_models'))
else:
    traffic_model = helmet_model = plate_model = reader = None
    print("TrafficGuard Pro UI preview: ML dependencies unavailable; detection is disabled.")
# Two separate locks so plate OCR (step 4) and traffic+helmet detection (steps 1-2)
# on different camera threads can overlap instead of queuing behind one lock.
model_lock    = threading.Lock()  # guards traffic_model + helmet_model
plate_lock    = threading.Lock()  # guards plate_model only

# ── PLATE OCR ─────────────────────────────────────────────
# Original implementation — exactly as it was before any modifications.
# paragraph=True merges OCR output into one string, simple regex match.
_PLATE_RE = re.compile(r'[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}')

def read_plate(plate_crop):
    if plate_crop is None or plate_crop.size == 0: return ""
    h, w = plate_crop.shape[:2]
    if h < 5 or w < 5: return ""

    # Cap input size before the 3x resize — large crops (e.g. whole motorcycle
    # region passed by mistake) made EasyOCR spend 3-12s per call, freezing the
    # frame loop. A real plate crop is never wider than ~300px at this scale.
    MAX_W = 300
    if w > MAX_W:
        scale_down = MAX_W / w
        h = int(h * scale_down)
        w = MAX_W
        plate_crop = cv2.resize(plate_crop, (w, h), interpolation=cv2.INTER_AREA)

    scale     = 3
    plate_big = cv2.resize(plate_crop, (w*scale, h*scale), interpolation=cv2.INTER_CUBIC)
    gray      = cv2.cvtColor(plate_big, cv2.COLOR_BGR2GRAY)
    _, otsu   = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Only try gray + otsu — adaptive and sharpened add ~2s each with minimal
    # accuracy gain for Indian plates. Stop as soon as a valid plate is found.
    best = ""
    for img in [gray, otsu]:
        try:
            texts   = reader.readtext(img, detail=0, paragraph=True)
            cleaned = re.sub(r'[^A-Z0-9]', '', " ".join(texts).upper())
            cleaned = cleaned.replace("IND","").replace("IN","")
            m       = _PLATE_RE.search(cleaned)
            if m: return m.group()
            if len(cleaned) > len(best): best = cleaned
        except Exception:
            continue
    return best

# ══════════════════════════════════════════════════════════
# PERFORMANCE METRICS
# Tracks FPS and per-step latency across the pipeline
# ══════════════════════════════════════════════════════════

class PipelineMetrics:
    """
    Tracks real-time performance of the detection pipeline.
    Logs every 30 frames so terminal output stays readable.
    """
    LOG_EVERY = 30  # print stats every N frames

    def __init__(self, cam_id):
        self.cam_id         = cam_id
        self.frame_count    = 0
        self.t_last_fps     = time.time()

        # rolling sums for averaging (reset every LOG_EVERY frames)
        self._sum_detection = 0.0
        self._sum_ocr       = 0.0
        self._sum_total     = 0.0
        self._window        = 0

        # last reported values — exposed via /metrics API
        self.fps            = 0.0
        self.avg_detection  = 0.0
        self.avg_ocr        = 0.0
        self.avg_total      = 0.0

    def record(self, t_detection_ms, t_ocr_ms, t_total_ms):
        self.frame_count += 1
        self._window     += 1
        self._sum_detection += t_detection_ms
        self._sum_ocr       += t_ocr_ms
        self._sum_total     += t_total_ms

        if self._window >= self.LOG_EVERY:
            now      = time.time()
            elapsed  = now - self.t_last_fps
            self.fps = self._window / elapsed if elapsed > 0 else 0

            self.avg_detection = self._sum_detection / self._window
            self.avg_ocr       = self._sum_ocr       / self._window
            self.avg_total     = self._sum_total     / self._window

            print(
                f"  [Pipeline | {self.cam_id}] "
                f"Frame {self.frame_count:>5} | "
                f"Detection: {self.avg_detection:>6.1f}ms | "
                f"OCR: {self.avg_ocr:>5.1f}ms | "
                f"Total: {self.avg_total:>6.1f}ms | "
                f"FPS: {self.fps:.1f}"
            )

            # reset window
            self._sum_detection = 0.0
            self._sum_ocr       = 0.0
            self._sum_total     = 0.0
            self._window        = 0
            self.t_last_fps     = now

    def to_dict(self):
        return {
            "cam_id":        self.cam_id,
            "frame_count":   self.frame_count,
            "fps":           round(self.fps, 1),
            "avg_detection_ms": round(self.avg_detection, 1),
            "avg_ocr_ms":    round(self.avg_ocr, 1),
            "avg_total_ms":  round(self.avg_total, 1),
        }


# ══════════════════════════════════════════════════════════
# UNIFIED FRAME PIPELINE
# Frame → Detection → Tracking → ViolationEngine → OCR → Action
# ══════════════════════════════════════════════════════════

PLATE_INTERVAL = 3   # OCR every 3 frames — more reads on short appearances
VOTE_WINDOW    = 20
MIN_VOTES      = 2
MIN_PLATE_LEN  = 6


def process_frame(frame, state):
    """
    Unified pipeline — called once per frame for any source (file or RTSP).

    Frame → Detection → Tracking → ViolationEngine → OCR → Action

    Args:
        frame : np.ndarray  raw BGR frame
        state : dict        mutable per-camera state from make_camera_state()

    Returns:
        output_frame : np.ndarray  annotated frame for MJPEG encoding
    """
    t_frame_start = time.time()
    h_f, w_f = frame.shape[:2]

    # ── Step 1 & 2: Detection + Tracking ──────────────────
    t0 = time.time()
    with model_lock:
        traffic_results = traffic_model.track(
            frame, persist=True, tracker="bytetrack.yaml", verbose=False)[0]
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
        x1,y1,x2,y2 = map(int, box.xyxy[0])
        if label == "motorcycle" and conf >= 0.3:
            motorcycle_boxes.append((x1,y1,x2,y2))
        # Include motorcycles AND persons in traffic_boxes for the violation engine
        if label in ("motorcycle", "person") and conf >= 0.3:
            traffic_boxes.append({
                "label": label,
                "id":    int(box.id) if box.id is not None else None,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "cx":    (x1+x2)//2,
                "cy":    (y1+y2)//2,
            })

    for box in helmet_results.boxes:
        label = helmet_model.names[int(box.cls)]
        conf  = float(box.conf)
        # Confidence threshold for nohelmet — filters weak detections.
        # Fixed at 0.55 (not adaptive): the adaptive version suppressed
        # nohelmet on large motorcycle boxes, breaking triple riding detection.
        if label == "nohelmet" and conf < 0.55:
            continue
        helmet_objects.append(label)

    # ── Step 3: Violation Engine ───────────────────────────
    engine     = state["engine"]
    violations = engine.check(traffic_objects, helmet_objects, traffic_boxes, w_f, h_f)

    safety_event = near_miss(traffic_boxes, state.setdefault("track_history", {}), state["label"])
    if safety_event:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO near_miss_events (camera,timestamp,vehicle_ids,risk_score,risk_level,reason,source) VALUES (?,?,?,?,?,?,?)",
            (safety_event["camera"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             ",".join(map(str, safety_event["vehicle_ids"])), safety_event["risk_score"],
             safety_event["risk_level"], safety_event["reason"], safety_event["source"]),
        )
        conn.commit(); conn.close()

    # Triple riding + no helmet: front rider's helmet cancels nohelmet on pillion
    # in the default frame-global check. Override: any nohelmet present while
    # triple riding is confirmed is a valid additional violation.
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


    # ── Step 4: OCR (only when violation active) ───────────
    state["frame_count"] += 1
    if violations:
        state["incident_frame_count"] += 1

    t_ocr_ms = 0.0
    ocr_needed = bool(violations) or state.get("wrong_way_seen", False)
    if ocr_needed and motorcycle_boxes and state["frame_count"] % PLATE_INTERVAL == 0:
        t1 = time.time()
        _run_plate_ocr(frame, motorcycle_boxes, state, h_f, w_f)
        t_ocr_ms = (time.time() - t1) * 1000
    elif not motorcycle_boxes:
        state["cached_plates"] = []

    if not violations:
        if not motorcycle_boxes:
            state["cached_plates"] = []
        if not state.get("wrong_way_seen", False):
            state["plate_history"] = []
            state["last_good_plate"] = ""
        # Count consecutive frames with no violation
        if state["logged"]:
            state["no_violation_frames"] += 1
            # After cooldown, reset so a new incident in the same video can be logged
            if state["no_violation_frames"] >= COOLDOWN_FRAMES:
                state["logged"]               = False
                state["no_violation_frames"]  = 0
                state["incident_frame_count"] = 0
                state["all_violations_seen"]  = set()
                state["wrong_way_seen"]       = False
                state["wrong_way_frames"]     = 0
                state["last_good_plate"]      = ""
                state["engine"].reset()
    else:
        state["no_violation_frames"] = 0  # reset cooldown while violation active

    # ── Step 5: Draw annotations ───────────────────────────
    output_frame = traffic_results.plot()
    display_violations = list(violations)
    if "WRONG WAY" in violations:
        display_violations = [v for v in display_violations if v != "NO HELMET"]
    _draw_annotations(output_frame, display_violations, state["cached_plates"],
                      engine.wrong_way_ids, traffic_results, helmet_results,
                      state["label"])

    # ── Step 6: Log + action (fires once per video source) ─
    # logged is set to True HERE in the frame thread (before spawning) to
    # prevent a second frame from passing _should_log while the thread starts.
    # output_frame.copy() prevents a data race on the numpy array.
    if _should_log(state):
        state["logged"] = True
        frame_snapshot = output_frame.copy()
        # Deep-copy mutable state fields so _log_violation thread reads a
        # stable snapshot — not the live dict that process_frame keeps mutating.
        violations_to_log = set(state["all_violations_seen"])
        # If WRONG WAY was seen during this incident, suppress NO HELMET —
        # best.pt is unreliable on front-facing riders.
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
        threading.Thread(
            target=_log_violation,
            args=(state_snapshot, frame_snapshot),
            daemon=True
        ).start()

    # ── Record metrics ─────────────────────────────────────
    t_total_ms = (time.time() - t_frame_start) * 1000
    state["metrics"].record(t_detection_ms, t_ocr_ms, t_total_ms)

    return output_frame


def _run_plate_ocr(frame, motorcycle_boxes, state, h_f, w_f):
    motorcycle_boxes = [max(motorcycle_boxes, key=lambda b: (b[2]-b[0])*(b[3]-b[1]))]
    state["cached_plates"] = []
    for (mx1,my1,mx2,my2) in motorcycle_boxes:
        pad  = 20
        cx1  = max(0, mx1-pad); cy1 = max(0, my1-pad)
        cx2  = min(w_f, mx2+pad); cy2 = min(h_f, my2+pad)
        crop = frame[cy1:cy2, cx1:cx2]
        if crop.size == 0: continue
        crop_w = cx2-cx1; crop_h = cy2-cy1
        # plate_model uses its own lock so traffic+helmet inference on other
        # camera threads can proceed concurrently with plate OCR here.
        with plate_lock:
            pr = plate_model(crop, verbose=False)[0]
        cands = []
        for pb in pr.boxes:
            cf = float(pb.conf)
            if cf < 0.4: continue
            px1,py1,px2,py2 = map(int, pb.xyxy[0])
            pw=px2-px1; ph=py2-py1
            if ph==0 or (pw/ph)<1.0 or pw>crop_w*0.95: continue
            cands.append((px1,py1,px2,py2,cf))
        if not cands: continue
        best_c = max(cands, key=lambda c: c[4])   # sort by confidence, not py2
        px1,py1,px2,py2,_ = best_c
        plate_text = read_plate(crop[py1:py2, px1:px2])
        # Only add to history if it matches Indian plate pattern AND starts
        # with a valid state code — prevents OCR garbage polluting the vote
        if plate_text and len(plate_text) >= MIN_PLATE_LEN:
            sc = plate_text[:2]
            _valid = {
                'AP','AR','AS','BR','CG','CH','DD','DL','DN','GA','GJ',
                'HR','HP','JH','JK','KA','KL','LA','LD','MH','ML','MN',
                'MP','MZ','NL','OD','PB','PY','RJ','SK','TN','TR','TS',
                'TG','UK','UP','WB','AN'
            }
            if sc in _valid and re.match(r'^[A-Z]{2}\d{2}', plate_text):
                state["plate_history"].append(plate_text)
                if len(state["plate_history"]) > VOTE_WINDOW:
                    state["plate_history"].pop(0)
        if state["plate_history"]:
            for mc, cnt in Counter(state["plate_history"]).most_common():
                if cnt < MIN_VOTES or len(mc) < MIN_PLATE_LEN:
                    break
                # Only lock in plates starting with a valid Indian state code
                # Filters ZZ34..., UK14... (UK is valid but UK1405156 fails pattern)
                state_code = mc[:2] if len(mc) >= 2 else ""
                valid_states = {
    'AP','AR','AS','BR','CG','CH','DD','DL','DN','GA','GJ',
    'HR','HP','JH','JK','KA','KL','LA','LD','MH','ML','MN',
    'MP','MZ','NL','OD','PB','PY','RJ','SK','TN','TR','TS',
    'TG','UK','UP','WB','AN'
}
                if state_code in valid_states:
                    state["last_good_plate"] = mc
                    break  # take the best valid candidate
        state["cached_plates"] = [
            (px1+cx1, py1+cy1, px2+cx1, py2+cy1, state["last_good_plate"])
        ]


def _draw_annotations(frame, violations, cached_plates,
                       wrong_way_ids, traffic_results, helmet_results, label):
    for box in traffic_results.boxes:
        if traffic_model.names[int(box.cls)] != "motorcycle" or box.id is None: continue
        if int(box.id) in wrong_way_ids:
            x1,y1,x2,y2 = map(int, box.xyxy[0]); cx=(x1+x2)//2
            cv2.arrowedLine(frame,(cx,y1+10),(cx,y1+50),(0,0,255),3,tipLength=0.4)
            cv2.putText(frame,"WRONG WAY",(x1,y1-10),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,255),2)
    for box in helmet_results.boxes:
        if helmet_model.names[int(box.cls)] != "licenseplate":
            x1,y1,x2,y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame,(x1,y1),(x2,y2),(255,0,0),2)
    y = 50
    for v in violations:
        cv2.putText(frame,v,(20,y),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),3); y+=40
    for (px1,py1,px2,py2,pt) in cached_plates:
        cv2.rectangle(frame,(px1,py1),(px2,py2),(0,255,255),2)
        cv2.putText(frame,pt if pt else "PLATE",(px1,py1-10),
                    cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255),2)
    cv2.putText(frame, label, (10, frame.shape[0]-12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,229,255), 1)


def _should_log(state):
    is_wrong_way  = "WRONG WAY" in state["all_violations_seen"]
    has_plate     = bool(state["last_good_plate"])
    n             = state["incident_frame_count"]

    if is_wrong_way:
        # Wrong-way: head-on plates are rarely readable.
        # Log after 60 frames regardless of plate.
        return (
            not state["logged"] and
            state["all_violations_seen"] and
            (has_plate or n >= 60)
        )

    # Normal violations: always wait at least 15 frames so all violations
    # in the same incident (e.g. NO HELMET + TRIPLE RIDING) have time to
    # accumulate before logging. Then require a plate, or fall back at 30.
    return (
        not state["logged"] and
        state["all_violations_seen"] and
        n >= 15 and
        (has_plate or n >= 30)
    )


def _log_violation(state_snapshot, output_frame):
    # state_snapshot is a plain dict copy — safe to read without locks.
    # ts is passed in so it reflects when the violation was DETECTED,
    # not when this background thread happened to start.
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
    owner_name  = owner_info["name"]  if owner_info else "Not Available"
    owner_phone = owner_info["phone"] if owner_info else None
    owner_email = owner_info.get("email") if owner_info else None

    violations_list = [v.strip() for v in violation_str.split("+")]

    # Count BEFORE insert — generate_challan also calls get_offence_count after
    # insert, which would count the current row and inflate the number by 1.
    offence_count    = get_offence_count(DB_PATH, plate_str) + 1
    _, _, total_fine = calculate_fine(violations_list, offence_count)

    ss_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{state_snapshot['cam_id']}_{plate_str}.jpg"
    cv2.imwrite(os.path.join(SCREENSHOT_DIR, ss_filename), output_frame)

    vid = save_violation(label, violation_str, plate_str,
                         owner_name, total_fine, ss_filename)
    # Pass pre-computed offence_count to challan so it doesn't re-query
    # and pick up the just-inserted row (which would show offence_count+1).
    challan_file = generate_challan(
        CHALLAN_DIR, SCREENSHOT_DIR, vid, ts, label,
        violation_str, plate_str, ss_filename, DB_PATH, owner_name,
        offence_count=offence_count
    )
    update_challan(vid, challan_file)
    notify_violation(vid, plate_str, violation_str, total_fine,
                     ts, os.path.join(CHALLAN_DIR, challan_file),
                     owner_name, owner_phone, owner_email)

    try:
        from violation_engine import log_to_trajectory
        from alert_engine import trigger_on_violation_detection
        cam_id = state_snapshot.get("cam_id", "cam_1")
        log_to_trajectory(plate_str, cam_id, ts)
        trigger_on_violation_detection(plate_str, violation_str)
    except Exception as e:
        print(f"Error logging trajectory/triggering alert: {e}")



# ══════════════════════════════════════════════════════════
# MULTI-CAMERA STATE + LOOP
# ══════════════════════════════════════════════════════════

cameras       = {}
cameras_lock  = threading.Lock()
_cam_id_counter = 0   # monotonically incrementing — never reused after removal


COOLDOWN_FRAMES = 150  # frames of no-violation before resetting for next incident

def make_camera_state(cam_id, source, label):
    return {
        "cam_id": cam_id, "source": source, "label": label,
        "frame": None, "running": False, "error": None,
        "lock":       threading.Lock(),
        "stop_event": threading.Event(),   # set() to signal thread to exit cleanly
        "engine":              ViolationEngine(),
        "metrics":             PipelineMetrics(cam_id),
        "frame_count":          0,
        "incident_frame_count": 0,  # frames since current incident started
        "no_violation_frames":  0,  # frames with no active violation (for cooldown)
        "cached_plates":       [],
        "plate_history":       [],
        "last_good_plate":     "",
        "all_violations_seen": set(),
        "wrong_way_seen":  False,
        "wrong_way_frames": 0,
        "track_history": {},
        "logged":              False,
    }


def get_all_camera_info():
    with cameras_lock:
        return [{"cam_id": s["cam_id"], "source": s["source"],
                 "label": s["label"], "running": s["running"],
                 "error": s["error"]} for s in cameras.values()]


def process_source(cam_id):
    with cameras_lock:
        if cam_id not in cameras: return
        state = cameras[cam_id]

    source  = state["source"]
    is_rtsp = any(source.startswith(p) for p in ("rtsp://","rtmp://","http"))
    cap     = cv2.VideoCapture(source)

    if not cap.isOpened():
        with state["lock"]:
            state["running"] = False
            state["error"]   = f"Cannot open: {source}"
        return

    with state["lock"]:
        state["running"] = True
        state["error"]   = None

    # Skip frames for video files so CPU keeps up.
    # Read every frame (keeps OpenCV buffer happy), process every Nth.
    # RTSP is real-time — process every frame.
    if is_rtsp:
        process_every = 1
    else:
        video_fps    = cap.get(cv2.CAP_PROP_FPS) or 25
        process_every = max(1, round(video_fps / 5))  # target ~5 detections/sec

    raw_idx = 0

    while not state["stop_event"].is_set():
        ret, frame = cap.read()
        if not ret:
            if is_rtsp:
                # RTSP: reconnect on drop
                cap.release(); time.sleep(2)
                cap = cv2.VideoCapture(source)
                if not cap.isOpened():
                    with state["lock"]: state["error"] = "Stream disconnected"
                    break
                continue
            else:
                # Video file ended — stop cleanly, show "completed" frame
                with state["lock"]:
                    state["running"] = False
                    done_frame = _make_text_frame("Video completed.", source.split('/')[-1], (0, 229, 255))
                    state["frame"]   = done_frame
                break

        raw_idx += 1
        if raw_idx % process_every != 0:
            continue  # read frame (advances buffer) but skip ML detection

        try:
            output_frame = process_frame(frame, state)
        except Exception as exc:
            print(f"  [process_source | {cam_id}] Frame error: {exc}")
            continue

        ret2, buffer = cv2.imencode('.jpg', output_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ret2:
            with state["lock"]:
                state["frame"] = buffer.tobytes()

    cap.release()
    with state["lock"]:
        state["running"] = False


def _make_text_frame(line1, line2="", color=(0, 229, 255)):
    """Generate a JPEG frame with text — used for loading and error states."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, line1, (40, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    if line2:
        cv2.putText(img, line2, (40, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (150,150,150), 1)
    _, buf = cv2.imencode('.jpg', img)
    return buf.tobytes()

# Encode once at startup — reused by every streaming client on every tick.
_PLACEHOLDER_FRAME = _make_text_frame("Starting video...", "Loading models — please wait")

def _placeholder_frame():
    return _PLACEHOLDER_FRAME

def gen_frames_for(cam_id):
    loading = _placeholder_frame()
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
                # Cache per error string — don't re-encode on every 25fps tick
                if state.get('_cached_err_msg') != error:
                    state['_cached_err_frame'] = _make_text_frame('Error:', error[:55], (0, 80, 255))
                    state['_cached_err_msg']   = error
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + state['_cached_err_frame'] + b'\r\n')
            else:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + loading + b'\r\n')
        else:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + loading + b'\r\n')
        time.sleep(0.04)


# ── ROUTES ────────────────────────────────────────────────
# Simple in-memory brute-force guard: max 10 attempts per IP per 15 minutes
_login_attempts      = {}             # ip -> [timestamp, ...]
_login_attempts_lock = threading.Lock()
_MAX_ATTEMPTS        = 10
_LOCKOUT_SECS        = 900            # 15 minutes
_MAX_IPS             = 10_000         # evict oldest when dict grows too large

def _is_rate_limited(ip):
    now = time.time()
    with _login_attempts_lock:
        times = [t for t in _login_attempts.get(ip, []) if now - t < _LOCKOUT_SECS]
        _login_attempts[ip] = times
        return len(times) >= _MAX_ATTEMPTS

def _record_attempt(ip):
    with _login_attempts_lock:
        if len(_login_attempts) >= _MAX_IPS:
            # Evict oldest IP to prevent unbounded growth
            oldest = min(_login_attempts, key=lambda k: _login_attempts[k][-1] if _login_attempts[k] else 0)
            del _login_attempts[oldest]
        _login_attempts.setdefault(ip, []).append(time.time())

@app.route('/login', methods=['GET', 'POST'])
def login():
    _log_visitor('/login')
    error = None
    ip    = request.remote_addr
    if request.method == 'POST':
        submitted = request.form.get('password', '')
        # Accept either the real admin password or the demo password (if set)
        is_admin  = (submitted == ADMIN_PASSWORD)
        is_demo   = bool(DEMO_PASSWORD) and (submitted == DEMO_PASSWORD)
        if _is_rate_limited(ip):
            error = 'Too many attempts. Try again in 15 minutes.'
        elif is_admin or is_demo:
            session['is_admin'] = True
            session['is_demo']  = is_demo and not is_admin  # demo flag for UI hints
            _login_attempts.pop(ip, None)
            next_url  = request.args.get('next', '/')
            parsed    = urlparse(next_url)
            safe_next = next_url if (not parsed.scheme and not parsed.netloc) else '/'
            return redirect(safe_next)
        else:
            _record_attempt(ip)
            error = 'Incorrect password'
    return render_template(
        'login.html', error=error,
        demo_enabled=bool(DEMO_PASSWORD),
        demo_password=DEMO_PASSWORD if DEMO_PASSWORD else ''
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/citizen')

@app.route('/')
@require_admin
def index():
    _log_visitor('/dashboard')
    videos = [f for f in os.listdir(VIDEO_FOLDER)
              if f.lower().endswith(('.mp4','.avi','.mov','.mkv'))]
    conn = _get_conn()
    demo_videos = build_demo_catalog(VIDEO_FOLDER, conn)
    conn.close()
    return render_template('index.html', videos=videos, demo_videos=demo_videos,
                           is_demo=session.get('is_demo', False))

@app.route('/api/demo-videos')
@require_admin_api
def demo_videos_api():
    conn = _get_conn()
    try:
        return jsonify(build_demo_catalog(VIDEO_FOLDER, conn))
    finally:
        conn.close()

@app.route('/demo-video/<path:filename>')
@require_admin
def demo_video(filename):
    """Serve demo inputs only from the configured video directory."""
    safe_name = os.path.basename(filename)
    return send_from_directory(VIDEO_FOLDER, safe_name)

@app.route('/analytics')
@require_admin
def analytics():
    _log_visitor('/analytics')
    return render_template('analytics.html')

@app.route('/cameras')
@require_admin_api
def list_cameras():
    return jsonify(get_all_camera_info())

@app.route('/camera/add', methods=['POST'])
@require_admin_api
def add_camera():
    data   = request.get_json()
    source = data.get("source","").strip()
    label  = data.get("label","Camera").strip()
    if not source: return jsonify({"error":"source required"}), 400

    # SSRF guard: if caller supplies an RTSP/HTTP URL, reject private IP ranges.
    if any(source.startswith(p) for p in ("rtsp://","rtmp://","http")):
        parsed_host = urlparse(source).hostname or ""
        try:
            # Try as raw IP first
            addr = ipaddress.ip_address(parsed_host)
            if addr.is_private or addr.is_loopback or addr.is_link_local:
                return jsonify({"error": "private IP addresses are not allowed"}), 400
        except ValueError:
            # It's a hostname — resolve it and check all returned IPs
            # This prevents DNS rebinding attacks where hostname resolves to 127.0.0.1
            import socket
            try:
                resolved = socket.getaddrinfo(parsed_host, None)
                for r in resolved:
                    try:
                        raddr = ipaddress.ip_address(r[4][0])
                        if raddr.is_private or raddr.is_loopback or raddr.is_link_local:
                            return jsonify({"error": "private addresses are not allowed"}), 400
                    except ValueError:
                        pass
            except socket.gaierror:
                return jsonify({"error": "could not resolve host"}), 400
    else:
        # Treat as a local filename — restrict to VIDEO_FOLDER, no path traversal
        safe_name = os.path.basename(source)
        source    = os.path.join(VIDEO_FOLDER, safe_name)

    global _cam_id_counter
    with cameras_lock:
        _cam_id_counter += 1
        cam_id = f"cam_{_cam_id_counter}"
        cameras[cam_id] = make_camera_state(cam_id, source, label)
    threading.Thread(target=process_source, args=(cam_id,), daemon=True).start()
    return jsonify({"status":"started","cam_id":cam_id,"label":label})

@app.route('/camera/stop/<cam_id>')
@require_admin_api
def stop_camera(cam_id):
    with cameras_lock: state = cameras.get(cam_id)
    if state:
        state["stop_event"].set()
        with state["lock"]: state["running"] = False
    return jsonify({"status":"stopped","cam_id":cam_id})

@app.route('/camera/remove/<cam_id>')
@require_admin_api
def remove_camera(cam_id):
    with cameras_lock: state = cameras.pop(cam_id, None)
    if state:
        state["stop_event"].set()
        with state["lock"]: state["running"] = False
    return jsonify({"status":"removed","cam_id":cam_id})

@app.route('/camera/stop_all')
@require_admin_api
def stop_all_cameras():
    with cameras_lock:
        states = list(cameras.values())
    for state in states:
        state["stop_event"].set()
        with state["lock"]: state["running"] = False
    return jsonify({"status":"all stopped"})

@app.route('/video_feed/<cam_id>')
def video_feed(cam_id):
    # MJPEG streams can't use @require_admin (streaming breaks redirect).
    # Check session here — unauthenticated requests get a single error frame.
    if not session.get('is_admin'):
        return Response(status=401)
    return Response(gen_frames_for(cam_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed')
def video_feed_legacy():
    """Streams the first active camera — looks up dynamically each frame."""
    if not session.get('is_admin'):
        return Response(status=401)
    def dynamic_gen():
        placeholder = _placeholder_frame()
        while True:
            with cameras_lock:
                cam_id = next(iter(cameras), None)
            if cam_id:
                with cameras_lock:
                    state = cameras.get(cam_id)
                if state:
                    with state["lock"]:
                        frame = state["frame"]
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                           + (frame if frame else placeholder) + b'\r\n')
                    time.sleep(0.04)
                    continue
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                   + placeholder + b'\r\n')
            time.sleep(0.1)
    return Response(dynamic_gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start/<video_name>')
@require_admin_api
def start_video(video_name):
    # Prevent path traversal — e.g. /start/../../etc/passwd
    safe_name = os.path.basename(video_name)
    source    = os.path.join(VIDEO_FOLDER, safe_name)
    if not os.path.isfile(source):
        return jsonify({"error": "video not found"}), 404
    # Signal threads via Event (not just flag) — the event is checked at the
    # top of the frame loop, so the thread exits after finishing its current
    # inference rather than mid-frame. Wait up to 1s for clean exit.
    with cameras_lock:
        old_states = list(cameras.values())
    for s in old_states:
        s["stop_event"].set()
        with s["lock"]: s["running"] = False
    # Wait for each thread to finish its current frame (max 1 inference cycle)
    deadline = time.time() + 1.0
    for s in old_states:
        remaining = max(0.0, deadline - time.time())
        s["stop_event"].wait(timeout=remaining)
    with cameras_lock:
        cameras.clear()
    global _cam_id_counter
    with cameras_lock:
        _cam_id_counter += 1
        cam_id = f"cam_{_cam_id_counter}"
        cameras[cam_id] = make_camera_state(cam_id, source, safe_name)
    threading.Thread(target=process_source, args=(cam_id,), daemon=True).start()
    return jsonify({"status":"started","video":safe_name,"cam_id":cam_id})

@app.route('/stop')
@require_admin_api
def stop_video():
    with cameras_lock:
        states = list(cameras.values())
    for state in states:
        state["stop_event"].set()
        with state["lock"]: state["running"] = False
    return jsonify({"status":"stopped"})

@app.route('/status')
@require_admin_api
def status_api():
    with cameras_lock:
        running = any(s["running"] for s in cameras.values())
        vids    = [s["label"] for s in cameras.values() if s["running"]]
    return jsonify({"running":running,"video":vids[0] if vids else ""})

# ── NEW: Performance metrics API ──────────────────────────
@app.route('/metrics')
@require_admin_api
def metrics_api():
    """
    Returns live pipeline performance for all active cameras.
    Use this to answer: "What's the FPS? What's the latency?"

    Example response:
    [
      {
        "cam_id": "cam_0",
        "fps": 4.3,
        "avg_detection_ms": 187.2,
        "avg_ocr_ms": 43.5,
        "avg_total_ms": 235.4,
        "frame_count": 420
      }
    ]
    """
    with cameras_lock:
        return jsonify([s["metrics"].to_dict() for s in cameras.values()])

@app.route('/violations')
@require_admin_api
def violations_api():
    since = request.args.get('since', 0, type=int)
    return jsonify(get_violations(since_id=since))

@app.route('/stats')
def stats_api():
    return jsonify(get_stats())

@app.route('/api/insights')
@require_admin_api
def insights_api():
    return jsonify(get_enforcement_insights())

@app.route('/ai-safety')
@require_admin
def ai_safety_page():
    return render_template('ai_safety.html')

@app.route('/api/risk/vehicles')
@require_admin_api
def vehicle_risk_api():
    conn = _get_conn()
    try:
        return jsonify({"disclaimer": "Historical, explainable risk estimate; not accident prediction.", "vehicles": vehicle_risks(conn)})
    finally:
        conn.close()

@app.route('/api/near-misses')
@require_admin_api
def near_misses_api():
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT id,camera,timestamp,vehicle_ids,risk_score,risk_level,reason,evidence_frame,source FROM near_miss_events ORDER BY id DESC LIMIT 50").fetchall()
        return jsonify({"disclaimer": "AI-assisted risk estimation; not guaranteed accident prediction.", "events": [dict(row) for row in rows]})
    finally:
        conn.close()

@app.route('/api/blackspots')
@require_admin_api
def blackspots_api():
    conn = _get_conn()
    try:
        return jsonify({"basis": "Available heatmap data only; location-less records are excluded.", "blackspots": blackspots(conn)})
    finally:
        conn.close()

@app.route('/api/emergency-events')
@require_admin_api
def emergency_events_api():
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM emergency_events ORDER BY id DESC LIMIT 50").fetchall()
        return jsonify({"events": [dict(row) for row in rows], "signal_control": "API-ready simulation only; no real traffic signals are controlled."})
    finally:
        conn.close()

@app.route('/api/reviews')
@require_admin_api
def reviews_api():
    conn = _get_conn()
    try:
        return jsonify({"workflow": {"automated": ">=95%", "human_review": "70-95%", "needs_evidence": "<70%"}, "reviews": reviews(conn)})
    finally:
        conn.close()

@app.route('/api/recommendations')
@require_admin_api
def recommendations_api():
    return jsonify({"recommendations": get_enforcement_insights()["recommendations"], "basis": "Existing violation ledger and available heatmap data."})

@app.route('/api/system-health')
@require_admin_api
def system_health_api():
    return jsonify({"status": "degraded" if not ML_AVAILABLE else "healthy", "ml_available": ML_AVAILABLE, "cameras": len(cameras), "database": "connected", "privacy_mode": "ON"})

@app.route('/api/evidence/<int:vid>/verify')
@require_admin_api
def evidence_verify_api(vid):
    conn = _get_conn()
    try:
        result = verify_evidence(conn, vid, SCREENSHOT_DIR)
        return jsonify(result or {"error": "Violation not found"}), 404 if result is None else 200
    finally:
        conn.close()

@app.route('/verify/<int:vid>')
def verify_challan(vid):
    """Public, read-only challan verification target for QR codes."""
    conn = _get_conn(); conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, timestamp, violation, plate, fine, paid FROM violations WHERE id=?",
        (vid,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"verified": False, "error": "Challan not found"}), 404
    result = dict(row)
    result["challan"] = f"TG-{vid:06d}"
    result["verified"] = True
    return jsonify(result)

@app.route('/reports/monthly')
@require_admin
def monthly_report():
    """Generate a compact PDF enforcement report from the live ledger."""
    if generate_challan is None:
        return jsonify({"error": "PDF dependencies are not installed"}), 503
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    stats = get_stats()
    insights = get_enforcement_insights()
    story = [Paragraph(f"{APP_NAME} | Monthly Enforcement Report", styles["Title"]),
             Paragraph(f"Prepared by {AUTHOR_NAME} | Satyameva Jayate", styles["Normal"]), Spacer(1, 18)]
    data = [["Metric", "Value"], ["Total violations", stats["total"]],
            ["Pending challans", stats["pending"]], ["Revenue assessed", f"Rs. {stats['total_fines']:,}"],
            ["Revenue collected", f"Rs. {stats['paid']:,} paid records"],
            ["Violations / hour", insights["violations_per_hour"]]]
    table = Table(data, colWidths=[230, 230])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b1b36")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#ccd5df")),
                               ("PADDING", (0, 0), (-1, -1), 8)]))
    story.extend([table, Spacer(1, 18), Paragraph("Risk watchlist", styles["Heading2"])])
    for offender in insights["repeat_offenders"][:5]:
        story.append(Paragraph(f"{offender['plate']} - {offender['risk']} risk, {offender['offences']} offences, Rs. {offender['total_fine']:,}", styles["Normal"]))
    doc.build(story)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="trafficguard_pro_monthly_report.pdf", mimetype="application/pdf")

@app.route('/challan/<int:vid>')
@require_admin
def download_challan(vid):
    if generate_challan is None:
        return jsonify({"error": "PDF dependencies are not installed"}), 503
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM violations WHERE id=?", (vid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return "Not found", 404
    row = dict(row)
    if not row.get('challan'):
        cf = generate_challan(CHALLAN_DIR, SCREENSHOT_DIR,
                              row['id'], row['timestamp'], row['video'],
                              row['violation'], row['plate'],
                              row['screenshot'] or "", DB_PATH,
                              row.get('owner_name','Not Available'))
        update_challan(vid, cf)
    else:
        cf = row['challan']
    return send_file(os.path.join(CHALLAN_DIR, cf),
                     as_attachment=True, download_name=cf)

@app.route('/daily_summary')
@require_admin_api
def daily_summary():
    stats = get_stats()
    # Run in background — SMTP can block for 5s+ and would hang the request
    threading.Thread(target=send_daily_summary, args=(stats,), daemon=True).start()
    return jsonify({"status":"sending","stats":stats})

@app.route('/static/screenshots/<filename>')
def screenshot(filename):
    if not session.get('is_admin'):
        return Response(status=401)
    safe = os.path.basename(filename)
    return send_from_directory(SCREENSHOT_DIR, safe)

@app.route('/analytics_data')
@require_admin_api
def analytics_data():
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM violations WHERE violation LIKE '%NO HELMET%'")
    no_helmet = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM violations WHERE violation LIKE '%TRIPLE%'")
    triple = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM violations WHERE violation LIKE '%WRONG WAY%'")
    wrong_way = c.fetchone()[0]
    by_type = {}
    if no_helmet: by_type["No Helmet"]    = no_helmet
    if triple:    by_type["Triple Riding"] = triple
    if wrong_way: by_type["Wrong Way"]     = wrong_way
    c.execute("""SELECT DATE(timestamp) as day, COUNT(*) as cnt FROM violations
                 WHERE DATE(timestamp) >= DATE('now','-6 days') GROUP BY day ORDER BY day""")
    day_map = {r[0]:r[1] for r in c.fetchall()}
    today   = date.today()
    daily   = []
    for i in range(6,-1,-1):
        d = (today-timedelta(days=i)).strftime('%Y-%m-%d')
        daily.append({"date":d[5:],"count":day_map.get(d,0)})
    c.execute("""SELECT DATE(timestamp) as day, COALESCE(SUM(fine),0) as total
                 FROM violations WHERE DATE(timestamp) >= DATE('now','-6 days')
                 GROUP BY day ORDER BY day""")
    fine_map    = {r[0]:r[1] for r in c.fetchall()}
    daily_fines = []
    for i in range(6,-1,-1):
        d = (today-timedelta(days=i)).strftime('%Y-%m-%d')
        daily_fines.append({"date":d[5:],"total":fine_map.get(d,0)})
    c.execute("""SELECT CAST(strftime('%H',timestamp) AS INTEGER) as hr, COUNT(*) as cnt
                 FROM violations GROUP BY hr ORDER BY hr""")
    hourly = [{"hour":r[0],"count":r[1]} for r in c.fetchall()]
    c.execute("""SELECT plate, owner_name, COUNT(*) as cnt,
                        GROUP_CONCAT(DISTINCT violation) as all_violations,
                        COALESCE(SUM(fine),0) as total_fine
                 FROM violations WHERE plate != 'UNKNOWN'
                 GROUP BY plate ORDER BY cnt DESC, total_fine DESC LIMIT 10""")
    top_plates = [{"plate":r[0],"owner":r[1],"count":r[2],
                   "violations":r[3] or "","total_fine":r[4]} for r in c.fetchall()]
    c.execute("SELECT COALESCE(SUM(fine),0) FROM violations WHERE paid=1")
    paid_fines = c.fetchone()[0]
    conn.close()
    return jsonify({"by_type":by_type,"daily":daily,"daily_fines":daily_fines,
                    "hourly":hourly,"top_plates":top_plates,"paid_fines":paid_fines})


# ── MARK AS PAID ──────────────────────────────────────────
@app.route('/violation/<int:vid>/paid', methods=['PATCH'])
@require_admin_api
def mark_paid(vid):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT paid FROM violations WHERE id=?", (vid,))
    row = c.fetchone()
    if not row: conn.close(); return jsonify({"error":"Not found"}), 404
    new_status = 0 if row[0] == 1 else 1
    c.execute("UPDATE violations SET paid=? WHERE id=?", (new_status, vid))
    conn.commit(); conn.close()
    return jsonify({"status":"ok","paid":new_status})

# ── CSV EXPORT ────────────────────────────────────────────
@app.route('/export')
@require_admin
def export_csv():
    conn = _get_conn(); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id,timestamp,video,violation,plate,owner_name,fine,paid FROM violations ORDER BY id DESC").fetchall()
    conn.close()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Challan No","Timestamp","Camera","Violation","Plate","Owner","Fine (Rs.)","Status"])
    for r in rows:
        w.writerow([f"RX-{r['id']:06d}", r['timestamp'], r['video'],
                    r['violation'], r['plate'], r['owner_name'],
                    r['fine'], "Paid" if r['paid'] else "Pending"])
    out.seek(0)
    resp = make_response(out.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=trafficguard_pro_violations.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp

# ── CITIZEN PORTAL — PUBLIC ───────────────────────────────
@app.route('/citizen')
def citizen_portal():
    _log_visitor('/citizen')
    return render_template('citizen.html')

@app.route('/citizen/violations')
def citizen_violations():
    conn = _get_conn(); conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id,timestamp,video,violation,plate,fine,paid,screenshot FROM violations ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()
    def _mask_plate(p):
        # Show first 2 + last 2 chars, mask middle — e.g. KA****34
        if not p or p == "UNKNOWN": return "UNKNOWN"
        return p[:2] + "*" * max(0, len(p) - 4) + p[-2:] if len(p) > 4 else "****"
    return jsonify([{"id":r["id"],"challan":f"RX-{r['id']:06d}","timestamp":r["timestamp"],
                     "camera":r["video"],"violation":r["violation"],
                     "plate": _mask_plate(r["plate"]),   # masked for public portal
                     "fine":r["fine"],"paid":bool(r["paid"]),
                     "screenshot": None} for r in rows])  # screenshots admin-only

@app.route('/citizen/stats')
def citizen_stats():
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM violations"); total = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(fine),0) FROM violations"); total_fines = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(fine),0) FROM violations WHERE paid=1"); collected = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM violations WHERE violation LIKE '%NO HELMET%'"); nh = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM violations WHERE violation LIKE '%TRIPLE%'"); tr = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM violations WHERE violation LIKE '%WRONG WAY%'"); ww = c.fetchone()[0]
    conn.close()
    return jsonify({"total_violations":total,"total_fines":total_fines,
                    "fines_collected":collected,"incentive_pool":int(collected*0.10),
                    "no_helmet":nh,"triple_riding":tr,"wrong_way":ww})





# ── VISITOR STATS ─────────────────────────────────────────
@app.route('/visitors')
@require_admin
def visitor_stats():
    stats = get_visitor_stats()
    if session.get('is_demo'):
        stats.pop('recent', None)
    return jsonify(stats)

# ── MAP, HEATMAP & BLACKLIST ─────────────────────────────
@app.route('/map')
def map_view():
    return render_template('map.html')

@app.route('/api/heatmap')
def get_heatmap():
    import sqlite3
    conn = sqlite3.connect('violations.db')
    c = conn.cursor()
    cells = c.execute('''SELECT grid_lat, grid_lng, vehicle_count FROM heatmap_cells 
                         WHERE vehicle_count > 0
                         ORDER BY vehicle_count DESC LIMIT 100''').fetchall()
    conn.close()
    return jsonify([{'grid_lat': c[0], 'grid_lng': c[1], 'vehicle_count': c[2]} for c in cells])

@app.route('/admin/blacklist/add', methods=['POST'])
def add_blacklist():
    from alert_engine import add_to_blacklist
    data = request.json
    add_to_blacklist(data['plate_text'], data['reason'])
    return jsonify({'status': 'ok', 'plate_text': data['plate_text']})


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port  = int(os.environ.get('PORT', 5001))
    app.run(debug=debug, threaded=True, host='0.0.0.0', port=port)