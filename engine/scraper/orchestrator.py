"""
Minimal ingest orchestrator for a single vendor.

Usage:
  python -m engine.scraper.orchestrator --vendor pickles --limit 10 [--dry-run]

Default is commit mode (persists via pipeline.save_normalized according to DB_BACKEND).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from collections import Counter
from typing import Callable, Dict, List, Optional, Tuple
from pathlib import Path

from engine.runtime.vendor_status import mark_success, mark_error
from engine.scraper import normalize as norm
from engine.scraper.pipeline import save_normalized, save_many


def _pickles_compute_buy_method(
    *,
    strict_prices: bool,
    final_buy_method: Optional[str],
    allow_enquire: bool,
    include_unpriced: bool,
) -> Optional[str]:
    if strict_prices:
        return "buy_now"
    if (final_buy_method or "").lower() == "buy_now" and not (allow_enquire or include_unpriced):
        return "buy_now"
    return None


def _compile_query_tokens(query: Optional[str], make: Optional[str]) -> Tuple[Optional[str], List[str]]:
    if not query:
        return None, []
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    if not tokens:
        return None, []
    make_token = make.lower() if make else tokens[0]
    other_tokens = [tok for tok in tokens if tok != make_token]
    return make_token, other_tokens


def _passes_query_filter(
    make_token: Optional[str],
    other_tokens: List[str],
    row: Dict[str, Any],
) -> bool:
    if not make_token and not other_tokens:
        return True
    text_parts = [
        str(row.get("title") or ""),
        str(row.get("make_guess") or ""),
        str(row.get("model_guess") or ""),
        str(row.get("variant") or ""),
    ]
    text_blob = " ".join(text_parts).lower()
    if make_token and make_token not in text_blob:
        return False
    if other_tokens:
        if not any(tok in text_blob for tok in other_tokens):
            return False
    return True


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
    p.add_argument("--hydrate-concurrency", type=int, default=4, help="Pickles: max concurrent detail fetches (default 4)")
    p.add_argument("--pages", "--max-pages", dest="pages", type=int, default=1, help="Pickles: max search result pages to walk (default 1)")
    p.add_argument("--buy-method", choices=["any", "buy_now"], default=None, help="Pickles: buy method filter (default: buy_now if require-price else any)")
    p.add_argument("--require-price", dest="require_price", action="store_true", help="Pickles: require numeric price (default)")
    p.add_argument("--no-require-price", dest="require_price", action="store_false", help="Pickles: allow missing price")
    p.set_defaults(require_price=True)
    p.add_argument("--include-unpriced", dest="include_unpriced", action="store_true", help="Pickles: include unpriced rows when price not required")
    p.add_argument("--allow-enquire", dest="allow_enquire", action="store_true", help="Pickles: allow 'Enquire Now' listings without prices when combined with unpriced flags")
    p.add_argument("--strict-prices", dest="strict_prices", action="store_true", help="Pickles: require numeric price for all sale methods")
    p.add_argument("--require-year", dest="require_year", action="store_true", help="Pickles: require parsed year (default)")
    p.add_argument("--no-require-year", dest="require_year", action="store_false", help="Pickles: allow missing year")
    p.add_argument("--require-state", dest="require_state", action="store_true", help="Pickles: require detected state (default)")
    p.add_argument("--no-require-state", dest="require_state", action="store_false", help="Pickles: allow missing state")
    p.set_defaults(require_year=True, require_state=True)
    p.add_argument("--min-year", type=int, default=None, help="Pickles: drop vehicles older than this year")
    p.add_argument("--min-price", type=int, default=None, help="Pickles: drop vehicles cheaper than this price")
    p.add_argument("--max-price", type=int, default=None, help="Pickles: drop vehicles more expensive than this price")
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
        pages_walked = 0
        try:
            filt: Dict[str, List[str]] = {}
            if args.salvage == "non-salvage":
                filt["salvage"] = ["non-Salvage"]
            elif args.salvage == "salvage":
                filt["salvage"] = ["Salvage"]
            elif args.salvage == "both":
                filt["salvage"] = ["non-Salvage", "Salvage"]
            if args.wovr == "repairable":
                filt["wovr"] = ["Repairable Write-Off"]
            elif args.wovr == "statutory":
                filt["wovr"] = ["Statutory Write-Off"]

            final_buy_method = args.buy_method
            if final_buy_method is None:
                if args.buy_now:
                    final_buy_method = "buy_now"
                else:
                    final_buy_method = "buy_now" if args.require_price else "any"

            buy_method_for_search = _pickles_compute_buy_method(
                strict_prices=args.strict_prices,
                final_buy_method=final_buy_method,
                allow_enquire=args.allow_enquire,
                include_unpriced=args.include_unpriced,
            )

            rows_raw, parse_stats, meta = pk.search_pickles(
                make=args.make,
                model=args.model,
                state=args.state,
                suburb=args.suburb,
                query=args.query,
                pages=args.pages,
                limit=limit,
                filters=(filt or None) if filt else None,
                double_encode_filter=args.double_encode_filter,
                buy_method=buy_method_for_search,
                hydrate=args.hydrate_details,
                hydrate_concurrency=args.hydrate_concurrency,
                debug=args.debug,
            )
            drop_counters = Counter(parse_stats)
            pages_walked = meta.get("pages_walked", 0)
        except Exception as e:
            mark_error("pickles", str(e))
            print("summary vendor=pickles fetched=0 normalized_ok=0 normalized_err=0 upserted=0 backend=%s mode=httpx error=%s" % (os.getenv('DB_BACKEND','?'), e))
            return 2
        kept_real_initial = drop_counters.get("kept_real", len(rows_raw))
        rows_filtered: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        min_year = args.min_year
        min_price = args.min_price
        max_price = args.max_price
        make_token, other_tokens = _compile_query_tokens(args.query, args.make)

        for raw in rows_raw:
            url = raw.get("url")
            if not url:
                drop_counters["dropped_quality_gate"] += 1
                if args.debug:
                    print("DEBUG pickles drop[quality_gate]: missing url")
                continue
            if url in seen_urls:
                drop_counters["dropped_duplicate"] += 1
                if args.debug and url:
                    print(f"DEBUG pickles drop[duplicate]: url={url}")
                continue
            seen_urls.add(url)

            flags = raw.get("flags", {})
            sale_method = (flags.get("sale_method") or raw.get("sale_method") or "").lower()
            price_val = flags.get("price")
            if price_val is None and isinstance(raw.get("price"), int):
                price_val = raw.get("price")
            has_price = price_val is not None
            year_val = flags.get("year")
            if year_val is None and raw.get("year_guess"):
                try:
                    year_val = int(str(raw["year_guess"]))
                except Exception:
                    year_val = None
            flags["price"] = price_val
            flags["year"] = year_val
            flags["has_price"] = has_price
            flags["has_year"] = flags.get("has_year") if flags.get("has_year") is not None else (year_val is not None)
            flags["has_state"] = flags.get("has_state") if flags.get("has_state") is not None else bool(raw.get("state"))
            flags["is_enquire"] = sale_method == "enquire"
            raw["flags"] = flags

            if args.require_year and not flags.get("has_year"):
                drop_counters["dropped_missing_year"] += 1
                if args.debug:
                    print(f"DEBUG pickles drop[missing_year]: url={url}")
                continue
            if args.require_state and not flags.get("has_state"):
                drop_counters["dropped_missing_state"] += 1
                if args.debug:
                    print(f"DEBUG pickles drop[missing_state]: url={url}")
                continue

            price_required = args.strict_prices or (args.require_price and not args.include_unpriced)
            if sale_method == "enquire" and args.allow_enquire and args.include_unpriced:
                price_required = args.strict_prices

            if price_required and not has_price:
                if sale_method == "enquire":
                    drop_counters["dropped_enquire_unpriced"] += 1
                    if args.debug:
                        print(f"DEBUG pickles drop[enquire_unpriced]: url={url}")
                else:
                    drop_counters["dropped_missing_price"] += 1
                    if args.debug:
                        print(f"DEBUG pickles drop[missing_price]: url={url}")
                continue

            out_of_range = False
            if has_price:
                if (min_price is not None and price_val < min_price) or (max_price is not None and price_val > max_price):
                    out_of_range = True
                elif not pk._price_in_bounds(price_val):
                    out_of_range = True
            if not out_of_range and year_val is not None and min_year is not None and year_val < min_year:
                out_of_range = True

            if out_of_range:
                drop_counters["dropped_out_of_range"] += 1
                if args.debug:
                    print(f"DEBUG pickles drop[out_of_range]: url={url} price={price_val} year={year_val}")
                continue

            if (make_token or other_tokens) and not _passes_query_filter(make_token, other_tokens, raw):
                drop_counters["dropped_off_query"] += 1
                if args.debug:
                    print(f"DEBUG pickles drop[off_query]: url={url}")
                continue

            rows_filtered.append(raw)

        rows_raw = rows_filtered
        drop_counters["kept_after_filters"] = len(rows_raw)
        drop_counters["sale_method_enquire"] = sum(
            1 for r in rows_raw if (r.get("sale_method") or "").lower() == "enquire"
        )
        drop_counters["enquire_unpriced"] = sum(
            1 for r in rows_raw if (r.get("sale_method") or "").lower() == "enquire" and not r.get("price")
        )
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
            "dropped_missing_year",
            "dropped_missing_state",
            "dropped_missing_price",
            "dropped_enquire_unpriced",
            "dropped_out_of_range",
            "dropped_off_query",
            "dropped_quality_gate",
            "dropped_parse_error",
            "dropped_normalize_error",
            "sale_method_enquire",
            "enquire_unpriced",
        ]
        drop_summary = " ".join(
            f"{k}={drop_counters.get(k, 0)}" for k in drop_keys if drop_counters.get(k, 0)
        )
        kept_after_filters = drop_counters.get("kept_after_filters", len(rows_raw))
        hydrated_count = drop_counters.get("hydrated", 0)
        fetched_real = kept_real_initial
        backend = os.getenv('DB_BACKEND', '?')
        summary_tail = f" drops[{drop_summary}]" if drop_summary else ""
        print(
            "summary vendor=pickles fetched_real=%d kept_after=%d normalized_ok=%d normalized_err=%d "
            "upserted=%d hydrated=%d pages_walked=%d backend=%s mode=httpx%s"
            % (
                fetched_real,
                kept_after_filters,
                n_ok,
                n_err,
                upserted,
                hydrated_count,
                pages_walked,
                backend,
                summary_tail,
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
