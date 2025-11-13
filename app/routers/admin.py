"""Admin endpoints for managing configuration and moderation."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.deps import get_admin
from app.common.exceptions import AppError
from app.common.serialization import serialize_diff
from app.db import get_db
from app.models.admin_config import AdminConfig
from app.models.audit_log import AuditLog
from app.models.parameter_set import ParameterSet, ParameterStatus, PricePolicy
from app.models.tag import Tag, TagAudit, TagStatus
from app.models.user import User
from app.schemas.admin import (
    AdminConfigOut,
    AdminConfigUpdate,
    ParameterPublishRequest,
    ParameterSetCreate,
    ParameterSetOut,
)
from app.schemas.tag import TagModerationRequest, TagOut

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_or_create_config(db: Session) -> AdminConfig:
    config = db.query(AdminConfig).first()
    if config is None:
        config = AdminConfig(commission_rate=Decimal("0.05"), cashback_default=Decimal("0.02"))
        db.add(config)
        db.flush()
    return config


@router.get("/config", response_model=AdminConfigOut)
def get_config(admin_user: User = Depends(get_admin), db: Session = Depends(get_db)) -> AdminConfigOut:
    config = _get_or_create_config(db)
    db.refresh(config)
    return AdminConfigOut.from_orm(config)


@router.put("/config", response_model=AdminConfigOut)
def update_config(
    payload: AdminConfigUpdate,
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> AdminConfigOut:
    config = _get_or_create_config(db)
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            action="admin.config.update",
            entity="AdminConfig",
            entity_id=str(config.id),
            diff=serialize_diff(update_data),
        )
    )
    db.commit()
    db.refresh(config)
    return AdminConfigOut.from_orm(config)


@router.get("/parameters", response_model=list[ParameterSetOut])
def list_parameter_sets(admin_user: User = Depends(get_admin), db: Session = Depends(get_db)) -> list[ParameterSetOut]:
    sets = db.query(ParameterSet).order_by(ParameterSet.version.desc()).all()
    _ = admin_user
    return [ParameterSetOut.from_orm(item) for item in sets]


@router.post("/parameters", status_code=status.HTTP_201_CREATED, response_model=ParameterSetOut)
def create_parameter_set(
    payload: ParameterSetCreate,
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> ParameterSetOut:
    config = _get_or_create_config(db)
    previous = (
        db.query(ParameterSet)
        .filter(ParameterSet.admin_config_id == config.id)
        .order_by(ParameterSet.version.desc())
        .first()
    )

    parameter_set = ParameterSet(
        admin_config_id=config.id,
        version=payload.version,
        status=ParameterStatus.DRAFT,
        payload=payload.payload,
        previous_version_id=previous.id if previous else None,
    )
    db.add(parameter_set)
    db.flush()

    policy = PricePolicy(
        parameter_set_id=parameter_set.id,
        min_price=payload.min_price,
        subsidy_cap=payload.subsidy_cap,
    )
    db.add(policy)
    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            action="admin.parameter.create",
            entity="ParameterSet",
            entity_id=str(parameter_set.id),
            diff={
                "version": payload.version,
                "min_price": str(payload.min_price),
                "subsidy_cap": str(payload.subsidy_cap),
            },
        )
    )
    db.commit()
    db.refresh(parameter_set)
    return ParameterSetOut.from_orm(parameter_set)


@router.post("/parameters/{parameter_id}/publish", response_model=ParameterSetOut)
def publish_parameter_set(
    parameter_id: int,
    payload: ParameterPublishRequest,
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> ParameterSetOut:
    config = _get_or_create_config(db)
    parameter = db.query(ParameterSet).filter(ParameterSet.id == parameter_id).first()
    if parameter is None:
        raise AppError(404, "Parameter set not found")

    parameter.status = ParameterStatus.PUBLISHED
    parameter.effective_at = payload.effective_at or datetime.now(tz=timezone.utc)
    config.current_parameter_set_id = parameter.id

    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            action="admin.parameter.publish",
            entity="ParameterSet",
            entity_id=str(parameter.id),
            diff={"effective_at": parameter.effective_at.isoformat()},
        )
    )
    db.commit()
    db.refresh(parameter)
    return ParameterSetOut.from_orm(parameter)


@router.post("/parameters/{parameter_id}/rollback", response_model=ParameterSetOut)
def rollback_parameter_set(
    parameter_id: int,
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> ParameterSetOut:
    config = _get_or_create_config(db)
    parameter = db.query(ParameterSet).filter(ParameterSet.id == parameter_id).first()
    if parameter is None or parameter.previous_version_id is None:
        raise AppError(400, "No previous version to rollback to")

    previous = db.query(ParameterSet).filter(ParameterSet.id == parameter.previous_version_id).first()
    if previous is None:
        raise AppError(404, "Previous parameter set not found")

    config.current_parameter_set_id = previous.id

    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            action="admin.parameter.rollback",
            entity="ParameterSet",
            entity_id=str(previous.id),
            diff={"from": parameter.id, "to": previous.id},
        )
    )
    db.commit()
    db.refresh(previous)
    return ParameterSetOut.from_orm(previous)


@router.get("/tags/pending", response_model=list[TagOut])
def list_pending_tags(admin_user: User = Depends(get_admin), db: Session = Depends(get_db)) -> list[TagOut]:
    tags = db.query(Tag).filter(Tag.status == TagStatus.PENDING).all()
    _ = admin_user
    return [TagOut.from_orm(tag) for tag in tags]


def _update_tag_status(
    db: Session,
    tag: Tag,
    status: TagStatus,
    admin_user: User,
    reason: str | None,
    extra_diff: dict[str, str] | None = None,
) -> Tag:
    tag.status = status
    diff = {"status": status.value}
    if reason:
        diff["reason"] = reason
    if extra_diff:
        diff.update(extra_diff)
    audit = TagAudit(
        tag_id=tag.id,
        actor_admin_id=admin_user.id,
        action=status.value,
        reason=reason,
    )
    db.add(audit)
    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            action=f"admin.tag.{status.value.lower()}",
            entity="Tag",
            entity_id=str(tag.id),
            diff=diff,
        )
    )
    return tag


@router.post("/tags/{tag_id}/approve", response_model=TagOut)
def approve_tag(
    tag_id: int,
    payload: TagModerationRequest,
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> TagOut:
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if tag is None:
        raise AppError(404, "Tag not found")
    _update_tag_status(db, tag, TagStatus.APPROVED, admin_user, payload.reason)
    db.commit()
    db.refresh(tag)
    return TagOut.from_orm(tag)


@router.post("/tags/{tag_id}/reject", response_model=TagOut)
def reject_tag(
    tag_id: int,
    payload: TagModerationRequest,
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> TagOut:
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if tag is None:
        raise AppError(404, "Tag not found")
    _update_tag_status(db, tag, TagStatus.REJECTED, admin_user, payload.reason)
    db.commit()
    db.refresh(tag)
    return TagOut.from_orm(tag)


@router.post("/tags/{tag_id}/merge", response_model=TagOut)
def merge_tag(
    tag_id: int,
    payload: TagModerationRequest,
    admin_user: User = Depends(get_admin),
    db: Session = Depends(get_db),
) -> TagOut:
    if payload.merge_to_tag_id is None:
        raise AppError(400, "Target tag id required for merge")

    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    target = db.query(Tag).filter(Tag.id == payload.merge_to_tag_id).first()
    if tag is None or target is None:
        raise AppError(404, "Tag not found")

    for product in tag.products:
        if target not in product.tags:
            product.tags.append(target)
    _update_tag_status(
        db,
        tag,
        TagStatus.MERGED,
        admin_user,
        payload.reason,
        extra_diff={"merged_into": str(target.id)},
    )
    db.commit()
    db.refresh(tag)
    return TagOut.from_orm(tag)