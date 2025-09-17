"""
Quick vendor scraper smoke test.

Usage examples:
  python engine/scripts/scrape_smoke.py --vendors ebay,gumtree,manheim,pickles --limit 5 --samples 3
  python engine/scripts/scrape_smoke.py --vendors gumtree --limit 10

Notes:
  - This only verifies the scraper returns items; it does not persist.
  - Gumtree currently launches a visible browser window (non-headless).
"""

from __future__ import annotations

import argparse
import time
from typing import Callable, Dict, List

from engine.scraper.vendors.ebay_scraper import scrape_ebay
from engine.scraper.vendors.gumtree_scraper import scrape_gumtree
from engine.scraper.vendors.manheim_scraper import scrape_manheim
from engine.scraper.vendors.pickles_scraper import scrape_pickles


def _sanitize(s: str | None, max_len: int = 120) -> str:
    if not s:
        return ""
    s = s.replace("\n", " ").strip()
    return (s[: max_len - 3] + "...") if len(s) > max_len else s


def run_vendor(vendor: str, limit: int) -> List[dict]:
    vendor = vendor.lower().strip()
    if vendor == "ebay":
        items = scrape_ebay()
    elif vendor == "gumtree":
        # Keep it light: only 1 page then trim
        items = scrape_gumtree(max_pages=1)
    elif vendor == "manheim":
        items = scrape_manheim()
    elif vendor == "pickles":
        items = scrape_pickles()
    else:
        raise ValueError(f"Unknown vendor: {vendor}")
    return items[:limit]


def main():
    parser = argparse.ArgumentParser(description="Run vendor scraper smoke tests")
    parser.add_argument(
        "--vendors",
        type=str,
        default="ebay,gumtree,manheim,pickles",
        help="Comma-separated vendors to test",
    )
    parser.add_argument("--limit", type=int, default=5, help="Max items per vendor to fetch")
    parser.add_argument("--samples", type=int, default=3, help="How many titles to print per vendor")
    args = parser.parse_args()

    vendors = [v.strip().lower() for v in args.vendors.split(",") if v.strip()]
    if not vendors:
        print("No vendors specified")
        return

    print(f"Running vendor smoke: vendors={vendors}, limit={args.limit}")
    for v in vendors:
        print(f"\n[{v.upper()}] starting...")
        t0 = time.time()
        try:
            items = run_vendor(v, args.limit)
            dt = time.time() - t0
            print(f"[{v.upper()}] fetched={len(items)} in {dt:.2f}s")

            for i, it in enumerate(items[: args.samples]):
                title = _sanitize(it.get("title") or it.get("subtitle"))
                link = it.get("link") or it.get("url") or ""
                if title:
                    print(f"  - {title}")
                if link:
                    print(f"    {link}")
        except Exception as e:
            dt = time.time() - t0
            print(f"[{v.upper()}] ERROR after {dt:.2f}s: {e}")


if __name__ == "__main__":
    main()

