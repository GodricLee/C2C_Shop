"""Stub risk engine used during authentication."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import DeviceFingerprint, RiskEvent, RiskEventType, User


@dataclass(slots=True)
class RiskAssessment:
    """Simple risk assessment result."""

    score: int
    requires_twofa: bool
    reason: str


KNOWN_DEVICE_SCORE = 20
NEW_DEVICE_SCORE = 80
ABNORMAL_IP_SCORE = 60


def evaluate_login(
    db: Session,
    user: User,
    device_fingerprint: Optional[str],
    ip_address: Optional[str],
) -> RiskAssessment:
    """Evaluate a login attempt and persist risk events as necessary."""

    requires_twofa = True  # platform enforces 2FA always
    score = KNOWN_DEVICE_SCORE
    reason = "baseline"

    if device_fingerprint:
        fingerprint = (
            db.query(DeviceFingerprint)
            .filter(
                DeviceFingerprint.user_id == user.id,
                DeviceFingerprint.fingerprint == device_fingerprint,
            )
            .first()
        )
        if fingerprint is None:
            reason = "new_device"
            score = NEW_DEVICE_SCORE
            new_fp = DeviceFingerprint(
                user_id=user.id,
                fingerprint=device_fingerprint,
                last_seen_at=datetime.now(tz=timezone.utc),
            )
            db.add(new_fp)
            db.add(
                RiskEvent(
                    user_id=user.id,
                    type=RiskEventType.MULTI_DEVICE,
                    score=NEW_DEVICE_SCORE,
                    description="Login from unrecognized device",
                )
            )
        else:
            fingerprint.last_seen_at = datetime.now(tz=timezone.utc)
    if ip_address and ip_address.endswith(".13"):
        score = max(score, ABNORMAL_IP_SCORE)
        reason = "suspicious_ip"
        db.add(
            RiskEvent(
                user_id=user.id,
                type=RiskEventType.SUSPICIOUS_LOCATION,
                score=ABNORMAL_IP_SCORE,
                description=f"Suspicious IP pattern: {ip_address}",
            )
        )

    return RiskAssessment(score=score, requires_twofa=requires_twofa, reason=reason)
