"""거버넌스 리포지토리 포트 — 도메인이 인프라에 요구하는 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.governance.domain.models.governance import (
    ApprovalRequest,
    GovernancePolicy,
    PolicyEvaluation,
)
from app.governance.types import (
    ApprovalId,
    ApprovalStatus,
    PolicyId,
    PolicyStatus,
    PolicyType,
)
from app.shared.types import Environment


class IPolicyRepository(ABC):
    """정책 영속성 포트"""

    @abstractmethod
    async def save(self, policy: GovernancePolicy) -> None:
        """정책을 저장(생성 또는 갱신)한다."""

    @abstractmethod
    async def find_by_id(self, policy_id: PolicyId) -> GovernancePolicy | None:
        """ID로 정책을 조회한다."""

    @abstractmethod
    async def list_active(
        self,
        *,
        policy_type: PolicyType | None = None,
        environment: Environment | None = None,
    ) -> list[GovernancePolicy]:
        """활성 정책 목록을 조회한다."""

    @abstractmethod
    async def list_all(
        self,
        *,
        status: PolicyStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GovernancePolicy]:
        """전체 정책 목록을 조회한다."""

    @abstractmethod
    async def delete(self, policy_id: PolicyId) -> None:
        """정책을 삭제한다."""


class IApprovalRepository(ABC):
    """승인 요청 영속성 포트"""

    @abstractmethod
    async def save(self, request: ApprovalRequest) -> None:
        """승인 요청을 저장(생성 또는 갱신)한다."""

    @abstractmethod
    async def find_by_id(self, approval_id: ApprovalId) -> ApprovalRequest | None:
        """ID로 승인 요청을 조회한다."""

    @abstractmethod
    async def list_pending(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ApprovalRequest]:
        """대기 중인 승인 요청 목록을 조회한다."""

    @abstractmethod
    async def list_by_status(
        self,
        status: ApprovalStatus,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ApprovalRequest]:
        """상태별 승인 요청 목록을 조회한다."""

    @abstractmethod
    async def list_by_resource(
        self,
        resource_type: str,
        resource_id: str,
    ) -> list[ApprovalRequest]:
        """리소스별 승인 요청 이력을 조회한다."""


class IPolicyEvaluationRepository(ABC):
    """정책 평가 이력 영속성 포트"""

    @abstractmethod
    async def save(self, evaluation: PolicyEvaluation) -> None:
        """평가 결과를 저장한다."""

    @abstractmethod
    async def list_by_target(
        self,
        target_id: str,
        *,
        limit: int = 20,
    ) -> list[PolicyEvaluation]:
        """대상별 평가 이력을 조회한다."""

    @abstractmethod
    async def latest_for_target(
        self,
        target_id: str,
        policy_id: PolicyId,
    ) -> PolicyEvaluation | None:
        """대상에 대한 특정 정책의 최신 평가 결과를 조회한다."""
