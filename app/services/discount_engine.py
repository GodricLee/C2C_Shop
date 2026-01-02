"""Pricing and discount calculations."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.config import get_settings

_TWO_DP = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    """Quantize a decimal value to two places."""

    return value.quantize(_TWO_DP, rounding=ROUND_HALF_UP)


def apply_discount(
    base_price: Decimal,
    is_member: bool,
    min_price: Decimal,
    subsidy_cap: Decimal,
    coupon_discount: Decimal | None,
) -> tuple[Decimal, Decimal]:
    """Apply membership and coupon discounts respecting platform guardrails.

    Returns a tuple of (final_price, platform_subsidy).
    
    The discount calculation follows these rules:
    1. Apply member discount first (percentage off base price)
    2. Apply coupon discount (fixed amount off)
    3. Enforce minimum price floor
    4. Enforce subsidy cap (maximum platform can subsidize)
    5. Re-enforce minimum price if subsidy cap adjustment violates it
    
    Args:
        base_price: Original product price
        is_member: Whether buyer has membership discount
        min_price: Minimum allowed final price
        subsidy_cap: Maximum subsidy platform will provide
        coupon_discount: Optional fixed coupon discount amount
        
    Returns:
        Tuple of (final_price, platform_subsidy)
    """
    # Validate inputs to prevent unexpected behavior
    if base_price < Decimal("0"):
        raise ValueError("base_price cannot be negative")
    if min_price < Decimal("0"):
        raise ValueError("min_price cannot be negative")
    if subsidy_cap < Decimal("0"):
        raise ValueError("subsidy_cap cannot be negative")

    settings = get_settings()
    member_rate = Decimal(str(settings.member_discount_rate))

    working_price = base_price
    if is_member and member_rate > Decimal("0"):
        working_price = working_price * (Decimal("1") - member_rate)

    if coupon_discount is not None:
        if coupon_discount < Decimal("0"):
            raise ValueError("coupon_discount cannot be negative")
        working_price -= coupon_discount

    # Enforce minimum price and zero floor
    working_price = max(working_price, min_price)
    working_price = max(working_price, Decimal("0"))

    final_price = _quantize(working_price)
    subsidy = base_price - final_price

    # Apply subsidy cap
    if subsidy > subsidy_cap:
        subsidy = subsidy_cap
        final_price = base_price - subsidy
        # Re-enforce minimum price after subsidy cap adjustment
        if final_price < min_price:
            final_price = min_price
            subsidy = base_price - final_price

    final_price = _quantize(final_price)
    subsidy = _quantize(max(subsidy, Decimal("0")))
    return final_price, subsidy
