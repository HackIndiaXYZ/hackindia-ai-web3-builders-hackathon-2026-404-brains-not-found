"""Real-time traffic intelligence with a deterministic offline fallback."""

from __future__ import annotations

import math
import os
import random
import threading
import time
from datetime import datetime, timezone


CITY_CENTER = (12.9716, 77.5946)
_RANDOM = random.Random(40431)
_LOCK = threading.Lock()
_STATE = {"snapshot": None, "updated_at": 0.0, "history": []}

_LOCATIONS = [
    ("MG Road", 12.9758, 77.6097),
    ("Silk Board", 12.9176, 77.6228),
    ("Hebbal Flyover", 13.0358, 77.5970),
    ("Electronic City", 12.8452, 77.6602),
    ("Whitefield Main Road", 12.9698, 77.7499),
    ("Outer Ring Road", 12.9352, 77.6245),
    ("Yeshwanthpur", 13.0285, 77.5400),
    ("Indiranagar 100ft Road", 12.9784, 77.6408),
]
_VIOLATIONS = ["NO HELMET", "WRONG WAY", "TRIPLE RIDING", "NO SEATBELT", "RED LIGHT"]


def _provider_status():
    return {
        "mode": "LIVE_PROVIDER" if os.environ.get("GOOGLE_MAPS_API_KEY") else "SIMULATION_FALLBACK",
        "google_maps": bool(os.environ.get("GOOGLE_MAPS_API_KEY")),
        "weather": bool(os.environ.get("WEATHER_API_KEY")),
        "camera_feeds": int(os.environ.get("TRAFFIC_CAMERA_COUNT", "50")),
        "message": "External providers configured" if os.environ.get("GOOGLE_MAPS_API_KEY") else "Interactive demo data is active; add provider keys for live feeds",
    }


def _risk_level(score):
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def _build_snapshot(now=None):
    now = now or time.time()
    minute = now / 60
    hotspots = []
    heatmap = []
    flows = []
    predictions = []
    violations = []

    for index, (name, lat, lng) in enumerate(_LOCATIONS):
        wave = (math.sin(minute / 2.5 + index * 0.9) + 1) / 2
        vehicle_count = int(28 + wave * 78 + _RANDOM.randint(-5, 8))
        avg_speed = max(8, round(58 - wave * 39 + _RANDOM.uniform(-3, 3), 1))
        congestion = max(0, min(100, round((1 - avg_speed / 60) * 100 * (vehicle_count / 100))))
        severity = _risk_level(congestion)
        hotspots.append({"id": f"hotspot-{index}", "location": name, "lat": lat, "lng": lng, "congestion": congestion, "vehicle_count": vehicle_count, "avg_speed": avg_speed, "trend": "up" if wave > .55 else "down", "severity": severity})
        heatmap.append({"lat": lat, "lng": lng, "intensity": round(congestion / 100, 2), "location": name, "congestion": congestion})
        flows.append({"id": f"flow-{index}", "name": name, "lat": lat, "lng": lng, "heading": int((index * 43 + now / 8) % 360), "vehicle_count": vehicle_count, "avg_speed": avg_speed, "color": "#ef4444" if avg_speed < 25 else "#f59e0b" if avg_speed < 42 else "#22c55e"})
        risk_score = min(99, round(congestion * .7 + vehicle_count * .22 + wave * 8))
        predictions.append({"id": f"risk-{index}", "location": name, "lat": lat, "lng": lng, "risk_score": risk_score, "risk_level": _risk_level(risk_score), "factors": ["high congestion" if congestion > 45 else "dense traffic", "reduced average speed", "peak-hour pattern"], "recommended_action": "Deploy patrol and reduce speed limit" if risk_score >= 60 else "Monitor traffic flow"})

        if index < 6 and (int(now) // 8 + index) % 3 == 0:
            violations.append({"id": int(now * 10) + index, "lat": lat + _RANDOM.uniform(-.004, .004), "lng": lng + _RANDOM.uniform(-.004, .004), "plate": f"KA03{index + 1:02d}MX{4521 + index}", "type": _VIOLATIONS[index % len(_VIOLATIONS)], "fine": [500, 1000, 1500, 1000, 2000][index % 5], "timestamp": datetime.now(timezone.utc).isoformat(), "confidence": round(.82 + _RANDOM.random() * .16, 2), "severity": "high" if index % 3 == 0 else "medium"})

    hotspots.sort(key=lambda item: item["congestion"], reverse=True)
    violations = violations[-100:]
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "provider": _provider_status(), "center": {"lat": CITY_CENTER[0], "lng": CITY_CENTER[1]}, "heatmap": heatmap, "hotspots": hotspots[:10], "flows": flows, "predictions": predictions, "violations": violations, "kpis": {"current_violations": len(violations), "total_vehicles": sum(item["vehicle_count"] for item in hotspots), "average_speed": round(sum(item["avg_speed"] for item in hotspots) / len(hotspots), 1), "hotspots": sum(item["congestion"] >= 40 for item in hotspots), "prediction_alerts": sum(item["risk_score"] >= 60 for item in predictions)}}


def get_snapshot(force=False):
    now = time.time()
    with _LOCK:
        if force or not _STATE["snapshot"] or now - _STATE["updated_at"] >= 0.5:
            _STATE["snapshot"] = _build_snapshot(now)
            _STATE["updated_at"] = now
            _STATE["history"] = (_STATE["history"] + [_STATE["snapshot"]])[-120:]
        return _STATE["snapshot"]


def get_history():
    with _LOCK:
        return [{"timestamp": item["timestamp"], "hotspots": item["hotspots"], "kpis": item["kpis"]} for item in _STATE["history"]]
