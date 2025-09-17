import os
import json
import hashlib
from typing import Any, Dict, Optional
from supabase import create_client, Client


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for supabase_api backend")

_sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _band(n: Optional[int], step: int) -> str:
    if n is None:
        return ""
    lo = (n // step) * step
    return f"{lo}-{lo+step}"


def _normalize_text(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def make_fingerprint(d: Dict[str, Any]) -> str:
    parts = [
        _normalize_text(d.get("make")),
        _normalize_text(d.get("model")),
        str(d.get("year") or ""),
        _band(d.get("odometer"), 25000),
        _band(d.get("price"), 2500),
        _normalize_text(d.get("variant")),
        _normalize_text(d.get("suburb") or d.get("postcode")),
    ]
    sha = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return sha


def upsert_listing(listing: Dict[str, Any]) -> None:
    if not listing.get("fingerprint"):
        listing["fingerprint"] = make_fingerprint(listing)
    # Supabase Python client handles JSON types; ensure serializable values
    # Perform upsert on conflict (source, source_id)
    _sb.table("listings").upsert(listing, on_conflict="source,source_id").execute()


def fetch_latest(limit: int = 10) -> list[dict]:
    resp = (
        _sb.table("listings")
        .select(
            "id, source, source_id, source_url, make, model, variant, year, price, odometer, state, suburb, postcode, last_seen"
        )
        .order("last_seen", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []

