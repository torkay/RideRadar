# engine/scripts/db_smoke.py
from db.supabase_client import upsert_listing, fetch_latest, make_fingerprint
from datetime import datetime

demo = {
  "source": "pickles",
  "source_id": "DEMO-123",
  "source_url": "https://www.pickles.com.au/cars/item/DEMO-123",
  "make": "Toyota", "model": "Corolla", "variant": "Ascent Sport",
  "year": 2018, "price": 17990, "odometer": 78500,
  "state": "QLD", "suburb": "Enoggera", "postcode": "4051",
  "media": ["https://example.com/img.jpg"],
  "seller": {"type": "dealer", "dealer_name": "Demo Motors"},
  "raw": {"note": "seed row for smoke test"},
  "status": "active"
}
demo["fingerprint"] = make_fingerprint(demo)

if __name__ == "__main__":
    upsert_listing(demo)
    rows = fetch_latest(3)
    print("Latest rows:")
    for r in rows:
        print(r)