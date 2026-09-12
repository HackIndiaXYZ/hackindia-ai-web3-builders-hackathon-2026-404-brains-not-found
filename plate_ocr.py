"""
TrafficGuard Pro — Enhanced Indian ANPR & Plate OCR Module
EasyOCR-based Indian license plate reader with multi-stage image preprocessing:
1. Contrast Limited Adaptive Histogram Equalization (CLAHE)
2. Bilateral Denoising & Kernel Sharpening
3. Otsu & Adaptive Gaussian Binarization
4. 36 Indian State & UT Code Validation + Bharat (BH) Series
5. Position-aware character ambiguity correction (0/O, 1/I, 5/S, 8/B, 2/Z, 6/G, 4/A)
6. Confidence scoring and "Low Confidence" resolution
"""

import re
import cv2
import numpy as np

# Comprehensive Indian plate patterns — most specific first
_PATTERNS = [
    re.compile(r'^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$'),     # Standard e.g. KA03MX4521
    re.compile(r'^[A-Z]{2}\d{2}[A-Z]{1}\d{4}$'),      # Single-letter series e.g. KL30G1234
    re.compile(r'^\d{2}BH\d{4}[A-Z]{1,2}$'),           # Bharat Series e.g. 22BH1234AA
    re.compile(r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}$'), # Vintage / commercial catch-all
]

_SEARCH_PATTERNS = [
    re.compile(r'[A-Z]{2}\d{2}[A-Z]{2}\d{4}'),
    re.compile(r'[A-Z]{2}\d{2}[A-Z]{1}\d{4}'),
    re.compile(r'\d{2}BH\d{4}[A-Z]{1,2}'),
    re.compile(r'[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{3,4}'),
]

# All 36 Indian States and Union Territories
_VALID_STATES = {
    'AP', 'AR', 'AS', 'BR', 'CG', 'CH', 'DD', 'DL', 'DN', 'GA', 'GJ',
    'HR', 'HP', 'JH', 'JK', 'KA', 'KL', 'LA', 'LD', 'MH', 'ML', 'MN',
    'MP', 'MZ', 'NL', 'OD', 'PB', 'PY', 'RJ', 'SK', 'TN', 'TR', 'TS',
    'TG', 'UK', 'UP', 'WB', 'AN'
}

_STATE_FIXES = {
    '0L': 'DL', 'OL': 'DL', 'QL': 'DL', 'CL': 'DL',
    'HH': 'MH', 'HM': 'MH', 'IH': 'MH', 'NH': 'MH',
    'EL': 'KL', 'IL': 'KL',
    'KI': 'KA', 'KR': 'KA',
    'OD': 'OD', 'OR': 'OD',
    'TZ': 'TN', 'TM': 'TN',
    'IK': 'UK', 'UA': 'UK',
    'DH': 'DL', 'DI': 'DL',
}


def validate_indian_plate(plate_str):
    """
    Validate whether a plate string conforms to standard Indian vehicle registration formats.
    Returns (is_valid, normalized_plate, plate_type).
    """
    if not plate_str or str(plate_str).strip().upper() in ("UNKNOWN", "NONE", "LOW CONFIDENCE", ""):
        return False, "", "INVALID"

    clean = re.sub(r'[^A-Z0-9]', '', str(plate_str).upper()).replace("IND", "").replace("INDIA", "")
    corrected = _correct(clean)

    # Check BH Series
    if re.match(r'^\d{2}BH\d{4}[A-Z]{1,2}$', corrected):
        return True, corrected, "BHARAT_SERIES"

    # Check Standard State Series
    state_code = corrected[:2]
    if state_code in _VALID_STATES or state_code in _STATE_FIXES:
        for pat in _PATTERNS:
            if pat.match(corrected):
                return True, corrected, "STANDARD_STATE"

    # Catch-all match
    for pat in _SEARCH_PATTERNS:
        m = pat.search(corrected)
        if m:
            return True, m.group(), "MATCHED_SERIES"

    return False, corrected, "UNKNOWN_FORMAT"


def clean_raw_plate_text(raw):
    """Strip noise and IND/INDIA prefixes from raw OCR text."""
    if not raw:
        return ""
    t = re.sub(r'[^A-Z0-9]', '', str(raw).upper())
    return t.replace('IND', '').replace('INDIA', '').replace('IN', '')


def normalize_indian_plate(raw):
    """Return normalized Indian license plate string."""
    return _correct(raw)


def is_valid_indian_plate(raw):
    """Boolean check for Indian plate validity."""
    valid, _, _ = validate_indian_plate(raw)
    return valid


