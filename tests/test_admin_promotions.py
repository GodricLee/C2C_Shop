"""Integration tests for admin promotion flows."""
from __future__ import annotations

from decimal import Decimal

from app.models.coupon import CouponAssignment


def test_admin_config_parameter_flow(client, current_user_override, admin_user, pricing_setup) -> None:
    _ = pricing_setup

    headers = current_user_override(admin_user)
    response = client.get("/api/admin/config", headers=headers)
    assert response.status_code == 200
    config = response.json()
    assert Decimal(str(config["commission_rate"])) == Decimal("0.05")
    assert Decimal(str(config["cashback_default"])) == Decimal("0.02")

    payload = {
        "commission_rate": "0.08",
        "cashback_default": "0.03",
    }
    headers = current_user_override(admin_user)
    response = client.put("/api/admin/config", json=payload, headers=headers)
    assert response.status_code == 200
    updated = response.json()
    assert Decimal(str(updated["commission_rate"])) == Decimal("0.08")
    assert Decimal(str(updated["cashback_default"])) == Decimal("0.03")

    headers = current_user_override(admin_user)
    response = client.get("/api/admin/config", headers=headers)
    assert response.status_code == 200
    config = response.json()
    assert Decimal(str(config["commission_rate"])) == Decimal("0.08")
    assert Decimal(str(config["cashback_default"])) == Decimal("0.03")



def test_coupon_lifecycle(
    client,
    current_user_override,
    admin_user,
    buyer_user,
    pricing_setup,
    db_session,
) -> None:
    _ = pricing_setup

    admin_headers = current_user_override(admin_user)
    payload = {
        "code": "WELCOME20",
        "min_revenue": "20.00",
        "min_sales": 0,
        "discount_amount": "5.00",
        "description": "Welcome coupon",
    }

    response = client.post("/api/promotions/coupons", json=payload, headers=admin_headers)
    assert response.status_code == 201
    coupon = response.json()
    assert coupon["code"] == "WELCOME20"
    assert coupon["status"] == "DRAFT"

    admin_headers = current_user_override(admin_user)
    response = client.put(
        f"/api/promotions/coupons/{coupon['id']}",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    activated = response.json()
    assert activated["status"] == "ACTIVE"

    admin_headers = current_user_override(admin_user)
    response = client.get("/api/promotions/coupons", headers=admin_headers)
    assert response.status_code == 200
    listing = response.json()
    assert any(item["code"] == "WELCOME20" for item in listing)

    admin_headers = current_user_override(admin_user)
    response = client.post(
        f"/api/promotions/coupons/{coupon['id']}/assign",
        json={"user_id": buyer_user.id},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assignment_view = response.json()
    assert assignment_view["id"] == coupon["id"]

    assignment = (
        db_session.query(CouponAssignment)
        .filter(
            CouponAssignment.coupon_id == coupon["id"],
            CouponAssignment.user_id == buyer_user.id,
        )
        .one()
    )
    assert assignment.used is False

    admin_headers = current_user_override(admin_user)
    response = client.put(
        f"/api/promotions/coupons/{coupon['id']}",
        json={"discount_amount": str(Decimal("7.50"))},
        headers=admin_headers,
    )
    assert response.status_code == 200
    updated_coupon = response.json()
    assert Decimal(str(updated_coupon["discount_amount"])) == Decimal("7.50")
