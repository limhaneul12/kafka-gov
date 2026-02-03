"""거버넌스 통계 유스케이스"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.cluster.domain.services import IConnectionManager
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSubjectStat,
    GovernanceDashboardStats,
    GovernanceScore,
)
from app.schema.domain.policies.dynamic_engine import DynamicSchemaPolicyEngine
from app.schema.domain.repositories.interfaces import (
    ISchemaMetadataRepository,
    ISchemaPolicyRepository,
)
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter


class GetGovernanceStatsUseCase:
    """거버넌스 대시보드 통계 조회"""

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

    async def execute(self, registry_id: str) -> GovernanceDashboardStats:
        """거버넌스 대시보드 통계 조회"""
        try:
            registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
            registry_repository = ConfluentSchemaRegistryAdapter(registry_client)
        except Exception:
            return GovernanceDashboardStats(
                total_subjects=0,
                total_versions=0,
                orphan_subjects=0,
                scores=GovernanceScore(
                    compatibility_pass_rate=0.0,
                    documentation_coverage=0.0,
                    average_lint_score=0.0,
                    total_score=0.0,
                ),
                top_subjects=[],
            )

        # 1. 모든 Subject 조회
        all_subjects = await registry_repository.list_all_subjects()
        total_subjects = len(all_subjects)

        # 2. 메타데이터 조회 (DB)
        artifact_list = await self.metadata_repository.list_artifacts()

        # Subject 별 메타데이터 매핑
        meta_map = {
            artifact.subject: artifact
            for artifact in artifact_list
            if artifact.subject in all_subjects
        }

        # 활성화된 정책 로드 (거버넌스 점수 계산용)
        active_policies = []
        if self.policy_repository:
            active_policies = await self.policy_repository.list_active_policies(env="total")

        policy_engine = DynamicSchemaPolicyEngine(active_policies)

        # 3. 통계 계산
        orphan_count = 0
        doc_count = 0
        total_policy_score = 0.0

        # 상위 Subject 목록
        top_subjects = []

        # 샘플링 검사 (최대 50개) - 성능 고려
        target_subjects = all_subjects[:50]

        # 병렬로 스키마 조회
        tasks = [registry_repository.describe_subjects([sub]) for sub in target_subjects]
        schema_results = await asyncio.gather(*tasks, return_exceptions=True)

        idx = 0
        for subject in target_subjects:
            result = schema_results[idx]
            idx += 1

            if isinstance(result, Exception):
                continue

            if not result.get(subject):
                continue

            schema_info = result[subject]
            meta = meta_map.get(subject)

            # Owner 체크
            owner = meta.owner if meta else None
            if not owner:
                orphan_count += 1

            # Policy 검증 (Lint + Guardrails)
            violations = []
            policy_score = 1.0
            if schema_info.schema:
                # Mock spec for evaluation
                spec_mock = DomainSchemaSpec(
                    subject=subject,
                    schema=schema_info.schema,
                    schema_type=DomainSchemaType(schema_info.schema_type)
                    if schema_info.schema_type
                    else DomainSchemaType.AVRO,
                    compatibility=DomainCompatibilityMode(
                        (
                            meta.compatibility_mode.value
                            if hasattr(meta.compatibility_mode, "value")
                            else meta.compatibility_mode
                        )
                        if meta and meta.compatibility_mode
                        else "NONE"
                    ),
                )
                violations = policy_engine.evaluate(spec_mock, env="total")

                # 감점 방식 (간단히 위반 개수당 0.1 차감, 0.5 하한)
                policy_score = max(0.5, 1.0 - (len(violations) * 0.1))
                total_policy_score += policy_score

            # Doc 체크
            has_doc = bool(meta)
            if has_doc:
                doc_count += 1

            top_subjects.append(
                DomainSubjectStat(
                    subject=subject,
                    owner=owner,
                    version_count=schema_info.version if schema_info.version else 0,
                    last_updated=datetime.now().isoformat(),
                    compatibility_mode=(
                        meta.compatibility_mode.value
                        if hasattr(meta.compatibility_mode, "value")
                        else meta.compatibility_mode
                    )
                    if meta and meta.compatibility_mode
                    else None,
                    lint_score=policy_score,
                    has_doc=has_doc,
                    violations=[
                        {"rule": v.rule, "message": v.message, "severity": v.severity}
                        for v in violations
                    ],
                )
            )

        # 점수 집계
        avg_policy = total_policy_score / len(target_subjects) if target_subjects else 0.0
        doc_rate = doc_count / len(target_subjects) if target_subjects else 0.0
        compat_rate = 0.95

        total_score = (avg_policy + doc_rate + compat_rate) / 3

        return GovernanceDashboardStats(
            total_subjects=total_subjects,
            total_versions=sum(s.version_count for s in top_subjects),
            orphan_subjects=orphan_count + (len(all_subjects) - len(target_subjects)),
            scores=GovernanceScore(
                compatibility_pass_rate=compat_rate,
                documentation_coverage=doc_rate,
                average_lint_score=avg_policy,
                total_score=total_score,
            ),
            top_subjects=top_subjects,
        )
