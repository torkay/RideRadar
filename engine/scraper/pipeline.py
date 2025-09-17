import os
from typing import Dict, Any, Iterable


def save_normalized(listing: Dict[str, Any]) -> None:
    """
    Persist a normalized listing based on DB_BACKEND.
    - postgres (default): upsert into Supabase Postgres
    - other values: no-op for now (Mongo path reserved)
    """
    backend = os.getenv("DB_BACKEND", "postgres").lower()
    if backend == "supabase_api":
        # Lazy import to avoid hard dependency when not used
        from engine.db import supabase_api as sb

        if not listing.get("fingerprint"):
            listing["fingerprint"] = sb.make_fingerprint(listing)
        sb.upsert_listing(listing)
        return

    if backend == "postgres":
        # Lazy import so environments without DB can still import the module
        from engine.db.supabase_client import upsert_listing, make_fingerprint

        if not listing.get("fingerprint"):
            listing["fingerprint"] = make_fingerprint(listing)
        upsert_listing(listing)
        return

    # Other backends: no-op for now
    return


def save_many(listings: Iterable[Dict[str, Any]]) -> int:
    """Save a collection of normalized listings. Returns count saved."""
    count = 0
    for item in listings:
        save_normalized(item)
        count += 1
    return count
