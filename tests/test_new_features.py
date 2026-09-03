"""
Unit Tests for TrafficGuard Pro Hackathon Upgrades
Tests:
1. Vahan National Database Lookup & Procedural Fallback
2. Enhanced ReportLab PDF Challan & Receipt Generation
3. Saarthi AI Bilingual Chatbot (Hindi + English)
4. Suraksha Safe Driving Compliance Scoring
5. Blockchain Tamper-Proof Audit Ledger & Immutability
6. Officer Management & Leaderboard
7. Notifications Formatting & Multi-Channel Alert Delivery
"""

import os
import sys
import sqlite3
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vahan import lookup_owner, get_vehicle_comparison
from challan import generate_challan, generate_receipt, calculate_fine, get_offence_count
from chatbot import answer_traffic_query
from gamification import calculate_suraksha_score, get_safest_zones_leaderboard
from blockchain_audit import (
    init_blockchain_table, record_challan_on_blockchain,
    verify_challan_block, compute_block_hash
)
from officer_management import init_officers_table, get_officer_leaderboard
from safety_intelligence import (
    init_safety_tables, get_peak_violation_hours,
    get_predictive_recommendations, submit_dispute, get_disputes
)
from notifications import _violator_whatsapp_msg, _violator_sms_msg, process_bot_message


# ── 1. VAHAN TESTS ─────────────────────────────────────────────
class TestVahanDatabase:
    def test_lookup_preseeded_karnataka_plate(self):
        res = lookup_owner("KA03MX4521")
        assert res is not None
        assert res["name"] == "Rajesh Kumar"
        assert "Classic 350" in res["make_model"]
        assert res["state"] == "Karnataka"

    def test_lookup_preseeded_delhi_plate(self):
        res = lookup_owner("DL09WR6392")
        assert res is not None
        assert res["city"] == "Janakpuri, New Delhi"
        assert res["fuel_type"] == "Petrol"

    def test_procedural_fallback_for_custom_plate(self):
        res = lookup_owner("MH02XY9999")
        assert res is not None
        assert res["state"] == "Maharashtra"
        assert len(res["name"]) > 0
        assert "POL-MH" in res["insurance_policy"]

    def test_unknown_or_none_plate(self):
        assert lookup_owner("UNKNOWN") is None
        assert lookup_owner("") is None
        assert lookup_owner(None) is None

    def test_vehicle_comparison_analytics(self):
        comp = get_vehicle_comparison("KA03MX4521")
        assert comp["plate"] == "KA03MX4521"
        assert len(comp["similar_vehicles"]) > 0


# ── 2. SAARTHI AI CHATBOT TESTS ───────────────────────────────
class TestSaarthiChatbot:
    def test_helmet_query_english(self):
        res = answer_traffic_query("What is the fine for not wearing a helmet?", user_lang="en")
        assert "1,000" in res["answer"]
        assert "Section 129" in res["answer"]

    def test_helmet_query_hindi(self):
        res = answer_traffic_query("हेलमेट का कितना चालान कटता है?", user_lang="hi")
        assert "1,000" in res["answer"]
        assert "धारा 129" in res["answer"]

    def test_wrong_way_query(self):
        res = answer_traffic_query("wrong way driving penalty", user_lang="en")
        assert "5,000" in res["answer"]
        assert "Section 184" in res["answer"]

    def test_driving_license_procedure(self):
        res = answer_traffic_query("How to apply for driving license?", user_lang="en")
        assert "sarathi.parivahan.gov.in" in res["answer"]


