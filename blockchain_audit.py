"""
Tamper-Evident Cryptographic Audit Ledger for TrafficGuard Pro
Ensures:
1. Every e-challan, payment settlement, and tribunal decision is committed to an immutable SHA-256 block hash chain.
2. Prevents accusations of evidence alteration, fine tampering, or corrupt records.
3. Provides full-chain mathematical verification (VERIFY LEDGER) detecting any block alterations across history.
4. Delivers public verification proofs on the citizen portal and verification page.
"""

import hashlib
import json
import sqlite3
from datetime import datetime

GENESIS_PREV_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


def init_blockchain_table(conn):
    """Initialize the tamper-evident cryptographic ledger table with index and event support."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS blockchain_ledger (
            block_height    INTEGER PRIMARY KEY AUTOINCREMENT,
            challan_ref     TEXT UNIQUE,
            timestamp       TEXT,
            plate           TEXT,
            violation       TEXT,
            fine            INTEGER,
            evidence_hash   TEXT,
            officer_id      TEXT,
            event_type      TEXT DEFAULT 'CHALLAN_ISSUED',
            prev_hash       TEXT,
            block_hash      TEXT,
            is_valid        INTEGER DEFAULT 1
        )
    """)
    # Check if event_type column exists for existing databases
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(blockchain_ledger)")
    columns = [row[1] for row in cursor.fetchall()]
    if "event_type" not in columns:
        try:
            conn.execute("ALTER TABLE blockchain_ledger ADD COLUMN event_type TEXT DEFAULT 'CHALLAN_ISSUED'")
        except Exception:
            pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_blockchain_challan ON blockchain_ledger(challan_ref)")

    # Auto-seed Genesis Block #0 if blockchain ledger is brand new
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM blockchain_ledger")
    if c.fetchone()[0] == 0:
        ts = "2026-01-01 00:00:00"
        genesis_hash = compute_block_hash(0, "GENESIS_ROOT", ts, "SYSTEM", "GENESIS_INITIALIZATION", 0, "0"*64, "SYSTEM_GENESIS", GENESIS_PREV_HASH, "GENESIS_ROOT")
        conn.execute("""
            INSERT INTO blockchain_ledger (block_height, challan_ref, timestamp, plate, violation, fine, evidence_hash, officer_id, event_type, prev_hash, block_hash)
            VALUES (0, 'GENESIS_ROOT', ?, 'SYSTEM', 'GENESIS_INITIALIZATION', 0, ?, 'SYSTEM_GENESIS', 'GENESIS_ROOT', ?, ?)
        """, (ts, "0"*64, GENESIS_PREV_HASH, genesis_hash))

    conn.commit()


def compute_block_hash(block_height, challan_ref, timestamp, plate, violation, fine, evidence_hash, officer_id, prev_hash, event_type="CHALLAN_ISSUED"):
    """Compute SHA-256 digest of block payload."""
    raw_payload = f"{block_height}|{challan_ref}|{timestamp}|{plate}|{violation}|{fine}|{evidence_hash}|{officer_id}|{event_type}|{prev_hash}"
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


