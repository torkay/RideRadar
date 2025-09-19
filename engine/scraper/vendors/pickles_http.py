from __future__ import annotations

import asyncio
import json
import os
import random
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urljoin, quote

import httpx
from bs4 import BeautifulSoup


BASE = "https://www.pickles.com.au"
_AU_STATES = {"nsw", "qld", "vic", "sa", "wa", "tas", "act", "nt"}
_UA_ROTATE = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ),
]

_PRICE_REGEX = re.compile(
    r"(?i)(?:buy\s*now\s*|price\s*)?(?:a?\$)\s*([0-9]{1,3}(?:[\s,]\d{3})*(?:\.\d{2})?|\d+)"
)

_SALE_METHOD_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "buy_now": ("buy now", "buy-now", "buynow", "fixed price"),
    "auction": ("auction", "bid now", "going once"),
    "proposed": (
        "proposed",
        "expression of interest",
        "eoi",
        "make an offer",
        "submit offer",
    ),
    "tender": ("tender", "tender closes"),
    "enquire": ("enquire", "enquiry", "enquiry now", "enquire now"),
}

_PLACEHOLDER_MEDIA = {
    "/PicklesAuctions/images/watchlist-img.png",
}


def _price_in_bounds(value: int) -> bool:
    return 500 <= value <= 500_000


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
    buy_method: Optional[str] = None,
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
    # Merge in explicit buy method filter if requested
    if buy_method and buy_method.lower() == "buy_now":
        if not filters:
            filters = {"buyMethod": ["Buy Now"]}
        else:
            # Append without overwriting any existing buyMethod if present
            vals = filters.get("buyMethod", [])
            if "Buy Now" not in vals:
                filters["buyMethod"] = vals + ["Buy Now"]
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


def _client_headers(ua: str) -> Dict[str, str]:
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.9",
        "Referer": BASE,
        "Sec-Fetch-Mode": "navigate",
    }


def _has_anti_bot(html: str) -> bool:
    s = (html or "").lower()
    needles = [
        "access denied",
        "request blocked",
        "bot detected",
        "captcha",
        "unusual traffic",
    ]
    return any(n in s for n in needles)


def fetch_html(url: str, debug: bool = False) -> str:
    last_err: Optional[str] = None
    for i, ua in enumerate(_UA_ROTATE[:2]):  # single retry with a different UA
        headers = _client_headers(ua)
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=15.0) as client:
                # Warmup to set cookies
                try:
                    client.get(BASE, headers=headers)
                except Exception:
                    pass
                r = client.get(url, headers=headers)
                status = r.status_code
                text = r.text
                if debug:
                    print(f"DEBUG pickles status={status} len={len(text)} url={r.request.url}")
                    # Preview first 200 chars from title/body
                    try:
                        soup = BeautifulSoup(text, "html.parser")
                        title = (soup.title.get_text(strip=True) if soup.title else "")
                        preview = title or soup.get_text(" ", strip=True)
                        preview = preview[:200].replace("\n", " ")
                        print(f"DEBUG pickles preview: {preview}")
                    except Exception:
                        print("DEBUG pickles preview: <parse error>")
                    # Save snapshot
                    try:
                        from pathlib import Path

                        snap_dir = Path(__file__).resolve().parents[2] / "storage" / "snapshots"
                        snap_dir.mkdir(parents=True, exist_ok=True)
                        (snap_dir / "pickles_page1.html").write_text(text, encoding="utf-8")
                    except Exception:
                        pass
                if status in (403, 429):
                    last_err = f"HTTP {status}"
                    continue  # try next UA once
                if status != 200:
                    raise RuntimeError(f"http {status}")
                if _has_anti_bot(text):
                    raise RuntimeError("anti-bot page detected; retry with different UA")
                return text
        except Exception as e:
            last_err = str(e)
            continue
    raise RuntimeError(f"fetch failed: {last_err or 'unknown error'} (try a different UA)")


def _abs(href: str) -> str:
    return urljoin(BASE, href)


def _page_delay_seconds() -> float:
    try:
        min_ms = int(os.getenv("PICKLES_PAGE_DELAY_MIN_MS", "400"))
        max_ms = int(os.getenv("PICKLES_PAGE_DELAY_MAX_MS", "800"))
    except ValueError:
        min_ms, max_ms = 400, 800
    if max_ms < min_ms:
        max_ms = min_ms
    return random.uniform(min_ms, max_ms) / 1000.0


