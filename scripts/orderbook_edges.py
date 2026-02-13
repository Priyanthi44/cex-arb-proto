import ccxt
from collections import defaultdict
from time import sleep

EXCHANGE_ID = "kraken"
TRADE_SIZE_QUOTE = 200.0  # e.g., 200 GBP worth per leg (tune later)
TAKER_FEE_OVERRIDE = None
MAX_MARKETS = 80          # limit calls (Kraken rate limits)
SLEEP_S = 0.25            # be gentle with API

def get_taker_fee(ex):
    if TAKER_FEE_OVERRIDE is not None:
        return float(TAKER_FEE_OVERRIDE)
    fee = ex.fees.get("trading", {}).get("taker", None)
    return float(fee) if fee is not None else 0.001

def sell_base_for_quote_using_bids(bids, base_amount):
    """
    You have base_amount of BASE, you sell into bids to receive QUOTE.
    bids: list of [price, amount_base]
    returns quote_received
    """
    remaining = base_amount
    quote_out = 0.0
    for level in bids:
        price, amt_base = level[0], level[1]
        take = min(remaining, amt_base)
        quote_out += take * price
        remaining -= take
        if remaining <= 1e-12:
            return quote_out
    return None  # not enough depth

def buy_base_using_quote_using_asks(asks, quote_amount):
    """
    You have quote_amount of QUOTE, you buy BASE from asks.
    asks: list of [price, amount_base]
    returns base_received
    """
    remaining_quote = quote_amount
    base_out = 0.0
    for level in asks:
        price, amt_base = level[0], level[1]
        cost = amt_base * price
        if cost <= remaining_quote:
            base_out += amt_base
            remaining_quote -= cost
        else:
            base_out += remaining_quote / price
            remaining_quote = 0.0
            return base_out
    return None  # not enough depth

def build_edges_from_orderbooks(ex, symbols, trade_size_quote):
    fee = get_taker_fee(ex)
    fee_mult = 1.0 - fee
    edges = defaultdict(dict)

    for i, sym in enumerate(symbols, 1):
        try:
            ob = ex.fetch_order_book(sym, limit=50)
        except Exception:
            continue
        sleep(SLEEP_S)

        bids = ob.get("bids") or []
        asks = ob.get("asks") or []
        if not bids or not asks:
            continue

        base, quote = sym.split("/")

        # We define conversion edges using a consistent "quote-sized trade":
        # 1) quote -> base: spend trade_size_quote quote on asks, get base_out
        base_out = buy_base_using_quote_using_asks(asks, trade_size_quote)
        if base_out:
            # rate: how many base units per 1 quote unit
            rate_q_to_b = (base_out / trade_size_quote) * fee_mult
            edges[quote][base] = max(edges[quote].get(base, 0), rate_q_to_b)

        # 2) base -> quote: we need a base_amount equivalent to trade_size_quote at mid-ish price
        mid = (bids[0][0] + asks[0][0]) / 2.0
        base_amount = trade_size_quote / mid
        quote_out = sell_base_for_quote_using_bids(bids, base_amount)
        if quote_out:
            rate_b_to_q = (quote_out / base_amount) * fee_mult  # quote per 1 base
            edges[base][quote] = max(edges[base].get(quote, 0), rate_b_to_q)

    return edges

def best_triangles(edges, assets):
    res = []
    checked = 0
    for A in assets:
        for B, rAB in edges.get(A, {}).items():
            for C, rBC in edges.get(B, {}).items():
                rCA = edges.get(C, {}).get(A)
                if not rCA:
                    continue
                checked += 1
                final = rAB * rBC * rCA
                profit_pct = (final - 1.0) * 100.0
                res.append((profit_pct, A, B, C, final))
    print(f"triangles_checked={checked} triangles_kept={len(res)}")
    print(f"triangles_found={len(res)}")
    res.sort(reverse=True, key=lambda x: x[0])
    return res

def main():
    ex = getattr(ccxt, EXCHANGE_ID)({"enableRateLimit": True})
    ex.load_markets()

    # Keep it manageable: choose spot, active, and common quotes
    quotes = {"USD", "USDT", "EUR", "GBP"}
    syms = []
    for s, m in ex.markets.items():
        if "/" not in s:
            continue
        if m.get("active") is False:
            continue
        if m.get("spot") is False:
            continue
        base = m.get("base"); quote = m.get("quote")
        if quote in quotes:
            syms.append(s)

    syms = syms[:MAX_MARKETS]
    print(f"Using {len(syms)} markets with order books (limit={MAX_MARKETS})")

    edges = build_edges_from_orderbooks(ex, syms, TRADE_SIZE_QUOTE)

    assets = sorted(set(list(edges.keys()) + [v for u in edges for v in edges[u].keys()]))
    tris = best_triangles(edges, assets)

    print("\nTop 15 triangles (order-book effective rates):")
    for p, A, B, C, f in tris[:15]:
        print(f"{A} -> {B} -> {C} -> {A} | profit={p:+.4f}% | final={f:.6f}")

if __name__ == "__main__":
    main()
