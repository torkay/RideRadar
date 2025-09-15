from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from uuid import UUID
import psycopg
from db.supabase_client import get_conn

router = APIRouter(prefix="/listings", tags=["Listings"])

@router.get("/")
async def get_listings(
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    price_min: Optional[int] = Query(None, ge=0),
    price_max: Optional[int] = Query(None, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    where = []
    params = []
    if make:
        where.append("lower(make) = lower(%s)")
        params.append(make)
    if model:
        where.append("lower(model) = lower(%s)")
        params.append(model)
    if state:
        where.append("upper(state) = upper(%s)")
        params.append(state)
    if price_min is not None:
        where.append("price >= %s")
        params.append(price_min)
    if price_max is not None:
        where.append("price <= %s")
        params.append(price_max)

    where_sql = " where " + " and ".join(where) if where else ""
    sql = f"""
      select id, source, source_id, source_url, fingerprint,
             make, model, variant, year, price, odometer,
             body, trans, fuel, engine, drive,
             state, postcode, suburb, lat, lng,
             media, seller, status, last_seen
      from listings
      {where_sql}
      order by last_seen desc
      limit %s
    """
    with get_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(sql, (*params, limit))
        rows = cur.fetchall()
        return rows

@router.get("/{listing_id}")
async def get_listing_by_id(listing_id: UUID):
    sql = """
      select id, source, source_id, source_url, fingerprint,
             make, model, variant, year, price, odometer,
             body, trans, fuel, engine, drive,
             state, postcode, suburb, lat, lng,
             media, seller, raw, status, last_seen
      from listings
      where id = %s
    """
    with get_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(sql, (listing_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Listing not found")
        return row
