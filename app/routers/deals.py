"""Deal management endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.deps import get_current_user
from app.common.exceptions import AppError
from app.db import get_db
from app.models.admin_config import AdminConfig
from app.models.audit_log import AuditLog
from app.models.cashback import Cashback
from app.models.coupon import Coupon, CouponAssignment, CouponStatus
from app.models.deal import Deal, DealStatus
from app.models.product import Product, ProductStatus
from app.models.user import User
from app.schemas.deal import DealConfirmRequest, DealCreate, DealOut
from app.services.discount_engine import apply_discount
from app.services.price_policy import get_active_price_policy

router = APIRouter(prefix="/deals", tags=["deals"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=DealOut)
def create_deal(
    payload: DealCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DealOut:
    """Initiate a deal for a product by the buyer."""

    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if product is None or product.status != ProductStatus.PUBLISHED:
        raise AppError(404, "Product not available")
    if product.seller_id == current_user.id:
        raise AppError(400, "Seller cannot initiate deal as buyer")

    deal = Deal(
        product_id=product.id,
        buyer_id=current_user.id,
        seller_id=product.seller_id,
    )
    db.add(deal)
    db.flush()

    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="deal.create",
            entity="Deal",
            entity_id=str(deal.id),
            diff={"product_id": product.id},
        )
    )
    db.commit()
    db.refresh(deal)
    return DealOut.from_orm(deal)


@router.post("/{deal_id}/confirm-by-seller", response_model=DealOut)
def confirm_deal(
    deal_id: int,
    payload: DealConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DealOut:
    """Confirm a deal by seller, generating cashback if thresholds satisfied."""

    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        raise AppError(404, "Deal not found")
    if deal.seller_id != current_user.id:
        raise AppError(403, "Only seller can confirm deal")
    if deal.status != DealStatus.INITIATED:
        raise AppError(400, "Deal already processed")

    product = db.query(Product).filter(Product.id == deal.product_id).first()
    if product is None:
        raise AppError(404, "Product not found")

    coupon_discount = None
    if payload.coupon_id is not None:
        coupon = db.query(Coupon).filter(Coupon.id == payload.coupon_id).first()
        if coupon is None or coupon.status != CouponStatus.ACTIVE:
            raise AppError(400, "Coupon unavailable")
        if product.price < coupon.min_revenue:
            raise AppError(400, "Coupon revenue threshold unmet")
        completed_sales = (
            db.query(func.count())
            .select_from(Deal)
            .filter(Deal.seller_id == current_user.id, Deal.status == DealStatus.CONFIRMED_BY_SELLER)
            .scalar()
            or 0
        )
        if completed_sales < coupon.min_sales:
            raise AppError(400, "Coupon sales threshold unmet")

        assignment = (
            db.query(CouponAssignment)
            .filter(
                CouponAssignment.user_id == deal.buyer_id,
                CouponAssignment.coupon_id == coupon.id,
                CouponAssignment.used.is_(False),
            )
            .first()
        )
        if assignment is None:
            raise AppError(400, "Coupon not assigned or already used")
        coupon_discount = coupon.discount_amount
        assignment.used = True
        assignment.used_at = datetime.now(tz=timezone.utc)
        deal.used_coupon_id = coupon.id
        db.add(assignment)

    min_price, subsidy_cap = get_active_price_policy(db)
    buyer = deal.buyer
    is_member = bool(
        buyer
        and buyer.membership is not None
        and buyer.membership.level.name == "SHOPPER"
    )
    final_price, subsidy = apply_discount(
        base_price=product.price,
        is_member=is_member,
        min_price=min_price,
        subsidy_cap=subsidy_cap,
        coupon_discount=coupon_discount,
    )

    config = db.query(AdminConfig).first()
    if config is None:
        raise AppError(500, "Admin config missing")
    cashback_ratio = Decimal(str(config.cashback_default))
    cashback_amount = (final_price * cashback_ratio).quantize(Decimal("0.01"))

    cashback = Cashback(
        deal_id=deal.id,
        ratio=cashback_ratio,
        amount=cashback_amount,
    )
    deal.status = DealStatus.CONFIRMED_BY_SELLER
    deal.confirmed_at = datetime.now(tz=timezone.utc)
    deal.cashback = cashback
    product.status = ProductStatus.SOLD

    db.add(cashback)
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="deal.confirm",
            entity="Deal",
            entity_id=str(deal.id),
            diff={
                "final_price": str(final_price),
                "subsidy": str(subsidy),
                "cashback": str(cashback_amount),
            },
        )
    )
    db.commit()
    db.refresh(deal)
    return DealOut.from_orm(deal)


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(
    deal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DealOut:
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        raise AppError(404, "Deal not found")
    if current_user.id not in {deal.buyer_id, deal.seller_id} and not current_user.is_admin:
        raise AppError(403, "Not authorized to view deal")
    return DealOut.from_orm(deal)
