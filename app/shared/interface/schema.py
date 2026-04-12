"""Shared Interface Schemas (Pydantic)"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApprovalRequestCreateRequest(BaseModel):
    resource_type: str = Field(..., examples=["schema"])
    resource_name: str
    change_type: str
    change_ref: str | None = None
    summary: str
    justification: str
    requested_by: str
    metadata: dict[str, Any] | None = None


class ApprovalDecisionRequest(BaseModel):
    approver: str
    decision_reason: str | None = None


class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    resource_type: str
    resource_name: str
    change_type: str
    change_ref: str | None = None
    summary: str
    justification: str
    requested_by: str
    status: str
    approver: str | None = None
    decision_reason: str | None = None
    metadata: dict[str, Any] | None = None
    requested_at: datetime
    decided_at: datetime | None = None
