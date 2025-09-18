import re
from typing import Any, Dict, List, Optional


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


def normalize_pickles(item: Dict[str, Any]) -> Dict[str, Any]:
    url = (item.get("link") or item.get("url") or "").strip()
    if not url:
        raise ValueError("missing source_url")
    source = "pickles"
    source_id = _extract_trailing_token(url, (item.get("title") or ""))
    if not source_id:
        raise ValueError("missing source_id")

    out = _canon_base(source, source_id, url, item)
    # Attempt a very light year parse from title
    title = item.get("title") or ""
    m = re.search(r"\b(20\d{2}|19\d{2})\b", title)
    if m:
        out["year"] = _to_int(m.group(1))

    # Image
    if item.get("img"):
        out["media"] = [item["img"]]

    # Odometer if provided in card (rare)
    if item.get("odometer"):
        out["odometer"] = _to_int(item["odometer"])

    # Basic state can sometimes be in title like "NSW"; keep conservative
    sm = re.search(r"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", title.upper())
    if sm:
        out["state"] = sm.group(1)

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


def normalize_gumtree(item: Dict[str, Any]) -> Dict[str, Any]:
    url = (item.get("link") or item.get("url") or "").strip()
    if not url:
        raise ValueError("missing source_url")
    source = "gumtree"
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
    if item.get("price"):
        out["price"] = _to_int(item["price"])
    return out

