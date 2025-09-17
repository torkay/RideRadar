"""
Supabase API smoke: upsert a demo listing through supabase-py and fetch latest 3.

Requires env:
  SUPABASE_URL
  SUPABASE_SERVICE_KEY (service role)

Usage:
  python -m engine.scripts.api_smoke
"""

from engine.db import supabase_api as sb


demo = {
    "source": "pickles",
    "source_id": "DEMO-API-123",
    "source_url": "https://www.pickles.com.au/cars/item/DEMO-API-123",
    "make": "Toyota",
    "model": "Corolla",
    "variant": "Ascent Sport",
    "year": 2019,
    "price": 18990,
    "odometer": 65500,
    "state": "NSW",
    "suburb": "Chatswood",
    "postcode": "2067",
    "media": ["https://example.com/img.jpg"],
    "seller": {"type": "dealer", "dealer_name": "API Motors"},
    "raw": {"note": "api smoke"},
    "status": "active",
}


if __name__ == "__main__":
    if not demo.get("fingerprint"):
        demo["fingerprint"] = sb.make_fingerprint(demo)
    print("Upserting via Supabase API...")
    sb.upsert_listing(demo)
    print("Fetching latest 3...")
    rows = sb.fetch_latest(3)
    for r in rows:
        print(r)

