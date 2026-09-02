"""
VehicleTrack — Unit Tests
Run with: python -m pytest tests/ -v
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from violation_engine import ViolationEngine
from challan import calculate_fine


# ══════════════════════════════════════════════════════════
# ViolationEngine — No Helmet
# ══════════════════════════════════════════════════════════

class TestNoHelmet:

    def setup_method(self):
        self.engine = ViolationEngine()

    def test_flags_when_nohelmet_outnumbers_helmet(self):
        assert self.engine.check_no_helmet(
            traffic_objects=["motorcycle"],
            helmet_objects=["nohelmet", "nohelmet"]
        ) is True

    def test_clears_when_helmet_outnumbers_nohelmet(self):
        assert self.engine.check_no_helmet(
            traffic_objects=["motorcycle"],
            helmet_objects=["helmet", "helmet", "nohelmet"]
        ) is False

    def test_no_flag_without_motorcycle(self):
        assert self.engine.check_no_helmet(
            traffic_objects=["car", "bus"],
            helmet_objects=["nohelmet"]
        ) is False

    def test_no_flag_when_no_helmet_objects(self):
        assert self.engine.check_no_helmet(
            traffic_objects=["motorcycle"],
            helmet_objects=[]
        ) is False

    def test_motorcyclist_label_is_neutral(self):
        # "motorcyclist" = unclear helmet status (rear angle, occluded)
        # It is NEUTRAL — does not count as helmeted or unhelmetted.
        # So 1 nohelmet + 1 motorcyclist → nohelmet(1) > confirmed_helmet(0) → flag
        assert self.engine.check_no_helmet(
            traffic_objects=["motorcycle"],
            helmet_objects=["motorcyclist", "nohelmet"]
        ) is True   # motorcyclist is neutral; nohelmet outnumbers confirmed helmets

    def test_confirmed_helmet_suppresses_flag(self):
        # Only explicit "helmet" label suppresses the flag
        assert self.engine.check_no_helmet(
            traffic_objects=["motorcycle"],
            helmet_objects=["helmet", "nohelmet"]
        ) is False   # 1 confirmed helmet vs 1 nohelmet → equal, not outnumbered


# ══════════════════════════════════════════════════════════
# ViolationEngine — Triple Riding
# ══════════════════════════════════════════════════════════

class TestTripleRiding:

    def setup_method(self):
        self.engine = ViolationEngine()

    def test_flags_three_persons(self):
        assert self.engine.check_triple_riding(
            ["motorcycle", "person", "person", "person"]
        ) is True

    def test_flags_more_than_three(self):
        assert self.engine.check_triple_riding(
            ["motorcycle", "person", "person", "person", "person"]
        ) is True

    def test_no_flag_with_two_persons(self):
        assert self.engine.check_triple_riding(
            ["motorcycle", "person", "person"]
        ) is False

    def test_no_flag_without_motorcycle(self):
        assert self.engine.check_triple_riding(
            ["car", "person", "person", "person"]
        ) is False

    def test_no_flag_empty(self):
        assert self.engine.check_triple_riding([]) is False


# ══════════════════════════════════════════════════════════
# ViolationEngine — Wrong Way
# ══════════════════════════════════════════════════════════

class TestWrongWay:

    def setup_method(self):
        self.engine = ViolationEngine()

    def _make_box(self, track_id, cx, cy):
        return {"label": "motorcycle", "id": track_id, "cx": cx, "cy": cy}

    def test_no_flag_initially(self):
        assert self.engine.check_wrong_way() is False

    def test_flags_fast_vertical_movement_decreasing(self):
        """Dashcam: wrong-way rider moves toward camera (cy decreasing fast)."""
        frame_width = 1280
        cx = 640
        for i in range(15):
            cy = 400 - (i * 12)   # -12px/frame > threshold of 8
            self.engine._update_wrong_way(
                [self._make_box(track_id=1, cx=cx, cy=cy)], frame_width
            )
        assert self.engine.check_wrong_way() is True

    def test_flags_fast_vertical_movement_increasing(self):
        """Static camera: wrong-way rider moves toward camera (cy increasing fast)."""
        frame_width = 1280
        cx = 640
        for i in range(15):
            cy = 100 + (i * 12)   # +12px/frame > threshold of 8
            self.engine._update_wrong_way(
                [self._make_box(track_id=5, cx=cx, cy=cy)], frame_width
            )
        assert self.engine.check_wrong_way() is True

    def test_no_flag_for_slow_movement(self):
        """Slow movement (normal traffic) should not trigger wrong-way."""
        frame_width = 1280
        cx = 640
        for i in range(15):
            cy = 100 + (i * 4)   # 4px/frame < threshold of 8
            self.engine._update_wrong_way(
                [self._make_box(track_id=2, cx=cx, cy=cy)], frame_width
            )
        assert self.engine.check_wrong_way() is False

    def test_ignores_edge_zone_motorcycles(self):
        """Bikes near frame edges are excluded to avoid entry/exit false positives."""
        frame_width = 1280
        cx = 10   # left edge zone (<15% = <192px)

        for i in range(20):
            cy = 400 - (i * 15)
            self.engine._update_wrong_way(
                [self._make_box(track_id=3, cx=cx, cy=cy)],
                frame_width
            )

        assert self.engine.check_wrong_way() is False

    def test_reset_clears_state(self):
        frame_width = 1280
        for i in range(20):
            self.engine._update_wrong_way(
                [self._make_box(1, 640, 400 - i * 15)],
                frame_width
            )
        assert self.engine.check_wrong_way() is True
        self.engine.reset()
        assert self.engine.check_wrong_way() is False


# ══════════════════════════════════════════════════════════
# Fine Calculation
# ══════════════════════════════════════════════════════════

class TestFineCalculation:

    def test_first_offence_no_multiplier(self):
        base, mult, total = calculate_fine(["NO HELMET"], offence_count=1)
        assert base  == 1000
        assert mult  == 1.0
        assert total == 1000

    def test_second_offence_doubles_fine(self):
        _, _, first  = calculate_fine(["NO HELMET"], offence_count=1)
        _, _, second = calculate_fine(["NO HELMET"], offence_count=2)
        assert second == first * 2

    def test_third_offence_triples_fine(self):
        _, _, first = calculate_fine(["NO HELMET"], offence_count=1)
        _, _, third = calculate_fine(["NO HELMET"], offence_count=3)
        assert third == first * 3

    def test_multiple_violations_sum(self):
        base, _, _ = calculate_fine(["NO HELMET", "TRIPLE RIDING"], offence_count=1)
        assert base == 2000   # 1000 + 1000

    def test_wrong_way_higher_base(self):
        base, _, _ = calculate_fine(["WRONG WAY"], offence_count=1)
        assert base == 5000

    def test_unknown_violation_fallback_fine(self):
        base, _, _ = calculate_fine(["UNKNOWN_VIOLATION"], offence_count=1)
        assert base == 500   # fallback fine for unrecognised types


# ══════════════════════════════════════════════════════════
# Plate OCR — Regex
# ══════════════════════════════════════════════════════════

class TestPlateRegex:

    PLATE_PATTERN = re.compile(r'[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}')

    def test_valid_standard_plate(self):
        assert self.PLATE_PATTERN.search("KA01AB1234")

    def test_valid_single_letter_series(self):
        assert self.PLATE_PATTERN.search("MH02A5678")

    def test_valid_dl_plate(self):
        assert self.PLATE_PATTERN.search("DL09WR3456")

    def test_rejects_too_short(self):
        assert not self.PLATE_PATTERN.search("KA011")

    def test_rejects_all_letters(self):
        assert not self.PLATE_PATTERN.search("ABCDEFGH")

    def test_rejects_random_string(self):
        assert not self.PLATE_PATTERN.search("INVALID123")

    def test_extracts_from_noisy_string(self):
        # OCR often returns surrounding noise — regex must still find the plate
        noisy = "XYZKA01AB1234ABC"
        m = self.PLATE_PATTERN.search(noisy)
        assert m and m.group() == "KA01AB1234"