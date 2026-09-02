"""
VehicleTrack — Violation Engine
Encapsulates all violation detection logic in one testable class.
"""

from collections import defaultdict, deque


class ViolationEngine:
    WRONG_WAY_FRAMES    = 5
    WRONG_WAY_THRESHOLD = 5
    EDGE_ZONE           = 0.15

    def __init__(self):
        self.track_cy_history   = defaultdict(lambda: deque(maxlen=self.WRONG_WAY_FRAMES + 2))
        self.track_area_history = defaultdict(lambda: deque(maxlen=self.WRONG_WAY_FRAMES + 2))
        self.wrong_way_ids      = set()

    # ── PUBLIC API ────────────────────────────────────────

    def check(self, traffic_objects, helmet_objects, traffic_boxes, frame_width, frame_height=0):
        self._update_wrong_way(traffic_boxes, frame_width)
        violations = []
        if self.check_no_helmet(traffic_objects, helmet_objects):
            violations.append("NO HELMET")
        person_boxes = [(b["x1"],b["y1"],b["x2"],b["y2"])
                        for b in traffic_boxes if b.get("label")=="person"]
        motorcycle_boxes = [(b["x1"],b["y1"],b["x2"],b["y2"])
                            for b in traffic_boxes if b.get("label")=="motorcycle"]
        if self.check_triple_riding(traffic_objects, person_boxes,
                                     motorcycle_boxes, frame_width, frame_height):
            violations.append("TRIPLE RIDING")
        if self.check_wrong_way():
            violations.append("WRONG WAY")
        return violations

    def check_no_helmet(self, traffic_objects, helmet_objects):
        if "motorcycle" not in traffic_objects:
            return False
        nohelmet_count   = helmet_objects.count("nohelmet")
        confirmed_helmet = helmet_objects.count("helmet")
        return nohelmet_count > 0 and nohelmet_count > confirmed_helmet

    def check_triple_riding(self, traffic_objects, person_boxes=None,
                             motorcycle_boxes=None, frame_w=0, frame_h=0):
        if "motorcycle" not in traffic_objects:
            return False
        if not person_boxes or not motorcycle_boxes:
            return traffic_objects.count("person") >= 3
        for (mx1,my1,mx2,my2) in motorcycle_boxes:
            mw=mx2-mx1; mh=my2-my1
            ex1 = max(0, mx1 - int(mw*0.10))
            ey1 = max(0, my1 - int(mh*0.80))
            ex2 = min(frame_w if frame_w else mx2+mw, mx2 + int(mw*0.10))
            ey2 = min(frame_h if frame_h else my2+mh, my2 + int(mh*0.05))
            count = sum(1 for (px1,py1,px2,py2) in person_boxes
                        if self._overlap((px1,py1,px2,py2),(ex1,ey1,ex2,ey2)) > 0.30)
            if count >= 3: return True
        return False

    @staticmethod
    def _overlap(boxA, boxB):
        ax1,ay1,ax2,ay2=boxA; bx1,by1,bx2,by2=boxB
        ix1,iy1=max(ax1,bx1),max(ay1,by1)
        ix2,iy2=min(ax2,bx2),min(ay2,by2)
        if ix2<=ix1 or iy2<=iy1: return 0.0
        return ((ix2-ix1)*(iy2-iy1))/max((ax2-ax1)*(ay2-ay1),1)

    def check_wrong_way(self):
        return len(self.wrong_way_ids) > 0

    def reset(self):
        self.track_cy_history.clear()
        self.track_area_history.clear()
        self.wrong_way_ids.clear()

    # ── INTERNAL ──────────────────────────────────────────

    def _update_wrong_way(self, traffic_boxes, frame_width):
        """
        Dual-mode wrong-way detection:
        Mode A: cy decreasing fast — dashcam, wrong-way bike approaches from ahead
        Mode B: area growing fast — static/front-facing camera, head-on approach
        """
        for box in traffic_boxes:
            if box["label"] != "motorcycle" or box["id"] is None:
                continue

            track_id = box["id"]
            cx       = box["cx"]
            cy       = box["cy"]
            if "x2" in box and "x1" in box and "y2" in box and "y1" in box:
                area = (box["x2"] - box["x1"]) * (box["y2"] - box["y1"])
            else:
                area = 0

            if cx < frame_width * self.EDGE_ZONE or cx > frame_width * (1 - self.EDGE_ZONE):
                self.wrong_way_ids.discard(track_id)
                continue

            cy_hist   = self.track_cy_history[track_id]
            area_hist = self.track_area_history[track_id]
            cy_hist.append(cy)
            area_hist.append(area)

            if len(cy_hist) < self.WRONG_WAY_FRAMES:
                continue

            dy = (cy_hist[-1] - cy_hist[-self.WRONG_WAY_FRAMES]) / self.WRONG_WAY_FRAMES

            # Mode A: fast vertical movement (dashcam or static camera)
            mode_a = abs(dy) > self.WRONG_WAY_THRESHOLD

            # Mode B: area growing fast (head-on approach, static camera)
            initial_area = area_hist[-self.WRONG_WAY_FRAMES]
            if initial_area > 0:
                area_growth_rate = (area_hist[-1] - initial_area) / (initial_area * self.WRONG_WAY_FRAMES)
                mode_b = area_growth_rate > 0.25
            else:
                area_growth_rate = 0.0
                mode_b = False

            if mode_a or mode_b:
                self.wrong_way_ids.add(track_id)
            else:
                self.wrong_way_ids.discard(track_id)


def log_to_trajectory(plate_text, camera_id, timestamp):
    import sqlite3
    conn = sqlite3.connect('violations.db')
    c = conn.cursor()
    
    camera = c.execute('SELECT latitude, longitude FROM cameras WHERE id = ?', 
                       (camera_id,)).fetchone()
    
    if camera:
        lat, lng = camera
        c.execute('''INSERT INTO trajectory_points (trajectory_id, camera_id, plate_text, latitude, longitude, timestamp) VALUES 
            (NULL, ?, ?, ?, ?, ?)''',
            (camera_id, plate_text, lat, lng, timestamp))
        conn.commit()
    else:
        c.execute('''INSERT INTO trajectory_points (trajectory_id, camera_id, plate_text, latitude, longitude, timestamp) VALUES 
            (NULL, ?, ?, NULL, NULL, ?)''',
            (camera_id, plate_text, timestamp))
        conn.commit()
    
    conn.close()