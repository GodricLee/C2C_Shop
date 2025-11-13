"""Authentication API routes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.deps import get_current_user
from app.common.exceptions import AppError
from app.db import get_db
from app.models.audit_log import AuditLog
from app.models.user import Session as SessionModel
from app.models.user import TwoFAMethod, TwoFAMethodType, User
from app.schemas.auth import (
    LoginFlowResponse,
    LoginRequest,
    LogoutRequest,
    TokenResponse,
    Verify2FARequest,
)
from app.schemas.user import SessionOut, UserCreate, UserOut
from app.security import auth as auth_security
from app.security.hashing import hash_password
from app.services import risk_engine

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    """Register a new user account."""

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise AppError(409, "Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        two_fa_enabled=True,
    )
    db.add(user)
    db.flush()

    method = TwoFAMethod(
        user_id=user.id,
        type=TwoFAMethodType.EMAIL,
        secret="stub",
        enabled=True,
    )
    db.add(method)
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="user.register",
            entity="User",
            entity_id=str(user.id),
            diff={"email": user.email},
        )
    )
    db.commit()
    db.refresh(user)
    return UserOut.from_orm(user)


@router.post("/login", response_model=LoginFlowResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginFlowResponse:
    """Start the login process and issue a 2FA challenge."""

    user = auth_security.authenticate_user(db, payload.email, payload.password)
    assessment = risk_engine.evaluate_login(
        db,
        user,
        device_fingerprint=payload.device_info,
        ip_address=payload.ip_address,
    )
    flow = auth_security.initiate_login_flow(
        user,
        channel=TwoFAMethodType.EMAIL,
        device_info=payload.device_info,
        ip_address=payload.ip_address,
    )
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="auth.login.init",
            entity="User",
            entity_id=str(user.id),
            diff={"risk_score": assessment.score, "reason": assessment.reason},
        )
    )
    db.commit()
    return LoginFlowResponse.from_orm(flow)


@router.post("/verify-2fa", response_model=TokenResponse)
def verify_twofa(payload: Verify2FARequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Complete login after validating 2FA code."""

    token, session = auth_security.complete_twofa(db, payload.flow_id, payload.code)
    db.add(
        AuditLog(
            actor_user_id=session.user_id,
            action="auth.login.success",
            entity="Session",
            entity_id=str(session.id),
            diff={"issued_at": session.issued_at.isoformat()},
        )
    )
    db.commit()
    return TokenResponse(
        access_token=token,
        session=SessionOut.from_orm(session),
    )


@router.post("/logout", response_model=dict)
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Revoke a user session."""

    session = db.query(SessionModel).filter(SessionModel.id == payload.session_id).first()
    if session is None or session.user_id != current_user.id:
        raise AppError(404, "Session not found")
    session.revoked = True
    db.add(session)
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="auth.logout",
            entity="Session",
            entity_id=str(session.id),
            diff={"revoked_at": datetime.now(tz=timezone.utc).isoformat()},
        )
    )
    db.commit()
    return {"message": "Logged out"}
