import sqlite3
from pathlib import Path

DB_PATH = Path("data/market.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS ticks (
  ts_ms INTEGER NOT NULL,
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  base TEXT,
  quote TEXT,
  bid REAL,
  ask REAL,
  mid REAL,
  spread_bps REAL,
  PRIMARY KEY (ts_ms, exchange, symbol)
);

CREATE TABLE IF NOT EXISTS divergences (
  ts_ms INTEGER NOT NULL,
  pair TEXT NOT NULL,
  ex_a TEXT NOT NULL,
  ex_b TEXT NOT NULL,
  mid_a REAL NOT NULL,
  mid_b REAL NOT NULL,
  div_pct REAL NOT NULL,
  spread_bps_a REAL,
  spread_bps_b REAL
);

CREATE TABLE IF NOT EXISTS alerts (
  ts_ms INTEGER NOT NULL,
  kind TEXT NOT NULL,
  severity TEXT NOT NULL,
  message TEXT NOT NULL
);
"""

def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.executescript(SCHEMA)
    conn.commit()  # <-- ensures schema is persisted immediately
    return conn

def insert_ticks(conn: sqlite3.Connection, rows):
    conn.executemany(
        """
        INSERT OR IGNORE INTO ticks
        (ts_ms, exchange, symbol, base, quote, bid, ask, mid, spread_bps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

def insert_divergences(conn: sqlite3.Connection, rows):
    conn.executemany(
        """
        INSERT INTO divergences
        (ts_ms, pair, ex_a, ex_b, mid_a, mid_b, div_pct, spread_bps_a, spread_bps_b)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

def insert_alert(conn: sqlite3.Connection, ts_ms: int, kind: str, severity: str, message: str):
    conn.execute(
        "INSERT INTO alerts (ts_ms, kind, severity, message) VALUES (?, ?, ?, ?)",
        (ts_ms, kind, severity, message),
    )
