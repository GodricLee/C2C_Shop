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
    
    MAX_VERIFY_ATTEMPTS = 5  # Maximum verification attempts before lockout

    def __init__(self) -> None:
        self._codes: Dict[Tuple[int, TwoFAMethodType], TwoFACode] = {}
        self._attempts: Dict[Tuple[int, TwoFAMethodType], int] = {}  # Track failed attempts

    def send_code(self, user_id: int, channel: TwoFAMethodType) -> str:
        token = "".join(random.choices(string.digits, k=6))
        expires = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
        self._codes[(user_id, channel)] = TwoFACode(code=token, expires_at=expires)
        # Reset attempt counter when new code is sent
        self._attempts[(user_id, channel)] = 0
        return token

    def verify_code(self, user_id: int, channel: TwoFAMethodType, code: str) -> bool:
        key = (user_id, channel)
        
        # Check for too many failed attempts (rate limiting)
        attempts = self._attempts.get(key, 0)
        if attempts >= self.MAX_VERIFY_ATTEMPTS:
            # Remove the code to force requesting a new one
            self._codes.pop(key, None)
            return False
        
        stored = self._codes.get(key)
        if stored is None or stored.is_expired:
            return False
        if stored.code != code:
            # Increment failed attempt counter
            self._attempts[key] = attempts + 1
            return False
        # Successful verification - clean up
        del self._codes[key]
        self._attempts.pop(key, None)
        return True


transport = InMemoryTwoFATransport()
