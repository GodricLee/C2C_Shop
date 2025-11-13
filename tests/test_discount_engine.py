"""Unit tests for the discount engine."""
from __future__ import annotations

from decimal import Decimal

from app.services.discount_engine import apply_discount


def test_member_discount_with_coupon_and_cap() -> None:
    final_price, subsidy = apply_discount(
        base_price=Decimal("100.00"),
        is_member=True,
        min_price=Decimal("50.00"),
        subsidy_cap=Decimal("30.00"),
        coupon_discount=Decimal("10.00"),
    )
    assert final_price == Decimal("85.00")
    assert subsidy == Decimal("15.00")


def test_min_price_floor_enforced() -> None:
    final_price, subsidy = apply_discount(
        base_price=Decimal("40.00"),
        is_member=True,
        min_price=Decimal("45.00"),
        subsidy_cap=Decimal("30.00"),
        coupon_discount=Decimal("20.00"),
    )
    assert final_price == Decimal("45.00")
    assert subsidy == Decimal("0.00")


def test_subsidy_cap_limits_discount() -> None:
    final_price, subsidy = apply_discount(
        base_price=Decimal("200.00"),
        is_member=True,
        min_price=Decimal("100.00"),
        subsidy_cap=Decimal("30.00"),
        coupon_discount=Decimal("50.00"),
    )
    assert final_price == Decimal("170.00")
    assert subsidy == Decimal("30.00")
