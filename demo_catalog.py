"""Metadata and status helpers for the seven-file hackathon demo library."""

import os


NEW_DEMOS = {
    "Driving without helmet...!! How it looks vs How it feels..!! #bike #helmet #shorts #youtubeshorts.mp4": {
        "label": "Demo Video - No Helmet Detection",
        "description": "Primary flow: motorcycle video to helmet evidence, ANPR, review, and challan.",
        "category": "NEW DEMO",
    },
    "City Sound  Mega City  Traffic Horns  People's Ambiance  MG Road Kolkata West Bengal.mp4": {
        "label": "Demo Video - Traffic Intelligence",
        "description": "Traffic scene input for vehicle density, tracking, trends, and safety intelligence.",
        "category": "NEW DEMO",
    },
}

EXISTING_LABELS = {
    "No_Helmet_Violation.mp4": "No Helmet Detection",
    "Triple_Riding_Violation.mp4": "Triple Riding Detection",
    "Wrong_Way_Violation.mp4": "Wrong Way Detection",
    "Combined_Violation.mp4": "Combined Violation Detection",
    "Combined_Violation_2.mp4": "Combined Enforcement Detection",
}


def build_demo_catalog(video_folder, conn=None):
    """Return only files present on disk, with observed rather than fabricated status."""
    names = sorted(name for name in os.listdir(video_folder) if name.lower().endswith((".mp4", ".avi", ".mov", ".mkv")))
    observed = {}
    if conn is not None:
        rows = conn.execute("SELECT video, violation, COUNT(*) FROM violations GROUP BY video, violation").fetchall()
        for video, violation, count in rows:
            observed.setdefault(video, []).append({"violation": violation, "count": count})
    catalog = []
    for name in names:
        is_new = name in NEW_DEMOS
        details = NEW_DEMOS.get(name, {})
        events = observed.get(name, [])
        catalog.append({
            "video_name": name,
            "display_label": details.get("label", EXISTING_LABELS.get(name, name)),
            "description": details.get("description", "Existing TrafficGuard Pro demonstration input."),
            "category": details.get("category", "EXISTING DEMO"),
            "duration": None,
            "processing_status": "READY",
            "detected_violations": events or [],
            "vehicles_detected": None,
            "near_miss_events": 0,
            "risk_level": "NOT ASSESSED",
            "is_new": is_new,
            "available": os.path.isfile(os.path.join(video_folder, name)),
        })
    return catalog
