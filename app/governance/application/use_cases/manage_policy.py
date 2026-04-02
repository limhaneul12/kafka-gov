"""거버넌스 정책 관리 유스케이스 — 생성, 활성화, 아카이브"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.governance.domain.models.governance import GovernancePolicy, PolicyRule
from app.governance.domain.repositories.governance_repository import IPolicyRepository
from app.governance.types import (
    PolicyId,
    PolicyScope,
    PolicyStatus,
    PolicyType,
    RiskLevel,
    RuleId,
)
from app.shared.exceptions.governance_exceptions import PolicyNotFoundError
from app.shared.types import DomainName, Environment, ProductId

logger = logging.getLogger(__name__)


class CreatePolicyUseCase:
    """거버넌스 정책 생성 — DRAFT 상태로 시작"""

    def __init__(self, repository: IPolicyRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        name: str,
        description: str,
        policy_type: PolicyType,
        scope: PolicyScope,
        created_by: str,
        target_domains: list[DomainName] | None = None,
        target_environments: list[Environment] | None = None,
        target_products: list[ProductId] | None = None,
    ) -> GovernancePolicy:
        policy = GovernancePolicy(
            policy_id=f"gp-{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            policy_type=policy_type,
            status=PolicyStatus.DRAFT,
            scope=scope,
            target_domains=target_domains or [],
            target_environments=target_environments or [],
            target_products=target_products or [],
            created_by=created_by,
            created_at=datetime.now(),
        )

        await self._repository.save(policy)

        logger.info(
            "policy_created",
            extra={"policy_id": policy.policy_id, "type": policy_type},
        )
        return policy


class AddPolicyRuleUseCase:
    """정책에 규칙 추가 (DRAFT 상태에서만 가능)"""

    def __init__(self, repository: IPolicyRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        policy_id: PolicyId,
        *,
        rule_id: RuleId,
        name: str,
        expression: str,
        message: str,
        severity: RiskLevel = RiskLevel.MEDIUM,
    ) -> GovernancePolicy:
        policy = await self._load(policy_id)

        rule = PolicyRule(
            rule_id=rule_id,
            name=name,
            expression=expression,
            message=message,
            severity=severity,
        )
        policy.add_rule(rule)
        policy.updated_at = datetime.now()
        await self._repository.save(policy)

        logger.info(
            "policy_rule_added",
            extra={"policy_id": policy_id, "rule_id": rule_id},
        )
        return policy

    async def _load(self, policy_id: PolicyId) -> GovernancePolicy:
        policy = await self._repository.find_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(policy_id)
        return policy


class ActivatePolicyUseCase:
    """정책 활성화 (DRAFT → ACTIVE)"""

    def __init__(self, repository: IPolicyRepository) -> None:
        self._repository = repository

    async def execute(self, policy_id: PolicyId) -> GovernancePolicy:
        policy = await self._load(policy_id)
        policy.activate()
        policy.updated_at = datetime.now()
        await self._repository.save(policy)

        logger.info("policy_activated", extra={"policy_id": policy_id})
        return policy

    async def _load(self, policy_id: PolicyId) -> GovernancePolicy:
        policy = await self._repository.find_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(policy_id)
        return policy


class ArchivePolicyUseCase:
    """정책 아카이브 (ACTIVE → ARCHIVED)"""

    def __init__(self, repository: IPolicyRepository) -> None:
        self._repository = repository

    async def execute(self, policy_id: PolicyId) -> GovernancePolicy:
        policy = await self._load(policy_id)
        policy.archive()
        policy.updated_at = datetime.now()
        await self._repository.save(policy)

        logger.info("policy_archived", extra={"policy_id": policy_id})
        return policy

    async def _load(self, policy_id: PolicyId) -> GovernancePolicy:
        policy = await self._repository.find_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(policy_id)
        return policy
