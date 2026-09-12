"""
VehicleTrack — Image Detection Script
Runs detection on all images in the images/ folder.
Output saved to results/ folder.
"""

from ultralytics import YOLO
import easyocr
import threading
from plate_ocr import read_plate as _plate_ocr_read
import os
import cv2
import numpy as np

# ── MODELS ────────────────────────────────────────────────
traffic_model = YOLO("models/yolov8s.pt")
helmet_model  = YOLO("models/best.pt")
plate_model   = YOLO("models/Plate.pt")
_reader     = easyocr.Reader(['en'], gpu=False)
_plate_lock = threading.Lock()

def read_plate(crop):
    return _plate_ocr_read(crop, _reader, _plate_lock)

image_folder  = "images"
output_folder = "results"
os.makedirs(output_folder, exist_ok=True)

print("Starting detection...\n")


def overlap_ratio(boxA, boxB):
    """Fraction of boxA covered by boxB."""
    ax1,ay1,ax2,ay2 = boxA
    bx1,by1,bx2,by2 = boxB
    ix1,iy1 = max(ax1,bx1), max(ay1,by1)
    ix2,iy2 = min(ax2,bx2), min(ay2,by2)
    if ix2 <= ix1 or iy2 <= iy1: return 0.0
    return ((ix2-ix1)*(iy2-iy1)) / max((ax2-ax1)*(ay2-ay1), 1)


# ── MAIN LOOP ─────────────────────────────────────────────
images = sorted([f for f in os.listdir(image_folder)
                 if f.lower().endswith((".jpg",".png",".jpeg"))])

if not images:
    print(f"No images in {image_folder}/"); exit()

print(f"Found {len(images)} images\n")

for image_name in images:
    image = cv2.imread(os.path.join(image_folder, image_name))
    if image is None:
        print(f"  ❌ Cannot read {image_name}\n"); continue

    img_h, img_w = image.shape[:2]
    print(f"Processing: {image_name}")

    # ── Traffic detection ──────────────────────────────
    traffic_results  = traffic_model(image, verbose=False)[0]
    traffic_objects  = []
    motorcycle_boxes = []  # (x1,y1,x2,y2)
    person_boxes     = []  # (x1,y1,x2,y2)

    for box in traffic_results.boxes:
        label = traffic_model.names[int(box.cls)]
        conf  = float(box.conf)
        traffic_objects.append(label)
        if label == "motorcycle" and conf >= 0.3:
            motorcycle_boxes.append(list(map(int, box.xyxy[0])))
        if label == "person" and conf >= 0.4:
            person_boxes.append(list(map(int, box.xyxy[0])))

    # ── Helmet detection ──────────────────────────────
    helmet_results = helmet_model(image, verbose=False)[0]
    helmet_objects = [helmet_model.names[int(b.cls)] for b in helmet_results.boxes]

    # ── No helmet ──────────────────────────────────────
    nohelmet_n = helmet_objects.count("nohelmet")
    helmet_n   = helmet_objects.count("helmet") + helmet_objects.count("motorcyclist")
    no_helmet  = "motorcycle" in traffic_objects and nohelmet_n > 0 and nohelmet_n > helmet_n

    # ── Triple riding — 5% expansion, 50% overlap ─────
    triple_riding = False
    for (mx1,my1,mx2,my2) in motorcycle_boxes:
        mw=mx2-mx1; mh=my2-my1
        ex1=max(0,mx1-int(mw*0.05)); ey1=max(0,my1-int(mh*0.05))
        ex2=min(img_w,mx2+int(mw*0.05)); ey2=min(img_h,my2+int(mh*0.05))
        count = sum(1 for (px1,py1,px2,py2) in person_boxes
                    if overlap_ratio((px1,py1,px2,py2),(ex1,ey1,ex2,ey2)) > 0.50)
        if count >= 3:
            triple_riding = True
            break

    violations = []
    if no_helmet:     violations.append("NO HELMET")
    if triple_riding: violations.append("TRIPLE RIDING")

    for v in violations: print(f"  🚨 {v}")
    if not violations:   print("  ✅ No violations")

    # ── Draw ──────────────────────────────────────────
    output_img = traffic_results.plot()
    for box in helmet_results.boxes:
        lbl = helmet_model.names[int(box.cls)]
        if lbl != "licenseplate":
            x1,y1,x2,y2 = map(int, box.xyxy[0])
            cv2.rectangle(output_img,(x1,y1),(x2,y2),
                          (0,0,255) if lbl=="nohelmet" else (255,128,0), 2)
    y = 50
    for v in violations:
        cv2.putText(output_img, v, (20,y), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0,0,255), 3)
        y += 55

    # ── Plate detection ───────────────────────────────
    # Process ONLY the single largest motorcycle — prevents double detection.
    # Largest by area = closest to camera = most likely to have readable plate.
    if violations and motorcycle_boxes:
        # Pick the single largest motorcycle box
        mx1,my1,mx2,my2 = max(motorcycle_boxes,
                               key=lambda b: (b[2]-b[0]) * (b[3]-b[1]))

        pad_x     = int((mx2-mx1) * 0.2)
        pad_y_top = int((my2-my1) * 0.05)
        pad_y_bot = int((my2-my1) * 0.35)
        cx1 = max(0,     mx1 - pad_x)
        cy1 = max(0,     my1 - pad_y_top)
        cx2 = min(img_w, mx2 + pad_x)
        cy2 = min(img_h, my2 + pad_y_bot)

        crop = image[cy1:cy2, cx1:cx2]
        crop_w = cx2-cx1; crop_h = cy2-cy1
        plate_text = ""

        if crop.size > 0:
            plate_res = plate_model(crop, verbose=False)[0]
            cands = []
            for pb in plate_res.boxes:
                cf = float(pb.conf)
                if cf < 0.40: continue
                px1,py1,px2,py2 = map(int, pb.xyxy[0])
                pw=px2-px1; ph=py2-py1
                if ph==0 or (pw/ph)<1.0 or pw>crop_w*0.95: continue
                if py1 < crop_h*0.25: continue
                cands.append((px1,py1,px2,py2,cf))

            if cands:
                # Take single best candidate only
                px1,py1,px2,py2,cf = max(cands, key=lambda c: c[4])
                plate_crop = crop[py1:py2, px1:px2]
                plate_text = read_plate(plate_crop)
                print(f"  [Plate] conf={cf:.2f}  text='{plate_text}'")

                # Draw on output
                px1+=cx1; px2+=cx1; py1+=cy1; py2+=cy1
                cv2.rectangle(output_img,(px1,py1),(px2,py2),(0,255,255),2)
                cv2.putText(output_img, plate_text if plate_text else "PLATE",
                            (px1,py1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8,(0,255,255),2)
            else:
                print("  [Plate] Not detected")
    elif violations:
        print("  [Plate] Not detected")

    cv2.imwrite(os.path.join(output_folder, image_name), output_img)
    print(f"  Saved → results/{image_name}\n")

print("✅ Done.")