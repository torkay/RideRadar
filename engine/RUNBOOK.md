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
