"""Tests for product CRUD endpoints."""
from __future__ import annotations

from decimal import Decimal

from app.models.product import Product, ProductStatus


def test_product_create_and_publish(
    client,
    current_user_override,
    user_factory,
    db_session,
) -> None:
    seller = user_factory("seller.product@example.com")
    headers = current_user_override(seller)

    payload = {
        "title": "Wireless Headphones",
        "description": "Noise cancelling over-ear",
        "price": "199.90",
    }
    response = client.post("/api/products", json=payload, headers=headers)
    assert response.status_code == 201
    created = response.json()
    assert created["status"] == ProductStatus.DRAFT.value
    product_id = created["id"]

    update_payload = {"price": "189.90", "status": ProductStatus.PUBLISHED.value}
    response = client.put(
        f"/api/products/{product_id}",
        json=update_payload,
        headers=headers,
    )
    assert response.status_code == 200
    updated = response.json()
    assert Decimal(str(updated["price"])) == Decimal("189.90")
    assert updated["status"] == ProductStatus.PUBLISHED.value

    product = db_session.query(Product).filter(Product.id == product_id).one()
    assert product.status == ProductStatus.PUBLISHED
    assert product.price == Decimal("189.90")


def test_product_delete_marks_unlisted(
    client,
    current_user_override,
    user_factory,
    db_session,
) -> None:
    seller = user_factory("seller.delete@example.com")
    headers = current_user_override(seller)

    product = Product(
        seller_id=seller.id,
        title="Retro Console",
        description="Modded handheld",
        price=Decimal("249.00"),
        status=ProductStatus.PUBLISHED,
    )
    db_session.add(product)
    db_session.commit()

    response = client.delete(f"/api/products/{product.id}", headers=headers)
    assert response.status_code == 204

    db_session.refresh(product)
    assert product.status == ProductStatus.UNLISTED


def test_product_update_requires_owner(
    client,
    current_user_override,
    user_factory,
    db_session,
) -> None:
    owner = user_factory("owner@example.com")
    intruder = user_factory("intruder@example.com")

    product = Product(
        seller_id=owner.id,
        title="Smart Watch",
        description="Fitness tracking",
        price=Decimal("149.00"),
        status=ProductStatus.PUBLISHED,
    )
    db_session.add(product)
    db_session.commit()

    response = client.put(
        f"/api/products/{product.id}",
        json={"title": "Updated Title"},
        headers=current_user_override(intruder),
    )
    assert response.status_code == 403

    response = client.put(
        f"/api/products/{product.id}",
        json={"title": "Seller Updated"},
        headers=current_user_override(owner),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Seller Updated"
