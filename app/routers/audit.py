"""Audit log retrieval endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.deps import get_admin
from app.common.pagination import apply_pagination, pagination_params
from app.db import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.common import AuditInfo

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditInfo])
def list_audit_logs(
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
    actor_user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[AuditInfo]:
    query = db.query(AuditLog)
    if actor_user_id is not None:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    if entity is not None:
        query = query.filter(AuditLog.entity == entity)
    if start is not None:
        query = query.filter(AuditLog.created_at >= start)
    if end is not None:
        query = query.filter(AuditLog.created_at <= end)

    page, page_size = pagination
    statement = apply_pagination(query.order_by(AuditLog.created_at.desc()).statement, page, page_size)
    rows = db.execute(statement).scalars().all()
    _ = admin_user
    return [AuditInfo.from_orm(row) for row in rows]
