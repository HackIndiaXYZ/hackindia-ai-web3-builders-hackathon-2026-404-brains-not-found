"""
Unit & Integration Tests for TrafficGuard Intelligence Dashboard & Operations Command
Tests:
1. Intelligence Engine Core Metrics & Telemetry (Overview, Corridors, Camera Nodes)
2. Cross-Camera Vehicle Journey Tracking & Sequence Synthesis
3. Multi-Dimensional Risk Intelligence & Tier Filtering (Critical, High, Medium, Low)
4. Incident Command Feed & Automated Police Dispatch Directives
5. Officer Response Fleet Roster & Simulation Notice
6. Signal Optimization Simulator (Webster green splits & emergency preemption)
7. Enforcement Effectiveness Evaluation (Before vs After Interventions)
8. Policy / What-If Simulator (Officer deployment, Turbo inference, Green corridors)
9. Grounded TrafficGuard Copilot AI Assistant (Hotspots, Criticals, Plate Profiles, Stats)
10. Intelligence Authentication & RBAC Access Control (Login, Logout, Route Gating, 401 API)
"""

import os
import sys
import json
import sqlite3
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, init_db, _get_conn, DB_PATH
from intelligence_engine import (
    get_intelligence_overview,
    get_cross_camera_journeys,
    get_risk_intelligence,
    get_incident_command_feed,
    get_officer_response_fleet,
    get_corridor_intelligence,
    simulate_signal_optimization,
    get_enforcement_effectiveness,
    simulate_policy_scenario,
    answer_copilot_query,
    CAMERA_NODES,
    CORRIDORS
)


