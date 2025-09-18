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
from pathlib import Path

from engine.runtime.vendor_status import mark_success, mark_error
from engine.scraper import normalize as norm
from engine.scraper.pipeline import save_normalized, save_many


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
    p.add_argument("--force-pw", action="store_true", help="Gumtree: force Playwright and skip HTTPX")
    p.add_argument("--pw-storage", type=str, default=None, help="Gumtree: optional Playwright storage_state path (cookies/session)")
    p.add_argument("--assist", action="store_true", help="Gumtree: manual assist prompt when using Playwright")
    p.add_argument("--dry-run", action="store_true", help="Print first 3 normalized objects instead of saving")
    args = p.parse_args(argv)

    vendor = args.vendor.lower().strip()
    limit = max(1, int(args.limit))

    # Autotrader branch: HTTPX, SSR
    if vendor == "autotrader":
        print(
            f"autotrader run make='{args.make}' model='{args.model}' state='{args.state}' limit={limit} debug={args.debug}"
        )
        from engine.scraper.vendors import autotrader_http as at
        try:
            url = at.build_search_url(args.make, args.model, args.state, page=1)
            html = at.fetch_html(url)
            if args.debug:
                snap_dir = Path(__file__).resolve().parents[2] / "storage" / "snapshots"
                snap_dir.mkdir(parents=True, exist_ok=True)
                (snap_dir / "autotrader_page1.html").write_text(html, encoding="utf-8")
            rows_raw = at.parse_list(html, limit=limit, debug=args.debug)
        except Exception as e:
            mark_error("autotrader", str(e))
            print(
                f"summary vendor=autotrader fetched=0 normalized_ok=0 normalized_err=0 upserted=0 backend={os.getenv('DB_BACKEND','?')} mode=httpx error={e}"
            )
            return 2
        # Normalize
        n_ok = 0
        n_err = 0
        normalized: List[dict] = []
        for r in rows_raw:
            try:
                n = norm.normalize_autotrader(r)
                normalized.append(n)
                n_ok += 1
            except Exception:
                n_err += 1
        upserted = 0
        if not args.dry_run:
            upserted = save_many(normalized)
        if upserted > 0:
            mark_success("autotrader")
        else:
            mark_error("autotrader", "no results")
        print(
            f"summary vendor=autotrader fetched={len(rows_raw)} normalized_ok={n_ok} normalized_err={n_err} "
            f"upserted={upserted} backend={os.getenv('DB_BACKEND','?')} mode=httpx"
        )
        return 0

    # Pickles branch: HTTPX, SSR
    if vendor == "pickles":
        print("pickles run make='%s' model='%s' state='%s' limit=%d debug=%s" % (
            args.make, args.model, args.state, limit, args.debug))
        from engine.scraper.vendors import pickles_http as pk
        try:
            url = pk.build_search_url(args.make, args.model, args.state, page=1)
            html = pk.fetch_html(url)
            if args.debug:
                snap_dir = Path(__file__).resolve().parents[2] / "storage" / "snapshots"
                snap_dir.mkdir(parents=True, exist_ok=True)
                (snap_dir / "pickles_page1.html").write_text(html, encoding="utf-8")
            rows_raw = pk.parse_list(html, limit=limit, debug=args.debug)
        except Exception as e:
            mark_error("pickles", str(e))
            print("summary vendor=pickles fetched=0 normalized_ok=0 normalized_err=0 upserted=0 backend=%s mode=httpx error=%s" % (os.getenv('DB_BACKEND','?'), e))
            return 2
        n_ok = 0
        n_err = 0
        normalized = []
        for r in rows_raw:
            try:
                n = norm.normalize_pickles(r)
                normalized.append(n)
                n_ok += 1
            except Exception:
                n_err += 1
        upserted = 0
        if not args.dry_run:
            upserted = save_many(normalized)
        if upserted > 0:
            mark_success("pickles")
        else:
            mark_error("pickles", "no results")
        print("summary vendor=pickles fetched=%d normalized_ok=%d normalized_err=%d upserted=%d backend=%s mode=httpx" % (
            len(rows_raw), n_ok, n_err, upserted, os.getenv('DB_BACKEND','?')))
        return 0

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
            # Gumtree special handling: HTTPX path with optional Playwright fallback/force
            from engine.scraper.vendors.gumtree_scraper import build_search_url
            # Log intent
            print(
                f"gumtree run make='{args.make}' model='{args.model}' state='{args.state}' limit={limit} "
                f"force_pw={args.force_pw} assist={args.assist}"
            )
            keywords = " ".join(x for x in [args.make, args.model] if x)
            page1_url = build_search_url(keywords, args.state, 1)
            # Determine force PW default via env if flag not set
            force_pw_env = os.getenv("USE_PLAYWRIGHT", "").lower() in ("1", "true", "yes")
            force_pw = args.force_pw or False
            if not args.force_pw and force_pw_env:
                force_pw = True

            if force_pw:
                # Use Playwright directly
                try:
                    from engine.scraper.vendors.gumtree_playwright import fetch_page
                    debug_path = None
                    if args.debug:
                        snap_dir = (
                            Path(__file__).resolve().parents[2]
                            / "storage"
                            / "snapshots"
                        )
                        snap_dir.mkdir(parents=True, exist_ok=True)
                        debug_path = str(snap_dir / "gumtree_pw_page1.html")
                    rows = fetch_page(
                        page1_url,
                        limit=limit,
                        timeout=20000,
                        debug_html_path=debug_path,
                        assist=args.assist,
                    )
                except Exception as e:
                    mark_error(vendor, f"playwright error: {e}")
                    print(f"summary vendor=gumtree fetched=0 normalized_ok=0 normalized_err=0 upserted=0 backend={os.getenv('DB_BACKEND','postgres')} mode=playwright")
                    return 2
                fetched = len(rows)
                n_ok = 0
                n_err = 0
                normalized: List[dict] = []
                for it in rows:
                    try:
                        n = norm.normalize_gumtree(it)
                        normalized.append(n)
                        n_ok += 1
                    except Exception:
                        n_err += 1
                upserted = save_many(normalized)
                if upserted > 0:
                    mark_success(vendor)
                else:
                    mark_error(vendor, "no results (PW)")
                print(
                    f"summary vendor=gumtree fetched={fetched} normalized_ok={n_ok} normalized_err={n_err} "
                    f"upserted={upserted} backend={os.getenv('DB_BACKEND','postgres')} mode=playwright"
                )
                return 0

            # HTTPX-first path
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
        if vendor == "gumtree" and isinstance(e, RuntimeError) and ("challenge" in str(e).lower() or "403" in str(e)):
            mark_error(vendor, "challenge")
            print("error: gumtree challenge/403 encountered; aborting politely")
            return 2
        mark_error(vendor, f"scrape failed: {e}")
        print(f"error: scrape failed: {e}")
        return 2

    fetched = len(items)
    if fetched == 0:
        # For Gumtree, guide user to force PW
        if vendor == "gumtree":
            mark_error(vendor, "no results (HTTPX)")
        else:
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

    mode = "httpx"
    print(
        f"summary vendor={vendor} fetched={fetched} normalized_ok={norm_ok} normalized_err={norm_err} "
        f"upserted={upserted} backend={os.getenv('DB_BACKEND','postgres')} mode={mode}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted.")
        sys.exit(130)
