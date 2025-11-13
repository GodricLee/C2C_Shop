"""Stubbed 2FA transport implementations."""
from __future__ import annotations

import random
import string
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

from app.models.user import TwoFAMethodType


@dataclass
class TwoFACode:
    """Represents an issued 2FA code."""

    code: str
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return datetime.now(tz=timezone.utc) >= self.expires_at


class TwoFATransport:
    """Abstract 2FA transport contract."""

    def send_code(self, user_id: int, channel: TwoFAMethodType) -> str:
        raise NotImplementedError

    def verify_code(self, user_id: int, channel: TwoFAMethodType, code: str) -> bool:
        raise NotImplementedError


class InMemoryTwoFATransport(TwoFATransport):
    """Simple in-memory 2FA dispatcher used for tests and demo."""

    def __init__(self) -> None:
        self._codes: Dict[Tuple[int, TwoFAMethodType], TwoFACode] = {}

    def send_code(self, user_id: int, channel: TwoFAMethodType) -> str:
        token = "".join(random.choices(string.digits, k=6))
        expires = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
        self._codes[(user_id, channel)] = TwoFACode(code=token, expires_at=expires)
        return token

    def verify_code(self, user_id: int, channel: TwoFAMethodType, code: str) -> bool:
        key = (user_id, channel)
        stored = self._codes.get(key)
        if stored is None or stored.is_expired:
            return False
        if stored.code != code:
            return False
        del self._codes[key]
        return True


transport = InMemoryTwoFATransport()
