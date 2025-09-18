"""
eBay Browse API integration (AU) — token fetch, search, normalize, ingest.

Env vars required for API calls:
- EBAY_APP_ID (client id)
- EBAY_CERT_ID (client secret)

Optional:
- EBAY_SCOPES (space-separated). Defaults to 'https://api.ebay.com/oauth/api_scope'.

Note: This module performs network calls using httpx. Ensure network access is available.
"""

from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from engine.scraper.pipeline import save_many


_TOKEN_CACHE: Dict[str, Any] = {
    "access_token": None,
    "expires_at": 0.0,
}

EBAY_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_BROWSE_SEARCH = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def _auth_basic_header(app_id: str, cert_id: str) -> str:
    token = base64.b64encode(f"{app_id}:{cert_id}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def get_app_token() -> Tuple[str, float]:
    """Return (access_token, expires_at). Caches token in memory until expiry.

    Uses Client Credentials grant for Browse API scope.
    """
    now = time.time()
    if _TOKEN_CACHE.get("access_token") and _TOKEN_CACHE.get("expires_at", 0) - now > 60:
        return _TOKEN_CACHE["access_token"], _TOKEN_CACHE["expires_at"]

    app_id = os.getenv("EBAY_APP_ID")
    cert_id = os.getenv("EBAY_CERT_ID")
    if not app_id or not cert_id:
        raise RuntimeError("EBAY_APP_ID and EBAY_CERT_ID must be set")

    scopes = os.getenv("EBAY_SCOPES", "https://api.ebay.com/oauth/api_scope")

    headers = {
        "Authorization": _auth_basic_header(app_id, cert_id),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": scopes,
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(EBAY_OAUTH_URL, data=data, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
        access_token = payload.get("access_token")
        expires_in = float(payload.get("expires_in", 3600))
        if not access_token:
            raise RuntimeError(f"Failed to fetch eBay token: {payload}")
        expires_at = now + expires_in
        _TOKEN_CACHE.update({"access_token": access_token, "expires_at": expires_at})
        return access_token, expires_at


def _build_filter(price: Optional[Tuple[Optional[int], Optional[int]]], include_auctions: bool) -> str:
    parts: List[str] = ["deliveryCountry:AU"]
    if include_auctions:
        parts.append("buyingOptions:{AUCTION|FIXED_PRICE}")
    else:
        parts.append("buyingOptions:{FIXED_PRICE}")
    if price is not None:
        lo, hi = price
        lo_s = "" if lo is None else str(lo)
        hi_s = "" if hi is None else str(hi)
        parts.append(f"price:[{lo_s}..{hi_s}]")
    return ",".join(parts)


def search_items(
    q: Optional[str],
    category_id: str = "29690",
    limit: int = 20,
    price: Optional[Tuple[Optional[int], Optional[int]]] = None,
    include_auctions: bool = True,
) -> List[Dict[str, Any]]:
    token, _ = get_app_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    params = {
        "q": q or "",
        "category_ids": category_id,
        "limit": str(limit),
        "filter": _build_filter(price, include_auctions),
    }
    with httpx.Client(headers=headers, timeout=20.0) as client:
        resp = client.get(EBAY_BROWSE_SEARCH, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("itemSummaries", [])


def normalize(item: Dict[str, Any]) -> Dict[str, Any]:
    """Map eBay item summary to our canonical listing dict."""
    item_id = item.get("itemId")
    url = item.get("itemWebUrl")
    if not item_id or not url:
        raise ValueError("missing itemId or itemWebUrl")
    price_val = None
    if item.get("price") and item["price"].get("value") is not None:
        try:
            price_val = int(float(item["price"]["value"]))
        except Exception:
            price_val = None
    # Try bid price if present
    if price_val is None and item.get("currentBidPrice") and item["currentBidPrice"].get("value"):
        try:
            price_val = int(float(item["currentBidPrice"]["value"]))
        except Exception:
            price_val = None

    title = item.get("title") or ""
    # Attempt year inference from title
    import re

    m = re.search(r"\b(19\d{2}|20\d{2})\b", title)
    year = int(m.group(1)) if m else None

    # Location
    loc = item.get("itemLocation", {}) or {}
    state = None
    if isinstance(loc, dict):
        st = (loc.get("stateOrProvince") or "").strip().upper()
        if 2 <= len(st) <= 3:
            state = st
    # Media
    media = []
    img = (item.get("image") or {}).get("imageUrl")
    if img:
        media = [img]

    seller = {}
    if item.get("seller"):
        seller = {
            "username": item["seller"].get("username"),
            "feedbackPercentage": item["seller"].get("feedbackPercentage"),
            "feedbackScore": item["seller"].get("feedbackScore"),
        }

    return {
        "source": "ebay",
        "source_id": item_id,
        "source_url": url,
        "make": None,
        "model": None,
        "variant": None,
        "year": year,
        "price": price_val,
        "odometer": None,
        "body": None,
        "trans": None,
        "fuel": None,
        "engine": None,
        "drive": None,
        "state": state,
        "postcode": loc.get("postalCode") if isinstance(loc, dict) else None,
        "suburb": None,
        "lat": None,
        "lng": None,
        "media": media,
        "seller": seller,
        "raw": item,
        "status": "active",
    }


def ingest(q: Optional[str], limit: int = 20) -> Dict[str, int]:
    """Fetch via API, normalize and save using pipeline. Returns counts."""
    items = search_items(q=q, limit=limit)
    normalized = []
    for it in items:
        try:
            normalized.append(normalize(it))
        except Exception:
            continue
    saved = save_many(normalized)
    return {"fetched": len(items), "normalized": len(normalized), "saved": saved}

