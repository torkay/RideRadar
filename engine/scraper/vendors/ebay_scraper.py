from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _extract_item_id(url: str) -> Optional[str]:
    m = re.search(r"/itm/(\d+)", url or "")
    return m.group(1) if m else None


def search(make: Optional[str] = None, model: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch AU eBay Cars results via HTTPX + BeautifulSoup (no Selenium)."""
    q = " ".join([p for p in [make, model] if p])
    params = {
        "_dcat": "29690",  # Cars category
        "_sop": "10",      # newly listed first
    }
    if q:
        params["_nkw"] = q

    url = "https://www.ebay.com.au/sch/29690/i.html"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-AU,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }
    items: List[Dict[str, Any]] = []
    with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Primary: legacy result tiles
        for li in soup.select("li.s-item"):
            a = li.select_one("a.s-item__link")
            if not a:
                continue
            href = a.get("href") or ""
            title_el = li.select_one("h3.s-item__title") or li.select_one("div.s-item__title")
            title = (title_el.get_text(strip=True) if title_el else "").strip()
            price_el = li.select_one("span.s-item__price")
            price = price_el.get_text(strip=True) if price_el else None
            loc_el = li.select_one("span.s-item__location")
            location = loc_el.get_text(strip=True) if loc_el else None
            img_el = li.select_one("img.s-item__image-img")
            img = img_el.get("src") if img_el else None
            item_id = _extract_item_id(href)
            if not href or "ebay.com.au" not in href:
                continue
            items.append({
                "title": title,
                "price": price,
                "link": href,
                "item_id": item_id,
                "location": location,
                "img": img,
                "vendor": "eBay",
            })
            if len(items) >= limit:
                return items

        # Fallback: new browse tiles
        if not items:
            for card in soup.select('[class^="brwrvr__item-card brwrvr__item-card--"]'):
                a = card.find("a")
                href = a.get("href") if a else None
                if not href:
                    continue
                img_el = card.find("img")
                img = img_el.get("src") if img_el else None
                title = card.get_text(separator=" ", strip=True)
                item_id = _extract_item_id(href)
                items.append({
                    "title": title,
                    "price": None,
                    "link": href,
                    "item_id": item_id,
                    "location": None,
                    "img": img,
                    "vendor": "eBay",
                })
                if len(items) >= limit:
                    break
    return items


def scrape_ebay():
    """Backward‑compatible entry used elsewhere in the repo."""
    return search(limit=60)
