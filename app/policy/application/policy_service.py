"""정책 평가 서비스"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..domain.models import DomainPolicySet

from ..domain import (
    DomainEnvironment,
    DomainPolicyViolation,
    DomainResourceType,
    IPolicyRepository,
    PolicyEngine,
    PolicyTarget,
)
from ..domain.models import DomainPolicySeverity


class PolicyEvaluationService:
    """정책 평가 서비스"""

    def __init__(
        self, policy_engine: PolicyEngine, policy_repository: IPolicyRepository | None = None
    ) -> None:
        self._policy_engine = policy_engine
        self._policy_repository = policy_repository

    async def evaluate_batch(
        self,
        environment: DomainEnvironment,
        resource_type: DomainResourceType,
        targets: Iterable[PolicyTarget],
        actor: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[DomainPolicyViolation]:
        """배치 정책 평가

        Args:
            environment: 대상 환경
            resource_type: 리소스 타입 (Topic/Schema)
            targets: 평가 대상 목록
            actor: 요청자
            metadata: 추가 메타데이터

        Returns:
            정책 위반 목록
        """
        # 저장소에서 최신 정책 로드 (옵션)
        if self._policy_repository:
            policy_set = await self._policy_repository.get_policy_set(environment, resource_type)
            if policy_set:
                self._policy_engine.register_policy_set(policy_set)

        # 정책 평가 실행
        return self._policy_engine.evaluate(
            environment=environment,
            resource_type=resource_type,
            targets=targets,
            actor=actor,
            metadata=metadata,
        )

    async def evaluate_single(
        self,
        environment: DomainEnvironment,
        resource_type: DomainResourceType,
        target: PolicyTarget,
        actor: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[DomainPolicyViolation]:
        """단일 대상 정책 평가"""
        return await self.evaluate_batch(
            environment=environment,
            resource_type=resource_type,
            targets=[target],
            actor=actor,
            metadata=metadata,
        )

    def has_blocking_violations(self, violations: list[DomainPolicyViolation]) -> bool:
        """차단 수준의 위반이 있는지 확인

        WARNING 수준은 허용, ERROR/CRITICAL은 차단
        """

        return any(
            v.severity in (DomainPolicySeverity.ERROR, DomainPolicySeverity.CRITICAL)
            for v in violations
        )

    def group_violations_by_severity(
        self, violations: list[DomainPolicyViolation]
    ) -> dict[str, list[DomainPolicyViolation]]:
        """심각도별 위반 그룹화"""

        groups: dict[str, list[DomainPolicyViolation]] = defaultdict(list)
        for violation in violations:
            groups[violation.severity.value].append(violation)

        return dict(groups)


class PolicyManagementService:
    """정책 관리 서비스"""

    def __init__(self, policy_engine: PolicyEngine, policy_repository: IPolicyRepository) -> None:
        self._policy_engine = policy_engine
        self._policy_repository = policy_repository

    async def load_all_policies(self) -> None:
        """모든 정책을 저장소에서 로드하여 엔진에 등록"""
        environments = await self._policy_repository.list_environments()

        for env in environments:
            resource_types = await self._policy_repository.list_resource_types(env)
            for rt in resource_types:
                policy_set = await self._policy_repository.get_policy_set(env, rt)
                if policy_set:
                    self._policy_engine.register_policy_set(policy_set)

    async def update_policy_set(
        self,
        environment: DomainEnvironment,
        resource_type: DomainResourceType,
        policy_set: DomainPolicySet,
    ) -> None:
        """정책 집합 업데이트"""
        # 저장소에 저장
        await self._policy_repository.save_policy_set(policy_set)

        # 엔진에 등록
        self._policy_engine.register_policy_set(policy_set)

    async def delete_policy_set(
        self, environment: DomainEnvironment, resource_type: DomainResourceType
    ) -> bool:
        """정책 집합 삭제"""
        return await self._policy_repository.delete_policy_set(environment, resource_type)

    def get_active_policy_set(
        self, environment: DomainEnvironment, resource_type: DomainResourceType
    ) -> DomainPolicySet | None:
        """현재 활성화된 정책 집합 조회"""
        return self._policy_engine.get_policy_set(environment, resource_type)
