"""Health endpoint tests."""
from __future__ import annotations


def test_health_endpoint(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "uptime" in payload
