"""스키마 변경 계획 수립 유스케이스"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime

from app.cluster.domain.services import IConnectionManager
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSchemaBatch,
    DomainSchemaPlan,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSubjectStrategy,
)
from app.schema.domain.repositories.interfaces import (
    ISchemaMetadataRepository,
)
from app.schema.domain.services import SchemaPlannerService
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter


class PlanSchemaChangeUseCase:
    """단일 스키마 변경 계획 수립 (Edit 용)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        registry_id: str,
        subject: str,
        new_schema: str,
        compatibility: str,
        actor: str,
        reason: str | None = None,
        actor_context: dict[str, str] | None = None,
    ) -> DomainSchemaPlan:
        """단일 스키마 변경 계획 수립 (Edit 용)"""
        # 1. 환경 추론 (subject naming 기준)
        env_str = subject.split(".")[0] if "." in subject else "dev"
        try:
            env = DomainEnvironment(env_str)
        except ValueError:
            env = DomainEnvironment.DEV

        # 2. Batch 생성 (단일 Spec)
        change_id = f"edit_{subject}_{int(datetime.now().timestamp())}"

        # Spec에 schema_type이 필수라면 현재 정보에서 가져와야 함
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)
        describe_res = await registry_repository.describe_subjects([subject])
        current_info = describe_res.get(subject)

        # fix spec with correct type
        schema_type_str = current_info.schema_type if current_info else "AVRO"

        # Ensure we use Enum members
        try:
            domain_schema_type = DomainSchemaType(schema_type_str)
        except ValueError:
            domain_schema_type = DomainSchemaType.AVRO

        try:
            domain_compat = DomainCompatibilityMode(compatibility)
        except ValueError:
            domain_compat = DomainCompatibilityMode.NONE

        spec = DomainSchemaSpec(
            subject=subject,
            schema_type=domain_schema_type,
            compatibility=domain_compat,
            schema=new_schema,
            reason=reason,
        )

        batch = DomainSchemaBatch(
            change_id=change_id,
            env=env,
            subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
            specs=(spec,),
        )

        # 3. 계획 수립
        planner_service = SchemaPlannerService(registry_repository)
        plan = await planner_service.create_plan(batch)
        plan = replace(plan, actor_context=actor_context)

        # 4. 계획 저장
        await self.metadata_repository.save_plan(plan, actor)

        return plan
