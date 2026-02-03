"""Schema Policy Management Use Cases"""

from __future__ import annotations

import uuid
from datetime import datetime

from ....domain.models.policy_management import (
    DomainSchemaPolicy,
    SchemaPolicyStatus,
    SchemaPolicyType,
)
from ....domain.repositories.interfaces import ISchemaPolicyRepository


class SchemaPolicyUseCase:
    """스키마 정책 관리용 유스케이스 통합 서비스"""

    def __init__(self, policy_repository: ISchemaPolicyRepository) -> None:
        self.policy_repository = policy_repository

    async def create_policy(
        self,
        name: str,
        description: str,
        policy_type: SchemaPolicyType,
        content: dict,
        target_environment: str,
        created_by: str,
    ) -> DomainSchemaPolicy:
        """새로운 스키마 정책 생성 (v1 시작)"""
        policy_id = str(uuid.uuid4())

        policy = DomainSchemaPolicy(
            policy_id=policy_id,
            policy_type=policy_type,
            name=name,
            description=description,
            version=1,
            status=SchemaPolicyStatus.DRAFT,
            content=content,
            target_environment=target_environment,
            created_by=created_by,
            created_at=datetime.now().isoformat(),
        )

        await self.policy_repository.save(policy)
        return policy

    async def update_policy(
        self,
        policy_id: str,
        name: str,
        description: str,
        content: dict,
        target_environment: str,
        created_by: str,
    ) -> DomainSchemaPolicy:
        """기존 정책의 새로운 버전 생성"""
        # 1. 최신 버전 조회
        latest = await self.policy_repository.get_by_id(policy_id)
        if not latest:
            raise ValueError(f"Policy {policy_id} not found")

        # 2. 새로운 버전 생성
        new_version = DomainSchemaPolicy(
            policy_id=policy_id,
            policy_type=latest.policy_type,
            name=name,
            description=description,
            version=latest.version + 1,
            status=SchemaPolicyStatus.DRAFT,
            content=content,
            target_environment=target_environment,
            created_by=created_by,
            created_at=datetime.now().isoformat(),
        )

        await self.policy_repository.save(new_version)
        return new_version

    async def list_policies(
        self, env: str | None = None, policy_type: SchemaPolicyType | None = None
    ) -> list[DomainSchemaPolicy]:
        """정책 목록 조회 (최신 버전 기준)"""
        # 실제 구현에서는 Repository에서 Group By policy_id 하여 최신 버전만 가져오도록 최적화 필요
        return await self.policy_repository.list_all_policies(env, policy_type)

    async def get_policy_detail(
        self, policy_id: str, version: int | None = None
    ) -> DomainSchemaPolicy | None:
        """정책 상세 조회"""
        return await self.policy_repository.get_by_id(policy_id, version)

    async def get_history(self, policy_id: str) -> list[DomainSchemaPolicy]:
        """정책 변경 이력 조회"""
        return await self.policy_repository.get_history(policy_id)

    async def activate_policy(self, policy_id: str, version: int) -> None:
        """특정 버전의 정책을 활성화 (같은 ID의 다른 ACTIVE 버전은 ARCHIVED로 처리될 수 있음)"""
        # 1. 기존 ACTIVE 버전이 있다면 처리 (옵션: 단순화를 위해 여기서 skip 가능하지만 실무 패턴상 필요)
        active_policies = await self.policy_repository.list_active_policies()
        for p in active_policies:
            if p.policy_id == policy_id and p.version != version:
                await self.policy_repository.update_status(
                    p.policy_id, p.version, SchemaPolicyStatus.ARCHIVED
                )

        # 2. 지정된 버전을 ACTIVE로 변경
        await self.policy_repository.update_status(policy_id, version, SchemaPolicyStatus.ACTIVE)

    async def delete_policy(self, policy_id: str) -> None:
        """분기된 정책의 전 세대 버전을 포함하여 모두 삭제"""
        await self.policy_repository.delete_policy(policy_id)

    async def delete_version(self, policy_id: str, version: int) -> None:
        """정책의 특정 버전만 삭제"""
        await self.policy_repository.delete_version(policy_id, version)
