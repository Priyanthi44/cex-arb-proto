# cex-arb-proto

Prototype tools for:
- Building a directed FX/crypto conversion graph from CEX data (Kraken/Binance)
- Ranking cross-exchange price divergences (market anomaly monitoring)
- Logging ticks/divergences/alerts into SQLite (`data/market.db`)
- Triangle cycle scanning (prototype scripts)

## Project layout
cex-arb-proto/
src/
init.py
store.py # SQLite schema + insert helpers
scripts/
divergence_monitor.py # Kraken↔Binance divergence + DB logging
tri_arb.py # prototype: ticker-based triangle scan
orderbook_edges.py # prototype: orderbook-based edges + triangle scan
data/
market.db # SQLite db (created at runtime)
requirements.txt
README.md


## Prerequisites

- Python 3.9+ (3.11+ recommended)
- macOS/Linux/Windows supported

## Setup

Create and activate a virtual environment, then install dependencies:


python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

## Quick sanity check:

python -c "import ccxt; print('ccxt', ccxt.__version__)"
Run: Kraken ↔ Binance divergence monitor (writes SQLite)
python scripts/divergence_monitor.py
his will:

fetch tickers for Kraken and Binance

compute common-pair mid-price divergence

print top divergences

write to data/market.db tables:

ticks

divergences

alerts (when top divergence crosses threshold)

Inspect the DB

## List tables:

python - << 'PY'
import sqlite3
conn = sqlite3.connect("data/market.db")
print(conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
conn.close()
PY

## Row counts:
python - << 'PY'
import sqlite3
conn = sqlite3.connect("data/market.db")
for t in ["ticks","divergences","alerts"]:
    print(t, conn.execute(f"select count(*) from {t}").fetchone()[0])
conn.close()
PY
## Run: prototype triangle scanners
Ticker-based triangles (fast, optimistic):
python scripts/tri_arb.py
Orderbook-based edges/triangles (slower, more realistic):
python scripts/orderbook_edges.py
Common issues (macOS)
command not found: python or pip

Use python3 and python -m pip:
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
Database shows no such table: ticks

This typically means the schema hasn't been created in that DB file yet.
Run:python - << 'PY'
from src.store import connect
conn = connect()
print("schema ensured")
conn.close()
PY
Then re-run the monitor.

## Notes / disclaimers

This project is for monitoring and research. It is not a trading bot and does not guarantee profit.

Market data can be stale, incomplete, or rate-limited depending on venue and network conditions.
