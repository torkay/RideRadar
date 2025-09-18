from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


BASE = "https://www.autotrader.com.au"


def _slug(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or None


def build_search_url(make: Optional[str], model: Optional[str], state: Optional[str], page: int = 1) -> str:
    parts: List[str] = ["for-sale", "used"]
    mk = _slug(make)
    md = _slug(model)
    st = _slug(state)
    # Build path, excluding missing pieces
    for seg in (mk, md, st):
        if seg:
            parts.append(seg)
    path = "/".join(parts)
    url = urljoin(BASE, f"/{path}")
    if page and page > 1:
        url = f"{url}?page={page}"
    return url


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


def _abs_url(href: str) -> str:
    return urljoin(BASE, href)


def parse_list(html: str, limit: int, debug: bool = False) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: List[Dict[str, Any]] = []

    anchors = soup.find_all("a", href=True)
    seen: set[str] = set()
    for a in anchors:
        href = a.get("href") or ""
        if not re.match(r"^/car/\d+/", href, flags=re.IGNORECASE):
            continue
        url = _abs_url(href.split("?")[0])
        if url in seen:
            continue
        seen.add(url)
        # Parse path segments
        parts = href.split("?")[0].strip("/").split("/")
        # expected: ["car", id, make, model, state, ...]
        ad_id = parts[1] if len(parts) > 1 else None
        make_slug = parts[2] if len(parts) > 2 else None
        model_slug = parts[3] if len(parts) > 3 else None
        state_slug = parts[4] if len(parts) > 4 else None

        # Title
        title = (a.get_text(" ", strip=True) or "").strip()
        if not title:
            # Compose from slugs as a fallback
            comp = []
            if yguess:
                comp.append(yguess)
            if make_slug:
                comp.append(make_slug.replace("-", " "))
            if model_slug:
                comp.append(model_slug.replace("-", " "))
            title = " ".join(comp).title()
        # Find a nearby container for price/location
        card = a
        for _ in range(3):
            if getattr(card, "parent", None):
                card = card.parent
        text = card.get_text(" ", strip=True)
        # Price
        price_str = None
        mprice = re.search(r"\$[\s0-9,\.]+", text)
        if mprice:
            price_str = mprice.group(0)
        # Location / state
        location = None
        mstate = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", text)
        if mstate:
            location = mstate.group(1)
        # Thumb
        thumb = None
        img = card.find("img")
        if img:
            thumb = img.get("data-src") or img.get("src") or (img.get("srcset") or "").split(" ")[0]
        # Year guess from title
        yguess = None
        my = re.search(r"\b(19\d{2}|20\d{2})\b", title)
        if my:
            yguess = my.group(1)

        # State guess (validate AU states)
        st_guess = state_slug.upper() if isinstance(state_slug, str) else None
        if not (st_guess and re.match(r"^(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)$", st_guess)):
            st_guess = (location or None)

        rows.append(
            {
                "url": url,
                "ad_id": ad_id,
                "title": title,
                "price_str": price_str,
                "thumb": thumb,
                "location": location,
                "make_guess": make_slug,
                "model_guess": model_slug,
                "state_guess": st_guess,
                "year_guess": yguess,
            }
        )
        if len(rows) >= limit:
            break

    if not rows:
        raise RuntimeError("no tiles (autotrader)")
    return rows


def to_raw(row: Dict[str, Any]) -> Dict[str, Any]:
    # Already in desired raw shape; return as-is to signal intent
    return row
