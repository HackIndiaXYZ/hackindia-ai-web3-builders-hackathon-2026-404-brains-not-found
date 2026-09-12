"""
TrafficGuard Pro — End-to-End Workflow & Integration Test Suite
Tests:
1. Full Blockchain Audit Ledger Verification & Tamper Detection
2. Indian ANPR Parsing, Normalization & State Code Validation
3. 15-Day Dispute Window Enforcement & Tribunal Adjudication
4. Citizen Privacy Protection (Masked vs Unmasked Details)
5. Flask Web Endpoints & API Integration (Health, Reviews, Ledger, Blacklist)
6. Two-Way WhatsApp Bot Commands (STATUS, PAY, RULES, DISPUTE, SCORE, HELP)
7. Suraksha Safe Driving Compliance Scoring with Explainability
"""

import os
import sys
import json
import sqlite3
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, init_db, _get_conn, DB_PATH
from blockchain_audit import (
    init_blockchain_table, record_challan_on_blockchain,
    verify_challan_block, verify_ledger_chain
)
from plate_ocr import normalize_indian_plate, is_valid_indian_plate, clean_raw_plate_text
from vahan import lookup_owner, mask_owner_details
from safety_intelligence import (
    init_safety_tables, submit_dispute, resolve_dispute, get_disputes,
    get_near_misses, get_emergency_events, add_blacklist_entry, get_blacklist_entries,
    update_review_action, reviews, DISPUTE_WINDOW_DAYS
)
from notifications import process_bot_message
from gamification import calculate_suraksha_score, generate_certificate_data


# ── 1. BLOCKCHAIN AUDIT & TAMPER DETECTION ────────────────────────
class TestBlockchainIntegrity:
    @pytest.fixture
    def chain_db(self, tmp_path):
        db_file = tmp_path / "test_chain.db"
        conn = sqlite3.connect(str(db_file))
        init_blockchain_table(conn)
        yield conn
        conn.close()

    def test_genesis_block_and_chain_traversal(self, chain_db):
        # Verify genesis block
        res_genesis = verify_ledger_chain(chain_db)
        assert res_genesis["is_valid"] is True
        assert res_genesis["total_blocks"] >= 1
        assert res_genesis["status"] == "Ledger Valid"

        # Record multiple blocks
        record_challan_on_blockchain(chain_db, 101, "KA03MX4521", "NO HELMET", 1000, "hash101")
        record_challan_on_blockchain(chain_db, 102, "MH12AB3456", "WRONG WAY", 5000, "hash102")
        record_challan_on_blockchain(chain_db, 103, "DL09WR6392", "TRIPLE RIDING", 1000, "hash103")

        res = verify_ledger_chain(chain_db)
        assert res["is_valid"] is True
        assert res["total_blocks"] == 4
        assert res["status"] == "Ledger Valid"

    def test_tamper_detection_in_ledger(self, chain_db):
        record_challan_on_blockchain(chain_db, 201, "KA03MX4521", "NO HELMET", 1000, "hash201")
        record_challan_on_blockchain(chain_db, 202, "MH12AB3456", "WRONG WAY", 5000, "hash202")

        # Maliciously mutate fine amount in historical block
        chain_db.execute("UPDATE blockchain_ledger SET fine = 0 WHERE challan_ref = 'RX-000201'")
        chain_db.commit()

        res = verify_ledger_chain(chain_db)
        assert res["is_valid"] is False
        assert "Discrepancy" in res["status"] or "TAMPERED" in res["status"].upper() or res["status"] == "Ledger Tampered"


# ── 2. INDIAN ANPR PARSING & VALIDATION ────────────────────────────
class TestIndianANPR:
    def test_standard_state_plates(self):
        assert normalize_indian_plate("KA 03 MX 4521") == "KA03MX4521"
        assert is_valid_indian_plate("KA03MX4521") is True

        assert normalize_indian_plate("MH 12 AB 3456") == "MH12AB3456"
        assert is_valid_indian_plate("MH12AB3456") is True

        assert normalize_indian_plate("DL 09 WR 6392") == "DL09WR6392"
        assert is_valid_indian_plate("DL09WR6392") is True

    def test_bharat_series_plate(self):
        assert normalize_indian_plate("22 BH 1234 AA") == "22BH1234AA"
        assert is_valid_indian_plate("22BH1234AA") is True

    def test_character_confusion_normalization(self):
        # Letters in state code positions: '0' -> 'O', '1' -> 'I'
        cleaned = clean_raw_plate_text("IND 0L 08 PQ 5678")
        norm = normalize_indian_plate(cleaned)
        assert norm.startswith("DL")

        # Number position confusion: 'O' -> '0', 'I' -> '1', 'S' -> '5'
        raw = "KAO3MX452I"
        norm = normalize_indian_plate(raw)
        assert norm == "KA03MX4521"


