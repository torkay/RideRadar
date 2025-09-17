"""
Vendor smoke CLI (no DB writes)

Usage:
  python engine/scripts/vendor_smoke.py --vendor pickles --limit 3

Prints:
  1) count found (and limited)
  2) first 3 raw summaries (title/url/vendor id)
  3) first 3 normalized dicts (source, source_id, source_url, make, model, year, price, suburb, postcode)

Exit code:
  0 on success, non-zero on failure with a short message.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from typing import Any, Dict, Iterable, List


def _parse_price_to_int(val: Any) -> int | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val)
    digits = re.sub(r"[^0-9]", "", s)
    return int(digits) if digits else None


def _extract_source_id(url: str, fallback: str) -> str:
    if not url:
        return hashlib.sha1(fallback.encode("utf-8")).hexdigest()
    # Try to extract a trailing id-like token
    m = re.search(r"([A-Za-z0-9_-]{8,})/?$", url)
    if m:
        return m.group(1)
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def _normalize(vendor: str, item: Dict[str, Any]) -> Dict[str, Any]:
    url = item.get("link") or item.get("url") or ""
    title = item.get("title") or item.get("name") or ""
    source_id = _extract_source_id(url, title or repr(item)[:80])
    return {
        "source": vendor.lower(),
        "source_id": source_id,
        "source_url": url,
        "make": item.get("make"),
        "model": item.get("model"),
        "year": _parse_price_to_int(item.get("year")),
        "price": _parse_price_to_int(item.get("price")),
        "suburb": item.get("suburb"),
        "postcode": item.get("postcode"),
    }


def _load_scraper(vendor: str):
    vendor = vendor.lower().strip()
    if vendor == "pickles":
        from engine.scraper.vendors.pickles_scraper import scrape_pickles as fn
        return fn, {"make": None}
    if vendor == "manheim":
        from engine.scraper.vendors.manheim_scraper import scrape_manheim as fn
        return fn, {"make": None}
    if vendor == "gumtree":
        from engine.scraper.vendors.gumtree_scraper import scrape_gumtree as fn
        return fn, {"max_pages": 1}
    if vendor == "ebay":
        from engine.scraper.vendors.ebay_scraper import scrape_ebay as fn
        return fn, {}
    raise ValueError(f"Unknown vendor: {vendor}")


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Vendor smoke CLI (no DB)")
    p.add_argument("--vendor", required=True, help="Vendor key: pickles|manheim|gumtree|ebay")
    p.add_argument("--limit", type=int, default=3, help="Max items to fetch (<=5)")
    args = p.parse_args(argv)

    limit = max(1, min(5, int(args.limit)))
    vendor = args.vendor.lower().strip()

    try:
        fn, kw = _load_scraper(vendor)
    except Exception as e:
        print(f"error: {e}")
        return 2

    try:
        t0 = time.time()
        # Call the scraper function (most are synchronous)
        items = fn(**kw) if kw else fn()
        dt = time.time() - t0
    except Exception as e:
        print(f"error: scrape failed: {e}")
        return 3

    items = items[:limit]
    print(f"vendor={vendor} fetched={len(items)} (limit={limit}) in {dt:.2f}s")

    # Raw summaries
    print("\nRaw samples:")
    for i, it in enumerate(items[:3], 1):
        title = (it.get("title") or "").replace("\n", " ").strip()
        url = it.get("link") or it.get("url") or ""
        vid = _extract_source_id(url, title or repr(it)[:40])
        print(f"  {i}. title={title[:100]} | url={url[:120]} | vendor_id={vid}")

    # Normalized
    print("\nNormalized samples:")
    for it in items[:3]:
        nd = _normalize(vendor, it)
        # Only display the requested keys in a stable order
        ordered = {
            "source": nd["source"],
            "source_id": nd["source_id"],
            "source_url": nd["source_url"],
            "make": nd["make"],
            "model": nd["model"],
            "year": nd["year"],
            "price": nd["price"],
            "suburb": nd["suburb"],
            "postcode": nd["postcode"],
        }
        print(json.dumps(ordered, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted.")
        sys.exit(130)