def record_challan_on_blockchain(conn, violation_id, plate, violation, fine, evidence_hash, officer_id="POLICE_AI_OFFICER_01", event_type="CHALLAN_ISSUED"):
    """
    Append an immutable block to the cryptographic chain.
    """
    init_blockchain_table(conn)
    c = conn.cursor()

    challan_ref = f"RX-{violation_id:06d}"
    last_block = c.execute("SELECT block_height, block_hash FROM blockchain_ledger ORDER BY block_height DESC LIMIT 1").fetchone()

    if last_block:
        prev_height, prev_hash = last_block
        block_height = prev_height + 1
    else:
        block_height = 1
        prev_hash = GENESIS_PREV_HASH

    ts = datetime.now().isoformat()
    ev_hash = evidence_hash or "NO_EVIDENCE_HASH"
    block_hash = compute_block_hash(block_height, challan_ref, ts, plate, violation, fine, ev_hash, officer_id, prev_hash, event_type)

    c.execute("""
        INSERT OR REPLACE INTO blockchain_ledger
        (block_height, challan_ref, timestamp, plate, violation, fine, evidence_hash, officer_id, event_type, prev_hash, block_hash, is_valid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (block_height, challan_ref, ts, plate, violation, fine, ev_hash, officer_id, event_type, prev_hash, block_hash))

    conn.commit()
    return {
        "block_height": block_height,
        "challan_ref": challan_ref,
        "block_hash": block_hash,
        "prev_hash": prev_hash,
        "event_type": event_type,
        "timestamp": ts
    }


def verify_challan_block(conn, challan_ref):
    """
    Mathematically verify the integrity of a recorded challan against the cryptographic ledger.
    """
    init_blockchain_table(conn)
    c = conn.cursor()
    row = c.execute("""
        SELECT block_height, challan_ref, timestamp, plate, violation, fine, evidence_hash, officer_id, prev_hash, block_hash, COALESCE(event_type, 'CHALLAN_ISSUED')
        FROM blockchain_ledger
        WHERE challan_ref = ?
    """, (challan_ref,)).fetchone()

    if not row:
        return {
            "verified": False,
            "status": "NOT FOUND ON LEDGER",
            "message": f"Challan {challan_ref} has not been committed to the cryptographic ledger yet."
        }

    b_height, c_ref, ts, plate, viol, fine, ev_hash, off_id, prev_h, stored_hash, ev_type = row
    
    # Try computing hash with event_type and without for legacy compatibility
    recomputed_hash = compute_block_hash(b_height, c_ref, ts, plate, viol, fine, ev_hash, off_id, prev_h, ev_type)
    legacy_payload = f"{b_height}|{c_ref}|{ts}|{plate}|{viol}|{fine}|{ev_hash}|{off_id}|{prev_h}"
    legacy_hash = hashlib.sha256(legacy_payload.encode("utf-8")).hexdigest()

    is_intact = (recomputed_hash == stored_hash) or (legacy_hash == stored_hash)

    return {
        "verified": is_intact,
        "status": "MATHEMATICALLY VERIFIED (TAMPER-PROOF)" if is_intact else "INTEGRITY MISMATCH",
        "block_height": b_height,
        "challan_ref": c_ref,
        "block_hash": stored_hash,
        "prev_hash": prev_h,
        "evidence_sha256": ev_hash,
        "officer_signature": off_id,
        "event_type": ev_type,
        "timestamp": ts,
        "recomputed_hash": recomputed_hash if is_intact else recomputed_hash
    }


def verify_ledger_chain(conn):
    """
    Traverse the complete cryptographic audit ledger from genesis block to the tip.
    Validates:
    1. Genesis block references GENESIS_PREV_HASH.
    2. Every block's previous_hash strictly matches the preceding block's current_hash.
    3. Every block's current_hash recomputes to the exact cryptographic digest.
    Returns 'Ledger Valid' or 'Ledger Tampered' with full audit diagnostics.
    """
    init_blockchain_table(conn)
    c = conn.cursor()
    rows = c.execute("""
        SELECT block_height, challan_ref, timestamp, plate, violation, fine, evidence_hash, officer_id, prev_hash, block_hash, COALESCE(event_type, 'CHALLAN_ISSUED')
        FROM blockchain_ledger
        ORDER BY block_height ASC
    """).fetchall()

    if not rows:
        return {
            "is_valid": True,
            "status": "Ledger Valid",
            "total_blocks": 0,
            "genesis_hash": GENESIS_PREV_HASH,
            "latest_block_hash": GENESIS_PREV_HASH,
            "tampered_block": None,
            "message": "Cryptographic ledger is initialized (empty)."
        }

    prev_expected_hash = GENESIS_PREV_HASH

    for idx, row in enumerate(rows):
        b_height, c_ref, ts, plate, viol, fine, ev_hash, off_id, prev_h, stored_hash, ev_type = row

        # 1. Check prev_hash linkage
        if prev_h != prev_expected_hash:
            return {
                "is_valid": False,
                "status": "Ledger Tampered",
                "total_blocks": len(rows),
                "tampered_block": b_height,
                "challan_ref": c_ref,
                "error": f"Broken chain link at block #{b_height}. Expected prev_hash {prev_expected_hash[:16]}..., found {prev_h[:16]}...",
                "message": f"Ledger Tampered: Broken block linkage detected at Block #{b_height} ({c_ref})."
            }

        # 2. Check block hash integrity
        recomputed_hash = compute_block_hash(b_height, c_ref, ts, plate, viol, fine, ev_hash, off_id, prev_h, ev_type)
        legacy_payload = f"{b_height}|{c_ref}|{ts}|{plate}|{viol}|{fine}|{ev_hash}|{off_id}|{prev_h}"
        legacy_hash = hashlib.sha256(legacy_payload.encode("utf-8")).hexdigest()

        if stored_hash not in (recomputed_hash, legacy_hash):
            return {
                "is_valid": False,
                "status": "Ledger Tampered",
                "total_blocks": len(rows),
                "tampered_block": b_height,
                "challan_ref": c_ref,
                "error": f"Hash mismatch at block #{b_height}. Data inside block was altered.",
                "message": f"Ledger Tampered: Cryptographic hash mismatch at Block #{b_height} ({c_ref})."
            }

        prev_expected_hash = stored_hash

    return {
        "is_valid": True,
        "status": "Ledger Valid",
        "total_blocks": len(rows),
        "genesis_hash": GENESIS_PREV_HASH,
        "latest_block_hash": rows[-1][9],
        "tampered_block": None,
        "message": f"All {len(rows)} blocks mathematically verified. Cryptographic audit chain is fully intact and valid."
    }

