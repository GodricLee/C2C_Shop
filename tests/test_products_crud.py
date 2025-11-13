"""Integration tests for product CRUD endpoints."""
from __future__ import annotations

from decimal import Decimal

from app.models.product import ProductStatus


def test_product_crud_flow(client, auth_headers) -> None:
    create_payload = {
        "title": "Test Product",
        "description": "A product created during tests",
        "price": "120.00",
    }
    response = client.post("/api/products/", json=create_payload, headers=auth_headers)
    assert response.status_code == 201
    product_id = response.json()["id"]

    update_payload = {"status": ProductStatus.PUBLISHED.value}
    response = client.put(f"/api/products/{product_id}", json=update_payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == ProductStatus.PUBLISHED.value

    response = client.get("/api/products/")
    assert response.status_code == 200
    listing = response.json()
    assert listing["total"] >= 1

    response = client.get(f"/api/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Product"

    response = client.delete(f"/api/products/{product_id}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/api/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["status"] == ProductStatus.UNLISTED.value
