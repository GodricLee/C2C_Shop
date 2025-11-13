"""Pytest fixtures for backend tests."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.common.deps import get_current_user
from app.db import Base
from app.main import create_app
from app.models.admin_config import AdminConfig
from app.models.membership import Membership, MembershipLevel
from app.models.parameter_set import ParameterSet, ParameterStatus, PricePolicy
from app.models.user import TwoFAMethod, TwoFAMethodType, User
from app.security.hashing import hash_password

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"
os.environ.setdefault("DB_URL", SQLALCHEMY_DATABASE_URL)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("TWOFA_CHANNELS", "email")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session: Session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def app(db_session: Session) -> Generator:
    application = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            db_session.rollback()

    from app.db import get_db  # local import to avoid circular

    application.dependency_overrides[get_db] = override_get_db
    yield application
    application.dependency_overrides.clear()


@pytest.fixture()
def client(app) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def user_factory(db_session: Session) -> Callable[..., User]:
    def _create(
        email: str,
        *,
        password: str = "password123",
        is_admin: bool = False,
        membership_level: MembershipLevel | None = None,
    ) -> User:
        user = User(email=email, password_hash=hash_password(password), is_admin=is_admin)
        db_session.add(user)
        db_session.flush()
        db_session.add(
            TwoFAMethod(
                user_id=user.id,
                type=TwoFAMethodType.EMAIL,
                secret="seed-code",
                enabled=True,
            )
        )
        if membership_level is not None:
            membership = Membership(
                user_id=user.id,
                level=membership_level,
                expires_at=datetime.now(tz=timezone.utc) + timedelta(days=365),
            )
            db_session.add(membership)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create


@pytest.fixture()
def test_user(user_factory) -> User:
    return user_factory("tester@example.com")


@pytest.fixture()
def admin_user(user_factory) -> User:
    return user_factory("admin@example.com", password="admin123", is_admin=True)


@pytest.fixture()
def buyer_user(user_factory) -> User:
    return user_factory(
        "buyer@example.com",
        password="buyer123",
        membership_level=MembershipLevel.SHOPPER,
    )


@pytest.fixture()
def pricing_setup(db_session: Session) -> AdminConfig:
    config = AdminConfig(commission_rate=Decimal("0.05"), cashback_default=Decimal("0.02"))
    db_session.add(config)
    db_session.flush()

    parameter = ParameterSet(
        admin_config_id=config.id,
        version=1,
        status=ParameterStatus.PUBLISHED,
        effective_at=datetime.now(tz=timezone.utc),
        payload={"seed": True},
    )
    db_session.add(parameter)
    db_session.flush()
    config.current_parameter_set_id = parameter.id

    db_session.add(
        PricePolicy(
            parameter_set_id=parameter.id,
            min_price=Decimal("50.00"),
            subsidy_cap=Decimal("30.00"),
        )
    )
    db_session.commit()
    return config


@pytest.fixture()
def current_user_override(app) -> Generator[Callable[[User], dict[str, str]], None, None]:
    def _set_user(user: User) -> dict[str, str]:
        def override_current_user() -> User:
            return user

        app.dependency_overrides[get_current_user] = override_current_user
        return {"Authorization": f"Bearer test-{user.id}"}

    try:
        yield _set_user
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def auth_headers(current_user_override, test_user: User) -> dict[str, str]:
    return current_user_override(test_user)