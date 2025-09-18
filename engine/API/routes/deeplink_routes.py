from fastapi import APIRouter, Query
from typing import Optional

from engine.integrations.deeplinks.facebook import build_url as fb_build
from engine.integrations.deeplinks.ebay import build_search_url as ebay_search_url
from engine.integrations.deeplinks.ebay import get_item_urls as ebay_item_urls


router = APIRouter(prefix="/deeplinks", tags=["Deeplinks"])


@router.get("")
@router.get("/")
async def get_deeplinks(
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    price_min: Optional[int] = Query(None, ge=0),
    price_max: Optional[int] = Query(None, ge=0),
    limit: int = Query(5, ge=1, le=50),
):
    q = " ".join(x for x in [make, model] if x)
    fb_url = fb_build(make=make, model=model, state=state, price_min=price_min, price_max=price_max)
    ebay_url = ebay_search_url(make=make, model=model, price_min=price_min, price_max=price_max)
    # Attempt to also provide direct item URLs via API; ignore failures
    urls = []
    try:
        if q:
            urls = ebay_item_urls(q=q, limit=limit)
    except Exception:
        urls = []
    return {
        "facebook": fb_url,
        "ebay": {
            "search_url": ebay_url,
            "item_urls": urls,
        },
    }

