"""
SQLite persistence layer for Lipid EQ.

Replaces the old single blacklist_config.json with a proper schema that
supports:
  - batches            -> a solvent/extraction batch (e.g. "Hexane Batch 1")
  - blank_uploads       -> one uploaded blank file, tagged with a blank_type
                           (Solvent / Method / Carryover / Reagent) and linked
                           to a batch
  - blank_compounds     -> the parsed compound rows belonging to a blank_upload
  - blacklist_keywords   -> persisted blacklist keywords (replaces the old json)

The "blank pool" for a batch is the union of all blank_compounds belonging
to that batch's blank_uploads (optionally filtered by blank_type).
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "lipid_eq_data.db"

BLANK_TYPES = ["Solvent", "Method", "Carryover", "Reagent"]

DEFAULT_BLACKLIST = [
    'siloxane', 'phthalate', 'octaxiloxane'
]


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            solvent_system TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blank_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
            blank_type TEXT NOT NULL,
            filename TEXT,
            q_threshold REAL,
            area_threshold REAL,
            n_compounds INTEGER DEFAULT 0,
            uploaded_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blank_compounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blank_upload_id INTEGER NOT NULL REFERENCES blank_uploads(id) ON DELETE CASCADE,
            hit_name TEXT,
            rt_min REAL,
            area_abs REAL,
            area_pct REAL,
            quality REAL,
            chemical_status TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blacklist_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE NOT NULL
        )
    """)
    conn.commit()

    # seed default blacklist on first run only
    cur.execute("SELECT COUNT(*) FROM blacklist_keywords")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT OR IGNORE INTO blacklist_keywords (keyword) VALUES (?)",
            [(kw,) for kw in DEFAULT_BLACKLIST]
        )
        conn.commit()
    conn.close()


# ─── BATCHES ──────────────────────────────────────────────────────────────

def add_batch(name, solvent_system, notes=""):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO batches (name, solvent_system, notes, created_at) VALUES (?, ?, ?, ?)",
            (name.strip(), solvent_system.strip(), notes.strip(), datetime.now().isoformat())
        )
        conn.commit()
        return True, "OK"
    except sqlite3.IntegrityError:
        return False, f"Batch '{name}' sudah wujud."
    finally:
        conn.close()


def list_batches():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT b.id, b.name, b.solvent_system, b.notes, b.created_at,
               COUNT(bu.id) AS n_blanks
        FROM batches b
        LEFT JOIN blank_uploads bu ON bu.batch_id = b.id
        GROUP BY b.id
        ORDER BY b.created_at DESC
    """, conn)
    conn.close()
    return df


def delete_batch(batch_id):
    conn = get_connection()
    conn.execute("DELETE FROM batches WHERE id = ?", (batch_id,))
    conn.commit()
    conn.close()


# ─── BLANK UPLOADS / POOL ─────────────────────────────────────────────────

def add_blank_upload(batch_id, blank_type, filename, q_threshold, area_threshold, df_compounds):
    """Stores one parsed blank file. df_compounds must have columns:
    Hit Name, RT (min), Area (Ab*s), Area (%), Quality, Chemical_Status
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO blank_uploads (batch_id, blank_type, filename, q_threshold, area_threshold, n_compounds, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (batch_id, blank_type, filename, q_threshold, area_threshold, len(df_compounds), datetime.now().isoformat()))
    upload_id = cur.lastrowid

    rows = [
        (upload_id, r['Hit Name'], r['RT (min)'], r['Area (Ab*s)'], r['Area (%)'], r['Quality'], r['Chemical_Status'])
        for _, r in df_compounds.iterrows()
    ]
    cur.executemany("""
        INSERT INTO blank_compounds (blank_upload_id, hit_name, rt_min, area_abs, area_pct, quality, chemical_status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    return upload_id


def list_blanks(batch_id=None):
    conn = get_connection()
    q = """
        SELECT bu.id, bu.batch_id, b.name AS batch_name, bu.blank_type, bu.filename,
               bu.q_threshold, bu.area_threshold, bu.n_compounds, bu.uploaded_at
        FROM blank_uploads bu
        JOIN batches b ON b.id = bu.batch_id
    """
    params = ()
    if batch_id is not None:
        q += " WHERE bu.batch_id = ?"
        params = (batch_id,)
    q += " ORDER BY bu.uploaded_at DESC"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


def delete_blank_upload(upload_id):
    conn = get_connection()
    conn.execute("DELETE FROM blank_uploads WHERE id = ?", (upload_id,))
    conn.commit()
    conn.close()


def get_blank_pool(batch_id, blank_types=None):
    """Returns the combined blank pool (union of compounds) for a batch,
    optionally restricted to specific blank_types. Adds Blank_Type and
    Blank_Source columns so matches can be traced back to their origin.
    """
    conn = get_connection()
    q = """
        SELECT bc.hit_name AS "Hit Name", bc.rt_min AS "RT (min)",
               bc.area_abs AS "Area (Ab*s)", bc.area_pct AS "Area (%)",
               bc.quality AS "Quality", bc.chemical_status AS "Chemical_Status",
               bu.blank_type AS "Blank_Type", bu.filename AS "Blank_Source"
        FROM blank_compounds bc
        JOIN blank_uploads bu ON bu.id = bc.blank_upload_id
        WHERE bu.batch_id = ?
    """
    params = [batch_id]
    if blank_types:
        placeholders = ",".join("?" * len(blank_types))
        q += f" AND bu.blank_type IN ({placeholders})"
        params += list(blank_types)
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


def pool_summary(batch_id):
    """Quick per-type counts for display (n blank files, n compounds)."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT bu.blank_type AS "Blank Type", COUNT(DISTINCT bu.id) AS "Blank Files",
               COALESCE(SUM(bu.n_compounds), 0) AS "Total Compounds"
        FROM blank_uploads bu
        WHERE bu.batch_id = ?
        GROUP BY bu.blank_type
    """, conn, params=(batch_id,))
    conn.close()
    return df


# ─── BLACKLIST ────────────────────────────────────────────────────────────

def get_blacklist():
    conn = get_connection()
    rows = conn.execute("SELECT keyword FROM blacklist_keywords ORDER BY keyword").fetchall()
    conn.close()
    return [r[0] for r in rows]


def add_blacklist_keyword(keyword):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO blacklist_keywords (keyword) VALUES (?)", (keyword,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def remove_blacklist_keyword(keyword):
    conn = get_connection()
    conn.execute("DELETE FROM blacklist_keywords WHERE keyword = ?", (keyword,))
    conn.commit()
    conn.close()


def reset_blacklist():
    conn = get_connection()
    conn.execute("DELETE FROM blacklist_keywords")
    conn.executemany(
        "INSERT INTO blacklist_keywords (keyword) VALUES (?)",
        [(kw,) for kw in DEFAULT_BLACKLIST]
    )
    conn.commit()
    conn.close()
