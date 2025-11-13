"""Integration tests for deal workflows."""
from __future__ import annotations

from decimal import Decimal

from app.models.coupon import CouponAssignment
from app.models.product import Product, ProductStatus
from app.models.tag import Tag, TagStatus


def test_deal_create_and_confirm(
    client,
    current_user_override,
    buyer_user,
    pricing_setup,
    db_session,
    user_factory,
) -> None:
    _ = pricing_setup
    seller = user_factory("seller@example.com")

    product = Product(
        seller_id=seller.id,
        title="Vintage Camera",
        description="Film camera with accessories",
        price=Decimal("120.00"),
        status=ProductStatus.PUBLISHED,
    )
    db_session.add(product)
    db_session.commit()

    buyer_headers = current_user_override(buyer_user)
    create_response = client.post(
        "/api/deals",
        json={"product_id": product.id},
        headers=buyer_headers,
    )
    assert create_response.status_code == 201
    created_payload = create_response.json()
    deal_id = created_payload["id"]
    assert created_payload["status"] == "INITIATED"

    detail_response = client.get(f"/api/deals/{deal_id}", headers=buyer_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "INITIATED"

    confirm_response = client.post(
        f"/api/deals/{deal_id}/confirm-by-seller",
        json={"coupon_id": None},
        headers=current_user_override(seller),
    )
    assert confirm_response.status_code == 200
    confirmed_payload = confirm_response.json()
    assert confirmed_payload["status"] == "CONFIRMED_BY_SELLER"
    assert confirmed_payload["used_coupon_id"] is None
    assert confirmed_payload["cashback"] is not None
    assert confirmed_payload["cashback"]["amount"] == 2.28

    db_session.refresh(product)
    assert product.status == ProductStatus.SOLD


def test_deal_confirm_coupon_thresholds(
    client,
    current_user_override,
    buyer_user,
    admin_user,
    pricing_setup,
    db_session,
    user_factory,
) -> None:
    _ = pricing_setup
    seller = user_factory("seller.coupon@example.com")
    product = Product(
        seller_id=seller.id,
        title="Collector Figurine",
        description="Limited edition",
        price=Decimal("90.00"),
        status=ProductStatus.PUBLISHED,
    )
    db_session.add(product)
    db_session.commit()

    buyer_headers = current_user_override(buyer_user)
    create_response = client.post(
        "/api/deals",
        json={"product_id": product.id},
        headers=buyer_headers,
    )
    assert create_response.status_code == 201
    deal_id = create_response.json()["id"]

    coupon_payload = {
        "code": "THRESHOLD90",
        "min_revenue": "150.00",
        "min_sales": 0,
        "discount_amount": "10.00",
        "description": "High threshold coupon",
    }
    admin_headers = current_user_override(admin_user)
    create_coupon_response = client.post(
        "/api/promotions/coupons",
        json=coupon_payload,
        headers=admin_headers,
    )
    assert create_coupon_response.status_code == 201
    coupon_id = create_coupon_response.json()["id"]

    admin_headers = current_user_override(admin_user)
    activate_response = client.put(
        f"/api/promotions/coupons/{coupon_id}",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    assert activate_response.status_code == 200

    admin_headers = current_user_override(admin_user)
    assign_response = client.post(
        f"/api/promotions/coupons/{coupon_id}/assign",
        json={"user_id": buyer_user.id},
        headers=admin_headers,
    )
    assert assign_response.status_code == 200

    seller_headers = current_user_override(seller)
    first_confirm_response = client.post(
        f"/api/deals/{deal_id}/confirm-by-seller",
        json={"coupon_id": coupon_id},
        headers=seller_headers,
    )
    assert first_confirm_response.status_code == 400
    assert first_confirm_response.json()["message"] == "Coupon revenue threshold unmet"

    admin_headers = current_user_override(admin_user)
    lower_threshold_response = client.put(
        f"/api/promotions/coupons/{coupon_id}",
        json={"min_revenue": "60.00"},
        headers=admin_headers,
    )
    assert lower_threshold_response.status_code == 200

    seller_headers = current_user_override(seller)
    second_confirm_response = client.post(
        f"/api/deals/{deal_id}/confirm-by-seller",
        json={"coupon_id": coupon_id},
        headers=seller_headers,
    )
    assert second_confirm_response.status_code == 200
    confirmed_payload = second_confirm_response.json()
    assert confirmed_payload["status"] == "CONFIRMED_BY_SELLER"
    assert confirmed_payload["used_coupon_id"] == coupon_id

    assignment = (
        db_session.query(CouponAssignment)
        .filter(
            CouponAssignment.coupon_id == coupon_id,
            CouponAssignment.user_id == buyer_user.id,
        )
        .one()
    )
    assert assignment.used is True
    assert assignment.used_at is not None


def test_deal_access_control(
    client,
    current_user_override,
    buyer_user,
    pricing_setup,
    db_session,
    user_factory,
) -> None:
    _ = pricing_setup
    seller = user_factory("seller.acl@example.com")
    product = Product(
        seller_id=seller.id,
        title="Gaming Laptop",
        description="RTX graphics",
        price=Decimal("1500.00"),
        status=ProductStatus.PUBLISHED,
    )
    db_session.add(product)
    db_session.commit()

    deal_response = client.post(
        "/api/deals",
        json={"product_id": product.id},
        headers=current_user_override(buyer_user),
    )
    assert deal_response.status_code == 201
    deal_id = deal_response.json()["id"]

    another_user = user_factory("stranger@example.com")
    forbidden_response = client.get(
        f"/api/deals/{deal_id}",
        headers=current_user_override(another_user),
    )
    assert forbidden_response.status_code == 403

    seller_response = client.get(
        f"/api/deals/{deal_id}",
        headers=current_user_override(seller),
    )
    assert seller_response.status_code == 200

    buyer_response = client.get(
        f"/api/deals/{deal_id}",
        headers=current_user_override(buyer_user),
    )
    assert buyer_response.status_code == 200


def test_product_tagging_flow(
    client,
    current_user_override,
    user_factory,
    pricing_setup,
    db_session,
) -> None:
    _ = pricing_setup
    seller = user_factory("tagger@example.com")
    product = Product(
        seller_id=seller.id,
        title="Smartphone",
        description="Latest model",
        price=Decimal("699.00"),
        status=ProductStatus.DRAFT,
    )
    db_session.add(product)
    db_session.commit()

    create_tags_response = client.post(
        f"/api/products/{product.id}/tags",
        json={"names": ["electronics", "mobile"]},
        headers=current_user_override(seller),
    )
    assert create_tags_response.status_code == 200
    tags_payload = create_tags_response.json()
    assert {tag["name"] for tag in tags_payload} == {"electronics", "mobile"}

    pending_tags = db_session.query(Tag).filter(Tag.status == TagStatus.PENDING).all()
    assert len(pending_tags) == 2
    assert all(tag.status == TagStatus.PENDING for tag in pending_tags)