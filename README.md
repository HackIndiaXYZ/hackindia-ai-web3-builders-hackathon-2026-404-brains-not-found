---
title: TrafficGuard Pro
emoji: 🚦
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 🚦 TrafficGuard Pro — AI Traffic Enforcement System

**TrafficGuard Pro** is an AI-powered Indian traffic enforcement system that analyzes dashcam or RTSP CCTV footage to detect violations, read Indian license plates, look up vehicle owners, generate PDF challans, and send notifications.

**Owner:** Pawan Singh — Founder & Full-Stack Developer. B.Tech CSE, Delhi Technical Campus (DTC), Greater Noida; Guru Gobind Singh Indraprastha University (GGSIPU); CGPA 9.16; expected graduation 2028. [GitHub](https://github.com/pawan00207) · pawan9140582015@gmail.com · LinkedIn: Pawan Singh.

The dashboard carries **Satyameva Jayate (सत्यमेव जयते)**. TrafficGuard Pro adds explainable penalty recommendations, repeat-offender alerts, vehicle comparison hooks, geolocation heat maps, live KPIs, batch status, OCR transparency, WhatsApp-ready notifications, trend analysis, role-ready access, dark mode, monthly PDF reports and QR challan verification. Facial recognition is documented as a future roadmap item only.
---

## Key Features

- Live RTSP stream and video file processing, multi-camera support
- No helmet detection — Sec 129 MV Act, Rs. 1,000 (20-frame vote window)
- Triple riding detection — Sec 128 MV Act, Rs. 1,000 (overlap-based, >50% IoU on motorcycle ROI)
- Wrong-way driving detection — Sec 184 MV Act, Rs. 5,000 (dual-mode ByteTrack trajectory analysis)
- Indian license plate recognition — 97.6% precision, 95.9% mAP@0.5 (avg across 3 datasets, 438 images)
- Repeat-offender fine multiplier (1× / 2× / 3×)
- PDF challan generation with QR payment link (ReportLab)
- Email notifications with retry logic (3 attempts, 2s delay)
- Login-protected admin dashboard with live MJPEG feed
- Public citizen portal — no login required, masked plate numbers
- Analytics page with 5 Chart.js charts, 6 KPIs
- CSV export, mark-as-paid, performance metrics API (`/metrics`)
- Dockerized — deployed live on Hugging Face Spaces (CPU, 16GB RAM)

---

## Project Structure

```
app.py              — Main Flask app + detection pipeline
violation_engine.py — No-helmet, triple-riding, wrong-way logic
challan.py          — PDF challan generation (ReportLab)
notifications.py    — Email / WhatsApp notification system
vahan.py            — Vehicle owner lookup (mock; real API drop-in ready)
plate_ocr.py        — Advanced Indian plate OCR (used by detect_video.py)
detect.py           — Batch image detection script
detect_video.py     — Batch video processing script
evaluate_model.py   — Model evaluation (best.pt + Plate.pt)
seed_db.py          — Seeds violations.db with demo data
templates/          — Flask HTML templates (login, dashboard, citizen, analytics)
static/             — Screenshots, challans
videos/             — Input video files
models/             — YOLOv8 weights (downloaded at Docker build time)
Dockerfile          — CPU-only build, pre-downloads models + EasyOCR
docker-compose.yml  — Local multi-container setup
```

---

## Setup (Local)

```bash
git clone <repository-url>
cd VehicleTrack-traffic-enforcement

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root (never commit this):

```
SECRET_KEY=your-random-secret-here
ADMIN_PASSWORD=your-admin-password

# Optional — one-click demo login (separate from admin password)
DEMO_PASSWORD=

# Optional — email notifications
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASS=your-app-password
CITIZEN_EMAIL=citizen@example.com
ADMIN_EMAIL=admin@example.com

# Optional — Vahan API
VAHAN_API_KEY=

# Demo owner details (shown when plate not in mock DB)
DEMO_NAME=Demo Owner
DEMO_PHONE=+910000000000
DEMO_EMAIL=demo@example.com
```

---

## Usage

### Web dashboard (recommended)

```bash
python app.py
```

Open `http://localhost:5001/citizen` — public citizen portal
Open `http://localhost:5001/login` — admin login (traffic police)

From the admin dashboard, select a video file or enter an RTSP URL and click **▶ ADD**.

### Batch video processing

```bash
python detect_video.py
```

Processes all `.mp4 / .avi / .mov / .mkv` files in the `videos/` folder. Annotated output saved to `video_results/`.

### Batch image detection

```bash
python detect.py
```

Processes all images in `images/`. Results saved to `results/`.

### Model evaluation

```bash
python evaluate_model.py
```

Runs YOLO `val()` on held-out test splits for `best.pt` and `Plate.pt`. Results saved to `results/model_eval/`.

---

## Models

| Model | Type | Purpose | mAP@0.5 |
|---|---|---|---|
| `yolov8s.pt` | COCO pretrained | Vehicle + person detection, ByteTrack | — |
| `best.pt` | Custom trained | Helmet / no-helmet classification | 76.5% |
| `Plate.pt` | Custom trained | Indian license plate localisation | 95.9% avg (438 images, 3 datasets) |

Models are downloaded automatically at Docker build time from a public Hugging Face model repo — no Git LFS required.

---

## Performance (Apple M4 CPU)

| Step | Latency |
|---|---|
| Traffic + helmet detection | ~185ms/frame |
| Plate OCR | ~43ms/crop |
| Full pipeline | ~235ms → ~4-6 FPS |
| PDF + email (background thread) | 3-7s — does not block the feed |

**Multi-camera note:** On CPU, each additional camera reduces per-camera FPS due to the GIL. The deployed version uses frame-skipping to keep video playback smooth on free-tier CPU.

---

## Deployment

Deployed on **Hugging Face Spaces** (Docker SDK, CPU Basic, 16GB RAM):

- ML models (`yolov8s.pt`, `best.pt`, `Plate.pt`) and EasyOCR weights are downloaded/pre-cached at Docker build time — no runtime download delay
- SQLite database auto-seeds with demo violations on cold start (container filesystem is ephemeral)
- Session cookies configured for HF's reverse proxy (`SESSION_COOKIE_SECURE=False`, `ProxyFix`)

### Run locally with Docker

```bash
docker-compose up
```

Add videos to `./videos/`, set env vars in `.env`. Challans and screenshots persist in `./static/`.

---

## Disclaimer

Educational project. Not for production law enforcement use.

---

*Powered by Pawan Singh.*