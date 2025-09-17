# RideRadar

RideRadar is an engine for discovering and comparing used-vehicle listings across multiple sources. It ingests co-operative vendors, normalises to a unified schema, de-duplicates, and exposes a small API for search and health/status. The design favours stability, compliance, and a clean path to partnerships. For non-cooperative sources, use deep links and client-side helpers (no server-side scraping).

## At a glance
- **Focus:** AU vehicle listings; unified data model + API
- **Engine:** FastAPI, Python 3.11
- **Storage:** Postgres (psycopg) **or** Supabase REST (supabase-py)
- **Ingest:** vendor scrapers, normalisation, fingerprint de-dupe
- **Health:** per-vendor (/healthz), simple circuit breaker
- **Scheduler:** minimal CLI to run vendors on demand

## How it works
- Scrapers live in `engine/scraper/vendors/` and return lightweight listing summaries.
- The pipeline (`engine/scraper/pipeline.py`) normalises and upserts via `DB_BACKEND`:
  - `postgres` - direct Postgres (psycopg) with unique constraints
  - `supabase_api` - Supabase REST (supabase-py)
- The API (`engine/api/app.py`) provides:
  - `GET /listings` - filters: `make`, `model`, `state`, `price_min`, `price_max`, `limit`
  - `GET /listings/{id}` - UUID
  - `GET /healthz` - snapshot of vendor status

## Quick start

### 1) Prereqs
- Python 3.11
- Virtual environment recommended

```bash
# from repo root
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r engine/api/requirements.txt
```

### 2) Environment (pick ONE backend)
See `engine/.env.example` for reference.

**Option A — Postgres (direct):**
```env
DB_BACKEND=postgres
SUPABASE_DB_URL=postgresql://<user>:<pass>@<host>:5432/<db>?sslmode=require
```

**Option B — Supabase REST:**
```env
DB_BACKEND=supabase_api
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>
```

> Don't set both backends at once. Choose A **or** B.

### 3) Run the API
```bash
uvicorn engine.api.app:app --port 8000
```

### 4) Sanity checks
```bash
# health
curl http://localhost:8000/healthz

# sample listings
curl 'http://localhost:8000/listings?limit=5'
```

### 5) Smoke tests
```bash
# Postgres path
python -m engine.scripts.db_smoke

# Supabase REST path
python -m engine.scripts.api_smoke

# Vendor-only (no DB write)
python -m engine.scripts.vendor_smoke --vendor pickles --limit 3
```

More examples: `engine/API_SMOKE.md`, `engine/RUNBOOK.md`.

## Project direction
**Near-term**
- Harden vendor scrapers and normalisation
- Saved searches (skeleton) + basic deal scoring for co-operative sources
- Deep-link builders for non-cooperative sources; optional client-side helper

**Longer-term**
- Authorised data partnerships
- Expanded metrics + alerting

## Compliance & guardrails
- Respect `robots.txt` and vendor ToS; throttle + back-off
- Don't persist content from non-cooperative sources
- Abort on CAPTCHA/blocks; trip breaker; report via `/healthz`
- Secrets via environment only

## Repo layout (engine)
- `engine/api/` — FastAPI app, routes, models
- `engine/db/` — Postgres client + Supabase REST client
- `engine/scraper/` — vendor scrapers, pipeline
- `engine/runtime/` — vendor status tracker
- `engine/scripts/` — smokes and small CLIs

> This repo is the engine. Frontend lives elsewhere.

## Status
Active development. Contributions welcome. Scope stays lean while the engine and interfaces stabilise. Open focused issues/PRs.