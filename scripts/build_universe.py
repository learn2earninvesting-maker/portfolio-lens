#!/usr/bin/env python3
"""
build_universe.py  —  nightly fundamentals + 200-EMA feed for Portfolio Lens.

Reads universe.txt (one NSE base symbol per line), fetches from Yahoo Finance:
  - 200-day EMA   (computed from 1y of daily closes)
  - PE, ROE, D/E  (quoteSummary modules)
  - salesCagr     (proxy: YoY revenue growth — labelled honestly)
Writes data/universe.json keyed by base symbol.

Anti-fabrication: any field Yahoo doesn't return is simply left out
(the app renders it NOT DISCLOSED). A field-level MERGE with the existing
file means good values survive a night when Yahoo is flaky, and hand-seeded
values (e.g. promoter holding, which Yahoo doesn't cover for Indian names)
are preserved unless a fresh value replaces them.

Runs in GitHub Actions (open internet). Not meant for the offline sandbox.
"""
import json, time, sys, datetime, os, urllib.request, urllib.error

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIV   = os.path.join(ROOT, "universe.txt")
OUT    = os.path.join(ROOT, "data", "universe.json")
UA     = "Mozilla/5.0 (compatible; PortfolioLens/1.0; +https://github.com)"
CHART  = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1y&interval=1d"
QSUM   = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules=financialData,summaryDetail,defaultKeyStatistics"
DELAY  = 0.7          # polite gap between tickers (seconds)
RETRIES= 3

def http_json(url):
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept":"application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            if attempt == RETRIES-1: return None
            time.sleep(1.5*(attempt+1))
    return None

def ema(vals, period=200):
    vals = [v for v in vals if isinstance(v,(int,float))]
    if len(vals) < period: return None
    k = 2/(period+1)
    e = sum(vals[:period])/period      # seed with SMA of first `period`
    for v in vals[period:]:
        e = v*k + e*(1-k)
    return round(e, 2)

def fetch_symbol(base):
    """Try NSE (.NS) then BSE (.BO). Returns (rec, exchange) or (None,None)."""
    for suffix in (".NS", ".BO"):
        ysym = base + suffix
        chart = http_json(CHART.format(sym=ysym))
        try:
            res = chart["chart"]["result"][0]
            closes = res["indicators"]["quote"][0]["close"]
        except (TypeError, KeyError, IndexError):
            continue
        rec = {}
        e200 = ema(closes)
        if e200 is not None: rec["ema200"] = e200

        qs = http_json(QSUM.format(sym=ysym))
        try:
            r = qs["quoteSummary"]["result"][0]
        except (TypeError, KeyError, IndexError):
            r = {}
        fin = r.get("financialData", {}) or {}
        sd  = r.get("summaryDetail", {}) or {}

        pe = (sd.get("trailingPE") or {}).get("raw")
        if pe is not None: rec["pe"] = round(pe, 2)

        roe = (fin.get("returnOnEquity") or {}).get("raw")
        if roe is not None: rec["roe"] = round(roe*100, 1)          # fraction -> %

        de = (fin.get("debtToEquity") or {}).get("raw")
        if de is not None: rec["de"] = round(de/100, 2)             # Yahoo % -> ratio

        rg = (fin.get("revenueGrowth") or {}).get("raw")
        if rg is not None: rec["salesCagr"] = round(rg*100, 1)      # YoY growth proxy

        if rec:
            rec["src"] = f"Yahoo {suffix[1:]} {datetime.date.today().isoformat()}"
            return rec, suffix[1:]
    return None, None

def load_existing():
    try:
        with open(OUT) as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def main():
    with open(UNIV) as f:
        syms = [l.strip().upper() for l in f if l.strip() and not l.startswith("#")]
    syms = sorted(set(syms))
    prev = load_existing()
    out  = {"_meta": {}}
    ok = stale = 0
    for i, base in enumerate(syms, 1):
        rec, exch = fetch_symbol(base)
        old = {k:v for k,v in (prev.get(base) or {}).items()}
        if rec:
            merged = {**old, **rec}           # fresh values win; keep seeded promoter etc.
            out[base] = merged; ok += 1
            tag = f"OK({exch})"
        elif old:
            old["stale"] = True
            out[base] = old; stale += 1
            tag = "stale-kept"
        else:
            tag = "no-data"
        print(f"[{i:>4}/{len(syms)}] {base:<14} {tag}", flush=True)
        time.sleep(DELAY)

    out["_meta"] = {
        "generated": datetime.datetime.utcnow().isoformat(timespec="seconds")+"Z",
        "count": sum(1 for k in out if k != "_meta"),
        "fresh": ok, "stale": stale,
        "note": "ema200=200-day EMA; pe; roe(%); de(debt/equity ratio); salesCagr(%)=YoY revenue growth proxy. "
                "Promoter holding is not on Yahoo for Indian names — preserved only where hand-seeded, else NOT DISCLOSED.",
        "source": "Yahoo Finance (query1/query2). Educational use.",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\nWrote {OUT}: {out['_meta']['count']} symbols ({ok} fresh, {stale} stale-kept)")

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        # validate EMA math on a synthetic ramp; EMA200 of 1..300 should trail the mean
        series = list(range(1, 301))
        print("EMA200 selftest ->", ema(series), "(expected ~ high-100s, below last value 300)")
    else:
        main()
