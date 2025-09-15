RideRadar — Agent Context & MVP Build Sheet

Purpose

Build a minimum viable vehicle‑listing aggregator for Australia that ingests cooperative sources, normalizes to a unified schema, de‑dupes, exposes a query API, and lays the groundwork for saved‑search alerts. Avoid ToS friction by using deep‑links for protected sources (Carsales, Facebook Marketplace) rather than copying their content.

Non‑Goals & Compliance
	•	Do not persist content from Carsales or Facebook Marketplace.
	•	Respect robots.txt and vendors’ ToS; throttle and backoff aggressively.
	•	Marketplace access is opt‑in, user‑session only; no headless credentials storage.
	•	Abort on CAPTCHA/blocked states; trip a per‑vendor circuit breaker and report via /healthz.

MVP Scope (what “done” means)
	1.	Scrapers (ingest): Pickles AU, Manheim AU, Gumtree Cars, Autotrader AU.
	•	Capability: search (filters) → listing summaries; fetch listing details when needed.
	2.	Normalization to a unified Listing model; de‑dupe across vendors.
	3.	MongoDB persistence with unique indexes and incremental updater.
	4.	API (FastAPI): GET /listings, GET /listings/{id}, GET /healthz.
	5.	Scheduler: fresh/warm/cold queues with backoff and last‑seen markers.
	6.	SavedSearch & Alerts (skeleton): create/read saved searches; evaluation job computes matches + deal score; email transport can be stubbed.
	7.	Deep‑links: Builders for Carsales + FB Marketplace that pre‑fill filters and send the user off‑site.

Architecture (high‑level)
	•	engine/scraper/vendors/: per‑site modules implementing VendorScraper.
	•	engine/scraper/src_scraper.py: orchestrates fan‑out, normalization, upserts.
	•	engine/scraper/mongodb_handler.py: db client, indexes, upsert helpers.
	•	engine/api/: FastAPI app, Pydantic models, routes.
	•	engine/schedule_loop.py: runs search and refresh jobs per queue.
	•	engine/alerts/: saved search models + evaluator + email stub.

Vendor Contract

from typing import Iterable, Protocol, Dict, Any, Optional
from datetime import datetime

