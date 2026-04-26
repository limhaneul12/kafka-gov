"""Approval and audit API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    approver: str = Field(..., min_length=1)
    decision_reason: str | None = Field(default=None, max_length=500)


class AuditActivityResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    activity_type: str
    action: str
    target: str
    message: str
    actor: str
    team: str | None = None
    timestamp: datetime
    metadata: dict[str, Any] | None = None
