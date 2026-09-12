"""
VehicleTrack — Database Seed Script
Populates violations.db with realistic sample data for the live demo.

Run ONCE before deploying:
    python3 seed_db.py

Safe to re-run — clears existing violations first so you don't get duplicates.
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "violations.db")

# ── Sample data pools ──────────────────────────────────────
PLATES = [
    "KA03MX4521", "MH12AB3456", "DL09WR6392", "TN05AT7024",
    "KL07CD5678", "UP32GH8901", "RJ14XY2345", "GJ01BC7890",
    "TS09QR1234", "KA01HJ9876", "MH04CD1234", "DL08PQ5678",
    "KL09CA1671", "TN22EF3456", "KA05MN7654", "MH20ST9012",
]

OWNERS = [
    "Rajesh Kumar",    "Priya Sharma",   "Mohammed Irfan",
    "Sunita Patel",    "Amit Verma",     "Deepa Nair",
    "Suresh Reddy",    "Anita Joshi",    "Vikram Singh",
    "Kavitha Menon",   "Ravi Teja",      "Pooja Gupta",
    "UNKNOWN",         "UNKNOWN",        "Arjun Das",
    "Meena Krishnan",
]

VIDEOS = [
    "dashcam_mg_road.mp4",   "cctv_silk_board.mp4",
    "dashcam_outer_ring.mp4","cctv_koramangala.mp4",
    "dashcam_nh48.mp4",      "cctv_whitefield.mp4",
]

VIOLATIONS_POOL = [
    ("NO HELMET",              1000),
    ("TRIPLE RIDING",          1000),
    ("WRONG WAY",              5000),
    ("NO HELMET + TRIPLE RIDING", 2000),
]

# ── Build records ──────────────────────────────────────────
def make_violations(n=25):
    records = []
    now = datetime.now()
    # spread across last 7 days, weighted toward recent
    for i in range(n):
        days_ago  = random.choices([0,1,2,3,4,5,6], weights=[8,6,5,4,3,2,1])[0]
        hour      = random.randint(7, 22)
        minute    = random.randint(0, 59)
        ts        = (now - timedelta(days=days_ago)).replace(
                        hour=hour, minute=minute, second=random.randint(0,59))

        idx       = random.randint(0, len(PLATES)-1)
        plate     = PLATES[idx]
        owner     = OWNERS[idx]
        violation, base_fine = random.choice(VIOLATIONS_POOL)

        # repeat offender logic — some plates appear multiple times
        prev      = sum(1 for r in records if r["plate"] == plate)
        mult      = min(prev + 1, 3)
        fine      = base_fine * mult

        paid      = 1 if (days_ago >= 3 and random.random() < 0.45) else 0
        video     = random.choice(VIDEOS)

        records.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "video":     video,
            "violation": violation,
            "plate":     plate,
            "owner_name":owner,
            "fine":      fine,
            "paid":      paid,
        })

    # sort chronologically
    records.sort(key=lambda r: r["timestamp"])
    return records

# ── Write to DB ────────────────────────────────────────────
def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # Create table if fresh DB
    c.execute('''CREATE TABLE IF NOT EXISTS violations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp   TEXT,
        video       TEXT,
        violation   TEXT,
        plate       TEXT,
        owner_name  TEXT,
        fine        INTEGER,
        screenshot  TEXT,
        challan     TEXT,
        paid        INTEGER DEFAULT 0
    )''')

    # Create visitors table too
    c.execute('''CREATE TABLE IF NOT EXISTS visitors (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ip        TEXT,
        page      TEXT,
        referrer  TEXT,
        ua        TEXT
    )''')

    # Clear existing seed data (keep any real violations above id=1000)
    c.execute("DELETE FROM violations WHERE id < 1000")
    conn.commit()

    records = make_violations(25)
    for r in records:
        c.execute(
            "INSERT INTO violations "
            "(timestamp,video,violation,plate,owner_name,fine,screenshot,challan,paid) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (r["timestamp"], r["video"], r["violation"],
             r["plate"], r["owner_name"], r["fine"],
             None, None, r["paid"])
        )

    conn.commit()
    total = c.execute("SELECT COUNT(*) FROM violations").fetchone()[0]
    fines = c.execute("SELECT SUM(fine) FROM violations").fetchone()[0]
    paid  = c.execute("SELECT COUNT(*) FROM violations WHERE paid=1").fetchone()[0]
    conn.close()

    print(f"✅ Seeded {len(records)} violations into {DB_PATH}")
    print(f"   Total fines  : Rs. {fines:,}")
    print(f"   Paid         : {paid} / {total}")
    print(f"   DB size      : {os.path.getsize(DB_PATH)/1024:.1f} KB")
    print(f"\nCommit this file to your repo:")
    print(f"   git add violations.db")
    print(f"   git commit -m 'Add seeded demo database'")

if __name__ == "__main__":
    seed()