# ── 3. SURAKSHA SCORE & GAMIFICATION TESTS ────────────────────
class TestSurakshaGamification:
    @pytest.fixture
    def test_db(self, tmp_path):
        db_file = tmp_path / "test_gamification.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("""
            CREATE TABLE violations (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                video TEXT,
                violation TEXT,
                plate TEXT,
                owner_name TEXT,
                fine INTEGER,
                screenshot TEXT,
                challan TEXT,
                paid INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        yield conn
        conn.close()

    def test_clean_record_score(self, test_db):
        score_data = calculate_suraksha_score(test_db, "DL08PQ5678")
        assert score_data["score"] >= 90
        assert score_data["eligible_for_certificate"] is True

    def test_score_deductions_for_unpaid_violations(self, test_db):
        test_db.execute(
            "INSERT INTO violations (violation, plate, fine, paid) VALUES ('NO HELMET', 'KA03MX4521', 1000, 0)"
        )
        test_db.execute(
            "INSERT INTO violations (violation, plate, fine, paid) VALUES ('WRONG WAY', 'KA03MX4521', 5000, 0)"
        )
        test_db.commit()
        score_data = calculate_suraksha_score(test_db, "KA03MX4521")
        assert score_data["score"] < 80
        assert score_data["unpaid_challans"] == 2

    def test_safest_zones_leaderboard(self):
        zones = get_safest_zones_leaderboard()
        assert len(zones) >= 3
        assert zones[0]["rank"] == 1


# ── 4. BLOCKCHAIN AUDIT LEDGER TESTS ───────────────────────────
class TestBlockchainAudit:
    @pytest.fixture
    def test_db(self, tmp_path):
        db_file = tmp_path / "test_blockchain.db"
        conn = sqlite3.connect(str(db_file))
        init_blockchain_table(conn)
        yield conn
        conn.close()

    def test_record_and_verify_block(self, test_db):
        res = record_challan_on_blockchain(
            test_db, violation_id=101, plate="KA03MX4521",
            violation="NO HELMET", fine=1000, evidence_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        assert res["block_height"] == 1
        assert len(res["block_hash"]) == 64

        verify = verify_challan_block(test_db, "RX-000101")
        assert verify["verified"] is True
        assert verify["status"] == "MATHEMATICALLY VERIFIED (TAMPER-PROOF)"

    def test_unrecorded_challan_verification(self, test_db):
        verify = verify_challan_block(test_db, "RX-999999")
        assert verify["verified"] is False


# ── 5. OFFICER MANAGEMENT & LEADERBOARD TESTS ─────────────────
class TestOfficerManagement:
    @pytest.fixture
    def test_db(self, tmp_path):
        db_file = tmp_path / "test_officers.db"
        conn = sqlite3.connect(str(db_file))
        init_officers_table(conn)
        yield conn
        conn.close()

    def test_officer_leaderboard_ranking(self, test_db):
        officers = get_officer_leaderboard(test_db)
        assert len(officers) >= 3
        assert officers[0]["rank"] == 1
        assert officers[0]["is_top"] is True
        assert len(officers[0]["badges"]) > 0


# ── 6. PDF CHALLAN & RECEIPT TESTS ────────────────────────────
class TestPdfGeneration:
    def test_generate_challan_and_receipt(self, tmp_path):
        challan_dir = str(tmp_path / "challans")
        receipt_dir = str(tmp_path / "receipts")
        screenshot_dir = str(tmp_path / "screenshots")
        db_file = str(tmp_path / "violations.db")
        os.makedirs(challan_dir, exist_ok=True)
        os.makedirs(receipt_dir, exist_ok=True)
        os.makedirs(screenshot_dir, exist_ok=True)

        c_file = generate_challan(
            challan_dir, screenshot_dir, violation_id=1,
            timestamp="2026-09-03 10:00:00", video="dashcam.mp4",
            violation_str="NO HELMET", plate="KA03MX4521",
            screenshot_filename=None, db_path=db_file, owner_name="Rajesh Kumar"
        )
        assert os.path.isfile(os.path.join(challan_dir, c_file))
        assert os.path.getsize(os.path.join(challan_dir, c_file)) > 1000

        r_file = generate_receipt(
            receipt_dir, violation_id=1, plate="KA03MX4521",
            violation_str="NO HELMET", amount_paid=1000,
            payer_name="Rajesh Kumar"
        )
        assert os.path.isfile(os.path.join(receipt_dir, r_file))
        assert os.path.getsize(os.path.join(receipt_dir, r_file)) > 1000


# ── 7. NOTIFICATIONS & BOT TESTS ──────────────────────────────
class TestNotifications:
    def test_whatsapp_message_formatting(self):
        msg = _violator_whatsapp_msg("KA03MX4521", "NO HELMET", 1000, "RX-000001", "Rajesh Kumar")
        assert "KA03MX4521" in msg
        assert "Rs. 1,000" in msg
        assert "RX-000001" in msg

    def test_bot_status_query(self):
        res = process_bot_message("STATUS RX-000001")
        assert "reply" in res

    def test_bot_rules_query(self):
        res = process_bot_message("RULES")
        assert "Sec 129" in res["reply"]
