"""Policy CRUD UseCases - 정책 생성/조회/수정/삭제/롤백

Application Layer: 비즈니스 로직만 포함
DTOs는 Interface Layer에 위치 (app.topic.interface.schemas.policy)
"""

from __future__ import annotations

import logging

from app.topic.domain.policies.management import PolicyStatus, PolicyType, StoredPolicy
from app.topic.domain.repositories import IPolicyRepository

logger = logging.getLogger(__name__)


class CreatePolicyUseCase:
    """정책 생성 UseCase"""

    def __init__(self, policy_repository: IPolicyRepository) -> None:
        self.policy_repo = policy_repository

    async def execute(
        self,
        policy_type: PolicyType,
        name: str,
        description: str,
        content: dict,
        created_by: str,
    ) -> tuple[StoredPolicy, str]:
        """정책 생성 (version=1, status=DRAFT)"""
        logger.info(f"Creating policy: type={policy_type.value}, name={name}, by={created_by}")

        policy = await self.policy_repo.create_policy(
            policy_type=policy_type,
            name=name,
            description=description,
            content=content,
            created_by=created_by,
        )

        logger.info(f"Policy created: {policy.policy_id} v{policy.version}")
        message = (
            f"Policy '{policy.name}' created successfully "
            f"(version {policy.version}, status {policy.status.value})"
        )
        return policy, message


class GetPolicyUseCase:
    """정책 조회 UseCase"""

    def __init__(self, policy_repository: IPolicyRepository) -> None:
        self.policy_repo = policy_repository

    async def execute(self, policy_id: str, version: int | None = None) -> tuple[StoredPolicy, str]:
        """정책 조회 (version 지정 가능)"""
        policy = await self.policy_repo.get_policy(policy_id, version)

        if not policy:
            raise ValueError(f"Policy not found: {policy_id} (version={version})")

        message = f"Policy retrieved: {policy.name} v{policy.version}"
        return policy, message


class GetActivePolicyUseCase:
    """활성 정책 조회 UseCase"""

    def __init__(self, policy_repository: IPolicyRepository) -> None:
        self.policy_repo = policy_repository

    async def execute(self, policy_id: str) -> tuple[StoredPolicy, str]:
        """활성 정책 조회 (status=ACTIVE)"""
        policy = await self.policy_repo.get_active_policy(policy_id)

        if not policy:
            raise ValueError(f"Active policy not found: {policy_id}")

        message = f"Active policy retrieved: {policy.name} v{policy.version}"
        return policy, message


class ListPoliciesUseCase:
    """정책 목록 조회 UseCase"""

    def __init__(self, policy_repository: IPolicyRepository) -> None:
        self.policy_repo = policy_repository

    async def execute(
        self,
        policy_type: PolicyType | None = None,
        status: PolicyStatus | None = None,
    ) -> tuple[list[StoredPolicy], int]:
        """정책 목록 조회 (최신 버전만)"""
        policies = await self.policy_repo.list_policies(policy_type, status)
        return policies, len(policies)


class ListPolicyVersionsUseCase:
    """정책 버전 히스토리 조회 UseCase"""

    def __init__(self, policy_repository: IPolicyRepository) -> None:
        self.policy_repo = policy_repository

    async def execute(self, policy_id: str) -> tuple[str, list[StoredPolicy], int]:
        """정책의 모든 버전 조회"""
        versions = await self.policy_repo.list_policy_versions(policy_id)

        if not versions:
            raise ValueError(f"No versions found for policy: {policy_id}")

        return policy_id, versions, len(versions)


class UpdatePolicyUseCase:
    """정책 수정 UseCase (새 버전 생성)"""

    def __init__(self, policy_repository: IPolicyRepository) -> None:
        self.policy_repo = policy_repository

    async def execute(
        self,
        policy_id: str,
        name: str | None = None,
        description: str | None = None,
        content: dict | None = None,
    ) -> tuple[StoredPolicy, str]:
        """정책 수정 (새 버전 DRAFT 생성)"""
        logger.info(f"Updating policy: {policy_id}")

        policy = await self.policy_repo.update_policy(
            policy_id=policy_id,
            name=name,
            description=description,
            content=content,
        )

        logger.info(f"Policy updated: {policy.policy_id} v{policy.version} (DRAFT)")
        message = (
            f"Policy '{policy.name}' updated to version {policy.version} (DRAFT). "
            f"Activate to apply changes."
        )
        return policy, message


class ActivatePolicyUseCase:
    """정책 활성화 UseCase"""

    def __init__(self, policy_repository: IPolicyRepository) -> None:
        self.policy_repo = policy_repository

    async def execute(self, policy_id: str, version: int | None = None) -> tuple[StoredPolicy, str]:
        """정책 활성화 (DRAFT → ACTIVE, 기존 ACTIVE → ARCHIVED)"""
        logger.info(f"Activating policy: {policy_id} (version={version})")

        policy = await self.policy_repo.activate_policy(policy_id=policy_id, version=version)

        logger.info(f"Policy activated: {policy.policy_id} v{policy.version}")
        message = f"Policy '{policy.name}' version {policy.version} activated successfully"
        return policy, message


class ArchivePolicyUseCase:
    """정책 보관 UseCase"""

    def __init__(self, policy_repository: IPolicyRepository) -> None:
        self.policy_repo = policy_repository

    async def execute(self, policy_id: str) -> tuple[StoredPolicy, str]:
        """정책 보관 (ACTIVE → ARCHIVED)"""
        logger.info(f"Archiving policy: {policy_id}")

        policy = await self.policy_repo.archive_policy(policy_id)

        logger.info(f"Policy archived: {policy.policy_id} v{policy.version}")
        message = f"Policy '{policy.name}' version {policy.version} archived"
        return policy, message


class DeletePolicyUseCase:
    """정책 삭제 UseCase (DRAFT만 가능)"""

    def __init__(self, policy_repository: IPolicyRepository) -> None:
        self.policy_repo = policy_repository

    async def execute(self, policy_id: str, version: int | None = None) -> str:
        """정책 삭제 (DRAFT만)"""
        logger.info(f"Deleting policy: {policy_id} (version={version})")

        await self.policy_repo.delete_policy(policy_id, version)

        logger.info(f"Policy deleted: {policy_id}")
        return f"Policy {policy_id} (version={version or 'all drafts'}) deleted successfully"


class RollbackPolicyUseCase:
    """정책 롤백 UseCase"""

    def __init__(self, policy_repository: IPolicyRepository) -> None:
        self.policy_repo = policy_repository

    async def execute(self, policy_id: str, target_version: int) -> tuple[StoredPolicy, str]:
        """이전 버전으로 롤백 (새 DRAFT 버전 생성)"""
        logger.info(f"Rolling back policy: {policy_id} to version {target_version}")

        policy = await self.policy_repo.rollback_to_version(
            policy_id=policy_id, target_version=target_version
        )

        logger.info(
            f"Policy rolled back: {policy.policy_id} v{target_version} → v{policy.version} (DRAFT)"
        )
        message = (
            f"Policy '{policy.name}' rolled back to version {target_version}. "
            f"New version {policy.version} created (DRAFT). Activate to apply."
        )
        return policy, message
