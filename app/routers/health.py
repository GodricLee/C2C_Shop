"""Health endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
import time

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])
_settings = get_settings()
_start_time = time.monotonic()


@router.get("/health", summary="Health check")
def health() -> dict[str, object]:
    """Return service health status."""

    uptime = time.monotonic() - _start_time
    return {
        "ok": True,
        "env": _settings.app_env,
        "uptime": round(uptime, 2),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
