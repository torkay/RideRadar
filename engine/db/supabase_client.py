# engine/db/supabase_client.py
import os, json, hashlib
from typing import Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import psycopg

DB_URL = os.getenv("SUPABASE_DB_URL")


def _validate_dsn(url: Optional[str]) -> str:
    if not url:
        raise RuntimeError(
            "SUPABASE_DB_URL not set. For REST use DB_BACKEND=supabase_api."
        )
    u = urlparse(url)
    host = u.hostname or ""
    user = u.username or ""

    # Pooler host requires dotted username: postgres.<project-ref>
    if "pooler.supabase.com" in host and "." not in user:
        raise RuntimeError(
            "Pooler DSN requires dotted username 'postgres.<project-ref>'. "
            "Copy the Session Pooler DSN from the dashboard."
        )

    # Direct host: warn about resolver quirks
    if host.startswith("db."):
        print(
            "[supabase_client] Note: using direct host. If you see 'nodename nor servname', "
            "switch to the pooler host and username 'postgres.<project-ref>'."
        )

    # Ensure sslmode=require is present
    q = dict(parse_qsl(u.query, keep_blank_values=True))
    if "sslmode" not in q:
        q["sslmode"] = "require"
    new_query = urlencode(q)
    validated = urlunparse((u.scheme, u.netloc, u.path, u.params, new_query, u.fragment))
    return validated


def _mask_dsn(url: str) -> str:
    try:
        u = urlparse(url)
        if u.password:
            netloc = f"{u.username}:***@{u.hostname}:{u.port or ''}"
        else:
            netloc = u.netloc
        return urlunparse((u.scheme, netloc, u.path, u.params, u.query, u.fragment))
    except Exception:
        return "***"


@contextmanager
def get_conn():
    dsn = _validate_dsn(DB_URL)
    try:
        # psycopg3 auto-enables TLS when sslmode=require in the URL
        with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn:
            yield conn
    except psycopg.OperationalError as e:
        msg = str(e)
        if "Tenant or user not found" in msg:
            raise RuntimeError(
                "Pooler DSN likely missing dotted username 'postgres.<project-ref>'."
            ) from None
        if "nodename nor servname" in msg:
            raise RuntimeError(
                "DNS couldn't resolve the direct host. Use the pooler host or set DB_BACKEND=supabase_api."
            ) from None
        masked = _mask_dsn(dsn)
        raise RuntimeError(f"Database connection failed for DSN: {masked}\n{msg}") from None

def _band(n: Optional[int], step: int) -> str:
    if n is None:
        return ""
    lo = (n // step) * step
    return f"{lo}-{lo+step}"

def normalize_text(s: Optional[str]) -> str:
    return (s or "").strip().lower()

def make_fingerprint(d: Dict[str, Any]) -> str:
    parts = [
        normalize_text(d.get("make")),
        normalize_text(d.get("model")),
        str(d.get("year") or ""),
        _band(d.get("odometer"), 25000),
        _band(d.get("price"), 2500),
        normalize_text(d.get("variant")),
        normalize_text(d.get("suburb") or d.get("postcode")),
    ]
    sha = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return sha

def upsert_listing(listing: Dict[str, Any]) -> None:
    """Insert/update a normalized listing into Postgres."""
    # Ensure required keys exist
    required = ["source", "source_id", "source_url"]
    for k in required:
        if not listing.get(k):
            raise ValueError(f"Missing required field: {k}")

    # Compute fingerprint if absent
    if not listing.get("fingerprint"):
        listing["fingerprint"] = make_fingerprint(listing)

    cols = [
        "source","source_id","source_url","fingerprint",
        "make","model","variant","year","price","odometer",
        "body","trans","fuel","engine","drive",
        "state","postcode","suburb","lat","lng",
        "media","seller","raw","status"
    ]
    vals = [listing.get(c) for c in cols]
    # JSON fields
    for i, c in enumerate(cols):
        if c in ("media","seller","raw") and vals[i] is not None and not isinstance(vals[i], str):
            vals[i] = json.dumps(vals[i])

    sql = f"""
    insert into listings ({", ".join(cols)})
    values ({", ".join(["%s"]*len(cols))})
    on conflict (source, source_id) do update set
      price = excluded.price,
      odometer = excluded.odometer,
      body = excluded.body,
      trans = excluded.trans,
      fuel = excluded.fuel,
      engine = excluded.engine,
      drive = excluded.drive,
      state = excluded.state,
      postcode = excluded.postcode,
      suburb = excluded.suburb,
      lat = excluded.lat,
      lng = excluded.lng,
      media = excluded.media,
      seller = excluded.seller,
      raw = excluded.raw,
      status = excluded.status,
      last_seen = now();
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, vals)

def fetch_latest(limit: int = 10) -> list[dict]:
    sql = """
      select id, source, source_id, source_url, make, model, variant, year,
             price, odometer, state, suburb, postcode, last_seen
      from listings
      order by last_seen desc
      limit %s
    """
    with get_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(sql, (limit,))
        return cur.fetchall()
