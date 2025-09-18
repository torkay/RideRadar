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
from collections import Counter
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
    p.add_argument("--make", type=str, default=None, help="Optional make keyword (ebay/gumtree/pickles)")
    p.add_argument("--model", type=str, default=None, help="Optional model keyword (ebay/gumtree/pickles)")
    p.add_argument("--state", type=str, default=None, help="Optional AU state filter (gumtree/pickles)")
    p.add_argument("--debug", action="store_true", help="Vendor debug mode (e.g., save snapshots)")
    p.add_argument("--force-pw", action="store_true", help="Gumtree: force Playwright and skip HTTPX")
    p.add_argument("--pw-storage", type=str, default=None, help="Gumtree: optional Playwright storage_state path (cookies/session)")
    p.add_argument("--assist", action="store_true", help="Gumtree: manual assist prompt when using Playwright")
    p.add_argument("--dry-run", action="store_true", help="Print first 3 normalized objects instead of saving")
    # Pickles-specific flags
    p.add_argument("--query", type=str, default=None, help="Pickles: free-text search query")
    p.add_argument("--page", type=int, default=1, help="Pickles: page number")
    p.add_argument("--suburb", type=str, default=None, help="Pickles: optional suburb segment")
    p.add_argument("--buy-now", dest="buy_now", action="store_true", help="Pickles: legacy flag for Buy Now (prefer --buy-method)")
    p.add_argument("--salvage", choices=["non-salvage", "salvage", "both"], default="non-salvage", help="Pickles: salvage filter")
    p.add_argument("--wovr", choices=["none", "repairable", "statutory"], default="none", help="Pickles: WOVR filter")
    p.add_argument("--double-encode-filter", action="store_true", help="Pickles: double-encode filter value (rare)")
    p.add_argument("--hydrate-details", dest="hydrate_details", action="store_true", help="Pickles: fetch detail pages to fill title/price if missing")
    p.add_argument("--buy-method", choices=["any", "buy_now"], default=None, help="Pickles: buy method filter (default: buy_now if require-price else any)")
    p.add_argument("--require-price", dest="require_price", action="store_true", help="Pickles: require numeric price (default)")
    p.add_argument("--no-require-price", dest="require_price", action="store_false", help="Pickles: allow missing price")
    p.set_defaults(require_price=True)
    p.add_argument("--include-unpriced", dest="include_unpriced", action="store_true", help="Pickles: include unpriced rows when price not required")
    p.add_argument("--allow-enquire", dest="allow_enquire", action="store_true", help="Pickles: allow 'Enquire Now' listings without prices when combined with unpriced flags")
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
                snap_dir = Path(__file__).resolve().parents[1] / "storage" / "snapshots"
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
            # Build filters for Pickles
            filt: Dict[str, List[str]] = {}
            if args.salvage == "non-salvage":
                filt["salvage"] = ["non-Salvage"]
            elif args.salvage == "salvage":
                filt["salvage"] = ["Salvage"]
            elif args.salvage == "both":
                filt["salvage"] = ["non-Salvage", "Salvage"]
            # Compute buy_method default from flags
            final_buy_method = args.buy_method
            if final_buy_method is None:
                if args.buy_now:
                    final_buy_method = "buy_now"
                else:
                    final_buy_method = "buy_now" if args.require_price else "any"
            if args.wovr == "repairable":
                filt["wovr"] = ["Repairable Write-Off"]
            elif args.wovr == "statutory":
                filt["wovr"] = ["Statutory Write-Off"]

            url = pk.build_search_url(
                args.make,
                args.model,
                args.state,
                suburb=args.suburb,
                query=args.query,
                page=args.page,
                limit=args.limit,
                filters=(filt or None),
                double_encode_filter=args.double_encode_filter,
                buy_method=final_buy_method,
            )
            if args.debug:
                print(f"DEBUG pickles URL: {url}")
            html = pk.fetch_html(url, debug=args.debug)
            rows_raw, parse_stats = pk.parse_list(
                html,
                limit=limit,
                debug=args.debug,
                hydrate=args.hydrate_details,
                assume_buy_now=(final_buy_method == "buy_now"),
            )
            drop_counters = Counter(parse_stats)
        except Exception as e:
            mark_error("pickles", str(e))
            print("summary vendor=pickles fetched=0 normalized_ok=0 normalized_err=0 upserted=0 backend=%s mode=httpx error=%s" % (os.getenv('DB_BACKEND','?'), e))
            return 2
        kept_real_initial = drop_counters.get("kept_real", len(rows_raw))
        rows_candidates = list(rows_raw)
        rows_filtered: List[Dict[str, Any]] = []
        for raw in rows_candidates:
            price_val = raw.get("price")
            require_price = args.require_price or (not args.require_price and not args.include_unpriced)
            sale_method = (raw.get("sale_method") or "").lower()
            is_enquire = sale_method == "enquire"
            if require_price and price_val is None:
                if is_enquire and args.allow_enquire and args.include_unpriced:
                    rows_filtered.append(raw)
                    continue
                if is_enquire:
                    drop_counters["dropped_enquire_unpriced"] += 1
                    if args.debug:
                        print(f"DEBUG pickles drop[enquire_unpriced]: url={raw.get('url')}")
                else:
                    drop_counters["dropped_missing_price"] += 1
                    if args.debug:
                        print(f"DEBUG pickles drop[missing_price]: url={raw.get('url')}")
                continue
            rows_filtered.append(raw)
        rows_raw = rows_filtered
        drop_counters["kept_after_filters"] = len(rows_raw)
        n_ok = 0
        n_err = 0
        normalized = []
        for r in rows_raw:
            try:
                n = norm.normalize_pickles(r)
                normalized.append(n)
                n_ok += 1
            except Exception as exc:
                n_err += 1
                drop_counters["dropped_normalize_error"] += 1
                if args.debug:
                    print(f"DEBUG pickles drop[normalize_error]: url={r.get('url')} error={exc}")
        # Price-first behavior: filter rows based on price flags
        if args.require_price:
            normalized = [n for n in normalized if n.get("price") is not None]
        elif not args.include_unpriced:
            normalized = [n for n in normalized if n.get("price") is not None]

        n_ok = len(normalized)

        upserted = 0
        if args.dry_run:
            for n in normalized[:3]:
                print(n)
        else:
            upserted = save_many(normalized)
        if upserted > 0:
            mark_success("pickles")
        else:
            mark_error("pickles", "no results")
        drop_keys = [
            "dropped_category",
            "dropped_duplicate",
            "dropped_price_out_of_range",
            "dropped_missing_price",
            "dropped_enquire_unpriced",
            "dropped_parse_error",
            "dropped_normalize_error",
            "sale_method_enquire",
            "enquire_unpriced",
        ]
        if drop_counters.get("hydrated"):
            drop_keys.append("hydrated")
        drop_summary = " ".join(
            f"{k}={drop_counters.get(k, 0)}" for k in drop_keys if drop_counters.get(k, 0)
        )
        kept_after_filters = drop_counters.get("kept_after_filters", len(rows_raw))
        print(
            "summary vendor=pickles fetched=%d normalized_ok=%d normalized_err=%d upserted=%d backend=%s mode=httpx kept_real=%d kept_after=%d%s"
            % (
                len(rows_candidates),
                n_ok,
                n_err,
                upserted,
                os.getenv('DB_BACKEND','?'),
                kept_real_initial,
                kept_after_filters,
                (" drops[" + drop_summary + "]") if drop_summary else "",
            )
        )
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
                            Path(__file__).resolve().parents[1]
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
