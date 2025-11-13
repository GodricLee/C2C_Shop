"""Tests covering membership upgrade flows."""
from __future__ import annotations

from datetime import datetime

from app.models.membership import Membership, MembershipLevel


def test_membership_upgrade_and_fetch(
    client,
    current_user_override,
    test_user,
    db_session,
) -> None:
    headers = current_user_override(test_user)

    response = client.get("/api/membership/me", headers=headers)
    assert response.status_code == 404

    payload = {"level": MembershipLevel.SHOPPER.value, "duration_days": 45}
    response = client.post("/api/membership/upgrade", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == test_user.id
    assert data["level"] == MembershipLevel.SHOPPER.value
    assert data["expires_at"] is not None
    first_expiry = datetime.fromisoformat(data["expires_at"])

    response = client.get("/api/membership/me", headers=headers)
    assert response.status_code == 200
    fetched = response.json()
    assert fetched["level"] == MembershipLevel.SHOPPER.value

    extended_payload = {"level": MembershipLevel.SHOPPER.value, "duration_days": 90}
    response = client.post("/api/membership/upgrade", json=extended_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    second_expiry = datetime.fromisoformat(data["expires_at"])
    assert second_expiry > first_expiry

    membership_count = (
        db_session.query(Membership)
        .filter(Membership.user_id == test_user.id)
        .count()
    )
    assert membership_count == 1
