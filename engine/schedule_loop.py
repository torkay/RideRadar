import argparse
import asyncio
import importlib
import os
import re
import time
from hashlib import sha1

from engine.runtime.vendor_status import mark_success, mark_error
from engine.scraper.pipeline import save_normalized


def _parse_price_to_int(price_val):
    if price_val is None:
        return None
    if isinstance(price_val, (int, float)):
        return int(price_val)
    s = str(price_val)
    digits = re.sub(r"[^0-9]", "", s)
    return int(digits) if digits else None


def _basic_normalize(vendor: str, item: dict) -> dict:
    url = item.get("link") or item.get("url") or ""
    sid_basis = url or item.get("title") or repr(item)[:200]
    source_id = sha1(sid_basis.encode("utf-8")).hexdigest()
    media = [item.get("img")] if item.get("img") else []
    return {
        "source": vendor.lower(),
        "source_id": source_id,
        "source_url": url,
        "price": _parse_price_to_int(item.get("price")),
        "media": media,
        "raw": item,
        "status": "active",
    }


def _load_scrape_func(vendor: str):
    module_name = f"engine.scraper.vendors.{vendor}_scraper"
    func_name = f"scrape_{vendor}"
    mod = importlib.import_module(module_name)
    fn = getattr(mod, func_name)
    return fn


async def run_vendor_once(vendor: str, limit: int | None = None) -> tuple[int, int]:
    """Return (fetched, saved)."""
    try:
        scrape = _load_scrape_func(vendor)
    except Exception as e:
        mark_error(vendor, f"load failed: {e}")
        return (0, 0)

    try:
        listings = await asyncio.to_thread(scrape)
        if limit is not None:
            listings = listings[: int(limit)]
        saved = 0
        if os.getenv("SUPABASE_DB_URL"):
            for item in listings:
                norm = _basic_normalize(vendor, item)
                try:
                    save_normalized(norm)
                    saved += 1
                except Exception as e:
                    # Saving should not cause overall vendor failure
                    mark_error(vendor, f"save error: {e}")
        mark_success(vendor)
        return (len(listings), saved)
    except Exception as e:
        mark_error(vendor, e)
        return (0, 0)


def parse_args():
    p = argparse.ArgumentParser(description="RideRadar minimal vendor runner")
    p.add_argument("--vendors", type=str, required=False, default="",
                   help="Comma-separated vendor keys (e.g., pickles,manheim,gumtree)")
    p.add_argument("--limit", type=int, required=False, default=None,
                   help="Max listings to process per vendor")
    p.add_argument("--once", action="store_true", help="Run a single pass and exit (default)")
    return p.parse_args()


async def cli_main():
    args = parse_args()
    vendors = [v.strip().lower() for v in args.vendors.split(",") if v.strip()] if args.vendors else []
    if not vendors:
        # try to auto-discover the common ones if none specified
        vendors = ["pickles", "manheim", "gumtree"]

    print(f"Running vendors: {', '.join(vendors)} | limit={args.limit}")
    fetched_total = 0
    saved_total = 0
    for v in vendors:
        fetched, saved = await run_vendor_once(v, args.limit)
        fetched_total += fetched
        saved_total += saved
        print(f"{v}: fetched={fetched}, saved={saved}")

    print(f"done. totals: fetched={fetched_total}, saved={saved_total}")


if __name__ == "__main__":
    asyncio.run(cli_main())