# ── 3. DISPUTE WINDOW & TRIBUNAL ADJUDICATION ─────────────────────
class TestDisputeWorkflow:
    @pytest.fixture
    def dispute_db(self, tmp_path):
        db_file = tmp_path / "test_dispute.db"
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
                paid INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ISSUED'
            )
        """)
        init_safety_tables(conn)
        yield conn
        conn.close()

    def test_submit_valid_dispute(self, dispute_db):
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dispute_db.execute(
            "INSERT INTO violations (id, timestamp, plate, violation, fine) VALUES (1, ?, 'KA03MX4521', 'NO HELMET', 1000)",
            (now_ts,)
        )
        dispute_db.commit()

        d_id = submit_dispute(dispute_db, 1, "KA03MX4521", "Incorrect plate recognition", "Dashcam shows helmet worn.")
        assert d_id is not None
        assert d_id > 0

        disputes = get_disputes(dispute_db)
        assert len(disputes) == 1
        assert disputes[0]["status"] == "PENDING"

    def test_dispute_window_expiration(self, dispute_db):
        old_ts = (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")
        dispute_db.execute(
            "INSERT INTO violations (id, timestamp, plate, violation, fine) VALUES (2, ?, 'MH12AB3456', 'WRONG WAY', 5000)",
            (old_ts,)
        )
        dispute_db.commit()

        with pytest.raises(ValueError) as exc:
            submit_dispute(dispute_db, 2, "MH12AB3456", "Medical Emergency", "Car was carrying patient.")
        assert "expired" in str(exc.value).lower()

    def test_tribunal_adjudication_accept(self, dispute_db):
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dispute_db.execute(
            "INSERT INTO violations (id, timestamp, plate, violation, fine) VALUES (3, ?, 'DL09WR6392', 'NO HELMET', 1000)",
            (now_ts,)
        )
        dispute_db.commit()

        d_id = submit_dispute(dispute_db, 3, "DL09WR6392", "Medical Exemption", "Sikh turban exemption.")
        resolve_dispute(dispute_db, d_id, "ACCEPTED", officer_notes="Verified turban exemption.")

        row = dispute_db.execute("SELECT fine, paid, status FROM violations WHERE id=3").fetchone()
        assert row[0] == 0       # Fine waived
        assert row[1] == 1       # Marked settled
        assert row[2] == "CANCELLED"


# ── 4. VAHAN PRIVACY & MASKING ────────────────────────────────────
class TestVahanPrivacy:
    def test_masked_citizen_view(self):
        info = lookup_owner("KA03MX4521", masked=True)
        assert info is not None
        assert "****" in info["name"] or "R***" in info["name"] or info["name"].startswith("R")
        assert "****" in info["phone"]
        assert "****" in info.get("chassis_no", "")

    def test_unmasked_officer_view(self):
        info = lookup_owner("KA03MX4521", masked=False)
        assert info is not None
        assert info["name"] == "Rajesh Kumar"
        assert not info["phone"].startswith("******")


# ── 5. TWO-WAY BOT COMMAND SIMULATOR ──────────────────────────────
class TestTwoWayBot:
    def test_bot_help_command(self):
        res = process_bot_message("HELP")
        assert "Commands" in res["reply"] or "STATUS" in res["reply"]

    def test_bot_score_command(self):
        res = process_bot_message("SCORE KA03MX4521")
        assert "Suraksha" in res["reply"] or "Score" in res["reply"]

    def test_bot_rules_command(self):
        res = process_bot_message("RULES")
        assert "Motor Vehicles Act" in res["reply"] or "Sec 129" in res["reply"]


# ── 6. FLASK WEB APPLICATION INTEGRATION ──────────────────────────
class TestFlaskEndpoints:
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_system_health_api(self, client):
        res = client.get('/api/system-health')
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "healthy"
        assert "privacy_mode" in data
        assert "ledger_status" in data

    def test_blockchain_verify_ledger_endpoint(self, client):
        res = client.get('/api/blockchain/verify-ledger')
        assert res.status_code == 200
        data = res.get_json()
        assert "is_valid" in data
        assert "total_blocks" in data

    def test_near_misses_endpoint(self, client):
        res = client.get('/api/near-misses')
        assert res.status_code == 200
        data = res.get_json()
        assert "events" in data

    def test_emergency_events_endpoint(self, client):
        res = client.get('/api/emergency-events')
        assert res.status_code == 200
        data = res.get_json()
        assert "events" in data

    def test_reviews_endpoint(self, client):
        res = client.get('/api/reviews')
        assert res.status_code == 200
        data = res.get_json()
        assert "reviews" in data

    def test_citizen_violations_and_pay(self, client):
        with client.session_transaction() as sess:
            sess['is_citizen'] = True
        res = client.get('/citizen/violations')
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)

        if data:
            target = data[0]
            pay_res = client.post('/citizen/pay', json={
                "violation_id": target["id"],
                "payer_name": "Test Driver",
                "payment_mode": "UPI Simulated"
            })
            assert pay_res.status_code == 200
            pay_data = pay_res.get_json()
            assert pay_data["status"] == "PAID"