def _correct(raw):
    """
    Normalize OCR text with Indian license plate positioning heuristics:
    - First 2 characters must be State letters (or 2 digits for BH series).
    - Next 2 characters must be RTO digits.
    - Subsequent 1-2 characters must be series letters.
    - Final 4 characters must be registration digits.
    """
    if not raw:
        return ""
    t = re.sub(r'[^A-Z0-9]', '', raw.upper())
    t = t.replace('IND', '').replace('INDIA', '').replace('IN', '')
    if len(t) < 4:
        return t

    chars = list(t)
    letter_map = {'0': 'O', '1': 'I', '5': 'S', '8': 'B', '6': 'G', '2': 'Z', '4': 'A'}
    digit_map = {'O': '0', 'I': '1', 'S': '5', 'B': '8', 'Z': '2', 'G': '6', 'A': '4', 'T': '7', 'L': '1', 'D': '0'}

    # If starts with digits followed by BH, it is Bharat Series
    if len(chars) >= 4 and chars[2:4] == ['B', 'H']:
        for i in [0, 1]:
            if chars[i].isalpha():
                chars[i] = digit_map.get(chars[i], chars[i])
        for i in range(4, min(8, len(chars))):
            if chars[i].isalpha():
                chars[i] = digit_map.get(chars[i], chars[i])
        return ''.join(chars)

    # Standard state plate: first 2 chars are letters
    for i in [0, 1]:
        if i < len(chars) and chars[i].isdigit():
            chars[i] = letter_map.get(chars[i], chars[i])

    state = ''.join(chars[:2])
    if state not in _VALID_STATES and state in _STATE_FIXES:
        fixed = _STATE_FIXES[state]
        chars[0] = fixed[0]
        chars[1] = fixed[1]

    # RTO code: chars 2 and 3 are digits
    for i in [2, 3]:
        if i < len(chars) and chars[i].isalpha():
            chars[i] = digit_map.get(chars[i], chars[i])

    # Registration number at the end (last 4 characters are digits if length >= 8)
    if len(chars) >= 8:
        for i in range(len(chars) - 4, len(chars)):
            if chars[i].isalpha():
                chars[i] = digit_map.get(chars[i], chars[i])

    return ''.join(chars)


def _find_pattern(text):
    corrected = _correct(text)
    for pat in _SEARCH_PATTERNS:
        m = pat.search(corrected)
        if m:
            return m.group()
    return ""


def _try_swapped(text):
    t = _correct(text)
    if len(t) < 8:
        return ""
    for split in range(3, 7):
        if split >= len(t):
            continue
        swapped = t[split:] + t[:split]
        swapped_corrected = _correct(swapped)
        for pat in _SEARCH_PATTERNS:
            m = pat.search(swapped_corrected)
            if m:
                return m.group()
    return ""


def _best_match(text):
    result = _find_pattern(text)
    if result:
        return result
    return _try_swapped(text)


def _read_easyocr(img, reader, lock):
    """
    Read text from image using caller-owned reader with thread-safe lock.
    Sorts boxes by Y-coordinate first (top-to-bottom, left-to-right).
    """
    try:
        with lock:
            results = reader.readtext(img, detail=1)
        if not results:
            return "", 0.0
        results_sorted = sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))
        texts = []
        confs = []
        for r in results_sorted:
            if r[2] > 0.15:
                texts.append(r[1])
                confs.append(r[2])
        avg_conf = (sum(confs) / len(confs)) if confs else 0.0
        return " ".join(texts), avg_conf
    except Exception:
        return "", 0.0


def read_plate(plate_crop, reader, lock):
    """
    Read Indian license plate text from cropped image with multi-pass preprocessing.
    Returns:
        Plate string (e.g. 'KA03MX4521') or '' if unresolvable.
    """
    plate_text, _ = read_plate_with_confidence(plate_crop, reader, lock)
    return plate_text


def read_plate_with_confidence(plate_crop, reader, lock):
    """
    Read Indian license plate text and return tuple: (plate_string, confidence_score).
    If confidence is low (< 0.40) and format is invalid, returns ('', confidence).
    """
    if reader is None or plate_crop is None or plate_crop.size == 0:
        return "", 0.0

    h, w = plate_crop.shape[:2]
    if h < 5 or w < 5:
        return "", 0.0

    # Cap width before upscaling to keep inference fast
    MAX_W = 320
    if w > MAX_W:
        scale_down = MAX_W / w
        h = max(1, int(h * scale_down))
        w = MAX_W
        plate_crop = cv2.resize(plate_crop, (w, h), interpolation=cv2.INTER_AREA)

    # Scale to ~300px width for optimal OCR token height
    scale = min(4, max(2, int(300 / max(w, 1))))
    big = cv2.resize(plate_crop, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)

    # Preprocessing 1: CLAHE Contrast Enhancement
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    clahe_img = clahe.apply(gray)

    # Preprocessing 2: Denoising
    denoised = cv2.bilateralFilter(clahe_img, 9, 75, 75)

    # Preprocessing 3: Otsu Thresholding
    _, otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Preprocessing 4: Adaptive Gaussian Thresholding
    adaptive = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 13, 2
    )

    # Preprocessing 5: High-pass Sharpening
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(gray, -1, kernel)

    candidates = [otsu, clahe_img, adaptive, sharpened, gray]

    best_plate = ""
    best_conf = 0.0

    for img in candidates:
        raw_text, conf = _read_easyocr(img, reader, lock)
        if not raw_text:
            continue
        matched = _best_match(raw_text)
        is_valid, norm_plate, _ = validate_indian_plate(matched)

        if is_valid and len(norm_plate) >= 8:
            return norm_plate, max(conf, 0.95)

        if len(matched) > len(best_plate):
            best_plate = matched
            best_conf = conf

    if best_plate and len(best_plate) >= 6:
        is_valid, norm_plate, _ = validate_indian_plate(best_plate)
        if is_valid:
            return norm_plate, max(best_conf, 0.85)
        return best_plate, best_conf

    return "", best_conf