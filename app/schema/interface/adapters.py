"""Schema Interface TypeAdapter 기반 변환 어댑터"""

from __future__ import annotations

from pydantic import TypeAdapter, ValidationError

from ..domain.models import (
    CompatibilityMode as DomainCompatibilityMode,
    Environment as DomainEnvironment,
    SchemaApplyResult as DomainSchemaApplyResult,
    SchemaBatch as DomainSchemaBatch,
    SchemaMetadata as DomainSchemaMetadata,
    SchemaPlan as DomainSchemaPlan,
    SchemaReference as DomainSchemaReference,
    SchemaSource as DomainSchemaSource,
    SchemaSourceType as DomainSchemaSourceType,
    SchemaSpec as DomainSchemaSpec,
    SchemaType as DomainSchemaType,
    SubjectStrategy as DomainSubjectStrategy,
)
from .schema import (
    PolicyViolation,
    SchemaArtifact,
    SchemaBatchApplyResponse,
    SchemaBatchDryRunResponse,
    SchemaBatchRequest,
    SchemaCompatibilityIssue,
    SchemaCompatibilityReport,
    SchemaImpactRecord,
    SchemaPlanItem,
)
from .types.enums import Environment


class SchemaTypeAdapters:
    """Schema 모듈 TypeAdapter 컬렉션"""
    
    # Domain 모델 어댑터들
    schema_spec_adapter = TypeAdapter[DomainSchemaSpec]
    schema_metadata_adapter = TypeAdapter[DomainSchemaMetadata]
    schema_reference_adapter = TypeAdapter[DomainSchemaReference]
    schema_source_adapter = TypeAdapter[DomainSchemaSource]
    schema_batch_adapter = TypeAdapter[DomainSchemaBatch]
    
    # Interface 모델 어댑터들
    schema_batch_request_adapter = TypeAdapter[SchemaBatchRequest]
    
    @classmethod
    def convert_item_to_spec(cls, item) -> DomainSchemaSpec:
        """SchemaBatchRequest의 item을 DomainSchemaSpec으로 안전하게 변환
        
        Args:
            item: 변환할 스키마 아이템
            
        Returns:
            변환된 DomainSchemaSpec
            
        Raises:
            ValidationError: 변환 중 검증 실패 시
        """
        try:
            # 메타데이터 변환
            domain_metadata = None
            if item.metadata:
                metadata_data = {
                    "owner": item.metadata.owner,
                    "doc": item.metadata.doc,
                    "tags": tuple(item.metadata.tags),
                    "description": item.metadata.description,
                }
                domain_metadata = cls.schema_metadata_adapter.validate_python(metadata_data)

            # 참조 변환
            references = tuple(
                cls.schema_reference_adapter.validate_python({
                    "name": ref.name,
                    "subject": ref.subject,
                    "version": ref.version,
                })
                for ref in item.references
            )

            # 소스 변환
            domain_source = None
            if item.source:
                source_data = {
                    "type": DomainSchemaSourceType(item.source.type.value),
                    "inline": item.source.inline,
                    "file": item.source.file,
                    "yaml": item.source.yaml,
                }
                domain_source = cls.schema_source_adapter.validate_python(source_data)

            # 호환성 모드 처리
            compatibility_value = (
                item.compatibility.value if item.compatibility 
                else DomainCompatibilityMode.NONE.value
            )

            # SchemaSpec 생성
            spec_data = {
                "subject": item.subject,
                "schema_type": DomainSchemaType(item.type.value),
                "compatibility": DomainCompatibilityMode(compatibility_value),
                "schema": item.schema,
                "source": domain_source,
                "schema_hash": item.schema_hash,
                "references": references,
                "metadata": domain_metadata,
                "reason": item.reason,
                "dry_run_only": item.dry_run_only,
            }
            
            return cls.schema_spec_adapter.validate_python(spec_data)
            
        except ValidationError as e:
            raise ValueError(f"Failed to convert schema item to SchemaSpec: {e}") from e

    @classmethod
    def convert_request_to_batch(cls, request: SchemaBatchRequest) -> DomainSchemaBatch:
        """SchemaBatchRequest를 DomainSchemaBatch로 안전하게 변환
        
        Args:
            request: 변환할 SchemaBatchRequest
            
        Returns:
            변환된 DomainSchemaBatch
            
        Raises:
            ValidationError: 변환 중 검증 실패 시
        """
        try:
            # 각 아이템을 SchemaSpec으로 변환
            specs = tuple(cls.convert_item_to_spec(item) for item in request.items)
            
            # SchemaBatch 생성
            batch_data = {
                "change_id": request.change_id,
                "env": DomainEnvironment(request.env.value),
                "subject_strategy": DomainSubjectStrategy(request.subject_strategy.value),
                "specs": specs,
            }
            
            return cls.schema_batch_adapter.validate_python(batch_data)
            
        except ValidationError as e:
            raise ValueError(f"Failed to convert SchemaBatchRequest to SchemaBatch: {e}") from e

    @classmethod
    def convert_plan_to_response(cls, plan: DomainSchemaPlan) -> SchemaBatchDryRunResponse:
        """DomainSchemaPlan을 SchemaBatchDryRunResponse로 변환
        
        Args:
            plan: 변환할 DomainSchemaPlan
            
        Returns:
            변환된 SchemaBatchDryRunResponse
        """
        # 계획 아이템 변환
        plan_items = [
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
        violations = [
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
        compatibility_reports = [
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
        impacts = [
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
        artifacts = [
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
            failed=[entry.copy() for entry in result.failed],
            audit_id=result.audit_id,
            artifacts=artifacts,
            summary=result.summary(),
        )


# 전역 어댑터 인스턴스 (성능 최적화)
schema_adapters = SchemaTypeAdapters()


def safe_convert_request_to_batch(request: SchemaBatchRequest) -> DomainSchemaBatch:
    """안전한 SchemaBatchRequest → DomainSchemaBatch 변환 (전역 함수)"""
    return schema_adapters.convert_request_to_batch(request)


def safe_convert_plan_to_response(plan: DomainSchemaPlan) -> SchemaBatchDryRunResponse:
    """안전한 DomainSchemaPlan → SchemaBatchDryRunResponse 변환 (전역 함수)"""
    return schema_adapters.convert_plan_to_response(plan)


def safe_convert_apply_result_to_response(
    result: DomainSchemaApplyResult,
) -> SchemaBatchApplyResponse:
    """안전한 DomainSchemaApplyResult → SchemaBatchApplyResponse 변환 (전역 함수)"""
    return schema_adapters.convert_apply_result_to_response(result)
