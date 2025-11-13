"""JWT helper functions."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

from app.config import get_settings


def create_access_token(subject: str, session_id: int) -> str:
    """Create an access token for the given subject and session."""

    settings = get_settings()
    expire = datetime.now(tz=timezone.utc) + timedelta(hours=settings.jwt_exp_hours)
    payload: Dict[str, Any] = {
        "sub": subject,
        "sid": session_id,
        "exp": expire,
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT, returning the payload."""

    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "sid", "exp"]},
        )
    except jwt.PyJWTError as exc:  # pragma: no cover - library mapping
        raise ValueError("Invalid token") from exc
