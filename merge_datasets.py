from ultralytics import YOLO
from fast_plate_ocr import LicensePlateRecognizer as ONNXPlateRecognizer
import os
import cv2

# ---------------- LOAD MODELS ----------------
traffic_model = YOLO("yolov8n.pt")
helmet_model  = YOLO("best.pt")
plate_model   = YOLO("plate.pt")

# fast-plate-ocr — OCR only, no detection
# Uses the same model as fast-alpr internally
ocr_model = ONNXPlateRecognizer("global-plates-mobile-vit-v2-model")

image_folder  = "images"
output_folder = "results"

os.makedirs(output_folder, exist_ok=True)

print("Starting detection...\n")


for image_name in os.listdir(image_folder):

    if not image_name.lower().endswith((".jpg", ".png", ".jpeg")):
        continue

    image_path = os.path.join(image_folder, image_name)
    print("Processing:", image_name)

    image = cv2.imread(image_path)

    if image is None:
        print("  Error loading image\n")
        continue

    img_h, img_w = image.shape[:2]

    # ---------- TRAFFIC DETECTION ----------
    traffic_results = traffic_model(image, verbose=False)[0]

    traffic_objects  = []
    motorcycle_boxes = []
    for box in traffic_results.boxes:
        label = traffic_model.names[int(box.cls)]
        traffic_objects.append(label)
        if label == "motorcycle" and float(box.conf) >= 0.4:
            motorcycle_boxes.append(list(map(int, box.xyxy[0])))

    print("Traffic:", traffic_objects)

    # ---------- HELMET DETECTION ----------
    helmet_results = helmet_model(image, verbose=False)[0]

    helmet_objects = []
    for box in helmet_results.boxes:
        label = helmet_model.names[int(box.cls)]
        helmet_objects.append(label)

    print("Helmet:", helmet_objects)

    # ---------- VIOLATION LOGIC ----------
    violations   = []
    person_count = traffic_objects.count("person")

    nohelmet_count = helmet_objects.count("nohelmet")
    helmet_count   = helmet_objects.count("helmet") + helmet_objects.count("motorcyclist")

    if "motorcycle" in traffic_objects and nohelmet_count > 0 and nohelmet_count > helmet_count:
        violations.append("NO HELMET")

    if "motorcycle" in traffic_objects and person_count >= 3:
        violations.append("TRIPLE RIDING")

    for v in violations:
        print("VIOLATION:", v)

    # ---------- DRAW RESULTS ----------
    output_img = traffic_results.plot()

    for box in helmet_results.boxes:
        label = helmet_model.names[int(box.cls)]
        if label != "licenseplate":
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(output_img, (x1, y1), (x2, y2), (255, 0, 0), 2)

    y_offset = 60
    for v in violations:
        cv2.putText(output_img, v, (30, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        y_offset += 50

    # =========================================================
    # PLATE DETECTION (plate.pt) + RECOGNITION (fast-plate-ocr)
    # plate.pt finds WHERE the plate is
    # fast-plate-ocr reads WHAT it says
    # =========================================================
    if violations:

        plate_drawn = False

        for (mx1, my1, mx2, my2) in motorcycle_boxes:

            pad = 20
            cx1 = max(0, mx1 - pad)
            cy1 = max(0, my1 - pad)
            cx2 = min(img_w, mx2 + pad)
            cy2 = min(img_h, my2 + pad)

            crop = image[cy1:cy2, cx1:cx2]
            if crop.size == 0:
                continue

            crop_w = cx2 - cx1
            plate_results = plate_model(crop, verbose=False)[0]

            candidates = []
            for pbox in plate_results.boxes:
                conf = float(pbox.conf)
                if conf < 0.5:
                    continue
                px1, py1, px2, py2 = map(int, pbox.xyxy[0])
                pw = px2 - px1
                ph = py2 - py1
                if ph == 0:
                    continue
                if (pw / ph) < 1.0:
                    continue
                if pw > crop_w * 0.8:
                    continue
                candidates.append((px1, py1, px2, py2, conf))

            if not candidates:
                continue

            # Pick lowest detection in crop (real plate is at bottom of bike)
            best = max(candidates, key=lambda c: c[3])
            px1, py1, px2, py2, conf = best

            # Crop the plate region
            plate_crop = crop[py1:py2, px1:px2]
            plate_text = ""

            if plate_crop.size != 0:
                try:
                    gray_crop = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
                    predictions = ocr_model.run(gray_crop)
                    if predictions:
                        plate_text = predictions[0].upper().replace(" ", "")
                except Exception as e:
                    print(f"  OCR error: {e}")

            print(f"  [plate.pt] conf={conf:.2f}  OCR='{plate_text}'")

            # Offset back to full image coords
            px1 += cx1;  px2 += cx1
            py1 += cy1;  py2 += cy1

            cv2.rectangle(output_img, (px1, py1), (px2, py2), (0, 255, 255), 2)
            display = plate_text if plate_text else "PLATE"
            cv2.putText(output_img, display, (px1, py1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            plate_drawn = True

        # --- best.pt licenseplate fallback ---
        if not plate_drawn:
            for box in helmet_results.boxes:
                label = helmet_model.names[int(box.cls)]
                if label != "licenseplate":
                    continue
                conf = float(box.conf)
                if conf < 0.5:
                    continue
                bx1, by1, bx2, by2 = map(int, box.xyxy[0])
                if (by1 + by2) / 2 < img_h * 0.35:
                    continue

                plate_crop = image[by1:by2, bx1:bx2]
                plate_text = ""

                if plate_crop.size != 0:
                    try:
                        gray_crop = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
                        predictions = ocr_model.run(gray_crop)
                        if predictions:
                            plate_text = predictions[0].upper().replace(" ", "")
                    except Exception as e:
                        print(f"  OCR error: {e}")

                print(f"  [best.pt] conf={conf:.2f}  OCR='{plate_text}'")

                cv2.rectangle(output_img, (bx1, by1), (bx2, by2), (0, 255, 255), 2)
                display = plate_text if plate_text else "PLATE"
                cv2.putText(output_img, display, (bx1, by1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                plate_drawn = True

        if not plate_drawn:
            print("  No plate detected")

    output_path = os.path.join(output_folder, image_name)
    cv2.imwrite(output_path, output_img)
    print()

print("Detection complete. Results saved in 'results'.")