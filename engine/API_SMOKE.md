# RideRadar API Smoke

Prereqs
- Set `SUPABASE_DB_URL` to your Postgres connection string.
- Or set Supabase REST envs to use supabase-py instead of psycopg:
  - `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
  - `DB_BACKEND=supabase_api`
- Optional: set `PROD_ORIGIN` for CORS (adds to allowed origins).
- Ensure dependencies are installed for FastAPI and psycopg.

Run
- From `engine`: `uvicorn api.app:app --port 8000`
- Supabase API smoke: `python -m engine.scripts.api_smoke`

Quick checks
- Health:
  - `curl 'http://localhost:8000/healthz'`
- List latest 5:
  - `curl 'http://localhost:8000/listings?limit=5'`
- Filter by make/model:
  - `curl 'http://localhost:8000/listings?make=Toyota&model=Corolla&limit=5'`
- Filter by state and price band:
  - `curl 'http://localhost:8000/listings?state=NSW&price_min=10000&price_max=30000&limit=5'`
- Fetch by id (UUID):
  - `curl 'http://localhost:8000/listings/00000000-0000-0000-0000-000000000000'`

Notes
- `DB_BACKEND` defaults to `postgres`. `engine/scraper/pipeline.save_normalized()` no-ops for non‑postgres backends (Mongo path reserved).
- The API queries the `listings` table and orders by `last_seen desc`.
