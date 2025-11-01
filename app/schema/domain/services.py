"""Schema Domain 서비스"""

from __future__ import annotations

from app.shared.domain.subject_utils import SubjectStrategy, extract_topics_from_subject

from .models import (
    DomainPlanAction,
    DomainSchemaBatch,
    DomainSchemaDeleteImpact,
    DomainSchemaDiff,
    DomainSchemaImpactRecord,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaSpec,
    DomainSubjectStrategy,
    SchemaVersionInfo,
    SubjectName,
)
from .policy_engine import SchemaPolicyEngine
from .repositories.interfaces import ISchemaRegistryRepository

# 스키마 버전 임계값
HIGH_VERSION_COUNT_THRESHOLD = 10  # 버전이 이 개수를 초과하면 경고


class SchemaImpactAnalyzer:
    """스키마 영향도 분석 서비스"""

    def __init__(self, registry_repository: ISchemaRegistryRepository) -> None:
        self.registry_repository = registry_repository

    async def analyze_impact(
        self, subject: SubjectName, strategy: DomainSubjectStrategy
    ) -> DomainSchemaImpactRecord:
        """스키마 변경이 미치는 영향도 분석

        Note: 컨슈머 정보는 Schema Registry에서 알 수 없으므로 빈 튜플 반환
        실제 컨슈머 관리는 애플리케이션 레벨에서 수행해야 함
        """
        topics = self._extract_topics_from_subject(subject, strategy)

        return DomainSchemaImpactRecord(
            subject=subject,
            topics=tuple(topics),
            consumers=(),  # 컨슈머 정보는 제공하지 않음
        )

    def _extract_topics_from_subject(
        self, subject: SubjectName, strategy: DomainSubjectStrategy
    ) -> list[str]:
        """Subject naming strategy에 따라 토픽명 추출"""
        # DomainSubjectStrategy를 SubjectStrategy로 매핑
        strategy_map = {
            DomainSubjectStrategy.TOPIC_NAME: SubjectStrategy.TOPIC_NAME,
            DomainSubjectStrategy.RECORD_NAME: SubjectStrategy.RECORD_NAME,
            DomainSubjectStrategy.TOPIC_RECORD_NAME: SubjectStrategy.TOPIC_RECORD_NAME,
        }
        mapped_strategy = strategy_map.get(strategy, SubjectStrategy.TOPIC_NAME)
        return extract_topics_from_subject(subject, mapped_strategy)


class SchemaDeleteAnalyzer:
    """스키마 삭제 영향도 분석 서비스"""

    def __init__(self, registry_repository: ISchemaRegistryRepository) -> None:
        self.registry_repository = registry_repository
        self.impact_analyzer = SchemaImpactAnalyzer(registry_repository)

    async def analyze_delete_impact(
        self, subject: SubjectName, strategy: DomainSubjectStrategy
    ) -> DomainSchemaDeleteImpact:
        """스키마 삭제 전 영향도 분석

        Args:
            subject: 삭제할 Subject 이름
            strategy: Subject 전략

        Returns:
            삭제 영향도 분석 결과
        """
        # 1. 현재 스키마 정보 조회
        current_subjects = await self.registry_repository.describe_subjects([subject])
        current_info = current_subjects.get(subject)

        if not current_info:
            # 스키마가 존재하지 않음
            return DomainSchemaDeleteImpact(
                subject=subject,
                current_version=None,
                total_versions=0,
                affected_topics=(),
                warnings=("스키마가 존재하지 않습니다.",),
                safe_to_delete=True,
            )

        # 2. 영향받는 토픽 추출
        impact = await self.impact_analyzer.analyze_impact(subject, strategy)
        affected_topics = impact.topics

        # 3. 경고 메시지 생성
        warnings = self._generate_delete_warnings(
            subject=subject,
            current_version=current_info.version,
            affected_topics=affected_topics,
        )

        # 4. 안전 삭제 여부 판단
        safe_to_delete = len(warnings) == 0

        return DomainSchemaDeleteImpact(
            subject=subject,
            current_version=current_info.version,
            total_versions=current_info.version if current_info.version else 0,
            affected_topics=affected_topics,
            warnings=tuple(warnings),
            safe_to_delete=safe_to_delete,
        )

    def _generate_delete_warnings(
        self,
        subject: SubjectName,
        current_version: int | None,
        affected_topics: tuple[str, ...],
    ) -> list[str]:
        """삭제 경고 메시지 생성"""
        warnings = []

        # 경고 1: 영향받는 토픽이 있는 경우
        if affected_topics:
            topic_list = ", ".join(affected_topics)
            warnings.append(
                f"다음 토픽이 이 스키마를 사용 중일 수 있습니다: {topic_list}. "
                f"삭제 시 해당 토픽의 프로듀서/컨슈머에 영향을 줄 수 있습니다."
            )

        # 경고 2: 버전이 많은 경우
        if current_version and current_version > HIGH_VERSION_COUNT_THRESHOLD:
            warnings.append(
                f"이 스키마는 {current_version}개의 버전이 있습니다. "
                f"삭제 시 모든 버전이 제거됩니다."
            )

        # 경고 3: 프로덕션 환경 경고 (subject naming에서 추론)
        if "prod" in subject.lower():
            warnings.append("프로덕션 환경의 스키마입니다. 삭제 전 반드시 영향도를 확인하세요.")

        return warnings


