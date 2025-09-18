from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin, quote

import httpx
from bs4 import BeautifulSoup


BASE = "https://www.pickles.com.au"
_AU_STATES = {"nsw", "qld", "vic", "sa", "wa", "tas", "act", "nt"}


def _slug(seg: Optional[str]) -> Optional[str]:
    if not seg:
        return None
    s = re.sub(r"[^a-zA-Z0-9]+", "-", seg.strip().lower()).strip("-")
    return s or None


def _make_path(make: Optional[str], model: Optional[str], state: Optional[str], suburb: Optional[str]) -> str:
    parts: List[str] = ["used", "search", "cars"]
    m = _slug(make)
    mdl = _slug(model)
    st = (_slug(state) or "")
    sub = _slug(suburb)
    if m:
        parts.append(m)
    if mdl:
        parts.append(mdl)
    if st and st in _AU_STATES:
        parts += ["state", st]
        if sub:
            parts.append(sub)
    return "/" + "/".join(parts)


def _build_filter_value(filters: Dict[str, List[str]]) -> str:
    parts: List[str] = []
    and_i = 0
    for key, values in filters.items():
        for j, val in enumerate(values):
            parts.append(f"and[{and_i}][or][{j}][{key}]={val}")
        and_i += 1
    return "&".join(parts)


def build_search_url(
    make: Optional[str],
    model: Optional[str],
    state: Optional[str],
    *,
    suburb: Optional[str] = None,
    query: Optional[str] = None,
    page: int = 1,
    limit: Optional[int] = None,
    filters: Optional[Dict[str, List[str]]] = None,
    double_encode_filter: bool = False,
) -> str:
    path = _make_path(make, model, state, suburb)
    q = (query or " ".join([x for x in [make, model] if x]) or "").strip()
    params: Dict[str, str] = {}
    # Always include page=1 for consistency
    params["page"] = str(page or 1)
    if q:
        params["search"] = q
    if limit and limit > 0:
        params["limit"] = str(limit)
    if filters:
        raw = _build_filter_value(filters)
        # Encode once so that internal & becomes %26 and [] become %5B/%5D
        encoded_once = urlencode({"filter": raw}, quote_via=quote)
        filter_value = encoded_once.split("=", 1)[1]
        if double_encode_filter:
            filter_value = filter_value.replace("%", "%25")
        params["filter"] = filter_value

    qpairs: List[str] = []
    for k, v in params.items():
        if k == "filter":
            qpairs.append(f"filter={v}")
        else:
            qpairs.append(urlencode({k: v}, quote_via=quote))
    qs = "&".join(qpairs)
    return f"{BASE}{path}?{qs}"


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

    anchors = soup.find_all("a", href=True)
    seen: set[str] = set()
    for a in anchors:
        href = a.get("href") or ""
        if not re.match(r"^/cars/item/[^/]+/?$", href, flags=re.IGNORECASE):
            continue
        url = _abs(href.split("?")[0])
        if url in seen or url.rstrip("/") == BASE:
            continue
        seen.add(url)
        # Extract id/slug from url tail
        sid = href.rstrip("/").split("/")[-1]
        # Title
        title = (a.get_text(" ", strip=True) or "").strip()
        # Card container
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
        # Location
        location = None
        mstate = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", text)
        if mstate:
            location = mstate.group(1)
        # Thumb
        thumb = None
        img = card.find("img")
        if img:
            thumb = img.get("src") or (img.get("srcset") or "").split(" ")[0]
        # Year guess from title
        yguess = None
        my = re.search(r"\b(19\d{2}|20\d{2})\b", title)
        if my:
            yguess = my.group(1)

        rows.append(
            {
                "url": url,
                "source_id_guess": sid,
                "title": title,
                "price_str": price_str,
                "thumb": thumb,
                "location": location,
                "year_guess": yguess,
                "make_guess": None,
                "model_guess": None,
            }
        )
        if len(rows) >= limit:
            break

    if not rows:
        # Fallback to JSON-LD
        rows = _from_jsonld(soup)[:limit]

    if not rows:
        raise RuntimeError("no tiles (pickles)")
    return rows


def to_raw(row: Dict[str, Any]) -> Dict[str, Any]:
    return row
