from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from uuid import UUID
import os

DB_BACKEND = os.getenv("DB_BACKEND", "postgres").lower()

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
    if DB_BACKEND == "supabase_api":
        # Supabase REST path
        from engine.db import supabase_api as sb
        q = sb._sb.table("listings").select(
            "id, source, source_id, source_url, fingerprint, make, model, variant, year, price, odometer, body, trans, fuel, engine, drive, state, postcode, suburb, lat, lng, media, seller, status, last_seen"
        )
        if make:
            q = q.eq("make", make)
        if model:
            q = q.eq("model", model)
        if state:
            q = q.eq("state", state)
        if price_min is not None:
            q = q.gte("price", price_min)
        if price_max is not None:
            q = q.lte("price", price_max)
        q = q.order("last_seen", desc=True).limit(limit)
        res = q.execute()
        return res.data or []

    # Default Postgres path via psycopg
    import psycopg
    from engine.db.supabase_client import get_conn
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
    if DB_BACKEND == "supabase_api":
        from engine.db import supabase_api as sb
        res = (
            sb._sb.table("listings")
            .select(
                "id, source, source_id, source_url, fingerprint, make, model, variant, year, price, odometer, body, trans, fuel, engine, drive, state, postcode, suburb, lat, lng, media, seller, raw, status, last_seen"
            )
            .eq("id", str(listing_id))
            .limit(1)
            .execute()
        )
        data = res.data or []
        if not data:
            raise HTTPException(status_code=404, detail="Listing not found")
        return data[0]

    import psycopg
    from engine.db.supabase_client import get_conn
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
