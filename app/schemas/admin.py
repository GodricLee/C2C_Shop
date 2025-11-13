"""Admin schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from pydantic import BaseModel, Field

from app.models.parameter_set import ParameterStatus
from app.schemas.common import APIModel, AuditInfo


class AdminConfigUpdate(BaseModel):
    commission_rate: Decimal = Field(..., ge=Decimal("0"))
    cashback_default: Decimal = Field(..., ge=Decimal("0"), le=Decimal("1"))


class AdminConfigOut(APIModel):
    commission_rate: Decimal
    cashback_default: Decimal
    current_parameter_set_id: Optional[int]


class ParameterSetCreate(BaseModel):
    version: int
    payload: Dict[str, object] = Field(default_factory=dict)
    min_price: Decimal = Field(..., ge=Decimal("0"))
    subsidy_cap: Decimal = Field(..., ge=Decimal("0"))


class ParameterSetOut(APIModel):
    id: int
    version: int
    status: ParameterStatus
    effective_at: Optional[datetime]
    created_at: datetime
    payload: Dict[str, object]
    previous_version_id: Optional[int]


class ParameterPublishRequest(BaseModel):
    effective_at: Optional[datetime] = None


class AuditLogResponse(AuditInfo):
    pass
