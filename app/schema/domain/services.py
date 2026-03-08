"""Schema Domain 서비스"""

from __future__ import annotations

import json
from typing import Any

from app.shared.domain.subject_utils import SubjectStrategy, extract_topics_from_subject

from .models import (
    DomainPlanAction,
    DomainPolicyViolation,
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
from .policies.compatibility import CompatibilityGuardrail
from .policies.dynamic_engine import DynamicSchemaPolicyEngine
from .repositories.interfaces import ISchemaPolicyRepository, ISchemaRegistryRepository

# 스키마 버전 임계값
HIGH_VERSION_COUNT_THRESHOLD = 10  # 버전이 이 개수를 초과하면 경고


class SchemaImpactAnalyzer:
    """스키마 영향도 분석 서비스"""

    def __init__(self, registry_repository: ISchemaRegistryRepository) -> None:
        self.registry_repository = registry_repository

    async def analyze_impact(
        self, subject: SubjectName, strategy: DomainSubjectStrategy
    ) -> DomainSchemaImpactRecord:
        """스키마 변경이 미치는 영향도 분석"""
        try:
            topics = self._extract_topics_from_subject(subject, strategy)
            return DomainSchemaImpactRecord(
                subject=subject,
                topics=tuple(topics),
                consumers=(),  # 컨슈머 정보는 추후 구현
                status="success",
            )
        except Exception as e:
            return DomainSchemaImpactRecord(
                subject=subject,
                topics=(),
                consumers=(),
                status="failure",
                error_message=str(e),
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
        self,
        registry_repository: ISchemaRegistryRepository,
        policy_repository: ISchemaPolicyRepository | None = None,
    ) -> None:
        self.registry_repository = registry_repository
        self.policy_repository = policy_repository
        self.impact_analyzer = SchemaImpactAnalyzer(registry_repository)
        self.compat_guardrail = CompatibilityGuardrail()

    async def create_plan(self, batch: DomainSchemaBatch) -> DomainSchemaPlan:
        """배치 계획 및 정책 검증 실행"""

        current_subjects = await self.registry_repository.describe_subjects(
            spec.subject for spec in batch.specs
        )

        # 활성화된 정책 로드 (커스텀 정책 지원)
        active_policies = []
        if self.policy_repository:
            active_policies = await self.policy_repository.list_active_policies(env=batch.env.value)

        policy_engine = DynamicSchemaPolicyEngine(active_policies)

        compatibility_reports = []
        plan_items: list[DomainSchemaPlanItem] = []
        impacts: list[DomainSchemaImpactRecord] = []
        all_violations: list[DomainPolicyViolation] = []

        for spec in batch.specs:
            current_info = current_subjects.get(spec.subject)

            # 1. 계획 아이템 생성
            action = self._determine_plan_action(current_info, spec)
            current_version = current_info.version if current_info else None
            target_version = (
                current_version
                if action is DomainPlanAction.NONE
                else (current_info.version + 1)
                if (current_info and current_info.version is not None)
                else 1
            )

            # 스키마 diff 계산
            diff = (
                DomainSchemaDiff(
                    type="no_change",
                    changes=("No schema change detected",),
                    current_version=current_version,
                    target_compatibility=spec.compatibility.value
                    if hasattr(spec.compatibility, "value")
                    else spec.compatibility,
                    schema_type=spec.schema_type.value
                    if hasattr(spec.schema_type, "value")
                    else spec.schema_type,
                )
                if action is DomainPlanAction.NONE
                else self._calculate_schema_diff(current_info, spec)
            )

            plan_item = DomainSchemaPlanItem(
                subject=spec.subject,
                action=action,
                current_version=current_version,
                target_version=target_version,
                diff=diff,
                schema=spec.schema,
                current_schema=current_info.schema if current_info else None,
                reason=spec.reason,
            )
            plan_items.append(plan_item)

            # 2. 호환성 검증 (Registry 레벨)
            report = await self.registry_repository.check_compatibility(spec)
            compatibility_reports.append(report)

            # 3. 거버넌스 정책 검사 (Guardrails & Linting - Dynamic Engine)
            # 3.1 호환성 가드레일 (기본 내장 - 선택사항)
            hardcoded_violations = self.compat_guardrail.check(
                spec.subject, spec.compatibility, batch.env
            )
            all_violations.extend(hardcoded_violations)

            # 3.2 다이내믹 엔진 (사용자 정의 정책)
            dynamic_violations = policy_engine.evaluate(spec, batch.env.value)
            all_violations.extend(dynamic_violations)

            # 4. 영향도 분석
            impact = await self.impact_analyzer.analyze_impact(spec.subject, batch.subject_strategy)
            impacts.append(impact)

        return DomainSchemaPlan(
            change_id=batch.change_id,
            env=batch.env,
            items=tuple(plan_items),
            compatibility_reports=tuple(compatibility_reports),
            impacts=tuple(impacts),
            violations=tuple(all_violations),
            requested_total=len(batch.specs),
        )

    def _determine_plan_action(
        self,
        current_info: SchemaVersionInfo | None,
        spec: DomainSchemaSpec,
    ) -> DomainPlanAction:
        if current_info is None:
            return DomainPlanAction.REGISTER

        if self._schema_matches_current(current_info, spec):
            return DomainPlanAction.NONE

        return DomainPlanAction.UPDATE

    def _schema_matches_current(
        self,
        current_info: SchemaVersionInfo,
        spec: DomainSchemaSpec,
    ) -> bool:
        schema_type_value = (
            spec.schema_type.value if hasattr(spec.schema_type, "value") else str(spec.schema_type)
        )
        if current_info.schema_type is not None and current_info.schema_type != schema_type_value:
            return False

        return _normalize_schema_text(
            current_info.schema, schema_type_value
        ) == _normalize_schema_text(
            spec.schema,
            schema_type_value,
        )

    def _calculate_schema_diff(
        self,
        current_info: SchemaVersionInfo | None,
        spec: DomainSchemaSpec,
    ) -> DomainSchemaDiff:
        """스키마 변경 사항 계산"""
        if not current_info:
            return DomainSchemaDiff(
                type="new_registration",
                changes=("New schema registration",),
                current_version=None,
                target_compatibility=spec.compatibility.value
                if hasattr(spec.compatibility, "value")
                else spec.compatibility,
                schema_type=spec.schema_type.value
                if hasattr(spec.schema_type, "value")
                else spec.schema_type,
            )

        changes: list[str] = []

        # 1. 메타데이터/타입 변경 확인
        # 1. 메타데이터/타입 변경 확인
        schema_type_val = (
            spec.schema_type.value if hasattr(spec.schema_type, "value") else spec.schema_type
        )
        if current_info.schema_type is not None and current_info.schema_type != schema_type_val:
            changes.append(f"Type changed: {current_info.schema_type} → {schema_type_val}")

        # 2. 필드 레벨 Diff (JSON/Avro인 경우)
        if schema_type_val in ["AVRO", "JSON"]:
            try:
                old_raw = current_info.schema or "{}"
                new_raw = spec.schema or "{}"
                old_json = json.loads(old_raw)
                new_json = json.loads(new_raw)

                if old_raw != new_raw:

                    def get_field_diff(old_json: Any, new_json: Any, prefix: str = "") -> list[str]:
                        diffs = []
                        old_fields = {f["name"]: f for f in old_json.get("fields", [])}
                        new_fields = {f["name"]: f for f in new_json.get("fields", [])}

                        added = set(new_fields.keys()) - set(old_fields.keys())
                        removed = set(old_fields.keys()) - set(new_fields.keys())
                        common = set(old_fields.keys()) & set(new_fields.keys())

                        diffs.extend([f"Added field: {prefix}{name}" for name in added])
                        diffs.extend([f"Removed field: {prefix}{name}" for name in removed])

                        for name in common:
                            old_f = old_fields[name]
                            new_f = new_fields[name]
                            if old_f != new_f:
                                # If both are records, recurse
                                if (
                                    isinstance(old_f.get("type"), dict)
                                    and old_f["type"].get("type") == "record"
                                    and isinstance(new_f.get("type"), dict)
                                    and new_f["type"].get("type") == "record"
                                ):
                                    diffs.extend(
                                        get_field_diff(
                                            old_f["type"], new_f["type"], f"{prefix}{name}."
                                        )
                                    )
                                elif old_f.get("type") != new_f.get("type"):
                                    diffs.append(
                                        f"Changed type: {prefix}{name} ({old_f.get('type')} -> {new_f.get('type')})"
                                    )
                                else:
                                    diffs.append(f"Modified field: {prefix}{name}")
                        return diffs

                    changes = get_field_diff(old_json, new_json)
                    if not changes:
                        changes.append("Schema structure changed (reordered or metadata updated)")
            except Exception:
                changes.append("Schema definition updated")
        else:
            changes.append("Schema updated")

        if not changes:
            changes.append("No changes detected")

        return DomainSchemaDiff(
            type="update",
            changes=tuple(changes),
            current_version=current_info.version,
            target_compatibility=spec.compatibility.value
            if hasattr(spec.compatibility, "value")
            else spec.compatibility,
            schema_type=current_info.schema_type
            or (spec.schema_type.value if hasattr(spec.schema_type, "value") else spec.schema_type),
        )


def _normalize_schema_text(schema_text: str | None, schema_type: str) -> str | None:
    if schema_text is None:
        return None

    stripped = schema_text.strip()
    if schema_type in {"AVRO", "JSON"}:
        try:
            return json.dumps(json.loads(stripped), sort_keys=True, separators=(",", ":"))
        except json.JSONDecodeError:
            return stripped

    return stripped