class SchemaPlannerService:
    """스키마 배치 계획 생성 서비스"""

    def __init__(
        self, registry_repository: ISchemaRegistryRepository, policy_engine: SchemaPolicyEngine
    ) -> None:
        self.registry_repository = registry_repository
        self.policy_engine = policy_engine
        self.impact_analyzer = SchemaImpactAnalyzer(registry_repository)

    async def create_plan(self, batch: DomainSchemaBatch) -> DomainSchemaPlan:
        """배치 계획 및 정책 검증 실행"""
        violations = self.policy_engine.validate_batch(batch.specs)

        current_subjects = await self.registry_repository.describe_subjects(
            spec.subject for spec in batch.specs
        )

        compatibility_reports = []
        plan_items: list[DomainSchemaPlanItem] = []
        impacts: list[DomainSchemaImpactRecord] = []

        for spec in batch.specs:
            current_info = current_subjects.get(spec.subject)

            # 계획 아이템 생성
            action = DomainPlanAction.UPDATE if current_info else DomainPlanAction.REGISTER
            current_version = current_info.version if current_info else None
            target_version = (
                (current_info.version + 1)
                if (current_info and current_info.version is not None)
                else 1
            )

            # 스키마 diff 계산
            diff = self._calculate_schema_diff(current_info, spec)

            plan_item = DomainSchemaPlanItem(
                subject=spec.subject,
                action=action,
                current_version=current_version,
                target_version=target_version,
                diff=diff,
            )
            plan_items.append(plan_item)

            # 호환성 검증
            report = await self.registry_repository.check_compatibility(spec)
            compatibility_reports.append(report)

            # 영향도 분석
            impact = await self.impact_analyzer.analyze_impact(spec.subject, batch.subject_strategy)
            impacts.append(impact)

        return DomainSchemaPlan(
            change_id=batch.change_id,
            env=batch.env,
            items=tuple(plan_items),
            violations=tuple(violations),
            compatibility_reports=tuple(compatibility_reports),
            impacts=tuple(impacts),
        )

    def _calculate_schema_diff(
        self,
        current_info: SchemaVersionInfo | None,
        spec: DomainSchemaSpec,
    ) -> DomainSchemaDiff:
        """스키마 변경 사항 계산

        Args:
            current_info: 현재 등록된 스키마 정보 (없으면 신규 등록)
            spec: 등록하려는 스키마 명세

        Returns:
            DomainSchemaDiff: 변경 사항을 담은 Domain Model
        """
        if not current_info:
            # 신규 등록
            return DomainSchemaDiff(
                type="new_registration",
                changes=("New schema registration",),
                current_version=None,
                target_compatibility=spec.compatibility.value,
                schema_type=spec.schema_type.value,
            )

        # 기존 스키마 업데이트
        changes: tuple[str, ...] = ("Schema definition updated",)  # 기본값

        # 스키마 타입 변경 확인 (일반적으로 변경 불가하지만 체크)
        if (
            current_info.schema_type is not None
            and current_info.schema_type != spec.schema_type.value
        ):
            changes = (f"Schema type: {current_info.schema_type} → {spec.schema_type.value}",)

        # 메타데이터 변경 확인 (우선순위 높음)
        if spec.metadata is not None:
            changes = (f"Metadata updated (owner: {spec.metadata.owner})",)

        return DomainSchemaDiff(
            type="update",
            changes=changes,
            current_version=current_info.version,
            target_compatibility=spec.compatibility.value,
            schema_type=current_info.schema_type,
        )
