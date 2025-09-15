import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

_lock = threading.Lock()
_store: Dict[str, Dict[str, Any]] = {}


def _now_utc_z() -> str:
    # ISO8601 with trailing Z, seconds precision
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_vendor(vendor: str) -> None:
    v = (vendor or "unknown").strip().lower()
    with _lock:
        if v not in _store:
            _store[v] = {
                "last_success_ts": None,
                "errors": 0,
                "breaker": "closed",
                "last_error": None,
                # internal field to drive breaker policy; excluded from snapshot
                "_consecutive_errors": 0,
            }


def _discover_vendors() -> None:
    # best-effort scan of vendor modules
    vendors_dir = Path(__file__).resolve().parent.parent / "scraper" / "vendors"
    try:
        for p in vendors_dir.glob("*_scraper.py"):
            name = p.stem.replace("_scraper", "").lower()
            _ensure_vendor(name)
    except Exception:
        # ignore discovery failures; lazy init will handle later
        pass


def mark_success(vendor: str) -> None:
    _ensure_vendor(vendor)
    with _lock:
        rec = _store[vendor.lower()]
        rec["last_success_ts"] = _now_utc_z()
        rec["breaker"] = "closed"
        rec["last_error"] = None
        rec["_consecutive_errors"] = 0


def mark_error(vendor: str, err: Exception | str) -> None:
    _ensure_vendor(vendor)
    msg = str(err)
    if len(msg) > 200:
        msg = msg[:197] + "..."
    with _lock:
        rec = _store[vendor.lower()]
        rec["errors"] += 1
        rec["last_error"] = msg
        rec["_consecutive_errors"] += 1
        # simple breaker: open after 3 consecutive failures
        if rec["_consecutive_errors"] >= 3:
            rec["breaker"] = "open"


def snapshot() -> Dict[str, Dict[str, Any]]:
    # seed discovery on first snapshot
    _discover_vendors()
    with _lock:
        out: Dict[str, Dict[str, Any]] = {}
        for k, v in _store.items():
            out[k] = {
                "last_success_ts": v.get("last_success_ts"),
                "errors": v.get("errors", 0),
                "breaker": v.get("breaker", "closed"),
                "last_error": v.get("last_error"),
            }
        return out

