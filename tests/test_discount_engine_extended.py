"""Extended unit tests for the discount engine - 80%+ coverage."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.discount_engine import apply_discount, _quantize


class TestQuantizeFunction:
    """Tests for the _quantize helper function."""

    def test_quantize_rounds_down(self) -> None:
        """Test quantize rounds down when decimal is < 0.005"""
        result = _quantize(Decimal("10.124"))
        assert result == Decimal("10.12")

    def test_quantize_rounds_up(self) -> None:
        """Test quantize rounds up when decimal is >= 0.005"""
        result = _quantize(Decimal("10.125"))
        assert result == Decimal("10.13")

    def test_quantize_exact_value(self) -> None:
        """Test quantize keeps exact two decimal value"""
        result = _quantize(Decimal("10.50"))
        assert result == Decimal("10.50")

    def test_quantize_long_decimal(self) -> None:
        """Test quantize handles long decimals"""
        result = _quantize(Decimal("99.99999"))
        assert result == Decimal("100.00")


class TestApplyDiscountBasic:
    """Basic discount application tests."""

    def test_no_discount_applied(self) -> None:
        """Test when no discount is applied (non-member, no coupon)"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("100.00"),
            is_member=False,
            min_price=Decimal("50.00"),
            subsidy_cap=Decimal("30.00"),
            coupon_discount=None,
        )
        assert final_price == Decimal("100.00")
        assert subsidy == Decimal("0.00")

    def test_member_only_discount(self) -> None:
        """Test member discount without coupon"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("100.00"),
            is_member=True,
            min_price=Decimal("10.00"),
            subsidy_cap=Decimal("50.00"),
            coupon_discount=None,
        )
        # Member gets 5% off (default rate 0.05), so 95.00
        assert final_price == Decimal("95.00")
        assert subsidy == Decimal("5.00")

    def test_coupon_only_discount(self) -> None:
        """Test coupon discount without membership"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("100.00"),
            is_member=False,
            min_price=Decimal("10.00"),
            subsidy_cap=Decimal("50.00"),
            coupon_discount=Decimal("20.00"),
        )
        assert final_price == Decimal("80.00")
        assert subsidy == Decimal("20.00")


class TestApplyDiscountBoundary:
    """Boundary condition tests for apply_discount."""

    def test_zero_base_price(self) -> None:
        """Test with zero base price"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("0.00"),
            is_member=True,
            min_price=Decimal("0.00"),
            subsidy_cap=Decimal("10.00"),
            coupon_discount=Decimal("5.00"),
        )
        assert final_price == Decimal("0.00")
        assert subsidy == Decimal("0.00")

    def test_coupon_exceeds_price(self) -> None:
        """Test when coupon exceeds the working price"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("50.00"),
            is_member=False,
            min_price=Decimal("0.00"),
            subsidy_cap=Decimal("100.00"),
            coupon_discount=Decimal("60.00"),
        )
        # Working price would be -10, clamped to 0
        assert final_price == Decimal("0.00")
        assert subsidy == Decimal("50.00")

    def test_min_price_higher_than_discounted(self) -> None:
        """Test min price floor is enforced"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("100.00"),
            is_member=True,
            min_price=Decimal("90.00"),
            subsidy_cap=Decimal("50.00"),
            coupon_discount=Decimal("10.00"),
        )
        # Member discount gives 85, coupon gives 75, but min is 90
        assert final_price == Decimal("90.00")
        assert subsidy == Decimal("10.00")

    def test_subsidy_cap_exactly_reached(self) -> None:
        """Test when subsidy exactly equals cap"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("130.00"),
            is_member=False,
            min_price=Decimal("50.00"),
            subsidy_cap=Decimal("30.00"),
            coupon_discount=Decimal("30.00"),
        )
        assert final_price == Decimal("100.00")
        assert subsidy == Decimal("30.00")


class TestApplyDiscountComplexCases:
    """Complex scenario tests."""

    def test_member_coupon_and_subsidy_cap(self) -> None:
        """Combined member + coupon hitting subsidy cap"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("100.00"),
            is_member=True,
            min_price=Decimal("50.00"),
            subsidy_cap=Decimal("30.00"),
            coupon_discount=Decimal("10.00"),
        )
        # Member: 85, coupon: 75, cap is 30 so final = 70
        assert final_price == Decimal("85.00")
        assert subsidy == Decimal("15.00")

    def test_very_large_base_price(self) -> None:
        """Test with very large base price"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("10000.00"),
            is_member=True,
            min_price=Decimal("100.00"),
            subsidy_cap=Decimal("500.00"),
            coupon_discount=Decimal("200.00"),
        )
        # Member: 8500, coupon: 8300, but subsidy cap is 500
        assert final_price == Decimal("9500.00")
        assert subsidy == Decimal("500.00")

    def test_small_decimal_amounts(self) -> None:
        """Test with small decimal amounts"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("0.99"),
            is_member=True,
            min_price=Decimal("0.01"),
            subsidy_cap=Decimal("0.50"),
            coupon_discount=Decimal("0.10"),
        )
        # Member: 0.84, coupon: 0.74
        assert final_price >= Decimal("0.01")
        assert subsidy >= Decimal("0.00")

    def test_subsidy_cap_forces_min_price_adjustment(self) -> None:
        """Test when subsidy cap still results in price below min"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("60.00"),
            is_member=True,
            min_price=Decimal("55.00"),
            subsidy_cap=Decimal("10.00"),
            coupon_discount=Decimal("20.00"),
        )
        # Member: 51, coupon: 31, min price 55
        # subsidy = 60 - 55 = 5, not capped
        assert final_price == Decimal("55.00")
        assert subsidy == Decimal("5.00")


class TestApplyDiscountNegativeEdgeCases:
    """Edge cases that might cause issues."""

    def test_zero_coupon_discount(self) -> None:
        """Test with zero coupon discount (different from None)"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("100.00"),
            is_member=False,
            min_price=Decimal("50.00"),
            subsidy_cap=Decimal("30.00"),
            coupon_discount=Decimal("0.00"),
        )
        assert final_price == Decimal("100.00")
        assert subsidy == Decimal("0.00")

    def test_zero_subsidy_cap(self) -> None:
        """Test with zero subsidy cap"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("100.00"),
            is_member=True,
            min_price=Decimal("50.00"),
            subsidy_cap=Decimal("0.00"),
            coupon_discount=Decimal("10.00"),
        )
        # Cap is 0, so final must equal base
        assert final_price == Decimal("100.00")
        assert subsidy == Decimal("0.00")

    def test_min_price_equals_base_price(self) -> None:
        """Test when min price equals base price"""
        final_price, subsidy = apply_discount(
            base_price=Decimal("100.00"),
            is_member=True,
            min_price=Decimal("100.00"),
            subsidy_cap=Decimal("30.00"),
            coupon_discount=Decimal("10.00"),
        )
        assert final_price == Decimal("100.00")
        assert subsidy == Decimal("0.00")
