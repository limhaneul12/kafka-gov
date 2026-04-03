"""승인 워크플로 유스케이스 — 요청, 승인, 거부"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from app.governance.domain.models.commands import (
    DecideApprovalCommand,
    RequestApprovalCommand,
)
from app.governance.domain.models.governance import ApprovalRequest
from app.governance.domain.repositories.governance_repository import IApprovalRepository
from app.governance.types import ApprovalId, ApprovalStatus
from app.shared.exceptions.base_exceptions import NotFoundError
from app.shared.exceptions.governance_exceptions import (
    ApprovalExpiredError,
    ApprovalRequiredError,
)

logger = logging.getLogger(__name__)


class RequestApprovalUseCase:
    """승인 요청 생성

    비즈니스 규칙:
    - 정책 위반이 있어야 승인 요청 가능
    - TTL 기반 자동 만료 설정
    """

    def __init__(self, repository: IApprovalRepository) -> None:
        self._repository = repository

    async def execute(self, command: RequestApprovalCommand) -> ApprovalRequest:
        if not command.violations:
            raise ApprovalRequiredError(["no violations to approve"])

        request = ApprovalRequest(
            approval_id=f"ar-{uuid.uuid4().hex[:12]}",
            resource_type=command.resource_type,
            resource_id=command.resource_id,
            change_type=command.change_type,
            summary=command.summary,
            justification=command.justification,
            requested_by=command.requested_by,
            status=ApprovalStatus.PENDING,
            violations=list(command.violations),
            risk_level=command.risk_level,
            requested_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=command.ttl_hours),
        )

        await self._repository.save(request)

        logger.info(
            "approval_requested",
            extra={
                "approval_id": request.approval_id,
                "resource": f"{command.resource_type}:{command.resource_id}",
                "risk_level": command.risk_level,
                "violations": len(command.violations),
            },
        )
        return request


class ApproveRequestUseCase:
    """승인 요청 승인"""

    def __init__(self, repository: IApprovalRepository) -> None:
        self._repository = repository

    async def execute(self, command: DecideApprovalCommand) -> ApprovalRequest:
        request = await self._load(command.approval_id)
        self._check_expiry(request)

        request.approve(command.approver, command.reason)
        await self._repository.save(request)

        logger.info(
            "approval_granted",
            extra={
                "approval_id": command.approval_id,
                "approver": command.approver,
            },
        )
        return request

    async def _load(self, approval_id: ApprovalId) -> ApprovalRequest:
        request = await self._repository.find_by_id(approval_id)
        if request is None:
            raise NotFoundError("ApprovalRequest", approval_id)
        return request

    def _check_expiry(self, request: ApprovalRequest) -> None:
        if request.expires_at and datetime.now() > request.expires_at:
            request.expire()
            raise ApprovalExpiredError(request.approval_id)


class RejectRequestUseCase:
    """승인 요청 거부"""

    def __init__(self, repository: IApprovalRepository) -> None:
        self._repository = repository

    async def execute(self, command: DecideApprovalCommand) -> ApprovalRequest:
        request = await self._load(command.approval_id)
        self._check_expiry(request)

        request.reject(command.approver, command.reason)
        await self._repository.save(request)

        logger.info(
            "approval_rejected",
            extra={
                "approval_id": command.approval_id,
                "approver": command.approver,
            },
        )
        return request

    async def _load(self, approval_id: ApprovalId) -> ApprovalRequest:
        request = await self._repository.find_by_id(approval_id)
        if request is None:
            raise NotFoundError("ApprovalRequest", approval_id)
        return request

    def _check_expiry(self, request: ApprovalRequest) -> None:
        if request.expires_at and datetime.now() > request.expires_at:
            request.expire()
            raise ApprovalExpiredError(request.approval_id)
