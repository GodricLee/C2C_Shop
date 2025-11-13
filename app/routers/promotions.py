"""Promotion and coupon endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.deps import get_admin
from app.common.exceptions import AppError
from app.common.serialization import serialize_diff
from app.db import get_db
from app.models.audit_log import AuditLog
from app.models.coupon import Coupon, CouponAssignment
from app.models.user import User
from app.schemas.coupon import CouponAssignRequest, CouponCreate, CouponOut, CouponUpdate

router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.post("/coupons", status_code=status.HTTP_201_CREATED, response_model=CouponOut)
def create_coupon(
    payload: CouponCreate,
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> CouponOut:
    coupon = Coupon(**payload.dict())
    db.add(coupon)
    db.flush()

    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            action="coupon.create",
            entity="Coupon",
            entity_id=str(coupon.id),
            diff=serialize_diff(payload.dict()),
        )
    )
    db.commit()
    db.refresh(coupon)
    return CouponOut.from_orm(coupon)


@router.put("/coupons/{coupon_id}", response_model=CouponOut)
def update_coupon(
    coupon_id: int,
    payload: CouponUpdate,
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> CouponOut:
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if coupon is None:
        raise AppError(404, "Coupon not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(coupon, key, value)

    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            action="coupon.update",
            entity="Coupon",
            entity_id=str(coupon.id),
            diff=serialize_diff(update_data),
        )
    )
    db.commit()
    db.refresh(coupon)
    return CouponOut.from_orm(coupon)


@router.get("/coupons", response_model=list[CouponOut])
def list_coupons(admin_user: User = Depends(get_admin), db: Session = Depends(get_db)) -> list[CouponOut]:
    coupons = db.query(Coupon).order_by(Coupon.created_at.desc()).all()
    _ = admin_user
    return [CouponOut.from_orm(item) for item in coupons]


@router.post("/coupons/{coupon_id}/assign", response_model=CouponOut)
def assign_coupon(
    coupon_id: int,
    payload: CouponAssignRequest,
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> CouponOut:
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if coupon is None:
        raise AppError(404, "Coupon not found")

    existing = (
        db.query(CouponAssignment)
        .filter(
            CouponAssignment.user_id == payload.user_id,
            CouponAssignment.coupon_id == coupon.id,
        )
        .first()
    )
    if existing is not None:
        raise AppError(409, "Coupon already assigned to user")

    assignment = CouponAssignment(user_id=payload.user_id, coupon_id=coupon.id, used=False)
    db.add(assignment)
    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            action="coupon.assign",
            entity="Coupon",
            entity_id=str(coupon.id),
            diff={"user_id": payload.user_id},
        )
    )
    db.commit()
    db.refresh(coupon)
    return CouponOut.from_orm(coupon)
