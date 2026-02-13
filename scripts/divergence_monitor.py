import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.store import connect, insert_ticks, insert_divergences, insert_alert

import time
import ccxt

EXCHANGES = ["kraken", "binance"]
QUOTES = {"USDT", "USD", "EUR", "GBP"}  # reduce noise
TOP_N = 20

def safe_fetch_tickers(ex):
    try:
        return ex.fetch_tickers()
    except Exception:
        # fallback: fetch per symbol (slower); keep small if needed
        out = {}
        for s in list(ex.markets.keys())[:300]:
            try:
                out[s] = ex.fetch_ticker(s)
            except Exception:
                continue
        return out


def normalize_markets(ex):
    """
    Build mapping: (base, quote) -> symbol
    Only for spot & active.
    """
    mapping = {}
    for sym, m in ex.markets.items():
        if "/" not in sym:
            continue
        if m.get("active") is False:
            continue
        if m.get("spot") is False:
            continue
        base = m.get("base")
        quote = m.get("quote")
        if not base or not quote:
            continue
        if quote not in QUOTES:
            continue
        mapping[(base, quote)] = sym
    return mapping

def mid_from_ticker(t):
    bid = t.get("bid")
    ask = t.get("ask")
    if not bid or not ask or bid <= 0 or ask <= 0:
        return None, None, None
    mid = (bid + ask) / 2.0
    spread_bps = (ask - bid) / mid * 10_000.0
    return mid, bid, ask, spread_bps

def main():
    ex_objs = {}
    tickers = {}
    market_maps = {}
    rows = []
    ts = int(time.time() * 1000)
    conn = connect()
    print("DB ready:", "data/market.db")

    for eid in EXCHANGES:
        ex = getattr(ccxt, eid)({"enableRateLimit": True})
        ex.load_markets()
        ex_objs[eid] = ex
        market_maps[eid] = normalize_markets(ex)
        tickers[eid] = safe_fetch_tickers(ex)
        tick_rows = []
        
        for (base, quote), sym in list(market_maps[eid].items())[:500]:
            t = tickers[eid].get(sym)
            if not t:
                continue
            bid = t.get("bid"); ask = t.get("ask")
            if not bid or not ask or bid <= 0 or ask <= 0:
                continue
            mid = (bid + ask) / 2.0
            spread_bps = (ask - bid) / mid * 10_000.0
            tick_rows.append((ts, eid, sym, base, quote, bid, ask, mid, spread_bps))

        insert_ticks(conn, tick_rows)
        conn.commit()

        print(f"{eid}: markets={len(ex.markets)} tickers={len(tickers[eid])}")

    # common (base, quote)
    common = set(market_maps[EXCHANGES[0]].keys())
    for eid in EXCHANGES[1:]:
        common &= set(market_maps[eid].keys())

    

    a, b = EXCHANGES[0], EXCHANGES[1]
    for (base, quote) in common:
        sym_a = market_maps[a][(base, quote)]
        sym_b = market_maps[b][(base, quote)]

        ta = tickers[a].get(sym_a)
        tb = tickers[b].get(sym_b)
        if not ta or not tb:
            continue

        mid_a, bid_a, ask_a, spread_a = mid_from_ticker(ta)
        mid_b, bid_b, ask_b, spread_b = mid_from_ticker(tb)
        if mid_a is None or mid_b is None:
            continue

        lo = min(mid_a, mid_b)
        hi = max(mid_a, mid_b)
        div_pct = (hi - lo) / lo * 100.0

        rows.append({
            "ts_ms": ts,
            "pair": f"{base}/{quote}",
            f"{a}_mid": mid_a,
            f"{b}_mid": mid_b,
            "div_pct": div_pct,
            f"{a}_spread_bps": spread_a,
            f"{b}_spread_bps": spread_b,
            f"{a}_symbol": sym_a,
            f"{b}_symbol": sym_b,
        })

    rows.sort(key=lambda r: r["div_pct"], reverse=True)
    if rows and rows[0]["div_pct"] > 0.3:
        msg = f'TOP divergence {rows[0]["pair"]}: {rows[0]["div_pct"]:.3f}% ({a} vs {b})'
        insert_alert(conn, ts, "divergence", "high", msg)
        conn.commit()


    div_rows = []
    for r in rows:
        div_rows.append((
            r["ts_ms"],
            r["pair"],
            a, b,
            r[f"{a}_mid"],
            r[f"{b}_mid"],
            r["div_pct"],
            r[f"{a}_spread_bps"],
            r[f"{b}_spread_bps"],
        ))

    insert_divergences(conn, div_rows)
    conn.commit()

    print(f"\nCommon pairs={len(rows)} | Top {TOP_N} divergences ({a} vs {b}):")
    for r in rows[:TOP_N]:
        print(
            f'{r["pair"]:<12} div={r["div_pct"]:+.3f}% | '
            f'{a}_mid={r[f"{a}_mid"]:.8g} ({r[f"{a}_spread_bps"]:.1f} bps) | '
            f'{b}_mid={r[f"{b}_mid"]:.8g} ({r[f"{b}_spread_bps"]:.1f} bps)'
        )

if __name__ == "__main__":
    main()
