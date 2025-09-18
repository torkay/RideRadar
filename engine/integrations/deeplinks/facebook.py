"""
Facebook Marketplace deeplink builder (best-effort).

Note: Facebook may change Marketplace query parameters at any time.
This module only builds an outbound search URL; it does not fetch content.
"""

from urllib.parse import urlencode
from typing import Optional


BASE = "https://www.facebook.com/marketplace/australia/search"


def build_url(
    make: Optional[str] = None,
    model: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    state: Optional[str] = None,
) -> str:
    # Query term: combine make/model/state keywords conservatively
    terms = [t for t in [make, model, state] if t]
    query = " ".join(terms)
    params = {"query": query}
    if price_min is not None:
        params["minPrice"] = str(price_min)
    if price_max is not None:
        params["maxPrice"] = str(price_max)
    # 'exact' narrows keyword matching; leave off by default for recall
    return f"{BASE}?{urlencode(params)}"