class VendorScraper(Protocol):
    name: str  # vendor key, e.g. "pickles"

    def search(self, query: Dict[str, Any], *, since: Optional[datetime] = None) -> Iterable[Dict[str, Any]]:
        """Yield raw listing dicts from vendor search pages (newest first)."""

    def fetch_listing(self, source_id: str) -> Dict[str, Any]:
        """Return raw listing detail by vendor id if needed; may no‑op for some vendors."""

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Map raw vendor fields to unified Listing schema (see below)."""

Listing Schema (Pydantic v2 sketch)

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal
from datetime import datetime

class Media(BaseModel):
    thumb: Optional[HttpUrl] = None
    gallery: List[HttpUrl] = []

class Location(BaseModel):
    state: Optional[str] = None
    postcode: Optional[str] = None
    suburb: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class Seller(BaseModel):
    type: Optional[Literal['dealer','private','auction']] = None
    dealer_name: Optional[str] = None
    abn: Optional[str] = None
    phone_masked: Optional[str] = None

class Listing(BaseModel):
    id: Optional[str] = None                # internal _id
    source: str                             # 'pickles','manheim','gumtree','autotrader'
    source_id: str                          # vendor’s unique id
    source_url: HttpUrl
    fingerprint: str                        # deterministic hash for cross‑vendor de‑dupe

    make: Optional[str] = None
    model: Optional[str] = None
    variant: Optional[str] = None
    year: Optional[int] = None

    price: Optional[int] = None
    odometer: Optional[int] = None          # km
    body: Optional[str] = None
    trans: Optional[str] = None
    fuel: Optional[str] = None
    engine: Optional[str] = None
    drive: Optional[str] = None

    location: Location = Location()
    media: Media = Media()
    seller: Seller = Seller()

    meta: dict = Field(default_factory=lambda: {
        'first_seen': None,
        'last_seen': None,
        'status': 'active'  # active|sold|hidden
    })

Fingerprint (deterministic)

fingerprint = sha1(
  normalize_text(make), '|', normalize_text(model), '|', year or '', '|',
  band(odometer, step=25000), '|', band(price, step=2500), '|',
  normalize_text(variant), '|', normalize_text(location.suburb or location.postcode or '')
)

Mongo Indexes
	•	Unique: { source: 1, source_id: 1 }
	•	Unique: { fingerprint: 1 }
	•	Helpful: { make: 1, model: 1, year: 1 }, { price: 1 }, { 'location.state': 1 }, { 'meta.last_seen': 1 }

Upsert Strategy
	•	update_one({source, source_id}, {$set: normalized, $setOnInsert: {meta.first_seen: now}}, upsert=True) then always $set: {meta.last_seen: now}.
	•	If a new listing collides on fingerprint, prefer the newest last_seen and merge fields conservatively.

Scheduler
	•	Queues: fresh (every 5–10 min), warm (daily), cold (weekly).
	•	Per‑vendor state: last_success_ts, error_count, breaker_open_until.
	•	Backoff: exponential on network/429; hard break on CAPTCHA.

Deal Score (baseline)
	•	Build rolling medians by (make, model, year, odometer_band, state) from our sources only.
	•	expected = median(price | bucket); std = iqr‑scaled stdev.
	•	deal_score = (expected - price) / std → flag ≥ 1.5 as “below market”.

Deep‑Link Policy (Carsales/FB)
	•	Build query URLs that reproduce user filters; show cards with off‑site CTA.
	•	Do not fetch detail pages; do not store their content. Optionally track result count snapshots only.
	•	FB personal agent: run with user‑supplied session and do not persist any scraped content.

Coding Standards
	•	Python 3.11; prefer Playwright for browser control; fall back to undetected‑chromedriver only if needed.
	•	Pydantic v2 for models; type‑checked (mypy/pyright) and formatted (ruff/black).
	•	Config via env vars: MONGODB_URI, APP_ENV, SCRAPER_CONCURRENCY, REQUEST_TIMEOUT, RATE_LIMIT_*.
	•	Logging: structured (JSON) with vendor tags and job ids.
	•	Idempotent jobs; pure functions where possible; no secrets committed.

API (v0)
	•	GET /listings?make=&model=&year_min=&year_max=&price_min=&price_max=&state=&q=&page=&limit=
	•	GET /listings/{id}
	•	GET /healthz → per‑vendor { last_success_ts, error_count, breaker_state }
	•	(Skeleton) POST /agent/saved-searches {filters, email} → store only

Tests
	•	Unit: normalizers (raw→Listing); fingerprint; deal‑score bins.
	•	Fixtures: saved HTML snippets for each vendor’s list + detail.
	•	API: list filter + pagination snapshots.

DevOps
	•	Dockerfile with uvicorn entrypoint; optional separate worker command for scheduler.
	•	MongoDB Atlas for storage; .env ignored.
	•	GitHub Actions: lint/test on PR; option to build/push container.

Agent Guardrails (when editing code)
	•	Allowed paths: engine/ (api, scraper, alerts, schedule), not website/.
	•	Do not edit .gitignore, license, or CI without explicit instruction.
	•	Always: plan → wait for approval → apply. Suggest 1–3 atomic commits with conventional messages.
	•	Operate on a feature branch; run tests and show output before committing.

Backlog (MVP Order)
	1.	Schema + Indexes: align api/models/listing.py; create Mongo indexes; add fingerprint util.
	2.	Vendor Base + Refactor: introduce VendorScraper; refactor Pickles first.
	3.	Orchestrator: incremental updater, deltas by last_seen, backoff + breaker.
	4.	API v0 + Healthz: listings endpoint + health status.
	5.	Scheduler: fresh/warm/cold queues; metrics.
	6.	SavedSearch + Deal Score: basic evaluator; email stub.
	7.	Deep‑Link Builders: Carsales + FB search URL generators.

Example Prompts (Agent mode)

Refactor Pickles → VendorScraper