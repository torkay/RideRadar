"""
Simple HTML fetcher to aid scraper debugging.

Usage:
  python -m engine.scripts.scrape_debug --url "https://www.ebay.com.au/sch/i.html?_sacat=29690&_nkw=Toyota&_pgn=1&rt=nc" \
      --outfile engine/storage/snapshots/debug.html

It prints status code, final URL, and a short body preview, then writes
the full HTML to the given outfile. Exits 0 on success, non‑zero on error.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import httpx

try:
    # Reuse the same headers as our eBay scraper
    from engine.scraper.vendors.ebay_scraper import HEADERS as DEFAULT_HEADERS
except Exception:
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.8",
        "Referer": "https://www.ebay.com.au/",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Scraper debug HTML fetcher")
    p.add_argument("--url", required=True, help="Full URL to fetch")
    p.add_argument(
        "--outfile",
        default="engine/storage/snapshots/debug.html",
        help="Output path for HTML (default: engine/storage/snapshots/debug.html)",
    )
    args = p.parse_args(argv)

    out_path = Path(args.outfile)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with httpx.Client(headers=DEFAULT_HEADERS, timeout=10.0, follow_redirects=True) as client:
            resp = client.get(args.url)
            print(f"GET {resp.request.url} -> {resp.status_code} len={len(resp.text)}")
            preview = resp.text[:300].replace("\n", " ")
            print(f"body preview: {preview}")
            out_path.write_text(resp.text, encoding="utf-8")
            print(f"saved: {out_path}")
        return 0
    except httpx.HTTPError as e:
        print(f"error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

