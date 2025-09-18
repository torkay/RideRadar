# RideRadar Runbook

## Single-pass ingest

Run a lightweight scrape and persistence pass per specified vendors (best-effort):

- `python engine/schedule_loop.py --vendors pickles,manheim,gumtree --limit 5 --once`

Orchestrator (single vendor → normalize → pipeline):

- `python -m engine.scraper.orchestrator --vendor pickles --limit 10`
- `python -m engine.scraper.orchestrator --vendor ebay --limit 10`
- `python -m engine.scraper.orchestrator --vendor gumtree --make Toyota --model Corolla --state NSW --limit 5 --debug`

Playwright fallback (optional, dev):

- `pip install playwright && python -m playwright install chromium`
- Enable fallback on Gumtree: `export USE_PLAYWRIGHT=true`
- Headful browser in dev (default): `export PW_HEADLESS=false`
  - Persistent profile and manual assist (first-run):
    - `export PW_PROFILE_DIR=~/.rideradar/pw-gumtree`
    - `export PW_ASSIST=true`
    - Run: `python -m engine.scraper.orchestrator --vendor gumtree --make Toyota --model Corolla --state NSW --limit 5 --debug`

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
