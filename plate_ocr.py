"""
VehicleTrack — Plate OCR Module
EasyOCR-based Indian license plate reader.

Fixes applied in this version:
  1. Y-then-X sort — fixes two-line plates read bottom-to-top
  2. State code correction table — HH→MH, EL→KL, etc.
  3. Position-aware digit/letter corrections
  4. "Try swapped halves" — fallback for when two-line reversal slips through

Design note: reader and lock are passed in as parameters (dependency injection).
This means the caller owns the EasyOCR instance — no module-level globals,
no second instance created on import, no thread-safety surprises.
"""

import re
import cv2
import numpy as np

# Plate patterns — most specific first
_PATTERNS = [
    re.compile(r'[A-Z]{2}\d{2}[A-Z]{2}\d{4}'),    # KA03XY1234
    re.compile(r'[A-Z]{2}\d{2}[A-Z]{1}\d{4}'),     # KL30G1234
    re.compile(r'[A-Z]{2}\d{2}[A-Z]{1,3}\d{3,4}'), # catch-all
]

_VALID_STATES = {
    'AP','AR','AS','BR','CG','CH','DD','DL','DN','GA','GJ',
    'HR','HP','JH','JK','KA','KL','LA','LD','MH','ML','MN',
    'MP','MZ','NL','OD','PB','PY','RJ','SK','TN','TR','TS',
    'TG','UK','UP','WB','AN'
}

_STATE_FIXES = {
    'HH': 'MH', 'HM': 'MH', 'IH': 'MH', 'NH': 'MH',
    'EL': 'KL', 'IL': 'KL',
    'KI': 'KA',
    'OD': 'OD',
    'TZ': 'TN',
    'IK': 'UK',
}


def _correct(raw):
    t = re.sub(r'[^A-Z0-9]', '', raw.upper())
    t = t.replace('IND', '').replace('INDIA', '')
    if len(t) < 4:
        return t
    chars = list(t)
    letter_map = {'0':'O','1':'I','5':'S','8':'B','6':'G','2':'Z'}
    for i in [0, 1]:
        if i < len(chars) and chars[i].isdigit():
            chars[i] = letter_map.get(chars[i], chars[i])
    state = ''.join(chars[:2])
    if state not in _VALID_STATES and state in _STATE_FIXES:
        fixed = _STATE_FIXES[state]
        chars[0] = fixed[0]; chars[1] = fixed[1]
    digit_map = {'O':'0','I':'1','S':'5','B':'8','Z':'2','G':'6','A':'4','T':'7','L':'1'}
    for i in [2, 3]:
        if i < len(chars) and chars[i].isalpha():
            chars[i] = digit_map.get(chars[i], chars[i])
    return ''.join(chars)


def _find_pattern(text):
    corrected = _correct(text)
    for pat in _PATTERNS:
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
        for pat in _PATTERNS:
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
    Read text from img using the provided reader, holding lock during inference.
    Sorts results by Y coordinate first (top line before bottom line).
    """
    try:
        with lock:
            results = reader.readtext(img, detail=1)
        if not results:
            return ""
        results_sorted = sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))
        texts = [r[1] for r in results_sorted if r[2] > 0.1]
        return " ".join(texts)
    except Exception:
        return ""


def read_plate(plate_crop, reader, lock):
    """
    Read Indian license plate text from cropped image.

    Args:
        plate_crop : np.ndarray  BGR crop of the plate region
        reader     : easyocr.Reader  caller-owned instance (not created here)
        lock       : threading.Lock  protects reader during inference

    Returns:
        Plate string like 'MH04AB1234', or '' if nothing valid found.
    """
    if plate_crop is None or plate_crop.size == 0:
        return ""
    h, w = plate_crop.shape[:2]
    if h < 5 or w < 5:
        return ""

    # Cap width before upscaling — huge crops (e.g. whole motorcycle region)
    # make EasyOCR spend 3-12s per call. Real plate crops are never >300px wide.
    MAX_W = 300
    if w > MAX_W:
        scale_down = MAX_W / w
        h = max(1, int(h * scale_down))
        w = MAX_W
        plate_crop = cv2.resize(plate_crop, (w, h), interpolation=cv2.INTER_AREA)

    # Scale to ~300px wide, cap at 4x
    scale = min(4, max(2, int(300 / max(w, 1))))
    big   = cv2.resize(plate_crop, (w*scale, h*scale), interpolation=cv2.INTER_CUBIC)
    gray  = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)

    _, otsu   = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive  = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
    kernel    = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharpened = cv2.filter2D(gray, -1, kernel)

    best = ""
    for img in [otsu, adaptive, sharpened, gray]:
        raw     = _read_easyocr(img, reader, lock)
        if not raw:
            continue
        matched = _best_match(raw)
        if len(matched) >= 8:
            return matched
        if len(matched) > len(best):
            best = matched

    return best