from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup


BASE = "https://www.ebay.com.au/sch/i.html"
CARS_CAT = "29690"  # AU Motors -> Cars

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.8",
    "Referer": "https://www.ebay.com.au/",
}


def _extract_item_id(url: str) -> Optional[str]:
    m = re.search(r"/itm/(\d+)", url or "")
    return m.group(1) if m else None


def search(
    make: Optional[str] = None,
    model: Optional[str] = None,
    limit: int = 10,
    page_limit: int = 2,
    debug: bool = False,
) -> List[Dict[str, Any]]:
    """Fetch AU Cars via httpx + BS4. Deterministic category + lightweight pagination."""
    keywords = " ".join(x for x in [make, model] if x)
    items: List[Dict[str, Any]] = []

    with httpx.Client(headers=HEADERS, timeout=10.0, follow_redirects=True) as client:
        for page in range(1, max(1, page_limit) + 1):
            params = {
                "_nkw": keywords,
                "_sacat": CARS_CAT,
                "_pgn": str(page),
                "rt": "nc",
            }
            resp = client.get(BASE, params=params)
            if resp.status_code != 200:
                continue

            if debug and page == 1:
                snap_dir = Path(__file__).resolve().parents[2] / "storage" / "snapshots"
                snap_dir.mkdir(parents=True, exist_ok=True)
                (snap_dir / "ebay_page1.html").write_text(resp.text, encoding="utf-8")

            soup = BeautifulSoup(resp.text, "html.parser")

            # Primary selector set
            tiles = soup.select("li.s-item")
            # Fallbacks
            if not tiles:
                tiles = soup.select("div.s-item__wrapper")

            for li in tiles:
                a = li.select_one("a.s-item__link") or li.find("a")
                href = (a.get("href") if a else "") or ""
                if not href or "ebay.com.au" not in href:
                    continue
                title_el = li.select_one("h3.s-item__title") or li.select_one("div.s-item__title") or a
                title = (title_el.get_text(strip=True) if title_el else "").strip()
                price_el = li.select_one("span.s-item__price")
                price = price_el.get_text(strip=True) if price_el else None
                loc_el = li.select_one("span.s-item__location") or li.select_one('[data-testid="s-item-location"]')
                location = loc_el.get_text(strip=True) if loc_el else None
                img_el = li.select_one("img.s-item__image-img") or li.find("img")
                img = img_el.get("src") if img_el else None
                item_id = _extract_item_id(href)
                items.append(
                    {
                        "title": title,
                        "price": price,
                        "link": href,
                        "item_id": item_id,
                        "location": location,
                        "img": img,
                        "vendor": "eBay",
                    }
                )
                if len(items) >= limit:
                    return items[:limit]

    return items[:limit]


def scrape_ebay():
    """Backward‑compatible entry used elsewhere in the repo."""
    return search(limit=60)
