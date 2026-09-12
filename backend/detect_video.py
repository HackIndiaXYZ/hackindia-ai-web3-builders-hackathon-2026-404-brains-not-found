"""
VehicleTrack — Batch Video Processor
Processes all videos in /videos folder and saves annotated output to /video_results
"""

import cv2
import os
import re
import numpy as np
import easyocr
import threading
from collections import Counter, defaultdict
from ultralytics import YOLO

# ── MODEL PATHS ───────────────────────────────────────────
traffic_model = YOLO("models/yolov8s.pt")   # upgraded from yolov8n
helmet_model  = YOLO("models/best.pt")
plate_model   = YOLO("models/Plate.pt")
_reader     = easyocr.Reader(['en'], gpu=False)
_plate_lock = threading.Lock()

video_folder  = "videos"
output_folder = "video_results"
os.makedirs(output_folder, exist_ok=True)

# ── WRONG WAY CONFIG ──────────────────────────────────────
WRONG_WAY_FRAMES    = 5
WRONG_WAY_THRESHOLD = -5
WRONG_WAY_ZONE      = 0.7

_PLATE_RE = re.compile(r'[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}')

_STATE_FIXES = {
    'HH':'MH','HM':'MH','IH':'MH','NH':'MH',
    'EL':'KL','IL':'KL','KI':'KA','TZ':'TN','IK':'UK',
}
_VALID_STATES = {
    'AP','AR','AS','BR','CG','CH','DD','DL','DN','GA','GJ',
    'HR','HP','JH','JK','KA','KL','LA','LD','MH','ML','MN',
    'MP','MZ','NL','OD','PB','PY','RJ','SK','TN','TR','TS',
    'TG','UK','UP','WB','AN'
}

def _correct_plate(raw):
    t = re.sub(r'[^A-Z0-9]', '', raw.upper())
    t = t.replace('IND','').replace('INDIA','').replace('IN','')
    if len(t) < 4: return t
    chars = list(t)
    letter_map = {'0':'O','1':'I','5':'S','8':'B','6':'G','2':'Z'}
    for i in [0,1]:
        if i < len(chars) and chars[i].isdigit():
            chars[i] = letter_map.get(chars[i], chars[i])
    state = ''.join(chars[:2])
    if state not in _VALID_STATES and state in _STATE_FIXES:
        fixed = _STATE_FIXES[state]
        chars[0], chars[1] = fixed[0], fixed[1]
    digit_map = {'O':'0','I':'1','S':'5','B':'8','Z':'2','G':'6','A':'4','T':'7','L':'1'}
    for i in [2,3]:
        if i < len(chars) and chars[i].isalpha():
            chars[i] = digit_map.get(chars[i], chars[i])
    return ''.join(chars)

def read_plate(plate_crop):
    if plate_crop is None or plate_crop.size == 0: return ""
    h, w = plate_crop.shape[:2]
    if h < 5 or w < 5: return ""
    MAX_W = 300
    if w > MAX_W:
        scale_down = MAX_W / w
        h = max(1, int(h * scale_down)); w = MAX_W
        plate_crop = cv2.resize(plate_crop, (w, h), interpolation=cv2.INTER_AREA)
    scale = 3
    plate_big = cv2.resize(plate_crop, (w*scale, h*scale), interpolation=cv2.INTER_CUBIC)
    gray  = cv2.cvtColor(plate_big, cv2.COLOR_BGR2GRAY)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    best = ""
    for img in [gray, otsu]:
        try:
            texts = _reader.readtext(img, detail=0, paragraph=True)
            cleaned = _correct_plate(" ".join(texts))
            m = _PLATE_RE.search(cleaned)
            if m: return m.group()
            if len(cleaned) > len(best): best = cleaned
        except Exception:
            continue
    return best

PLATE_INTERVAL = 5
VOTE_WINDOW    = 20
MIN_VOTES      = 2


def get_overlap(boxA, boxB):
    """Fraction of boxA covered by boxB."""
    ax1, ay1, ax2, ay2 = boxA
    bx1, by1, bx2, by2 = boxB
    ix1, iy1 = max(ax1,bx1), max(ay1,by1)
    ix2, iy2 = min(ax2,bx2), min(ay2,by2)
    if ix2 <= ix1 or iy2 <= iy1: return 0.0
    inter = (ix2-ix1)*(iy2-iy1)
    areaA = max((ax2-ax1)*(ay2-ay1), 1)
    return inter / areaA


# read_plate is imported from plate_ocr (PaddleOCR-based)


