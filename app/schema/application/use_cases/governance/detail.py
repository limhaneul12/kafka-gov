"""스키마 상세 조회 유스케이스"""

from __future__ import annotations

import logging
from datetime import datetime

from app.infra.kafka.connection_manager import IConnectionManager
from app.infra.kafka.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainSchemaSpec,
    DomainSchemaType,
    SubjectDetail,
)
from app.schema.domain.policies.dynamic_engine import DynamicSchemaPolicyEngine
from app.schema.domain.repositories.interfaces import (
    ISchemaMetadataRepository,
    ISchemaPolicyRepository,
)


class GetSubjectDetailUseCase:
    """스키마 상세 정보 조회 (최신 스키마 포함)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        policy_repository: ISchemaPolicyRepository | None = None,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.policy_repository = policy_repository
        self.logger = logging.getLogger(__name__)

    async def execute(self, registry_id: str, subject: str) -> SubjectDetail:
        """스키마 상세 정보 조회 (최신 스키마 포함)"""
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

        describe_res = await registry_repository.describe_subjects([subject])
        if not describe_res.get(subject):
            raise ValueError(f"Subject '{subject}' not found in registry '{registry_id}'")

        info = describe_res[subject]
        artifact = await self.metadata_repository.get_latest_artifact(subject)
        metadata = await self.metadata_repository.get_schema_metadata(subject)

        # Policy 검증 수행
        env_str = subject.split(".")[0] if "." in subject else "dev"
        active_policies = []
        if self.policy_repository:
            # 해당 환경 및 전체 정책 로드
            active_policies = await self.policy_repository.list_active_policies(env=env_str)

        policy_engine = DynamicSchemaPolicyEngine(active_policies)

        violations = []
        policy_score = 1.0
        if info.schema:
            artifact_compatibility = (
                artifact.compatibility_mode
                if artifact and artifact.compatibility_mode
                else DomainCompatibilityMode.NONE
            )
            spec_mock = DomainSchemaSpec(
                subject=subject,
                schema=info.schema,
                schema_type=DomainSchemaType(info.schema_type)
                if info.schema_type
                else DomainSchemaType.AVRO,
                compatibility=(
                    artifact_compatibility
                    if isinstance(artifact_compatibility, DomainCompatibilityMode)
                    else DomainCompatibilityMode(artifact_compatibility)
                ),
            )
            violations = policy_engine.evaluate(spec_mock, env=env_str)
            policy_score = max(0.5, 1.0 - (len(violations) * 0.1))

        return SubjectDetail(
            subject=subject,
            version=info.version or 0,
            schema_id=info.schema_id or 0,
            schema_str=info.schema or "",
            schema_type=info.schema_type or "",
            compatibility_mode=(
                artifact.compatibility_mode.value
                if hasattr(artifact.compatibility_mode, "value")
                else artifact.compatibility_mode
            )
            if artifact and artifact.compatibility_mode
            else "NONE",
            owner=(metadata.get("owner") if metadata else None)
            or (artifact.owner if artifact else None),
            doc=metadata.get("doc") if metadata else None,
            tags=metadata.get("tags") if metadata else [],
            description=metadata.get("description") if metadata else None,
            updated_at=datetime.now().isoformat(),
            violations=[
                {"rule": v.rule, "message": v.message, "severity": v.severity} for v in violations
            ],
            policy_score=policy_score,
        )
