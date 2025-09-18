# RideRadar Runbook

## Single-pass ingest

Run a lightweight scrape and persistence pass per specified vendors (best-effort):

- `python engine/schedule_loop.py --vendors pickles,manheim,gumtree --limit 5 --once`

Orchestrator (single vendor → normalize → pipeline):

- `python -m engine.scraper.orchestrator --vendor pickles --limit 10`
- `python -m engine.scraper.orchestrator --vendor ebay --limit 10`
- `python -m engine.scraper.orchestrator --vendor gumtree --make Toyota --model Corolla --state NSW --limit 5 --debug`
### Pickles (HTTPX, SSR)

- `python -m engine.scraper.orchestrator --vendor pickles --make Toyota --model Corolla --state QLD --query "toyota corolla" --salvage non-salvage --buy-now --wovr none --limit 120 --page 1 --debug`
  - Prints the exact Pickles URL and saves snapshot to `engine/storage/snapshots/pickles_page1.html`
- `python -m engine.scraper.orchestrator --vendor pickles --state NT --query "toyota corolla" --salvage both --page 1 --debug`
- `python -m engine.scraper.orchestrator --vendor pickles --make Toyota --model Hilux --state NSW --suburb "wagga wagga" --query "toyota corolla" --salvage salvage --wovr repairable --debug`

Debug/troubleshooting notes:
- Expect lines like: `DEBUG pickles URL: ...`
- Then: `DEBUG pickles status=200 len=... url=...` and a preview line.
- Tile counts: `DEBUG pickles tiles: primary=N fallback_href=M ldjson=K kept=T` and `DEBUG pickles kept_real=R dropped_category=C [hydrated=H]`.
- Use `--dry-run` to print the first 3 normalized rows without upserting.

Examples:

1) Dry-run search only

```
python -m engine.scraper.orchestrator --vendor pickles --make Toyota --model Corolla --state QLD --page 1 --limit 20 --debug --dry-run
```

2) Hydrated details (fills missing title/price)

```
python -m engine.scraper.orchestrator --vendor pickles --state NT --query "toyota corolla" --salvage both --page 1 --debug --dry-run --hydrate-details
```

Price-first defaults and including unpriced:

- Defaults (require price → auto Buy Now filter):

```
python -m engine.scraper.orchestrator --vendor pickles --state NT --query "toyota corolla" --page 1 --limit 10 --debug --dry-run
```
- Yields Buy Now listings with numeric prices; summary line reflects the current DB backend.

- Include unpriced (any sale method):

```
python -m engine.scraper.orchestrator --vendor pickles --state NT --query "toyota corolla" --page 1 --limit 10 --debug --dry-run --buy-method any --no-require-price --include-unpriced --hydrate-details
```
- Keeps proposed/auction/tender rows (price may be None) and logs detected `sale_method` when hydration is enabled.

- Include “Enquire Now” listings (unpriced allowed):

```
python -m engine.scraper.orchestrator --vendor pickles --state NT --query "toyota corolla" --page 1 --limit 10 --hydrate-details --allow-enquire --no-require-price --include-unpriced --debug --dry-run
```
 - Preserves rows with `sale_method='enquire'` and `price=None`; summary shows `sale_method_enquire`/`enquire_unpriced` counters.

Pickles scraper notes:
- To surface `sale_method` at the top level, export `LISTINGS_ENABLE_SALE_METHOD_COLUMN=true` and add the column via `ALTER TABLE listings ADD COLUMN sale_method text;` (optional).
### Autotrader (HTTPX, SSR)

- `python -m engine.scraper.orchestrator --vendor autotrader --make Toyota --model Corolla --state QLD --limit 5 --debug`
  - Saves snapshot to `engine/storage/snapshots/autotrader_page1.html` when `--debug` is set.

Playwright fallback (optional, dev):

- `pip install playwright && python -m playwright install chromium`
- Enable fallback on Gumtree: `export USE_PLAYWRIGHT=true`
- Headful browser in dev (default): `export PW_HEADLESS=false`
  - Persistent profile and manual assist (first-run):
    - `export PW_PROFILE_DIR=~/.rideradar/pw-gumtree`
    - `export PW_ASSIST=true`
  - Run: `python -m engine.scraper.orchestrator --vendor gumtree --make Toyota --model Corolla --state NSW --limit 5 --debug`
### Gumtree (Playwright session)

- Force Playwright and skip HTTPX:
  - `python -m engine.scraper.orchestrator --vendor gumtree --make Toyota --model Corolla --state NSW --limit 5 --force-pw --debug`
- Optional manual assist for first run:
  - `export PW_ASSIST=true` then run the command above; follow the prompt to dismiss banners/challenges and press ENTER.
- Persistent profile: set `PW_PROFILE_DIR` (default `~/.rideradar/pw-gumtree`)
- Headless: set `PW_HEADLESS=true` (default false)

eBay with keywords and debug (saves snapshot):

- `python -m engine.scraper.orchestrator --vendor ebay --make Toyota --model Corolla --limit 5 --debug`
  - Snapshot saved to `engine/storage/snapshots/ebay_page1.html`

Notes:
- `--once` runs a single pass (default); omit to reuse later when loops are added.
- If `SUPABASE_DB_URL` is not set, results are fetched but not persisted; vendor status is still updated.

## Health check

Start the API and query health:

- `uvicorn engine.api.app:app --port 8000`
- `curl http://localhost:8000/healthz`

The response includes `ok`, server `time` (UTC Z), and per-vendor status snapshot.
