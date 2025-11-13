"""User and security related ORM models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class TwoFAMethodType(str, Enum):
    """Supported second-factor delivery channels."""

    EMAIL = "EMAIL"
    SMS = "SMS"
    TOTP = "TOTP"


class RiskEventType(str, Enum):
    """Enumerates supported risk event classifications."""

    ABNORMAL_LOGIN = "ABNORMAL_LOGIN"
    MULTI_DEVICE = "MULTI_DEVICE"
    SUSPICIOUS_LOCATION = "SUSPICIOUS_LOCATION"


class UserStatus(str, Enum):
    """Logical user states used for moderation."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class User(Base):
    """Account entity representing buyers, sellers, and admin."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        SqlEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False
    )
    two_fa_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    two_fa_methods: Mapped[List["TwoFAMethod"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    devices: Mapped[List["DeviceFingerprint"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    risk_events: Mapped[List["RiskEvent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    membership: Mapped[Optional["Membership"]] = relationship(
        back_populates="user", uselist=False
    )
    coupon_assignments: Mapped[List["CouponAssignment"]] = relationship(
        back_populates="user"
    )
    buyer_deals: Mapped[List["Deal"]] = relationship(
        back_populates="buyer", foreign_keys="Deal.buyer_id"
    )
    seller_deals: Mapped[List["Deal"]] = relationship(
        back_populates="seller", foreign_keys="Deal.seller_id"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="actor")
    products: Mapped[List["Product"]] = relationship(back_populates="seller")


class TwoFAMethod(Base):
    """Second-factor configuration linked to a user."""

    __tablename__ = "two_fa_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[TwoFAMethodType] = mapped_column(SqlEnum(TwoFAMethodType), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="two_fa_methods")


class Session(Base):
    """Server-side session to support revocation of JWT tokens."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_info: Mapped[Optional[str]] = mapped_column(String(255))
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")


class DeviceFingerprint(Base):
    """Known device fingerprint used for risk detection."""

    __tablename__ = "device_fingerprints"
    __table_args__ = (UniqueConstraint("user_id", "fingerprint", name="uq_device_fingerprint"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="devices")


class RiskEvent(Base):
    """Captures anomalous security events associated with a user."""

    __tablename__ = "risk_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[RiskEventType] = mapped_column(SqlEnum(RiskEventType), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="risk_events")
