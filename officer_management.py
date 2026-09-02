"""
Officer Management, RBAC & Enforcement Gamification for TrafficGuard Pro
Handles:
1. Traffic Police Officer Profiles & Station Rosters.
2. Individual Enforcement Performance Metrics & Badges.
3. Multi-Tier Role-Based Access Control (RBAC):
   - Superadmin (Full System & Security Access)
   - Admin (Traffic Police HQ Command)
   - Inspector / Field Officer (Camera & Challan Review)
   - Citizen (Public Status & Payment Portal)
"""

import sqlite3
from datetime import datetime

OFFICER_ROSTER = [
    {
        "id": "OFF-101",
        "name": "Inspector Rajesh K. Sharma",
        "badge": "KA-TP-404",
        "rank": "Senior Traffic Inspector",
        "station": "Indiranagar Traffic Station, Bengaluru",
        "zone": "East Zone",
        "avatar": "👮‍♂️",
        "violations_intercepted": 142,
        "challans_issued": 138,
        "revenue_generated": 245000,
        "accuracy_rate": 98.6,
        "badges": ["TOP ENFORCER 🏆", "EAGLE EYE 👁️", "HABITUAL TAMER 🛡️"]
    },
    {
        "id": "OFF-102",
        "name": "Sub-Inspector Priya Deshmukh",
        "badge": "MH-TP-209",
        "rank": "Traffic Sub-Inspector",
        "station": "Shivajinagar Traffic Division, Pune",
        "zone": "Central Zone",
        "avatar": "👮‍♀️",
        "violations_intercepted": 118,
        "challans_issued": 115,
        "revenue_generated": 198000,
        "accuracy_rate": 99.1,
        "badges": ["SPEED BUSTER ⚡", "ZERO BACKLOG ⚡", "ACCURACY CHAMP 🎯"]
    },
    {
        "id": "OFF-103",
        "name": "Head Constable Mohammed Irfan",
        "badge": "DL-TP-881",
        "rank": "Head Constable (AI Interceptor)",
        "station": "Janakpuri Traffic Circle, New Delhi",
        "zone": "West Zone",
        "avatar": "👮‍♂️",
        "violations_intercepted": 95,
        "challans_issued": 92,
        "revenue_generated": 156000,
        "accuracy_rate": 97.4,
        "badges": ["HELMET SHIELD 🪖", "NIGHT VIGIL 🌙"]
    },
    {
        "id": "OFF-104",
        "name": "Inspector Anand V. Swamy",
        "badge": "TN-TP-512",
        "rank": "Traffic Inspector",
        "station": "Mount Road Traffic Circle, Chennai",
        "zone": "South Zone",
        "avatar": "👮‍♂️",
        "violations_intercepted": 87,
        "challans_issued": 85,
        "revenue_generated": 141000,
        "accuracy_rate": 98.0,
        "badges": ["WRONG-WAY BUSTER ⛔", "RAPID REVIEWER ⏱️"]
    },
]


def init_officers_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS officers (
            id                     TEXT PRIMARY KEY,
            name                   TEXT,
            badge                  TEXT,
            rank                   TEXT,
            station                TEXT,
            zone                   TEXT,
            violations_intercepted INTEGER DEFAULT 0,
            challans_issued        INTEGER DEFAULT 0,
            revenue_generated      INTEGER DEFAULT 0,
            accuracy_rate          REAL DEFAULT 98.0,
            badges                 TEXT,
            active                 INTEGER DEFAULT 1
        )
    """)
    conn.commit()

    # Seed if empty
    c = conn.cursor()
    count = c.execute("SELECT COUNT(*) FROM officers").fetchone()[0]
    if count == 0:
        for off in OFFICER_ROSTER:
            c.execute("""
                INSERT INTO officers (id, name, badge, rank, station, zone,
                                      violations_intercepted, challans_issued,
                                      revenue_generated, accuracy_rate, badges, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (off["id"], off["name"], off["badge"], off["rank"], off["station"], off["zone"],
                  off["violations_intercepted"], off["challans_issued"], off["revenue_generated"],
                  off["accuracy_rate"], ",".join(off["badges"])))
        conn.commit()


def get_officer_leaderboard(conn):
    """Return live sorted performance ranking of enforcement officers."""
    init_officers_table(conn)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    rows = c.execute("""
        SELECT * FROM officers WHERE active = 1
        ORDER BY violations_intercepted DESC, revenue_generated DESC
    """).fetchall()

    officers = []
    for idx, r in enumerate(rows, 1):
        badges_list = [b.strip() for b in (r["badges"] or "").split(",") if b.strip()]
        officers.append({
            "rank": idx,
            "id": r["id"],
            "name": r["name"],
            "badge": r["badge"],
            "designation": r["rank"],
            "station": r["station"],
            "zone": r["zone"],
            "violations_intercepted": r["violations_intercepted"],
            "challans_issued": r["challans_issued"],
            "revenue_generated": r["revenue_generated"],
            "accuracy_rate": r["accuracy_rate"],
            "badges": badges_list,
            "is_top": idx == 1
        })
    return officers