# ── FIXTURES ───────────────────────────────────────────────────
@pytest.fixture
def test_db(tmp_path):
    """Creates a temporary isolated SQLite database with violations & near misses."""
    db_file = tmp_path / "test_intel.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        CREATE TABLE violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            video TEXT,
            violation TEXT,
            plate TEXT,
            owner_name TEXT,
            fine INTEGER,
            screenshot TEXT,
            challan TEXT,
            paid INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ISSUED',
            confidence REAL DEFAULT 97.4,
            tracking_id INTEGER,
            vehicle_type TEXT DEFAULT 'Two-Wheeler',
            location TEXT DEFAULT 'Silk Board Junction North'
        )
    """)
    c.execute("""
        CREATE TABLE near_miss_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera TEXT,
            timestamp TEXT,
            vehicle_ids TEXT,
            risk_score REAL,
            risk_level TEXT,
            reason TEXT,
            source TEXT
        )
    """)
    c.execute("""
        CREATE TABLE disputes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            violation_id INTEGER,
            plate TEXT,
            reason TEXT,
            evidence_url TEXT,
            status TEXT DEFAULT 'PENDING',
            submitted_at TEXT,
            reviewed_by TEXT,
            review_notes TEXT,
            resolution_at TEXT
        )
    """)

    # Seed data
    c.execute("INSERT INTO violations (timestamp, video, violation, plate, owner_name, fine, confidence, location) VALUES ('2026-09-05 10:15:00', 'cam1.mp4', 'NO HELMET', 'KA03MX4521', 'Rajesh Kumar', 1000, 98.5, 'Silk Board Junction North')")
    c.execute("INSERT INTO violations (timestamp, video, violation, plate, owner_name, fine, confidence, location) VALUES ('2026-09-05 10:25:00', 'cam2.mp4', 'WRONG WAY', 'DL09WR6392', 'Mohammed Irfan', 5000, 96.2, 'Sony World Crossing')")
    c.execute("INSERT INTO violations (timestamp, video, violation, plate, owner_name, fine, confidence, location) VALUES ('2026-09-05 10:35:00', 'cam3.mp4', 'TRIPLE RIDING', 'MH12AB3456', 'Priya Sharma', 1000, 99.1, 'MG Road Metro')")
    c.execute("INSERT INTO near_miss_events (camera, timestamp, vehicle_ids, risk_score, risk_level, reason, source) VALUES ('Silk Board North', '2026-09-05 10:20:00', 'Track #101, Track #104', 92.5, 'CRITICAL', 'TTC < 0.5s rapid deceleration', 'DEMO_ANALYZER')")
    c.execute("INSERT INTO disputes (violation_id, plate, reason, status, submitted_at) VALUES (1, 'KA03MX4521', 'Turban exemption claimed', 'PENDING', '2026-09-05 10:30:00')")

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def client():
    """Flask test client."""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_intel_secret'
    with app.test_client() as client:
        yield client


# ── 1. INTELLIGENCE ENGINE TESTS ──────────────────────────────
class TestIntelligenceEngine:
    def test_get_intelligence_overview(self, test_db):
        overview = get_intelligence_overview(test_db)
        assert overview["active_cameras"] == len(CAMERA_NODES)
        assert overview["total_violations"] == 3
        assert overview["unique_vehicles_detected"] == 3
        assert overview["active_incidents"] >= 2
        assert overview["near_miss_safety_events"] == 1
        assert overview["pending_tribunal_reviews"] == 1
        assert "68%" in overview["current_traffic_density"]

    def test_get_cross_camera_journeys(self, test_db):
        journeys = get_cross_camera_journeys(test_db)
        assert len(journeys) >= 3
        plates = [j["plate"] for j in journeys]
        assert "KA03MX4521" in plates
        assert "DL09WR6392" in plates
        for j in journeys:
            assert len(j["camera_sequence"]) >= 2
            assert j["transit_minutes"] > 0
            assert j["risk_level"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")

    def test_get_risk_intelligence_tiers_and_filtering(self, test_db):
        res = get_risk_intelligence(test_db)
        counts = res["counts"]
        assert counts["TOTAL"] == 3
        assert counts["CRITICAL"] >= 1  # WRONG WAY
        assert counts["HIGH"] >= 1      # TRIPLE RIDING
        assert counts["MEDIUM"] >= 1    # NO HELMET

        # Test filter by level
        filtered_crit = get_risk_intelligence(test_db, filter_level="CRITICAL")
        assert len(filtered_crit["records"]["CRITICAL"]) >= 1
        assert len(filtered_crit["records"]["LOW"]) == 0

        # Test filter by location
        filtered_loc = get_risk_intelligence(test_db, filter_location="Sony World")
        assert len(filtered_loc["records"]["CRITICAL"]) >= 1

    def test_get_incident_command_feed(self, test_db):
        incidents = get_incident_command_feed(test_db)
        assert len(incidents) >= 2
        # Check near-miss incident
        nm_inc = [i for i in incidents if i["type"] == "NEAR_MISS_COLLISION_WARNING"]
        assert len(nm_inc) >= 1
        assert nm_inc[0]["severity"] == "CRITICAL"
        assert "Interceptor" in nm_inc[0]["recommended_response"]

        # Check wrong way violation incident
        ww_inc = [i for i in incidents if i["type"] == "COUNTER_FLOW_HAZARD"]
        assert len(ww_inc) >= 1
        assert ww_inc[0]["severity"] == "CRITICAL"

    def test_get_officer_response_fleet(self):
        fleet = get_officer_response_fleet()
        assert fleet["mode"] == "DEMO_SIMULATION_MODE"
        assert "notice" in fleet
        assert fleet["active_officers_count"] == 4
        assert fleet["available_officers_count"] >= 1
        for off in fleet["officers"]:
            assert "badge" in off
            assert "station" in off
            assert "status" in off

    def test_get_corridor_intelligence(self):
        corr = get_corridor_intelligence()
        assert corr["total_corridors_monitored"] == len(CORRIDORS)
        assert corr["critical_corridors"] >= 1
        for c in corr["corridors"]:
            assert "length_km" in c
            assert "base_travel_time_min" in c
            assert "current_travel_time_min" in c
            assert len(c["bottlenecks"]) > 0

    def test_simulate_signal_optimization(self):
        # Normal simulation
        res_normal = simulate_signal_optimization("C01", density_pct=50, queue_vehicles=20, emergency_present=False)
        assert res_normal["mode"] == "SIMULATION"
        assert "SIMULATION ONLY" in res_normal["disclaimer"]
        assert res_normal["recommended_timing"]["phase_mode"] == "BALANCED_EQUILIBRIUM"

        # High congestion simulation
        res_heavy = simulate_signal_optimization("C01", density_pct=90, queue_vehicles=60, emergency_present=False)
        assert res_heavy["recommended_timing"]["phase_mode"] == "PEAK_THROUGHPUT_EXPANSION"
        assert res_heavy["recommended_timing"]["green_split_seconds"] > 60

        # Emergency preemption simulation
        res_emg = simulate_signal_optimization("C01", density_pct=75, queue_vehicles=40, emergency_present=True)
        assert res_emg["recommended_timing"]["phase_mode"] == "GREEN_PREEMPTION_PRIORITY"
        assert "Preemption" in res_emg["ai_rationale"]

    def test_get_enforcement_effectiveness(self):
        eff = get_enforcement_effectiveness()
        assert eff["status"] == "OBSERVED_DATASET"
        assert len(eff["interventions"]) >= 2
        for itv in eff["interventions"]:
            assert "OBSERVED CHANGE" in itv["disclaimer"]
            assert "before" in itv
            assert "after" in itv
            assert "observed_change" in itv
            assert itv["observed_change"]["violation_reduction"].startswith("-")

    def test_simulate_policy_scenario(self):
        pol = simulate_policy_scenario("OFFICER_DEPLOYMENT", 8)
        assert pol["mode"] == "SIMULATION_ESTIMATE"
        assert "SIMULATION ESTIMATE" in pol["disclaimer"]
        assert "8 Patrol Units" in pol["scenario"]["simulated_metric"]
        assert "response_time_reduction" in pol["scenario"]["estimated_impact"]

        pol_gpu = simulate_policy_scenario("INCREASED_MONITORING", 1)
        assert "60 FPS" in pol_gpu["scenario"]["simulated_metric"]

    def test_answer_copilot_query_grounding(self, test_db):
        # 1. Hotspot query
        r1 = answer_copilot_query("Which location needs attention right now?", db_conn=test_db)
        assert "Silk Board" in r1["answer"] or "High Priority" in r1["answer"]
        assert "violations" in r1["basis"]

        # 2. Critical query
        r2 = answer_copilot_query("Which incidents are critical?", db_conn=test_db)
        assert "Critical" in r2["answer"] or "WRONG WAY" in r2["answer"]

        # 3. Specific plate risk profile
        r3 = answer_copilot_query("Why is vehicle KA03MX4521 high risk?", db_conn=test_db)
        assert "KA03MX4521" in r3["answer"]
        assert "Rajesh Kumar" in r3["answer"]
        assert "NO HELMET" in r3["answer"]

        # 4. Today's summary statistics
        r4 = answer_copilot_query("What violations increased today?", db_conn=test_db)
        assert "Live Enforcement Statistics" in r4["answer"]
        assert "Recorded Infractions" in r4["answer"]


# ── 2. FLASK INTELLIGENCE RBAC & ROUTE INTEGRATION ─────────────
class TestIntelligenceRoutesAndRBAC:
    def test_intelligence_login_page_renders(self, client):
        resp = client.get('/intelligence/login')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert "TrafficGuard" in html
        assert "AI Traffic Intelligence & Operations Command" in html
        assert "intelligence" in html

    def test_intelligence_login_success(self, client):
        resp = client.post('/intelligence/login', data={
            'username': 'intelligence',
            'password': 'trafficguard2026'
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/intelligence"

        # Follow into dashboard
        with client.session_transaction() as sess:
            assert sess.get('is_intelligence') is True
            assert sess.get('user_role') == 'INTELLIGENCE_OPERATOR'

    def test_intelligence_login_invalid_password(self, client):
        resp = client.post('/intelligence/login', data={
            'username': 'intelligence',
            'password': 'wrongpassword'
        })
        assert resp.status_code == 200
        assert "Invalid Intelligence Command Credentials" in resp.data.decode('utf-8')

    def test_unauthenticated_dashboard_redirects_to_login(self, client):
        resp = client.get('/intelligence')
        assert resp.status_code == 302
        assert "/intelligence/login" in resp.headers["Location"]

    def test_authenticated_dashboard_renders_all_panels(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'
            sess['username'] = 'Test Intelligence Commander'

        resp = client.get('/intelligence')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert "Intelligence Overview" in html
        assert "Cross-Camera" in html or "Journey" in html
        assert "Risk Intel" in html or "Risk" in html
        assert "Incident" in html
        assert "Officer Response" in html
        assert "Corridor Intelligence" in html
        assert "Signal Sim" in html or "Signal" in html
        assert "Enforcement Effectiveness" in html
        assert "Policy Sim" in html or "Policy" in html
        assert "Copilot" in html or "TrafficGuard Copilot" in html

    def test_intelligence_logout_clears_session(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.get('/intelligence/logout')
        assert resp.status_code == 302
        assert "/intelligence/login" in resp.headers["Location"]

        with client.session_transaction() as sess:
            assert sess.get('is_intelligence') is None
            assert sess.get('user_role') is None

    def test_unauthenticated_api_returns_401(self, client):
        resp = client.get('/api/intelligence/overview')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"] == "unauthorised"

    def test_authenticated_api_overview(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.get('/api/intelligence/overview')
        assert resp.status_code == 200
        data = resp.get_json()
        assert "active_cameras" in data
        assert "camera_nodes" in data

    def test_authenticated_api_journeys(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.get('/api/intelligence/journeys')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_authenticated_api_risks_and_filtering(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.get('/api/intelligence/risks?level=CRITICAL')
        assert resp.status_code == 200
        data = resp.get_json()
        assert "counts" in data
        assert "records" in data

    def test_authenticated_api_incidents(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.get('/api/intelligence/incidents')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_authenticated_api_officers(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.get('/api/intelligence/officers')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["mode"] == "DEMO_SIMULATION_MODE"

    def test_authenticated_api_corridors(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.get('/api/intelligence/corridors')
        assert resp.status_code == 200
        data = resp.get_json()
        assert "corridors" in data

    def test_authenticated_api_simulate_signal(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.post('/api/intelligence/simulate-signal',
                           json={"intersection_id": "C01", "density_pct": 85, "queue_vehicles": 45, "emergency_present": True})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["mode"] == "SIMULATION"
        assert data["recommended_timing"]["phase_mode"] == "GREEN_PREEMPTION_PRIORITY"

    def test_authenticated_api_effectiveness(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.get('/api/intelligence/effectiveness')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "OBSERVED_DATASET"

    def test_authenticated_api_simulate_policy(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.post('/api/intelligence/simulate-policy',
                           json={"policy_type": "OFFICER_DEPLOYMENT", "parameter_value": 6})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["mode"] == "SIMULATION_ESTIMATE"
        assert "6 Patrol Units" in data["scenario"]["simulated_metric"]

    def test_authenticated_api_copilot(self, client):
        with client.session_transaction() as sess:
            sess['is_intelligence'] = True
            sess['user_role'] = 'INTELLIGENCE_OPERATOR'

        resp = client.post('/api/intelligence/copilot',
                           json={"query": "Which location needs attention right now?"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "answer" in data
        assert "basis" in data
