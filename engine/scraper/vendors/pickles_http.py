from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin

import httpx
from bs4 import BeautifulSoup


BASE = "https://www.pickles.com.au"


def build_search_url(make: Optional[str], model: Optional[str], state: Optional[str], page: int = 1) -> str:
    """
    Construct a simple SSR search URL for Pickles AU cars.
    Example (best‑effort): https://www.pickles.com.au/cars?keywords=toyota%20corolla&state=NSW&page=1
    """
    kw = " ".join(x for x in [make, model] if x)
    params = {}
    if kw:
        params["keywords"] = kw
    if state:
        params["state"] = state.upper()
    if page and page > 1:
        params["page"] = str(page)
    qs = f"?{urlencode(params)}" if params else ""
    return urljoin(BASE, f"/cars{qs}")


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.9",
        "Referer": BASE,
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
        r = client.get(url)
        if r.status_code != 200:
            raise RuntimeError(f"http {r.status_code}")
        return r.text


def _abs(href: str) -> str:
    return urljoin(BASE, href)


def _from_jsonld(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(sc.string or "{}")
        except Exception:
            continue
        # Sometimes a list of products
        candidates = data if isinstance(data, list) else [data]
        for d in candidates:
            if not isinstance(d, dict):
                continue
            url = d.get("url") or d.get("@id")
            if not url:
                continue
            title = d.get("name") or ""
            price_val = None
            price_str = None
            offers = d.get("offers") or {}
            if isinstance(offers, dict):
                price_str = offers.get("price") or offers.get("priceCurrency")
                price_val = offers.get("price")
            rows.append(
                {
                    "title": title,
                    "price_str": str(price_val or price_str) if (price_val or price_str) else None,
                    "url": _abs(url),
                    "thumb": None,
                    "location": None,
                    "year_guess": None,
                    "make_guess": None,
                    "model_guess": None,
                    "source_id_guess": None,
                }
            )
    return rows


def parse_list(html: str, limit: int, debug: bool = False) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: List[Dict[str, Any]] = []

    # Try anchors to known vehicle detail paths
    anchors = soup.select("a[href*='/cars/item/'], a[href^='/car/'], a[href*='/vehicles/']")
    seen: set[str] = set()
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        url = _abs(href)
        if url in seen:
            continue
        seen.add(url)
        title = (a.get_text(" ", strip=True) or "").strip()
        # Find price/location near the card
        card = a
        for _ in range(3):
            if card.parent:
                card = card.parent
        text = card.get_text(" ", strip=True)
        price_str = None
        mprice = re.search(r"\$\s*([0-9][0-9,]*)", text)
        if mprice:
            price_str = mprice.group(0)
        location = None
        mstate = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", text)
        if mstate:
            location = mstate.group(1)
        thumb = None
        img = card.find("img")
        if img:
            thumb = img.get("src") or (img.get("srcset") or "").split(" ")[0]
        # Guesses
        year_guess = None
        myear = re.search(r"\b(19\d{2}|20\d{2})\b", title)
        if myear:
            year_guess = myear.group(1)
        # Attempt id from url
        sid = None
        mid = re.search(r"/item/([^/?#]+)", url)
        if mid:
            sid = mid.group(1)

        rows.append(
            {
                "title": title,
                "price_str": price_str,
                "url": url,
                "thumb": thumb,
                "location": location,
                "year_guess": year_guess,
                "make_guess": None,
                "model_guess": None,
                "source_id_guess": sid,
            }
        )
        if len(rows) >= limit:
            break

    # Fallback to JSON-LD if no anchors parsed
    if not rows:
        rows = _from_jsonld(soup)[:limit]

    if not rows:
        raise RuntimeError("no tiles (pickles)")
    return rows


def to_raw(row: Dict[str, Any]) -> Dict[str, Any]:
    return row

