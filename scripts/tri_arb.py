import ccxt
from collections import defaultdict

EXCHANGE_ID = "kraken"          # try: kraken, binance, coinbase, okx
QUOTE_CURRENCIES = {"USD", "USDT", "EUR", "GBP"}
TOP_K_EDGES_PER_NODE = 40
TAKER_FEE_OVERRIDE = None
MIN_PROFIT_PCT = -100.0  # show everything
MAX_ASSETS = 120         # optional: more coverage

def get_taker_fee(ex):
    if TAKER_FEE_OVERRIDE is not None:
        return float(TAKER_FEE_OVERRIDE)
    try:
        fee = ex.fees.get("trading", {}).get("taker", None)
        return float(fee) if fee is not None else 0.001
    except Exception:
        return 0.001

def build_edges(ex, tickers, taker_fee):
    edges = defaultdict(dict)
    assets = set()
    fee_mult = 1.0 - taker_fee

    for symbol, m in ex.markets.items():
        if m.get("active") is False:
            continue
        if m.get("spot") is False:
            continue
        if "/" not in symbol:
            continue

        base = m.get("base")
        quote = m.get("quote")
        if not base or not quote:
            continue
        if quote not in QUOTE_CURRENCIES:
            continue

        t = tickers.get(symbol)
        if not t:
            continue
        bid = t.get("bid")
        ask = t.get("ask")
        if not bid or not ask or bid <= 0 or ask <= 0:
            continue

        # Sell base -> quote at bid
        edges[base][quote] = max(edges[base].get(quote, 0), bid * fee_mult)
        # Buy base using quote at ask => quote -> base is 1/ask
        edges[quote][base] = max(edges[quote].get(base, 0), (1.0 / ask) * fee_mult)

        assets.add(base); assets.add(quote)

    return edges, sorted(assets)

def prune(edges, top_k):
    pruned = defaultdict(dict)
    for u, nbrs in edges.items():
        best = sorted(nbrs.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        for v, r in best:
            pruned[u][v] = r
    return pruned

def best_triangles(edges, assets, min_profit_pct):
    res = []
    for A in assets:
        for B, rAB in edges.get(A, {}).items():
            for C, rBC in edges.get(B, {}).items():
                rCA = edges.get(C, {}).get(A)
                if not rCA:
                    continue
                final_amt = rAB * rBC * rCA
                profit_pct = (final_amt - 1.0) * 100.0
                if profit_pct >= min_profit_pct:
                    res.append((profit_pct, A, B, C, final_amt))
    res.sort(reverse=True, key=lambda x: x[0])
    return res

def main():
    ex = getattr(ccxt, EXCHANGE_ID)({"enableRateLimit": True})
    ex.load_markets()

    taker_fee = get_taker_fee(ex)
    print(f"Exchange={EXCHANGE_ID}  taker_fee≈{taker_fee*100:.3f}%")

    tickers = ex.fetch_tickers()
    edges, assets = build_edges(ex, tickers, taker_fee)
    assets = assets[:MAX_ASSETS]
    edges = prune(edges, TOP_K_EDGES_PER_NODE)

    print(f"assets={len(assets)}  nodes_with_edges={len(edges)}")
    tris = best_triangles(edges, assets, MIN_PROFIT_PCT)

    print("\nTop 15 triangles:")
    for p, A, B, C, f in tris[:15]:
        print(f"{A} -> {B} -> {C} -> {A} | profit={p:+.4f}% | fal={f:.6f}")

if __name__ == "__main__":
    main()
