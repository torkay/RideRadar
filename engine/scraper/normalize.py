import os
import re
from typing import Any, Dict, Optional


_BAD_GUESS_TOKENS = {"buy", "now", "price", "view", "photos", "more"}
_PICKLES_BASE = "https://www.pickles.com.au"


def _to_int(text: Any) -> Optional[int]:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        try:
            return int(text)
        except Exception:
            return None
    s = str(text)
    digits = re.sub(r"[^0-9]", "", s)
    return int(digits) if digits else None


def _extract_trailing_token(url: str, fallback: str) -> str:
    m = re.search(r"([A-Za-z0-9_-]{8,})/?$", url or "")
    if m:
        return m.group(1)
    return fallback or "unknown"


def _upper_state(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip().upper()
    # keep simple 2–3 letter codes
    if 2 <= len(s) <= 3:
        return s
    return None


def _canon_base(source: str, source_id: str, source_url: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": source,
        "source_id": source_id,
        "source_url": source_url,
        "make": None,
        "model": None,
        "variant": None,
        "year": None,
        "price": None,
        "odometer": None,
        "state": None,
        "suburb": None,
        "postcode": None,
        "media": [],
        "seller": {},
        "raw": raw,
        "status": "active",
    }


def _format_guess(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    parts = re.split(r"[-_/]", value.strip())
    cleaned = [p for p in parts if p and p.strip().lower() not in _BAD_GUESS_TOKENS]
    if not cleaned:
        return None
    return " ".join(w.capitalize() for w in cleaned)


def _absolutize_url(url: Optional[str]) -> Optional[str]:
    if not url or not isinstance(url, str):
        return None
    trimmed = url.strip()
    if not trimmed:
        return None
    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        return trimmed
    if trimmed.startswith("//"):
        return "https:" + trimmed
    if trimmed.startswith("/"):
        return _PICKLES_BASE + trimmed
    return trimmed


def _absolutize_media(media: Optional[list]) -> list:
    if not media:
        return []
    absolutized = []
    for item in media:
        abs_url = _absolutize_url(item)
        if abs_url and "watchlist" not in abs_url:
            absolutized.append(abs_url)
    return absolutized


def normalize_pickles(item: Dict[str, Any]) -> Dict[str, Any]:
    url = (item.get("url") or item.get("link") or "").strip()
    if not url:
        raise ValueError("missing source_url")
    # Hard guard: allow only real detail pages
    if not (
        re.search(r"/used/details/cars/[^/]+/[0-9A-Za-z-]+$", url)
        or re.search(r"/cars/item/[^/?#]+/?$", url)
    ):
        raise ValueError("non-listing url")
    source = "pickles"
    source_id = item.get("source_id_guess") or _extract_trailing_token(url, (item.get("title") or ""))
    if not source_id:
        raise ValueError("missing source_id")

    out = _canon_base(source, source_id, url, item)
    # Sale method passthrough (canonicalized)
    smap = {"buy_now": "buy_now", "auction": "auction", "proposed": "proposed", "tender": "tender"}
    enable_sale_method = os.getenv("LISTINGS_ENABLE_SALE_METHOD_COLUMN", "").lower() in ("1", "true", "yes")
    sm = item.get("sale_method")
    if isinstance(sm, str):
        sm_l = sm.strip().lower().replace(" ", "_")
        if sm_l in smap:
            sale_method_norm = smap[sm_l]
            item["sale_method"] = sale_method_norm
            if enable_sale_method:
                out["sale_method"] = sale_method_norm
        else:
            sale_method_norm = None
    else:
        sale_method_norm = None
    # Attempt a very light year parse from title or explicit year_guess
    title = item.get("title") or ""
    if item.get("year_guess"):
        try:
            yg = int(str(item["year_guess"]))
            out["year"] = yg
        except Exception:
            pass
    m = re.search(r"\b(20\d{2}|19\d{2})\b", title)
    if m:
        out["year"] = _to_int(m.group(1))

    # Image/media (prefer list of images if present, else thumb)
    media_urls = []
    if item.get("images") and isinstance(item.get("images"), list):
        media_urls.extend(item["images"][:3])
    elif item.get("thumb"):
        media_urls.append(item["thumb"])
    out["media"] = _absolutize_media(media_urls)

    # Odometer if provided in card/detail (km)
    if item.get("odometer") is not None:
        out["odometer"] = _to_int(item["odometer"])

    # Price if present (prefer explicit int)
    if item.get("price") is not None:
        try:
            out["price"] = int(item["price"])  # already an int from hydrator
        except Exception:
            pass
    if out.get("price") is None and item.get("price_str"):
        out["price"] = _to_int(item["price_str"])
    if out.get("price") is not None and not (500 <= out["price"] <= 500_000):
        out["price"] = None

    # State/suburb from detail if provided; else from location token
    state_field = item.get("state")
    st_norm = _upper_state(state_field) if isinstance(state_field, str) else None
    if st_norm:
        out["state"] = st_norm
    loc_tok = (item.get("location") or "").upper()
    sm_loc = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", loc_tok)
    if sm_loc:
        out["state"] = sm_loc.group(1)
    # Fallback: sometimes in the title
    if not out.get("state"):
        sm = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", title.upper())
        if sm:
            out["state"] = sm.group(1)

    # Suburb best effort
    sb = item.get("suburb") or None
    if isinstance(sb, str) and sb.strip():
        out["suburb"] = sb.strip()

    # Hydrated detail fields
    if item.get("body"):
        out["body"] = str(item["body"]).strip()
    if item.get("trans"):
        out["trans"] = str(item["trans"]).strip()
    if item.get("fuel"):
        out["fuel"] = str(item["fuel"]).strip()
    if item.get("engine"):
        out["engine"] = str(item["engine"]).strip()
    if item.get("drive"):
        out["drive"] = str(item["drive"]).strip()
    if item.get("variant"):
        out["variant"] = str(item["variant"]).strip()

    # Make/model guesses
    mk_guess = _format_guess(item.get("make_guess"))
    if mk_guess:
        out["make"] = mk_guess
    md_guess = _format_guess(item.get("model_guess"))
    if md_guess:
        out["model"] = md_guess

    if item.get("sale_method") is None and out.get("price") is not None:
        item["sale_method"] = "buy_now"
        if enable_sale_method and not out.get("sale_method"):
            out["sale_method"] = "buy_now"

    return out


def normalize_manheim(item: Dict[str, Any]) -> Dict[str, Any]:
    url = (item.get("link") or item.get("url") or "").strip()
    if not url:
        raise ValueError("missing source_url")
    source = "manheim"
    source_id = _extract_trailing_token(url, (item.get("title") or ""))
    if not source_id:
        raise ValueError("missing source_id")
    out = _canon_base(source, source_id, url, item)
    title = item.get("title") or ""
    m = re.search(r"\b(20\d{2}|19\d{2})\b", title)
    if m:
        out["year"] = _to_int(m.group(1))
    if item.get("img"):
        out["media"] = [item["img"]]
    if item.get("odometer"):
        out["odometer"] = _to_int(item["odometer"])
    sm = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", title.upper())
    if sm:
        out["state"] = sm.group(1)
    return out

def normalize_autotrader(item: Dict[str, Any]) -> Dict[str, Any]:
    url = (item.get("url") or item.get("link") or "").strip()
    if not url:
        raise ValueError("missing source_url")
    source = "autotrader"
    # Prefer ad_id field derived from URL path if available
    source_id = item.get("ad_id")
    if not source_id:
        m = re.search(r"/car/(\d+)/", url)
        source_id = m.group(1) if m else None
    if not source_id:
        raise ValueError("missing source_id")

    out = _canon_base(source, source_id, url, item)
    title = item.get("title") or ""
    # Year (plausible window)
    y = item.get("year_guess")
    if not y:
        my = re.search(r"\b(19\d{2}|20\d{2})\b", title)
        y = my.group(1) if my else None
    yr = _to_int(y) if y else None
    if yr is not None:
        from datetime import datetime
        current = datetime.utcnow().year
        if yr < 1980 or yr > current + 1:
            yr = None
    out["year"] = yr
    price_str = item.get("price_str")
    if price_str:
        mprice = re.search(r"(\d[\d,\.]*)", price_str)
        if mprice:
            out["price"] = _to_int(mprice.group(1))
    if item.get("thumb"):
        out["media"] = [item["thumb"]]
    mk = item.get("make_guess")
    md = item.get("model_guess")
    if isinstance(mk, str):
        out["make"] = " ".join(w.capitalize() for w in mk.replace("-", " ").split())
    if isinstance(md, str):
        out["model"] = " ".join(w.capitalize() for w in md.replace("-", " ").split())
    # State from state_guess or location
    st = item.get("state_guess")
    if isinstance(st, str) and re.match(r"^(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)$", st.upper()):
        out["state"] = st.upper()
    else:
        loc = (item.get("location") or "").upper()
        ms = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", loc)
        if ms:
            out["state"] = ms.group(1)
    # Require at least one useful field besides id/url
    if not out.get("make") and not out.get("model") and out.get("price") is None:
        raise ValueError("insufficient fields")
    return out


def normalize_gumtree(item: Dict[str, Any]) -> Dict[str, Any]:
    url = (item.get("link") or item.get("url") or "").strip()
    if not url:
        raise ValueError("missing source_url")
    source = "gumtree"
    source_id = item.get("ad_id") or _extract_trailing_token(url, (item.get("title") or ""))
    if not source_id:
        raise ValueError("missing source_id")
    out = _canon_base(source, source_id, url, item)
    title = item.get("title") or ""
    m = re.search(r"\b(20\d{2}|19\d{2})\b", title)
    if m:
        out["year"] = _to_int(m.group(1))
    thumb = item.get("thumb") or item.get("img")
    if thumb:
        out["media"] = [thumb]
    price_str = item.get("price_str") or item.get("price")
    if price_str:
        out["price"] = _to_int(price_str)
    loc = (item.get("location") or "").upper()
    sm = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", loc)
    if sm:
        out["state"] = sm.group(1)
    return out


def normalize_ebay(item: Dict[str, Any]) -> Dict[str, Any]:
    url = (item.get("link") or item.get("url") or "").strip()
    if not url:
        raise ValueError("missing source_url")
    source = "ebay"
    source_id = item.get("item_id")
    if not source_id:
        # require item id for ebay; avoid ambiguous URLs with tracking params
        raise ValueError("missing source_id")
    out = _canon_base(source, source_id, url, item)
    title = item.get("title") or ""
    m = re.search(r"\b(20\d{2}|19\d{2})\b", title)
    if m:
        out["year"] = _to_int(m.group(1))
    if item.get("img"):
        out["media"] = [item["img"]]
    if item.get("price"):
        out["price"] = _to_int(item["price"])
    # try capture AU state from location string if present
    loc = (item.get("location") or "").upper()
    sm = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", loc)
    if sm:
        out["state"] = sm.group(1)
    return out
