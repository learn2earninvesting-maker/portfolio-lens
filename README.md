# Portfolio Lens

Upload a holdings file from **any Indian broker** (Zerodha Console, Groww, Upstox, Angel One, ICICI Direct, or a generic sheet) and see allocation, concentration, sector exposure and P&L. **Everything is parsed in the browser — the file is never uploaded.**

Live at: `https://learn2earninvesting-maker.github.io/portfolio-lens/` *(after you enable Pages)*

## How it's built

- **`index.html`** — the whole app. Client-side parser (SheetJS) + structural engines (allocation, weight bands, sector exposure, HHI/top-5 concentration, P&L) + Quality tab. No backend, no accounts.
- **`data/universe.json`** — the fundamentals feed the Quality tab reads: `ema200`, `pe`, `roe`, `de`, `salesCagr` per symbol. Ships pre-seeded with real sourced values for the starter universe.
- **`universe.txt`** — the list of NSE symbols to cover (one per line). Add more to broaden coverage.
- **`scripts/build_universe.py`** — the nightly fetcher.
- **`.github/workflows/build-universe.yml`** — runs the fetcher on a schedule and commits a fresh `data/universe.json`.

The two halves are deliberately separate. The **structural** analysis needs nothing but the user's file and always works, privately. The **fundamentals + 200-EMA** half is the feed — where a symbol or field isn't covered, the app shows **NOT DISCLOSED** rather than guessing.

## Deploy (once)

1. Push this folder to a repo, e.g. `learn2earninvesting-maker/portfolio-lens`.
2. **Settings → Pages** → deploy from `main`, root. The site is live in ~1 min.
3. **Settings → Actions → General** → Workflow permissions → **Read and write** (lets the job commit the refreshed feed).
4. **Actions** tab → *Build fundamentals feed* → **Run workflow** once to confirm it works. After that it runs itself Mon–Fri early morning IST.

## The nightly feed

`build_universe.py` reads `universe.txt` and, per symbol, pulls from Yahoo Finance:

- **200-day EMA** — computed from a year of daily closes (reliable).
- **PE, ROE, D/E, revenue growth** — from Yahoo's summary modules where available.

It **merges field-by-field** with the existing file, so a value survives a night when Yahoo is flaky (kept and marked `stale`), and hand-seeded fields Yahoo can't provide are preserved.

### Honest coverage note

Yahoo covers prices (and therefore the 200-EMA) well for `.NS`/`.BO` tickers, and PE/ROE/D-E for most. It does **not** carry **promoter holding** for Indian companies, and `salesCagr` is a **YoY revenue-growth proxy**, not a true 5-year CAGR. Those fields stay NOT DISCLOSED unless seeded manually. The scoring engine drops any missing input and lowers the confidence flag accordingly — it never fabricates.

## Broaden the universe

Append plain NSE symbols to `universe.txt` (one per line) — e.g. the NIFTY 500. Roughly 500 names take ~12 minutes per run at the polite request rate. Symbols not in the list simply render NOT DISCLOSED in the Quality tab for users who hold them.

## Not investment advice

Structural, educational analysis of a user's own sheet. Not the recommendation of a SEBI-registered adviser, and no price targets are invented.