def _price_from_text(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    m = _PRICE_REGEX.search(text)
    if not m:
        return None
    num = m.group(1).strip()
    cleaned = re.sub(r"[ ,]", "", num)
    if not cleaned:
        return None
    if "." in cleaned:
        cleaned = cleaned.split(".", 1)[0]
    cleaned = re.sub(r"[^0-9]", "", cleaned)
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except Exception:
        return None


def _match_sale_method(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    low = text.lower()
    for method, keywords in _SALE_METHOD_KEYWORDS.items():
        for kw in keywords:
            if kw in low:
                return method
    return None


def _extract_spec_pairs(soup: BeautifulSoup) -> Dict[str, str]:
    specs: Dict[str, str] = {}
    # Definition lists
    for dl in soup.find_all("dl"):
        terms = dl.find_all("dt")
        values = dl.find_all("dd")
        for dt, dd in zip(terms, values):
            key = dt.get_text(" ", strip=True).lower()
            val = dd.get_text(" ", strip=True)
            if key and val and key not in specs:
                specs[key] = val
    # Tables (th/td, td/td)
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) != 2:
            continue
        key = cells[0].get_text(" ", strip=True).lower()
        val = cells[1].get_text(" ", strip=True)
        if key and val and key not in specs:
            specs[key] = val
    return specs


def _search_patterns(text: str, patterns: List[str]) -> Optional[str]:
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _clean_media_urls(urls: List[str]) -> List[str]:
    seen: set[str] = set()
    cleaned: List[str] = []
    for url in urls:
        if not url:
            continue
        u = url.strip()
        if not u or u in seen:
            continue
        if any(ph in u for ph in _PLACEHOLDER_MEDIA):
            continue
        if u.startswith("//"):
            u = "https:" + u
        cleaned.append(u)
        seen.add(u)
    return cleaned


def _detect_sale_method(soup: BeautifulSoup, body_text: str) -> Optional[str]:
    text_candidates: List[str] = []
    for tag in soup.select('[data-testid], a, button'):  # gather explicit call-to-action text
        txt = tag.get_text(" ", strip=True)
        if txt:
            text_candidates.append(txt)
        href = tag.get("href") or ""
        if href:
            text_candidates.append(href)
    text_candidates.append(body_text)

    # Prioritise explicit enquire cues
    for txt in text_candidates:
        method = _match_sale_method(txt)
        if method:
            return method
    return None


def _guess_make_model(title: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not title:
        return None, None
    tokens = re.findall(r"[A-Za-z0-9']+", title)
    if not tokens:
        return None, None
    idx = 0
    if re.match(r"^(19|20)\d{2}$", tokens[0]):
        idx += 1
    if idx >= len(tokens):
        return None, None
    make = tokens[idx]
    idx += 1
    model = tokens[idx] if idx < len(tokens) else None
    return make, model


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
            addr = d.get("address") if isinstance(d, dict) else None
            state_guess = None
            suburb_guess = None
            if isinstance(addr, dict):
                if isinstance(addr.get("addressRegion"), str):
                    state_guess = addr.get("addressRegion")
                if isinstance(addr.get("addressLocality"), str):
                    suburb_guess = addr.get("addressLocality")
            if isinstance(offers, dict):
                price_str = offers.get("price") or offers.get("priceCurrency")
                price_val = offers.get("price")
            price_int = _coerce_price_value(price_val if price_val is not None else price_str)
            rows.append(
                {
                    "title": title,
                    "price_str": str(price_val or price_str) if (price_val or price_str) else None,
                    "price": price_int,
                    "url": _abs(url),
                    "thumb": None,
                    "location": state_guess,
                    "state": state_guess,
                    "suburb": suburb_guess,
                    "year_guess": None,
                    "make_guess": None,
                    "model_guess": None,
                    "source_id_guess": None,
                    "sale_method": "buy_now" if price_int is not None else None,
                }
            )
    return rows


def _is_vehicle_href(href: str) -> bool:
    if not href:
        return False
    # Discard obvious non-vehicle paths
    bad_paths = (
        "/",
        "/home",
        "/about",
        "/contact",
        "/locations",
        "/auctions",
        "/sell",
        "/finance",
    )
    if href in bad_paths:
        return False
    # Known good forms
    if re.match(r"^/used/details/cars/[^/]+/[0-9A-Za-z-]+$", href, re.IGNORECASE):
        return True
    pat_strong = re.compile(r"^/cars/item/[^/?#]+/?$", re.IGNORECASE)
    if pat_strong.match(href):
        return True
    # More tolerant: contains /cars/ and ends with a token
    if "/cars/" in href:
        tail = href.split("?", 1)[0].rstrip("/").split("/")[-1]
        if re.match(r"[A-Za-z0-9_-]{6,}$", tail):
            return True
    return False


def _is_blacklisted_href(href: str) -> bool:
    if not href:
        return True
    if re.match(r"^https?://", href) and not href.startswith(BASE):
        return True
    if re.match(r"^/used/search/", href, re.IGNORECASE):
        return True
    if re.match(r"^/$|^/home/?$", href, re.IGNORECASE):
        return True
    bad_terms = ("office", "contact", "help", "terms", "privacy")
    low = href.lower()
    if any(bt in low for bt in bad_terms):
        return True
    return False


def _extract_fields_from_card(a: Any) -> Tuple[str, Dict[str, Any]]:
    href = a.get("href") or ""
    url = _abs(href.split("?", 1)[0])
    sid = href.rstrip("/").split("/")[-1]
    # Title from heading or attribute within card; fallback to anchor text
    title = None
    card = a
    for _ in range(3):
        if getattr(card, "parent", None):
            card = card.parent
    title_el = card.select_one("h3, h2, .title, [aria-label]")
    if title_el:
        t = title_el.get_text(" ", strip=True) if hasattr(title_el, "get_text") else None
        if not t and getattr(title_el, "has_attr", lambda *_: False)("aria-label"):
            t = title_el.get("aria-label")
        cand = (t or "").strip()
        low = cand.lower()
        if low and not ("view" in low and "photo" in low):
            title = cand or None
    if not title:
        title = (a.get_text(" ", strip=True) or "").strip()
    text = card.get_text(" ", strip=True)
    # Price
    price_str = None
    price_el = card.select_one("[data-testid*='price'], .price, .price__value, .Price")
    if price_el:
        pt = price_el.get_text(" ", strip=True)
        if re.search(r"\$[\s0-9,\.]+", pt):
            price_str = re.search(r"\$[\s0-9,\.]+", pt).group(0)
    if not price_str:
        mprice = re.search(r"\$[\s0-9,\.]+", text)
        if mprice:
            price_str = mprice.group(0)
    price_val = _digits_to_int(price_str)
    # Location/state token
    location = None
    mstate = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", text)
    if mstate:
        location = mstate.group(1)
    # Sale method detection from card text/badges
    sale_method = _match_sale_method(text)
    # Thumb
    thumb = None
    img = card.find("img")
    if img:
        thumb = img.get("data-src") or img.get("src") or (img.get("srcset") or "").split(" ")[0]
        if thumb and thumb.startswith("//"):
            thumb = "https:" + thumb
    # Year guess from title
    yguess = None
    my = re.search(r"\b(19\d{2}|20\d{2})\b", title)
    if my:
        yguess = my.group(1)
    make_guess, model_guess = _guess_make_model(title)
    return url, {
        "url": url,
        "source_id_guess": sid,
        "title": title,
        "price_str": price_str,
        "price": price_val,
        "thumb": thumb,
        "location": location,
        "state": location,
        "sale_method": sale_method,
        "year_guess": yguess,
        "make_guess": make_guess,
        "model_guess": model_guess,
    }


def _extract_by_containers(
    soup: BeautifulSoup,
    limit: int,
    counters: Counter,
    debug: bool,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    container_sel = [
        "section[class*='results']",
        "div[class*='results']",
        "div[class*='search']",
    ]
    item_sel = [
        "article a[href]",
        "li a[href]",
        "div a[href]",
    ]
    seen: set[str] = set()
    for csel in container_sel:
        for cont in soup.select(csel):
            for isel in item_sel:
                for a in cont.select(isel):
                    href = a.get("href") or ""
                    if not _is_vehicle_href(href):
                        continue
                    # Filter out office/homepage-like titles
                    tx = (a.get_text(" ", strip=True) or "").lower()
                    if any(x in tx for x in ["main office", "contact", "home"]):
                        continue
                    try:
                        url, data = _extract_fields_from_card(a)
                    except Exception as exc:
                        counters["dropped_parse_error"] += 1
                        if debug:
                            print(f"DEBUG pickles drop[parse_error]: selector={isel} error={exc}")
                        continue
                    if url in seen:
                        counters["dropped_duplicate"] += 1
                        if debug:
                            print(f"DEBUG pickles drop[duplicate]: url={url}")
                        continue
                    seen.add(url)
                    rows.append(data)
                    if len(rows) >= limit:
                        return rows
    return rows


def _digits_to_int(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    if isinstance(s, (int, float)):
        try:
            return int(float(s))
        except Exception:
            return None
    price = _price_from_text(str(s))
    if price is not None:
        return price
    m = re.search(r"(\d[\d,\.]*)", str(s))
    if not m:
        return None
    digits = re.sub(r"[^0-9]", "", m.group(1))
    return int(digits) if digits else None


def _coerce_price_value(val: Any) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            return int(float(val))
        except Exception:
            return None
    return _digits_to_int(str(val))


def _collect_ldjson_dicts(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(sc.string or "{}")
        except Exception:
            continue
        if isinstance(data, list):
            docs.extend([d for d in data if isinstance(d, dict)])
        elif isinstance(data, dict):
            docs.append(data)
    return docs


def get_price_from_detail(
    html: str,
    *,
    soup: Optional[BeautifulSoup] = None,
    ldjson_docs: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Optional[int], Dict[str, bool]]:
    created = False
    if soup is None:
        soup = BeautifulSoup(html, "html.parser")
        created = True
    if ldjson_docs is None:
        ldjson_docs = _collect_ldjson_dicts(soup)
    price_val: Optional[int] = None
    flags = {"ldjson": False, "meta": False, "text": False}

    for d in ldjson_docs:
        if not isinstance(d, dict):
            continue
        offers = d.get("offers")
        if isinstance(offers, list):
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                price_val = _coerce_price_value(offer.get("price") or offer.get("lowPrice") or offer.get("highPrice"))
                if price_val is not None:
                    flags["ldjson"] = True
                    break
            if price_val is not None:
                break
        elif isinstance(offers, dict):
            price_val = _coerce_price_value(offers.get("price") or offers.get("lowPrice") or offers.get("highPrice"))
            if price_val is not None:
                flags["ldjson"] = True
                break
        if price_val is None:
            price_val = _coerce_price_value(d.get("price"))
            if price_val is not None:
                flags["ldjson"] = True
                break

    if price_val is None:
        meta_selectors = [
            ("meta[itemprop='price']", "content"),
            ("meta[property='og:price:amount']", "content"),
            ("meta[property='product:price:amount']", "content"),
            ("meta[name='twitter:data1']", "content"),
        ]
        for sel, attr in meta_selectors:
            el = soup.select_one(sel)
            if not el:
                continue
            raw = el.get(attr)
            price_val = _coerce_price_value(raw)
            if price_val is not None:
                flags["meta"] = True
                break

    if price_val is None:
        priority_nodes = []
        for sel in [
            "#item-buy-now-price",
            "[id*='buy-now-price']",
            "[data-testid*='buy-now-price']",
        ]:
            el = soup.select_one(sel)
            if el and el.get_text(" ", strip=True):
                priority_nodes.append(el.get_text(" ", strip=True))
        if priority_nodes:
            values = []
            for txt in priority_nodes:
                val = _price_from_text(txt)
                if val is not None:
                    values.append(val)
            if values:
                price_val = max(values)
                flags["text"] = True

    if price_val is None:
        price_nodes = soup.select(
            "[data-testid*='price'], .price, .price__value, .Price, [class*='price'], [id*='price']"
        )
        texts: List[str] = [pn.get_text(" ", strip=True) for pn in price_nodes if pn.get_text(" ", strip=True)]
        if not texts:
            global_text = soup.get_text(" ", strip=True)
            if global_text:
                texts.append(global_text)
        values = []
        for txt in texts:
            for match in _PRICE_REGEX.finditer(txt):
                candidate = _price_from_text(match.group(0))
                if candidate is not None:
                    values.append(candidate)
        if values:
            price_val = max(values)
            flags["text"] = True

    if created:
        # Allow soup to be garbage collected quicker
        del soup
    return price_val, flags


def get_sale_method(
    html: str,
    *,
    soup: Optional[BeautifulSoup] = None,
    ldjson_docs: Optional[List[Dict[str, Any]]] = None,
) -> Optional[str]:
    if soup is None:
        soup = BeautifulSoup(html, "html.parser")
    if ldjson_docs is None:
        ldjson_docs = _collect_ldjson_dicts(soup)

    for d in ldjson_docs:
        try:
            as_text = json.dumps(d, ensure_ascii=False)
        except Exception:
            continue
        method = _match_sale_method(as_text)
        if method:
            return method
        offers = d.get("offers") if isinstance(d, dict) else None
        if isinstance(offers, dict):
            method = _match_sale_method(json.dumps(offers, ensure_ascii=False))
            if method:
                return method
        elif isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict):
                    method = _match_sale_method(json.dumps(offer, ensure_ascii=False))
                    if method:
                        return method

    selectors = [
        "[class*='badge']",
        "[class*='label']",
        "[class*='chip']",
        "[data-testid*='sale']",
        "[data-testid*='buy']",
        ".buy-now",
        ".buyNow",
        ".sale-method",
    ]
    for sel in selectors:
        for el in soup.select(sel):
            method = _match_sale_method(el.get_text(" ", strip=True))
            if method:
                return method

    price_el = soup.select_one("[data-testid*='price'], .price, .price__value, .Price")
    if price_el:
        method = _match_sale_method(price_el.get_text(" ", strip=True))
        if method:
            return method

    for el in soup.select("a, button, [role='button']"):
        txt = el.get_text(" ", strip=True)
        if not txt:
            continue
        method = _match_sale_method(txt)
        if method:
            return method

    body_snippet = soup.get_text(" ", strip=True)
    return _match_sale_method(body_snippet)



def _parse_detail_html(html: str, debug: bool = False) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    ldjson_docs = _collect_ldjson_dicts(soup)
    ld_count = len(ldjson_docs)

    price_val, price_flags = get_price_from_detail(html, soup=soup, ldjson_docs=ldjson_docs)
    sale_method = get_sale_method(html, soup=soup, ldjson_docs=ldjson_docs)
    body_text = soup.get_text(" ", strip=True)
    if not sale_method:
        sale_method = _detect_sale_method(soup, body_text)

    title: Optional[str] = None
    images: List[str] = []
    year_val: Optional[int] = None
    state_val: Optional[str] = None
    suburb_val: Optional[str] = None
    make_guess: Optional[str] = None
    model_guess: Optional[str] = None

    for d in ldjson_docs:
        if not isinstance(d, dict):
            continue
        if not title:
            title = (d.get("name") or d.get("title"))
        address = d.get("address")
        if isinstance(address, dict):
            if not suburb_val and isinstance(address.get("addressLocality"), str):
                suburb_val = address.get("addressLocality")
            if not state_val and isinstance(address.get("addressRegion"), str):
                state_val = address.get("addressRegion")
        brand = d.get("brand")
        if not make_guess:
            if isinstance(brand, dict) and isinstance(brand.get("name"), str):
                make_guess = brand.get("name")
            elif isinstance(brand, str):
                make_guess = brand
        if not model_guess and isinstance(d.get("model"), str):
            model_guess = d.get("model")
        img = d.get("image")
        if isinstance(img, list):
            for u in img:
                if isinstance(u, str):
                    images.append(u)
        elif isinstance(img, str):
            images.append(img)
        if not year_val:
            for key in ("modelDate", "vehicleModelDate", "productionDate", "releaseDate"):
                val = d.get(key)
                if not val:
                    continue
                ym = re.search(r"(19\d{2}|20\d{2})", str(val))
                if ym:
                    try:
                        year_val = int(ym.group(1))
                    except Exception:
                        pass
                if year_val:
                    break

    if not title:
        h1 = soup.find(["h1", "h2"])
        if h1:
            title = h1.get_text(" ", strip=True)
    if not title:
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            title = og.get("content")

    if title and not year_val:
        my = re.search(r"\b(19\d{2}|20\d{2})\b", title)
        if my:
            try:
                year_val = int(my.group(1))
            except Exception:
                pass

    if title:
        mg, md = _guess_make_model(title)
        if mg and not make_guess:
            make_guess = mg
        if md and not model_guess:
            model_guess = md

    if not (state_val or suburb_val):
        loc_el = soup.select_one("[data-testid*='location'], .vehicle-location, .listing-location")
        if loc_el:
            loc_text = loc_el.get_text(" ", strip=True)
            mloc = re.search(r"\b([A-Za-z][A-Za-z\-\s]{2,}),?\s+(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", loc_text)
            if mloc:
                suburb_val = suburb_val or mloc.group(1).strip()
                state_val = state_val or mloc.group(2)

    mloc_body = re.search(r"\b([A-Za-z][A-Za-z\-\s]{2,}),?\s+(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", body_text)
    if mloc_body:
        if not suburb_val:
            suburb_val = mloc_body.group(1).strip()
        if not state_val:
            state_val = mloc_body.group(2)
    elif not state_val:
        ms = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", body_text)
        if ms:
            state_val = ms.group(1)

    if not sale_method and price_val is not None:
        sale_method = "buy_now"

    specs = _extract_spec_pairs(soup)

    def spec_value(*keys: str) -> Optional[str]:
        for key in keys:
            val = specs.get(key.lower())
            if val:
                return val
        return None

    odometer_text = spec_value("odometer", "kilometres", "kilometers")
    if not odometer_text:
        odometer_text = _search_patterns(body_text, [r"odometer[:\s]*([0-9,\.]+)\s*(?:km|kms)", r"([0-9,\.]+)\s*(?:km|kms)\b"])
    odometer_val: Optional[int] = None
    if odometer_text:
        odometer_val = _digits_to_int(odometer_text)

    body_val = spec_value("body", "body type")
    if not body_val:
        body_val = _search_patterns(body_text, [r"body(?: type)?[:\s]*([A-Za-z0-9 /-]{3,30})"])

    trans_val = spec_value("transmission")
    if not trans_val:
        trans_val = _search_patterns(body_text, [r"transmission[:\s]*([A-Za-z0-9 /-]{3,30})"])

    fuel_val = spec_value("fuel", "fuel type")
    if not fuel_val:
        fuel_val = _search_patterns(body_text, [r"fuel(?: type)?[:\s]*([A-Za-z0-9 /-]{3,30})"])

    engine_val = spec_value("engine", "engine size")
    if not engine_val:
        engine_val = _search_patterns(body_text, [r"engine[:\s]*([A-Za-z0-9\./ -]{2,20})"])

    drive_val = spec_value("drive", "drivetrain", "driveline")
    if not drive_val:
        drive_val = _search_patterns(body_text, [r"(?:drive|drivetrain)[:\s]*([A-Za-z0-9/ -]{3,15})"])

    variant_val = spec_value("variant", "trim")
    if not variant_val:
        variant_val = _search_patterns(body_text, [r"variant[:\s]*([A-Za-z0-9 /-]{2,40})"])

    dom_media: List[str] = []
    for selector in [
        "[data-testid*='image'] img",
        "[data-testid*='gallery'] img",
        "pds-gallery img",
        "img",
    ]:
        for img in soup.select(selector):
            src = (
                img.get("data-src")
                or img.get("data-lazy")
                or (img.get("data-srcset") or "").split(" ")[0]
                or img.get("src")
            )
            if src:
                dom_media.append(src)
        if len(dom_media) >= 6:
            break

    images.extend(dom_media)
    images = _clean_media_urls(images)[:6]

    out: Dict[str, Any] = {}
    if title:
        out["title"] = title
    if price_val is not None:
        out["price"] = price_val
        out["price_str"] = str(price_val)
    if sale_method:
        out["sale_method"] = sale_method
    if year_val is not None:
        out["year_guess"] = str(year_val)
    if state_val:
        out["state"] = state_val
    if suburb_val:
        out["suburb"] = suburb_val
    if images:
        out["images"] = images
    if make_guess:
        out["make_guess"] = make_guess
    if model_guess:
        out["model_guess"] = model_guess
    if odometer_val is not None:
        out["odometer"] = odometer_val
    if body_val:
        out["body"] = body_val
    if trans_val:
        out["trans"] = trans_val
    if fuel_val:
        out["fuel"] = fuel_val
    if engine_val:
        out["engine"] = engine_val
    if drive_val:
        out["drive"] = drive_val
    if variant_val:
        out["variant"] = variant_val

    if debug:
        print(
            "DEBUG pickles hydrate parse: ldjson=%d meta_price=%s text_price=%s title='%s' price=%s year=%s state='%s' suburb='%s' sale_method=%s"
            % (
                ld_count,
                str(price_flags.get("meta", False)).lower(),
                str(price_flags.get("text", False)).lower(),
                (title or "")[:60],
                price_val if price_val is not None else "",
                year_val if year_val is not None else "",
                (state_val or "") or "",
                (suburb_val or "") or "",
                sale_method or "",
            )
        )
    return out

def _hydrate_detail(url: str, debug: bool = False) -> Dict[str, Any]:
    html = fetch_html(url, debug=False)
    return _parse_detail_html(html, debug=debug)


async def _async_hydrate_many(urls: List[str], concurrency: int, debug: bool = False) -> Dict[str, Dict[str, Any]]:
    if concurrency <= 0:
        concurrency = 1
    results: Dict[str, Dict[str, Any]] = {}
    headers = _client_headers(_UA_ROTATE[0])
    timeout = httpx.Timeout(15.0)
    sem = asyncio.Semaphore(concurrency)

    async def fetch_one(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
        for attempt in range(2):
            try:
                async with sem:
                    await asyncio.sleep(random.uniform(0.3, 0.6))
                    resp = await client.get(url)
                resp.raise_for_status()
                return _parse_detail_html(resp.text, debug=debug)
            except Exception as exc:
                if debug:
                    print(f"DEBUG pickles hydrate error: url={url} attempt={attempt + 1} err={exc}")
                if attempt == 0:
                    await asyncio.sleep(0.6 + random.uniform(0.2, 0.4))
                    continue
                return {}
        return {}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout) as client:
        tasks = {url: asyncio.create_task(fetch_one(client, url)) for url in urls}
        for url, task in tasks.items():
            try:
                results[url] = await task
            except Exception as exc:  # should be rare since fetch_one handles
                if debug:
                    print(f"DEBUG pickles hydrate uncaught error: url={url} err={exc}")
                results[url] = {}
    return results


def _merge_detail(row: Dict[str, Any], detail: Dict[str, Any]) -> None:
    if not detail:
        return
    for key in [
        "title",
        "price_str",
        "price",
        "year_guess",
        "state",
        "suburb",
        "sale_method",
        "make_guess",
        "model_guess",
    ]:
        if detail.get(key):
            row[key] = detail[key]
    if detail.get("images"):
        row["images"] = detail["images"]
        if not row.get("thumb") and detail["images"]:
            row["thumb"] = detail["images"][0]
    for field in ["odometer", "body", "trans", "fuel", "engine", "drive", "variant"]:
        if detail.get(field) not in (None, ""):
            row[field] = detail[field]
    if detail.get("location") and not row.get("location"):
        row["location"] = detail["location"]


def search_pickles(
    *,
    make: Optional[str],
    model: Optional[str],
    state: Optional[str],
    suburb: Optional[str] = None,
    query: Optional[str] = None,
    pages: int = 1,
    limit: Optional[int] = None,
    filters: Optional[Dict[str, List[str]]] = None,
    double_encode_filter: bool = False,
    buy_method: Optional[str] = None,
    hydrate: bool = False,
    hydrate_concurrency: int = 4,
    debug: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, int], Dict[str, int]]:
    pages = max(1, int(pages or 1))
    remaining = limit if limit and limit > 0 else None
    counters: Counter = Counter()
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    pages_walked = 0
    assume_buy_now = (buy_method or "").lower() == "buy_now"

    for page in range(1, pages + 1):
        if page > 1:
            delay = _page_delay_seconds()
            if debug:
                print(f"DEBUG pickles page-delay: sleeping {delay:.2f}s before page {page}")
            time.sleep(delay)

        page_limit = remaining if remaining is not None else None
        search_url = build_search_url(
            make,
            model,
            state,
            suburb=suburb,
            query=query,
            page=page,
            limit=page_limit,
            filters=filters,
            double_encode_filter=double_encode_filter,
            buy_method=buy_method,
        )
        if debug:
            print(f"DEBUG pickles page={page} url={search_url}")
        try:
            html = fetch_html(search_url, debug=debug)
        except Exception as exc:
            if debug:
                print(f"DEBUG pickles page fetch failed (page={page}): {exc}")
            break

        try:
            page_rows, page_counters = parse_list(
                html,
                limit=page_limit or 1000,
                debug=debug,
                hydrate=False,
                assume_buy_now=assume_buy_now,
            )
        except RuntimeError as exc:
            if debug:
                print(f"DEBUG pickles page parse stop (page={page}): {exc}")
            break
        counters.update(page_counters)
        pages_walked += 1

        new_rows = 0
        for row in page_rows:
            url = row.get("url")
            if not url or url in seen:
                counters["dropped_duplicate"] += 1
                continue
            seen.add(url)
            rows.append(row)
            new_rows += 1
            if remaining is not None:
                remaining -= 1
                if remaining <= 0:
                    break
        if debug:
            print(f"DEBUG pickles page {page} new_rows={new_rows} total_rows={len(rows)}")
        if remaining is not None and remaining <= 0:
            break
        if new_rows == 0:
            break

    metadata = {
        "pages_walked": pages_walked,
    }

    if not rows:
        counters["hydrated"] = 0
        return rows, dict(counters), metadata

    if hydrate:
        urls = [r["url"] for r in rows if r.get("url")]
        detail_map = asyncio.run(_async_hydrate_many(urls, hydrate_concurrency, debug=debug))
        hydrated_count = 0
        for row in rows:
            detail = detail_map.get(row["url"], {})
            if detail:
                hydrated_count += 1
                _merge_detail(row, detail)
        counters["hydrated"] = hydrated_count
    else:
        counters["hydrated"] = 0

    sale_enquire = 0
    enquire_unpriced = 0
    for row in rows:
        if row.get("price") is None and row.get("price_str"):
            row["price"] = _digits_to_int(row["price_str"])
        sale_method = (row.get("sale_method") or "").lower()
        if sale_method == "enquire":
            sale_enquire += 1
            if row.get("price") is None:
                enquire_unpriced += 1

        year_val = None
        if row.get("year_guess"):
            try:
                year_val = int(str(row["year_guess"]))
            except Exception:
                year_val = None

        price_val = row.get("price") if isinstance(row.get("price"), int) else None
        flags = {
            "has_year": year_val is not None,
            "has_state": bool(row.get("state")),
            "has_price": price_val is not None,
            "price": price_val,
            "year": year_val,
            "price_in_bounds": price_val is not None and _price_in_bounds(price_val),
            "price_in_range": price_val is not None and _price_in_bounds(price_val),
            "year_in_range": year_val is not None,
            "is_enquire": sale_method == "enquire",
            "sale_method": sale_method,
        }
        row["flags"] = flags

    counters["sale_method_enquire"] += sale_enquire
    counters["enquire_unpriced"] += enquire_unpriced
    counters["kept_real"] = len(rows)

    return rows, dict(counters), metadata
def parse_list(
    html: str,
    limit: int,
    debug: bool = False,
    hydrate: bool = False,
    assume_buy_now: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    soup = BeautifulSoup(html, "html.parser")
    counters: Counter = Counter()
    rows: List[Dict[str, Any]] = []

    # Strategy A: container-guided extraction
    rows_a = _extract_by_containers(soup, limit, counters, debug)
    # Strategy B: href whitelist across all anchors
    rows_b: List[Dict[str, Any]] = []
    if not rows_a or len(rows_a) < limit:
        seen_b: set[str] = set(x.get("url") for x in rows_a)
        for a in soup.find_all("a", href=True):
            href = a.get("href") or ""
            if not _is_vehicle_href(href):
                continue
            tx = (a.get_text(" ", strip=True) or "").lower()
            if any(x in tx for x in ["main office", "contact", "home"]):
                continue
            try:
                url, data = _extract_fields_from_card(a)
            except Exception as exc:
                counters["dropped_parse_error"] += 1
                if debug:
                    print(f"DEBUG pickles drop[parse_error]: url={href} error={exc}")
                continue
            if url in seen_b:
                counters["dropped_duplicate"] += 1
                if debug:
                    print(f"DEBUG pickles drop[duplicate]: url={url}")
                continue
            rows_b.append(data)
            seen_b.add(url)
            if len(rows_a) + len(rows_b) >= limit:
                break

    # Strategy C: JSON-LD structured data as last resort
    rows_c: List[Dict[str, Any]] = []
    if (not rows_a and not rows_b) or (len(rows_a) + len(rows_b) < limit):
        rows_c = _from_jsonld(soup)
        # constrain to vehicle-like URLs
        rows_c = [r for r in rows_c if "/cars/" in (r.get("url") or "")]

    # Combine and filter
    combined: List[Dict[str, Any]] = []
    seen_all: set[str] = set()
    for bucket in (rows_a, rows_b, rows_c):
        for r in bucket:
            url = r.get("url") or ""
            if not url or url in seen_all:
                if url in seen_all:
                    counters["dropped_duplicate"] += 1
                    if debug:
                        print(f"DEBUG pickles drop[duplicate]: url={url}")
                continue
            if url.rstrip("/") == BASE:
                continue
            # Final whitelist: must include /cars/
            if "/cars/" not in url:
                continue
            # Filter out office/homepage-like titles
            title = (r.get("title") or "").lower()
            if any(x in title for x in ["main office", "contact"]):
                continue
            seen_all.add(url)
            combined.append(r)
            if len(combined) >= limit:
                break
        if len(combined) >= limit:
            break

    # Post-filter: keep real details pages only; drop categories/search
    kept_real: List[Dict[str, Any]] = []
    for r in combined:
        u = r.get("url") or ""
        href_rel = u.replace(BASE, "") if u.startswith(BASE) else u
        if _is_blacklisted_href(href_rel):
            counters["dropped_category"] += 1
            if debug:
                print(f"DEBUG pickles drop[category]: url={u}")
            continue
        if not _is_vehicle_href(href_rel):
            counters["dropped_category"] += 1
            if debug:
                print(f"DEBUG pickles drop[category]: url={u}")
            continue
        kept_real.append(r)

    for r in kept_real:
        if r.get("price") is None and r.get("price_str"):
            r["price"] = _digits_to_int(r["price_str"])
        if r.get("state"):
            r["state"] = str(r["state"]).strip().upper()
            if not r.get("location"):
                r["location"] = r["state"]
        if assume_buy_now and r.get("price") is not None and not r.get("sale_method"):
            r["sale_method"] = "buy_now"
        if r.get("price") is not None and not r.get("price_str"):
            r["price_str"] = str(r["price"])

    hydrated = 0

    if debug:
        print(
            f"DEBUG pickles tiles: primary={len(rows_a)} fallback_href={len(rows_b)} ldjson={len(rows_c)} kept={len(combined)}"
        )
        drop_summary = [
            f"dropped_category={counters.get('dropped_category', 0)}",
            f"dropped_duplicate={counters.get('dropped_duplicate', 0)}",
            f"dropped_price_out_of_range={counters.get('dropped_price_out_of_range', 0)}",
            f"dropped_parse_error={counters.get('dropped_parse_error', 0)}",
        ]
        print(
            "DEBUG pickles kept_real=%d hydrated=%d %s"
            % (len(kept_real), hydrated, " ".join(drop_summary))
        )

    if not kept_real:
        raise RuntimeError("no tiles (pickles)")

    counters["kept_real"] = len(kept_real)
    return kept_real, dict(counters)


def to_raw(row: Dict[str, Any]) -> Dict[str, Any]:
    return row
