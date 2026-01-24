"""Schema Governance Use Cases"""

from __future__ import annotations

import asyncio
from datetime import datetime

from app.cluster.domain.services import IConnectionManager
from app.consumer.application.use_cases.query import GetTopicConsumersUseCase
from app.schema.application.services.schema_lint import SchemaLintService
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSchemaBatch,
    DomainSchemaPlan,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSubjectStat,
    DomainSubjectStrategy,
    GovernanceDashboardStats,
    GovernanceScore,
    GraphLink,
    GraphNode,
    ImpactGraph,
    SchemaHistoryItem,
    SubjectDetail,
    SubjectHistory,
    SubjectName,
)
from app.schema.domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
)
from app.schema.domain.services import SchemaPlannerService
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.shared.domain.subject_utils import SubjectStrategy, extract_topics_from_subject


class GovernanceUseCase:
    """스키마 거버넌스 유스케이스 (대시보드, 타임머신, 영향도)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
        lint_service: SchemaLintService,
        get_topic_consumers_use_case: GetTopicConsumersUseCase,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.lint_service = lint_service
        self.get_topic_consumers_use_case = get_topic_consumers_use_case

    async def plan_change(
        self,
        registry_id: str,
        subject: str,
        new_schema: str,
        compatibility: str,
        actor: str,
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

        # 4. 계획 저장
        await self.metadata_repository.save_plan(plan, actor)

        return plan

    async def rollback(
        self,
        registry_id: str,
        subject: str,
        version: int,
        actor: str,
    ) -> DomainSchemaPlan:
        """특정 버전으로 롤백 계획 수립"""
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

        # 1. 과거 버전 스키마 조회
        old_version_info = await registry_repository.get_schema_by_version(subject, version)
        if not old_version_info:
            raise ValueError(f"Version {version} for subject {subject} not found")

        # 2. 현재 메타데이터에서 호환성 모드 조회
        artifact = await self.metadata_repository.get_latest_artifact(subject)
        compatibility = "BACKWARD"
        if artifact and artifact.compatibility_mode:
            compatibility = (
                artifact.compatibility_mode
                if isinstance(artifact.compatibility_mode, str)
                else artifact.compatibility_mode.value
            )

        # 3. plan_change 호출하여 계획 수립 (롤백도 결국 새로운 버전 등록 계획임)
        plan = await self.plan_change(
            registry_id=registry_id,
            subject=subject,
            new_schema=old_version_info.schema or "",
            compatibility=compatibility,
            actor=actor,
        )

        return plan

    async def get_dashboard_stats(self, registry_id: str) -> GovernanceDashboardStats:
        """거버넌스 대시보드 통계 조회"""
        # ConnectionManager로 Registry Client 획득
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

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

        # 3. 통계 계산
        orphan_count = 0
        doc_count = 0
        total_lint_score = 0.0

        # 상위 Subject 목록
        top_subjects = []

        # 샘플링 검사 (최대 50개) - 성능 고려
        target_subjects = all_subjects[:50]

        # 병렬로 스키마 조회 및 린트 수행
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

            # Lint 수행
            lint_score = 0.0
            if schema_info.schema:
                report = self.lint_service.lint_avro_schema(schema_info.schema)
                lint_score = report.risk_score
                lint_score = 1.0 - lint_score
                total_lint_score += lint_score

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
                    lint_score=lint_score,
                    has_doc=has_doc,
                )
            )

        # 점수 집계
        avg_lint = total_lint_score / len(target_subjects) if target_subjects else 0.0
        doc_rate = doc_count / len(target_subjects) if target_subjects else 0.0
        compat_rate = 0.95

        total_score = (avg_lint + doc_rate + compat_rate) / 3

        return GovernanceDashboardStats(
            total_subjects=total_subjects,
            total_versions=sum(s.version_count for s in top_subjects),
            orphan_subjects=orphan_count + (len(all_subjects) - len(target_subjects)),
            scores=GovernanceScore(
                compatibility_pass_rate=compat_rate,
                documentation_coverage=doc_rate,
                average_lint_score=avg_lint,
                total_score=total_score,
            ),
            top_subjects=top_subjects,
        )

    async def get_subject_detail(self, registry_id: str, subject: str) -> SubjectDetail:
        """스키마 상세 정보 조회 (최신 스키마 포함)"""
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

        describe_res = await registry_repository.describe_subjects([subject])
        if not describe_res.get(subject):
            raise ValueError(f"Subject '{subject}' not found in registry '{registry_id}'")

        info = describe_res[subject]
        artifact = await self.metadata_repository.get_latest_artifact(subject)

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
            owner=artifact.owner if artifact else None,
            updated_at=datetime.now().isoformat(),
        )

    async def get_history(self, registry_id: str, subject: SubjectName) -> SubjectHistory:
        """스키마 이력 조회 (타임머신)"""
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

        versions = await registry_repository.get_schema_versions(subject)

        # 각 버전별 상세 조회 (병렬)
        tasks = [registry_repository.get_schema_by_version(subject, v) for v in versions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        history_items = [
            SchemaHistoryItem(
                version=result.version,
                schema_id=result.schema_id,
                created_at=None,
                diff_type="UPDATE" if i > 0 else "CREATE",
                author="system",
                commit_message=f"Schema update v{result.version}",
            )
            for i, result in enumerate(results)
            if not isinstance(result, Exception)
        ]

        return SubjectHistory(
            subject=subject, history=sorted(history_items, key=lambda x: x.version, reverse=True)
        )

    async def get_impact_graph(self, registry_id: str, subject: SubjectName) -> ImpactGraph:
        """영향도 그래프 조회"""
        nodes: list[GraphNode] = []
        links: list[GraphLink] = []

        # 1. 중심 노드 (Schema)
        nodes.append(
            GraphNode(id=subject, type="SCHEMA", label=subject, metadata={"layer": "schema"})
        )

        # 2. 토픽 추출 (Topic Strategy 가정)
        topics = extract_topics_from_subject(subject, SubjectStrategy.TOPIC_NAME)

        # 클러스터 ID 조회
        clusters = await self.connection_manager.kafka_cluster_repo.list_all()
        active_clusters = [c for c in clusters if c.is_active]
        cluster_id = active_clusters[0].cluster_id if active_clusters else "default"

        for topic in topics:
            nodes.append(
                GraphNode(id=topic, type="TOPIC", label=topic, metadata={"layer": "topic"})
            )
            links.append(GraphLink(source=subject, target=topic, relation="WRITES_TO"))

            # 3. 실제 컨슈머 조회
            mapping = await self.get_topic_consumers_use_case.execute(cluster_id, topic)

            for group in mapping.consumer_groups:
                group_id = group["group_id"]
                state = group.get("state", "unknown")
                member_count = group.get("member_count", 0)

                nodes.append(
                    GraphNode(
                        id=group_id,
                        type="CONSUMER",
                        label=group_id,
                        metadata={"layer": "app", "state": state, "members": member_count},
                    )
                )
                links.append(GraphLink(source=topic, target=group_id, relation="READS_FROM"))

        return ImpactGraph(subject=subject, nodes=nodes, links=links)
