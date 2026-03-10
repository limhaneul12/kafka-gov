"""Shared Interface Schemas (Pydantic)"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BrokerResponse(BaseModel):
    """브로커 정보 응답 스키마"""

    model_config = ConfigDict(from_attributes=True)

    broker_id: int
    host: str
    port: int
    is_controller: bool
    leader_partition_count: int


class ClusterStatusResponse(BaseModel):
    """클러스터 상태 응답 스키마"""

    model_config = ConfigDict(from_attributes=True)

    cluster_id: str
    controller_id: int
    brokers: list[BrokerResponse]
    total_topics: int
    total_partitions: int


class ApprovalRequestCreateRequest(BaseModel):
    resource_type: str = Field(..., examples=["topic"])
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
