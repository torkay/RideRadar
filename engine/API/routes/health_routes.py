from fastapi import APIRouter
from datetime import datetime, timezone
from engine.runtime.vendor_status import snapshot

router = APIRouter(tags=["Health"])


def _now_utc_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("/healthz")
async def healthz():
    return {
        "ok": True,
        "time": _now_utc_z(),
        "vendors": snapshot(),
    }