def get_writer(output_path, width, height, fps):
    """
    Try codecs in order until one works on this machine.
    Mac: avc1 works best. Falls back to mp4v then XVID (.avi).
    """
    # Try avc1 (H.264) — best quality on Mac
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if writer.isOpened():
        print(f"  Using codec: avc1 → {output_path}")
        return writer, output_path

    # Try mp4v
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if writer.isOpened():
        print(f"  Using codec: mp4v → {output_path}")
        return writer, output_path

    # Final fallback: save as .avi with XVID (always works)
    avi_path = output_path.replace('.mp4', '.avi').replace('.mov', '.avi').replace('.mkv', '.avi')
    if not avi_path.endswith('.avi'):
        avi_path = os.path.splitext(output_path)[0] + '.avi'
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter(avi_path, fourcc, fps, (width, height))
    print(f"  Using codec: XVID → {avi_path}")
    return writer, avi_path


# ── MAIN LOOP ─────────────────────────────────────────────
videos = [f for f in os.listdir(video_folder)
          if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]

if not videos:
    print("No videos found in the 'videos' folder.")
    exit()

for video_name in videos:
    video_path  = os.path.join(video_folder, video_name)
    output_path = os.path.join(output_folder, f"processed_{video_name}")
    # Normalize extension to .mp4
    base = os.path.splitext(output_path)[0]
    output_path = base + ".mp4"

    print(f"\nProcessing: {video_name}")

    cap    = cv2.VideoCapture(video_path)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = int(cap.get(cv2.CAP_PROP_FPS)) or 25
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"  Resolution: {width}x{height} | FPS: {fps} | Frames: {total}")

    out, actual_output_path = get_writer(output_path, width, height, fps)

    if not out.isOpened():
        print(f"  ERROR: Could not create output file. Skipping.")
        cap.release()
        continue

    frame_count      = 0
    cached_plates    = []
    plate_history    = []
    last_good_plate  = ""
    track_cy_history = defaultdict(list)
    wrong_way_ids    = set()
    violations_found = []

    while True:
        ret, frame = cap.read()
        if not ret: break
        frame_count += 1

        if frame_count % 30 == 0:
            print(f"  Frame {frame_count}/{total}...", end='\r')

        traffic_results = traffic_model.track(
            frame, persist=True, tracker="bytetrack.yaml", verbose=False)[0]
        helmet_results  = helmet_model(frame, verbose=False)[0]

        traffic_objects  = []
        motorcycle_boxes = []
        helmet_objects   = []
        person_boxes     = []

        for box in traffic_results.boxes:
            label = traffic_model.names[int(box.cls)]
            conf  = float(box.conf)
            traffic_objects.append(label)
            if label == "motorcycle" and conf >= 0.3:
                motorcycle_boxes.append(list(map(int, box.xyxy[0])))
            if label == "person" and conf >= 0.4:
                person_boxes.append(list(map(int, box.xyxy[0])))

        for box in helmet_results.boxes:
            helmet_objects.append(helmet_model.names[int(box.cls)])

        # Wrong-way detection
        for box in traffic_results.boxes:
            if traffic_model.names[int(box.cls)] != "motorcycle" or box.id is None: continue
            track_id        = int(box.id)
            x1,y1,x2,y2    = map(int, box.xyxy[0])
            cx              = (x1+x2)//2
            cy              = (y1+y2)//2
            # Exclude bikes in outer 15% of frame (entry/exit zones)
            if cx < width * 0.15 or cx > width * 0.85:
                wrong_way_ids.discard(track_id); continue
            # Exclude very small detections (far-away bikes, partial views)
            area = (x2-x1) * (y2-y1)
            if area < (width * height * 0.01):
                wrong_way_ids.discard(track_id); continue
            track_cy_history[track_id].append(cy)
            if len(track_cy_history[track_id]) > WRONG_WAY_FRAMES+2:
                track_cy_history[track_id].pop(0)
            if len(track_cy_history[track_id]) >= WRONG_WAY_FRAMES:
                hist = track_cy_history[track_id]
                dy   = (hist[-1]-hist[-WRONG_WAY_FRAMES])/WRONG_WAY_FRAMES
                if dy < WRONG_WAY_THRESHOLD: wrong_way_ids.add(track_id)
                else: wrong_way_ids.discard(track_id)

        # Triple riding — 5% expansion, 50% overlap (tight — avoids adjacent bike riders)
        triple_riding = False
        for (mx1,my1,mx2,my2) in motorcycle_boxes:
            bw=mx2-mx1; bh=my2-my1
            bike_region = (
                max(0,mx1-int(bw*0.05)), max(0,my1-int(bh*0.05)),
                min(width,mx2+int(bw*0.05)), min(height,my2+int(bh*0.05))
            )
            count = sum(1 for (px1,py1,px2,py2) in person_boxes
                        if get_overlap((px1,py1,px2,py2), bike_region) > 0.50)
            if count >= 3: triple_riding = True; break

        # No helmet
        nohelmet_count = helmet_objects.count("nohelmet")
        helmet_count   = helmet_objects.count("helmet") + helmet_objects.count("motorcyclist")
        no_helmet      = ("motorcycle" in traffic_objects and
                          nohelmet_count > 0 and nohelmet_count > helmet_count)

        violations = []
        if no_helmet:     violations.append("NO HELMET")
        if triple_riding: violations.append("TRIPLE RIDING")
        if wrong_way_ids: violations.append("WRONG WAY")

        # Suppress NO HELMET when WRONG WAY is active — helmet classifier
        # is unreliable on front-facing riders coming head-on
        if "WRONG WAY" in violations and "NO HELMET" in violations:
            violations.remove("NO HELMET")

        for v in violations:
            if v not in violations_found:
                violations_found.append(v)

        if violations and motorcycle_boxes and frame_count % PLATE_INTERVAL == 0:
            # Use only the largest (closest) motorcycle
            mx1,my1,mx2,my2 = max(motorcycle_boxes, key=lambda b:(b[2]-b[0])*(b[3]-b[1]))
            pad_x     = int((mx2-mx1) * 0.2)
            pad_y_top = int((my2-my1) * 0.05)
            pad_y_bot = int((my2-my1) * 0.35)
            cx1  = max(0,     mx1 - pad_x)
            cy1  = max(0,     my1 - pad_y_top)
            cx2  = min(width, mx2 + pad_x)
            cy2  = min(height,my2 + pad_y_bot)
            crop = frame[cy1:cy2, cx1:cx2]
            if crop.size > 0:
                crop_w = cx2-cx1; crop_h = cy2-cy1
                plate_results = plate_model(crop, verbose=False)[0]
                cands = []
                for pb in plate_results.boxes:
                    cf = float(pb.conf)
                    if cf < 0.40: continue
                    px1,py1,px2,py2 = map(int, pb.xyxy[0])
                    pw=px2-px1; ph=py2-py1
                    if ph==0 or (pw/ph)<1.0 or pw>crop_w*0.95: continue
                    cands.append((px1,py1,px2,py2,cf))
                if cands:
                    px1,py1,px2,py2,_ = max(cands, key=lambda c: c[4])
                    pt = read_plate(crop[py1:py2, px1:px2])
                    if pt:
                        plate_history.append(pt)
                        if len(plate_history) > VOTE_WINDOW: plate_history.pop(0)
                    if plate_history:
                        mc, cnt = Counter(plate_history).most_common(1)[0]
                        if cnt >= MIN_VOTES and len(mc) >= 8: last_good_plate = mc
                    cached_plates = [(px1+cx1, py1+cy1, px2+cx1, py2+cy1, last_good_plate)]

        if not violations:
            cached_plates = []; plate_history = []

        # Draw
        output_frame = traffic_results.plot()

        for box in traffic_results.boxes:
            if traffic_model.names[int(box.cls)] != "motorcycle" or box.id is None: continue
            if int(box.id) in wrong_way_ids:
                x1,y1,x2,y2 = map(int, box.xyxy[0]); cx=(x1+x2)//2
                cv2.arrowedLine(output_frame,(cx,y1+10),(cx,y1+50),(0,0,255),3,tipLength=0.4)
                cv2.putText(output_frame,"WRONG WAY",(x1,y1-10),
                            cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,255),2)

        for box in helmet_results.boxes:
            if helmet_model.names[int(box.cls)] != "licenseplate":
                x1,y1,x2,y2 = map(int, box.xyxy[0])
                cv2.rectangle(output_frame,(x1,y1),(x2,y2),(255,0,0),2)

        y = 50
        for v in violations:
            cv2.putText(output_frame,v,(20,y),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),3); y+=40

        for (px1,py1,px2,py2,pt) in cached_plates:
            cv2.rectangle(output_frame,(px1,py1),(px2,py2),(0,255,255),2)
            cv2.putText(output_frame, pt if pt else "PLATE",(px1,py1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255),2)

        # ── WRITE FRAME TO FILE ───────────────────────────
        out.write(output_frame)

    # ── RELEASE ───────────────────────────────────────────
    cap.release()
    out.release()  # This flushes and finalizes the file

    # Verify the file was actually written
    if os.path.exists(actual_output_path) and os.path.getsize(actual_output_path) > 0:
        size_mb = os.path.getsize(actual_output_path) / (1024*1024)
        print(f"\n  ✅ Saved: {actual_output_path} ({size_mb:.1f} MB)")
        if violations_found:
            print(f"  Violations detected: {', '.join(violations_found)}")
        else:
            print(f"  No violations detected")
    else:
        print(f"\n  ❌ Output file is empty or missing: {actual_output_path}")

print("\nAll videos processed. Results saved in 'video_results'.")