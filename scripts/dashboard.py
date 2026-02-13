import sqlite3
import pandas as pd
import streamlit as st

DB = "data/market.db"

st.set_page_config(page_title="CEX Dislocation Monitor", layout="wide")
st.title("Kraken↔Binance Dislocation Monitor")
st.caption("Reads from data/market.db (ticks, divergences, alerts).")

conn = sqlite3.connect(DB)

col1, col2, col3 = st.columns(3)
with col1:
    top_n = st.slider("Top N divergences", 10, 200, 50, 10)
with col2:
    min_div = st.slider("Min divergence %", 0.0, 5.0, 0.3, 0.05)
with col3:
    limit_alerts = st.slider("Recent alerts to show", 5, 200, 50, 5)

# Latest run timestamp (if any)
ts_latest = conn.execute("SELECT MAX(ts_ms) FROM divergences").fetchone()[0]
if not ts_latest:
    st.warning("No divergences in DB yet. Run: python scripts/divergence_monitor.py")
    st.stop()

st.subheader("Top divergences (latest snapshot)")
q_div = """
SELECT ts_ms, pair, ex_a, ex_b, div_pct, mid_a, mid_b, spread_bps_a, spread_bps_b
FROM divergences
WHERE ts_ms = ?
ORDER BY div_pct DESC
LIMIT ?
"""
df = pd.read_sql_query(q_div, conn, params=(ts_latest, top_n))
df = df[df["div_pct"] >= min_div]
st.dataframe(df, use_container_width=True)

st.subheader("Recent alerts")
q_alerts = """
SELECT ts_ms, kind, severity, message
FROM alerts
ORDER BY ts_ms DESC
LIMIT ?
"""
df_a = pd.read_sql_query(q_alerts, conn, params=(limit_alerts,))
st.dataframe(df_a, use_container_width=True)

st.subheader("Recent tick sample")
q_ticks = """
SELECT ts_ms, exchange, symbol, bid, ask, mid, spread_bps
FROM ticks
ORDER BY ts_ms DESC
LIMIT 200
"""
df_t = pd.read_sql_query(q_ticks, conn)
st.dataframe(df_t, use_container_width=True)

conn.close()
