"""Schema Interface 수동 변환 어댑터 - 고성능 최적화"""

from __future__ import annotations

from ..domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSchemaApplyResult,
    DomainSchemaBatch,
    DomainSchemaMetadata,
    DomainSchemaPlan,
    DomainSchemaReference,
    DomainSchemaSource,
    DomainSchemaSourceType,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSubjectStrategy,
)
from .schemas import (
    PolicyViolation,
    SchemaArtifact,
    SchemaBatchApplyResponse,
    SchemaBatchDryRunResponse,
    SchemaBatchItem,
    SchemaBatchRequest,
    SchemaCompatibilityIssue,
    SchemaCompatibilityReport,
    SchemaImpactRecord,
    SchemaPlanItem,
)
from .types.enums import Environment


class SchemaConverter:
    """Schema 모듈 고성능 변환기 - msgspec 직접 생성"""

    __slots__ = ()  # 메모리 최적화

    @staticmethod
    def convert_item_to_spec(item: SchemaBatchItem) -> DomainSchemaSpec:
        """SchemaBatchItem을 DomainSchemaSpec으로 직접 변환 (고성능)

        Args:
            item: 변환할 스키마 아이템

        Returns:
            변환된 DomainSchemaSpec

        Raises:
            ValueError: 변환 중 검증 실패 시
        """
        # 메타데이터 변환 - 직접 생성
        domain_metadata = None
        if item.metadata:
            domain_metadata = DomainSchemaMetadata(
                owner=item.metadata.owner,
                doc=item.metadata.doc,
                tags=tuple(item.metadata.tags) if item.metadata.tags else (),
                description=item.metadata.description,
            )

        # 참조 변환 - 직접 생성 (리스트 컴프리헨션으로 최적화)
        references = (
            tuple(
                DomainSchemaReference(
                    name=ref.name,
                    subject=ref.subject,
                    version=ref.version,
                )
                for ref in item.references
            )
            if item.references
            else ()
        )

        # 소스 변환 - 직접 생성
        domain_source = None
        if item.source:
            domain_source = DomainSchemaSource(
                type=DomainSchemaSourceType(item.source.type.value),
                inline=item.source.inline,
                file=item.source.file,
                yaml=item.source.yaml,
            )

        # 호환성 모드 - 직접 변환
        compatibility = (
            DomainCompatibilityMode(item.compatibility.value)
            if item.compatibility
            else DomainCompatibilityMode.NONE
        )

        # SchemaSpec 직접 생성 - msgspec.Struct는 __init__으로 빠르게 생성
        return DomainSchemaSpec(
            subject=item.subject,
            schema_type=DomainSchemaType(item.type.value),
            compatibility=compatibility,
            schema=item.schema_text,
            source=domain_source,
            schema_hash=item.schema_hash,
            references=references,
            metadata=domain_metadata,
            reason=item.reason,
            dry_run_only=item.dry_run_only,
        )

    @classmethod
    def convert_request_to_batch(cls, request: SchemaBatchRequest) -> DomainSchemaBatch:
        """SchemaBatchRequest를 DomainSchemaBatch로 직접 변환 (고성능)

        Args:
            request: 변환할 SchemaBatchRequest

        Returns:
            변환된 DomainSchemaBatch
        """
        # 각 아이템을 SchemaSpec으로 변환 (제너레이터로 메모리 효율화)
        specs = tuple(cls.convert_item_to_spec(item) for item in request.items)

        # SchemaBatch 직접 생성
        return DomainSchemaBatch(
            change_id=request.change_id,
            env=DomainEnvironment(request.env.value),
            subject_strategy=DomainSubjectStrategy(request.subject_strategy.value),
            specs=specs,
        )

    @classmethod
    def convert_plan_to_response(cls, plan: DomainSchemaPlan) -> SchemaBatchDryRunResponse:
        """DomainSchemaPlan을 SchemaBatchDryRunResponse로 변환

        Args:
            plan: 변환할 DomainSchemaPlan

        Returns:
            변환된 SchemaBatchDryRunResponse
        """
        # 계획 아이템 변환
        plan_items: list[SchemaPlanItem] = [
            SchemaPlanItem(
                subject=item.subject,
                action=item.action.value,
                current_version=item.current_version,
                target_version=item.target_version,
                diff=item.diff,
            )
            for item in plan.items
        ]

        # 위반 사항 변환
        violations: list[PolicyViolation] = [
            PolicyViolation(
                subject=v.subject,
                rule=v.rule,
                message=v.message,
                severity=v.severity,
                field=v.field,
            )
            for v in plan.violations
        ]

        # 호환성 보고서 변환
        compatibility_reports: list[SchemaCompatibilityReport] = [
            SchemaCompatibilityReport(
                subject=report.subject,
                mode=report.mode.value if hasattr(report.mode, "value") else report.mode,
                is_compatible=report.is_compatible,
                issues=[
                    SchemaCompatibilityIssue(
                        path=issue.path,
                        message=issue.message,
                        type=getattr(
                            issue, "issue_type", issue.type if hasattr(issue, "type") else "unknown"
                        ),
                    )
                    for issue in report.issues
                ],
            )
            for report in plan.compatibility_reports
        ]

        # 영향도 변환
        impacts: list[SchemaImpactRecord] = [
            SchemaImpactRecord(
                subject=impact.subject,
                topics=list(impact.topics),
                consumers=list(impact.consumers),
            )
            for impact in plan.impacts
        ]

        return SchemaBatchDryRunResponse(
            env=Environment(plan.env.value),
            change_id=plan.change_id,
            plan=plan_items,
            violations=violations,
            compatibility=compatibility_reports,
            impacts=impacts,
            summary=plan.summary(),
        )

    @classmethod
    def convert_apply_result_to_response(
        cls, result: DomainSchemaApplyResult
    ) -> SchemaBatchApplyResponse:
        """DomainSchemaApplyResult를 SchemaBatchApplyResponse로 변환

        Args:
            result: 변환할 DomainSchemaApplyResult

        Returns:
            변환된 SchemaBatchApplyResponse
        """
        # 아티팩트 변환
        artifacts: list[SchemaArtifact] = [
            SchemaArtifact(
                subject=artifact.subject,
                version=artifact.version,
                storage_url=artifact.storage_url,
                checksum=artifact.checksum,
            )
            for artifact in result.artifacts
        ]

        return SchemaBatchApplyResponse(
            env=Environment(result.env.value),
            change_id=result.change_id,
            registered=list(result.registered),
            skipped=list(result.skipped),
            failed=list(result.failed),  # tuple of dicts → list (no copy needed, immutable)
            audit_id=result.audit_id,
            artifacts=artifacts,
            summary=result.summary(),
        )


# 전역 변환기 인스턴스 (싱글톤 패턴으로 메모리 절약)
_converter = SchemaConverter()


def safe_convert_request_to_batch(request: SchemaBatchRequest) -> DomainSchemaBatch:
    """SchemaBatchRequest → DomainSchemaBatch 고성능 변환"""
    return _converter.convert_request_to_batch(request)


def safe_convert_plan_to_response(plan: DomainSchemaPlan) -> SchemaBatchDryRunResponse:
    """DomainSchemaPlan → SchemaBatchDryRunResponse 고성능 변환"""
    return _converter.convert_plan_to_response(plan)


def safe_convert_apply_result_to_response(
    result: DomainSchemaApplyResult,
) -> SchemaBatchApplyResponse:
    """DomainSchemaApplyResult → SchemaBatchApplyResponse 고성능 변환"""
    return _converter.convert_apply_result_to_response(result)
