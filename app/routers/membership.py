"""Membership endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.deps import get_current_user
from app.common.exceptions import AppError
from app.db import get_db
from app.models.audit_log import AuditLog
from app.models.membership import Membership, MembershipLevel
from app.models.user import User
from app.schemas.membership import MembershipOut, MembershipUpgradeRequest

router = APIRouter(prefix="/membership", tags=["membership"])


@router.get("/me", response_model=MembershipOut)
def get_membership(current_user: User = Depends(get_current_user)) -> MembershipOut:
    membership = current_user.membership
    if membership is None:
        raise AppError(404, "Membership not found")
    return MembershipOut.from_orm(membership)


@router.post("/upgrade", response_model=MembershipOut)
def upgrade_membership(
    payload: MembershipUpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MembershipOut:
    expires_at = datetime.now(tz=timezone.utc) + timedelta(days=payload.duration_days)

    membership = current_user.membership
    if membership is None:
        membership = Membership(
            user_id=current_user.id,
            level=payload.level,
            expires_at=expires_at,
        )
        db.add(membership)
    else:
        membership.level = payload.level
        membership.expires_at = expires_at

    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="membership.upgrade",
            entity="Membership",
            entity_id=str(current_user.id),
            diff={"level": payload.level.value, "expires_at": expires_at.isoformat()},
        )
    )
    db.commit()
    db.refresh(membership)
    return MembershipOut.from_orm(membership)
