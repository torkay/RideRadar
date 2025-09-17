"""
DB smoke: connect, upsert one demo row, and fetch latest.

Usage:
  python engine/scripts/db_smoke.py

Requires SUPABASE_DB_URL in the environment.
"""

from engine.db.supabase_client import get_conn, upsert_listing, fetch_latest, make_fingerprint

demo = {
    "source": "pickles",
    "source_id": "DEMO-123",
    "source_url": "https://www.pickles.com.au/cars/item/DEMO-123",
    "make": "Toyota",
    "model": "Corolla",
    "variant": "Ascent Sport",
    "year": 2018,
    "price": 17990,
    "odometer": 78500,
    "state": "QLD",
    "suburb": "Enoggera",
    "postcode": "4051",
    "media": ["https://example.com/img.jpg"],
    "seller": {"type": "dealer", "dealer_name": "Demo Motors"},
    "raw": {"note": "seed row for smoke test"},
    "status": "active",
}
demo["fingerprint"] = make_fingerprint(demo)

if __name__ == "__main__":
    print("Connecting to database...")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1")
            print("DB connection OK")

    print("Upserting demo row...")
    upsert_listing(demo)
    print("Fetching latest rows...")
    rows = fetch_latest(3)
    for r in rows:
        print(r)
