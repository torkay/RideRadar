"""
eBay deeplink helpers.

- build_search_url: constructs a category-scoped AU Cars search URL.
- get_item_urls: optional helper to retrieve item URLs via the Browse API
  (prefers affiliate URLs when present), falling back to itemWebUrl.
"""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import urlencode

from engine.integrations import ebay_api


BASE = "https://www.ebay.com.au/sch/i.html"
CARS_CAT = "29690"


def build_search_url(
    make: Optional[str] = None,
    model: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
) -> str:
    terms = [t for t in [make, model] if t]
    q = " ".join(terms)
    params = {
        "_sacat": CARS_CAT,
        "_nkw": q,
        "rt": "nc",
    }
    if price_min is not None:
        params["_udlo"] = str(price_min)
    if price_max is not None:
        params["_udhi"] = str(price_max)
    return f"{BASE}?{urlencode(params)}"


def get_item_urls(q: str, limit: int = 5) -> List[str]:
    items = ebay_api.search_items(q=q, limit=limit)
    urls: List[str] = []
    for it in items:
        url = it.get("itemAffiliateWebUrl") or it.get("itemWebUrl")
        if url:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls

