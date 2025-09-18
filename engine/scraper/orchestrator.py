"""
Minimal ingest orchestrator for a single vendor.

Usage:
  python -m engine.scraper.orchestrator --vendor pickles --limit 10 [--dry-run]

Default is commit mode (persists via pipeline.save_normalized according to DB_BACKEND).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Callable, Dict, List, Tuple

from engine.runtime.vendor_status import mark_success, mark_error
from engine.scraper import normalize as norm
from engine.scraper.pipeline import save_normalized


def _load_scraper(vendor: str) -> Tuple[Callable, Dict]:
    vendor = vendor.lower().strip()
    if vendor == "pickles":
        from engine.scraper.vendors.pickles_scraper import scrape_pickles as fn
        return fn, {}
    if vendor == "manheim":
        from engine.scraper.vendors.manheim_scraper import scrape_manheim as fn
        return fn, {}
    if vendor == "gumtree":
        # Use HTTPX-based search with keyword/state support
        from engine.scraper.vendors.gumtree_scraper import search as fn
        return fn, {}
    if vendor == "ebay":
        if os.getenv("USE_EBAY_API", "").lower() in ("1", "true", "yes"):
            from engine.integrations.ebay_api import search_items as fn
            return fn, {"limit": 50}
        else:
            from engine.scraper.vendors.ebay_scraper import search as fn
            return fn, {"limit": 50}
    raise ValueError(f"Unknown vendor: {vendor}")


_NORMALIZERS = {
    "pickles": norm.normalize_pickles,
    "manheim": norm.normalize_manheim,
    "gumtree": norm.normalize_gumtree,
    "ebay": norm.normalize_ebay,
}


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Vendor ingest orchestrator")
    p.add_argument("--vendor", required=True, help="pickles|manheim|gumtree|ebay")
    p.add_argument("--limit", type=int, default=10, help="Max items to process")
    p.add_argument("--make", type=str, default=None, help="Optional make keyword (ebay/gumtree)")
    p.add_argument("--model", type=str, default=None, help="Optional model keyword (ebay/gumtree)")
    p.add_argument("--state", type=str, default=None, help="Optional AU state filter (gumtree)")
    p.add_argument("--debug", action="store_true", help="Vendor debug mode (e.g., save snapshots)")
    p.add_argument("--dry-run", action="store_true", help="Print first 3 normalized objects instead of saving")
    args = p.parse_args(argv)

    vendor = args.vendor.lower().strip()
    limit = max(1, int(args.limit))

    try:
        fn, kw = _load_scraper(vendor)
        if vendor == "ebay" and os.getenv("USE_EBAY_API", "").lower() not in ("1", "true", "yes"):
            kw.update({
                "make": args.make,
                "model": args.model,
                "limit": limit,
                "page_limit": 2,
                "debug": args.debug,
            })
        if vendor == "gumtree":
            kw.update({
                "make": args.make,
                "model": args.model,
                "state": args.state,
                "limit": limit,
                "page_limit": 2,
                "debug": args.debug,
            })
        if vendor == "ebay" and os.getenv("USE_EBAY_API", "").lower() in ("1", "true", "yes"):
            q = " ".join(x for x in [args.make, args.model] if x)
            kw.update({"q": q, "limit": limit})
        t0 = time.time()
        items = fn(**kw) if kw else fn()
        _ = time.time() - t0
        items = items[:limit]
    except Exception as e:
        if vendor == "gumtree" and isinstance(e, RuntimeError) and "challenge" in str(e).lower():
            mark_error(vendor, "challenge")
            print("error: gumtree challenge page encountered; aborting politely")
            return 2
        mark_error(vendor, f"scrape failed: {e}")
        print(f"error: scrape failed: {e}")
        return 2

    fetched = len(items)
    if fetched == 0:
        mark_error(vendor, "no results")
    norm_ok = 0
    norm_err = 0
    upserted = 0

    if vendor == "ebay" and os.getenv("USE_EBAY_API", "").lower() in ("1", "true", "yes"):
        from engine.integrations.ebay_api import normalize as normalizer  # type: ignore
    else:
        normalizer = _NORMALIZERS.get(vendor)
    if not normalizer:
        print(f"warning: no normalizer for {vendor}; skipping")
        return 0

    normalized: List[dict] = []
    for it in items:
        try:
            n = normalizer(it)
            normalized.append(n)
            norm_ok += 1
        except Exception:
            norm_err += 1

    if args.dry_run:
        for n in normalized[:3]:
            print(n)
        print(
            f"summary vendor={vendor} fetched={fetched} normalized_ok={norm_ok} normalized_err={norm_err} upserted=0 backend={os.getenv('DB_BACKEND','postgres')}"
        )
        return 0

    # Commit path: save via pipeline
    success = False
    for n in normalized:
        try:
            save_normalized(n)
            upserted += 1
            success = True
        except Exception as e:
            print(f"upsert error: {e}")

    if success and upserted > 0 or fetched > 0:
        mark_success(vendor)
    else:
        mark_error(vendor, "no rows upserted")

    print(
        f"summary vendor={vendor} fetched={fetched} normalized_ok={norm_ok} normalized_err={norm_err} upserted={upserted} backend={os.getenv('DB_BACKEND','postgres')}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted.")
        sys.exit(130)
