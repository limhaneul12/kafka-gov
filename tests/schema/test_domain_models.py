"""Schema Domain Models 테스트"""

from __future__ import annotations

import pytest

from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSchemaBatch,
    DomainSchemaMetadata,
    DomainSchemaReference,
    DomainSchemaSource,
    DomainSchemaSourceType,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSubjectStrategy,
)
from tests.schema.factories import (
    create_schema_batch,
    create_schema_metadata,
    create_schema_reference,
    create_schema_source,
    create_schema_spec,
)


class TestDomainSchemaMetadata:
    """DomainSchemaMetadata 테스트"""

    def test_create_valid_metadata(self):
        """정상적인 메타데이터 생성"""
        metadata = create_schema_metadata(
            owner="team-data",
            doc="https://wiki.company.com/schemas/user",
            tags=("pii", "critical"),
            description="User schema",
        )

        assert metadata.owner == "team-data"
        assert metadata.doc == "https://wiki.company.com/schemas/user"
        assert metadata.tags == ("pii", "critical")
        assert metadata.description == "User schema"

    def test_owner_required(self):
        """owner는 필수"""
        with pytest.raises(ValueError, match="owner is required"):
            DomainSchemaMetadata(owner="", doc=None, tags=(), description=None)

    def test_metadata_is_frozen(self):
        """메타데이터는 불변"""
        metadata = create_schema_metadata()
        with pytest.raises(AttributeError):
            metadata.owner = "new-team"  # type: ignore[misc]


class TestDomainSchemaReference:
    """DomainSchemaReference 테스트"""

    def test_create_valid_reference(self):
        """정상적인 참조 생성"""
        ref = create_schema_reference(
            name="Address",
            subject="dev.address-value",
            version=2,
        )

        assert ref.name == "Address"
        assert ref.subject == "dev.address-value"
        assert ref.version == 2

    def test_version_must_be_positive(self):
        """버전은 1 이상"""
        with pytest.raises(ValueError, match="reference version must be >= 1"):
            create_schema_reference(version=0)

    def test_name_required(self):
        """name은 필수"""
        with pytest.raises(ValueError, match="reference name is required"):
            DomainSchemaReference(name="", subject="dev.test", version=1)

    def test_subject_required(self):
        """subject는 필수"""
        with pytest.raises(ValueError, match="reference subject is required"):
            DomainSchemaReference(name="Test", subject="", version=1)


class TestDomainSchemaSource:
    """DomainSchemaSource 테스트"""

    def test_inline_source(self):
        """Inline 소스"""
        source = create_schema_source(
            source_type=DomainSchemaSourceType.INLINE,
            inline='{"type": "string"}',
        )

        assert source.type == DomainSchemaSourceType.INLINE
        assert source.inline == '{"type": "string"}'

    def test_file_source(self):
        """File 소스"""
        source = create_schema_source(
            source_type=DomainSchemaSourceType.FILE,
            inline=None,
            file="schemas/user.avsc",
        )

        assert source.type == DomainSchemaSourceType.FILE
        assert source.file == "schemas/user.avsc"

    def test_yaml_source(self):
        """YAML 소스"""
        source = create_schema_source(
            source_type=DomainSchemaSourceType.YAML,
            inline=None,
            yaml="type: record\nname: User",
        )

        assert source.type == DomainSchemaSourceType.YAML
        assert source.yaml == "type: record\nname: User"

    def test_inline_requires_content(self):
        """Inline은 content 필수"""
        with pytest.raises(ValueError, match="inline source requires inline content"):
            DomainSchemaSource(
                type=DomainSchemaSourceType.INLINE,
                inline=None,
                file=None,
                yaml=None,
            )

    def test_file_requires_reference(self):
        """File은 reference 필수"""
        with pytest.raises(ValueError, match="file source requires file reference"):
            DomainSchemaSource(
                type=DomainSchemaSourceType.FILE,
                inline=None,
                file=None,
                yaml=None,
            )

    def test_inline_cannot_have_file(self):
        """Inline은 file 불가"""
        with pytest.raises(ValueError, match="inline source cannot include file or yaml"):
            DomainSchemaSource(
                type=DomainSchemaSourceType.INLINE,
                inline='{"type": "string"}',
                file="test.avsc",
                yaml=None,
            )

    def test_yaml_requires_content(self):
        """YAML은 content 필수"""
        with pytest.raises(ValueError, match="yaml source requires yaml content"):
            DomainSchemaSource(
                type=DomainSchemaSourceType.YAML,
                inline=None,
                file=None,
                yaml=None,
            )

    def test_file_cannot_have_inline(self):
        """File은 inline 불가"""
        with pytest.raises(ValueError, match="file source cannot include inline or yaml"):
            DomainSchemaSource(
                type=DomainSchemaSourceType.FILE,
                inline='{"type": "string"}',
                file="test.avsc",
                yaml=None,
            )

    def test_yaml_cannot_have_file(self):
        """YAML은 file 불가"""
        with pytest.raises(ValueError, match="yaml source cannot include inline or file"):
            DomainSchemaSource(
                type=DomainSchemaSourceType.YAML,
                inline=None,
                file="test.avsc",
                yaml="type: record",
            )


class TestDomainSchemaSpec:
    """DomainSchemaSpec 테스트"""

    def test_create_valid_spec(self):
        """정상적인 스키마 명세"""
        spec = create_schema_spec(
            subject="prod.user-value",
            schema_type=DomainSchemaType.AVRO,
            compatibility=DomainCompatibilityMode.FULL,
        )

        assert spec.subject == "prod.user-value"
        assert spec.schema_type == DomainSchemaType.AVRO
        assert spec.compatibility == DomainCompatibilityMode.FULL

    def test_subject_required(self):
        """subject는 필수"""
        with pytest.raises(ValueError, match="subject is required"):
            DomainSchemaSpec(
                subject="",
                schema_type=DomainSchemaType.AVRO,
                compatibility=DomainCompatibilityMode.BACKWARD,
                schema='{"type": "string"}',
            )

    def test_schema_or_source_required(self):
        """schema 또는 source 필수"""
        with pytest.raises(ValueError, match="schema spec must provide schema or source"):
            DomainSchemaSpec(
                subject="dev.test",
                schema_type=DomainSchemaType.AVRO,
                compatibility=DomainCompatibilityMode.BACKWARD,
                schema=None,
                source=None,
            )

    def test_schema_literal_with_non_inline_source(self):
        """schema literal은 inline source와만 사용 가능"""
        with pytest.raises(
            ValueError, match="schema literal is only allowed when source is inline"
        ):
            DomainSchemaSpec(
                subject="dev.test",
                schema_type=DomainSchemaType.AVRO,
                compatibility=DomainCompatibilityMode.BACKWARD,
                schema='{"type": "string"}',
                source=DomainSchemaSource(
                    type=DomainSchemaSourceType.FILE,
                    inline=None,
                    file="test.avsc",
                    yaml=None,
                ),
            )

    def test_environment_extraction(self):
        """subject에서 환경 추출"""
        prod_spec = create_schema_spec(subject="prod.user-value")
        assert prod_spec.environment == DomainEnvironment.PROD

        dev_spec = create_schema_spec(subject="dev.test-value")
        assert dev_spec.environment == DomainEnvironment.DEV

        stg_spec = create_schema_spec(subject="stg.test-value")
        assert stg_spec.environment == DomainEnvironment.STG

    def test_fingerprint_generation(self):
        """지문 생성"""
        spec1 = create_schema_spec(subject="dev.test", schema='{"type": "string"}')
        spec2 = create_schema_spec(subject="dev.test", schema='{"type": "string"}')

        # 동일한 명세는 동일한 지문
        assert spec1.fingerprint() == spec2.fingerprint()

        # 다른 명세는 다른 지문
        spec3 = create_schema_spec(subject="dev.other", schema='{"type": "string"}')
        assert spec1.fingerprint() != spec3.fingerprint()

    def test_with_references(self):
        """참조가 있는 스키마"""
        ref = create_schema_reference()
        spec = create_schema_spec(references=(ref,))

        assert len(spec.references) == 1
        assert spec.references[0].name == "TestRef"


class TestDomainSchemaBatch:
    """DomainSchemaBatch 테스트"""

    def test_create_valid_batch(self):
        """정상적인 배치 생성"""
        specs = (
            create_schema_spec(subject="dev.user-value"),
            create_schema_spec(subject="dev.order-value"),
        )
        batch = create_schema_batch(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            specs=specs,
        )

        assert batch.change_id == "test-001"
        assert batch.env == DomainEnvironment.DEV
        assert len(batch.specs) == 2

    def test_change_id_required(self):
        """change_id는 필수"""
        with pytest.raises(ValueError, match="change_id is required"):
            DomainSchemaBatch(
                change_id="",
                env=DomainEnvironment.DEV,
                subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
                specs=(create_schema_spec(),),
            )

    def test_specs_cannot_be_empty(self):
        """specs는 비어있을 수 없음"""
        with pytest.raises(ValueError, match="specs cannot be empty"):
            DomainSchemaBatch(
                change_id="test-001",
                env=DomainEnvironment.DEV,
                subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
                specs=(),
            )

    def test_duplicate_subjects_not_allowed(self):
        """중복된 subject 불허"""
        specs = (
            create_schema_spec(subject="dev.test-value"),
            create_schema_spec(subject="dev.test-value"),  # 중복
        )

        with pytest.raises(ValueError, match="duplicate subjects detected"):
            DomainSchemaBatch(
                change_id="test-001",
                env=DomainEnvironment.DEV,
                subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
                specs=specs,
            )

    def test_environment_consistency_check(self):
        """환경 일관성 검증"""
        specs = (
            create_schema_spec(subject="dev.test-value"),
            create_schema_spec(subject="prod.test-value"),  # 다른 환경
        )

        with pytest.raises(ValueError, match="does not match batch environment"):
            DomainSchemaBatch(
                change_id="test-001",
                env=DomainEnvironment.DEV,
                subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
                specs=specs,
            )

    def test_fingerprint_generation(self):
        """배치 지문 생성"""
        specs = (
            create_schema_spec(subject="dev.user-value"),
            create_schema_spec(subject="dev.order-value"),
        )
        batch1 = create_schema_batch(specs=specs)
        batch2 = create_schema_batch(specs=specs)

        # 동일한 배치는 동일한 지문
        assert batch1.fingerprint() == batch2.fingerprint()

        # 다른 change_id는 다른 지문
        batch3 = create_schema_batch(change_id="test-002", specs=specs)
        assert batch1.fingerprint() != batch3.fingerprint()


class TestDomainSchemaPlan:
    """DomainSchemaPlan 테스트"""

    def test_plan_summary(self):
        """계획 요약"""
        from app.schema.domain.models import (
            DomainPlanAction,
            DomainSchemaDiff,
            DomainSchemaPlan,
            DomainSchemaPlanItem,
        )

        items = (
            DomainSchemaPlanItem(
                subject="dev.user-value",
                action=DomainPlanAction.REGISTER,
                current_version=None,
                target_version=1,
                diff=DomainSchemaDiff(
                    type="new_registration",
                    changes=("New schema registration",),
                    current_version=None,
                    target_compatibility="BACKWARD",
                    schema_type="AVRO",
                ),
            ),
            DomainSchemaPlanItem(
                subject="dev.order-value",
                action=DomainPlanAction.UPDATE,
                current_version=1,
                target_version=2,
                diff=DomainSchemaDiff(
                    type="update",
                    changes=("Schema definition updated",),
                    current_version=1,
                    target_compatibility="BACKWARD",
                    schema_type="AVRO",
                ),
            ),
        )

        plan = DomainSchemaPlan(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            items=items,
        )

        summary = plan.summary()
        assert summary["total_items"] == 2
        assert summary["register_count"] == 1
        assert summary["update_count"] == 1
        assert summary["violation_count"] == 0

    def test_can_apply_with_no_violations(self):
        """위반 없으면 적용 가능"""
        from app.schema.domain.models import (
            DomainPlanAction,
            DomainSchemaCompatibilityReport,
            DomainSchemaDiff,
            DomainSchemaPlan,
            DomainSchemaPlanItem,
        )

        items = (
            DomainSchemaPlanItem(
                subject="dev.test-value",
                action=DomainPlanAction.REGISTER,
                current_version=None,
                target_version=1,
                diff=DomainSchemaDiff(
                    type="new_registration",
                    changes=("New schema registration",),
                    current_version=None,
                    target_compatibility="BACKWARD",
                    schema_type="AVRO",
                ),
            ),
        )

        compatibility_reports = (
            DomainSchemaCompatibilityReport(
                subject="dev.test-value",
                mode=DomainCompatibilityMode.BACKWARD,
                is_compatible=True,
                issues=(),
            ),
        )

        plan = DomainSchemaPlan(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            items=items,
            violations=(),
            compatibility_reports=compatibility_reports,
        )

        assert plan.can_apply is True

    def test_can_apply_with_violations(self):
        """위반 있으면 적용 불가"""
        from app.schema.domain.models import (
            DomainPlanAction,
            DomainPolicyViolation,
            DomainSchemaDiff,
            DomainSchemaPlan,
            DomainSchemaPlanItem,
        )

        items = (
            DomainSchemaPlanItem(
                subject="prod.test-value",
                action=DomainPlanAction.REGISTER,
                current_version=None,
                target_version=1,
                diff=DomainSchemaDiff(
                    type="new_registration",
                    changes=("New schema registration",),
                    current_version=None,
                    target_compatibility="BACKWARD",
                    schema_type="AVRO",
                ),
            ),
        )

        violations = (
            DomainPolicyViolation(
                subject="prod.test-value",
                rule="schema.compatibility.mode",
                message="BACKWARD not allowed in PROD",
                severity="error",
            ),
        )

        plan = DomainSchemaPlan(
            change_id="test-001",
            env=DomainEnvironment.PROD,
            items=items,
            violations=violations,
        )

        assert plan.can_apply is False

    def test_error_violations_property(self):
        """에러 위반만 필터링"""
        from app.schema.domain.models import (
            DomainPlanAction,
            DomainPolicyViolation,
            DomainSchemaDiff,
            DomainSchemaPlan,
            DomainSchemaPlanItem,
        )

        items = (
            DomainSchemaPlanItem(
                subject="dev.test-value",
                action=DomainPlanAction.REGISTER,
                current_version=None,
                target_version=1,
                diff=DomainSchemaDiff(
                    type="new_registration",
                    changes=("New schema registration",),
                    current_version=None,
                    target_compatibility="BACKWARD",
                    schema_type="AVRO",
                ),
            ),
        )

        violations = (
            DomainPolicyViolation(
                subject="dev.test-value",
                rule="test.rule1",
                message="Error violation",
                severity="error",
            ),
            DomainPolicyViolation(
                subject="dev.test-value",
                rule="test.rule2",
                message="Warning violation",
                severity="warning",
            ),
        )

        plan = DomainSchemaPlan(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            items=items,
            violations=violations,
        )

        error_violations = plan.error_violations
        assert len(error_violations) == 1
        assert error_violations[0].severity == "error"


class TestDomainSchemaApplyResult:
    """DomainSchemaApplyResult 테스트"""

    def test_create_apply_result(self):
        """적용 결과 생성"""
        from app.schema.domain.models import DomainSchemaApplyResult

        result = DomainSchemaApplyResult(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            registered=("dev.user-value", "dev.order-value"),
            skipped=(),
            failed=(),
            audit_id="audit-123",
            artifacts=(),
        )

        assert result.change_id == "test-001"
        assert len(result.registered) == 2
        assert len(result.failed) == 0

    def test_apply_result_with_failures(self):
        """실패 포함 결과"""
        from app.schema.domain.models import DomainSchemaApplyResult

        result = DomainSchemaApplyResult(
            change_id="test-001",
            env=DomainEnvironment.DEV,
            registered=("dev.user-value",),
            skipped=(),
            failed=({"subject": "dev.order-value", "error": "Validation failed"},),
            audit_id="audit-123",
            artifacts=(),
        )

        assert len(result.registered) == 1
        assert len(result.failed) == 1
        assert result.failed[0]["subject"] == "dev.order-value"


class TestDomainSchemaDeleteImpact:
    """DomainSchemaDeleteImpact 테스트"""

    def test_safe_delete(self):
        """안전한 삭제"""
        from app.schema.domain.models import DomainSchemaDeleteImpact

        impact = DomainSchemaDeleteImpact(
            subject="dev.test-value",
            current_version=1,
            total_versions=1,
            affected_topics=(),
            warnings=(),
            safe_to_delete=True,
        )

        assert impact.safe_to_delete is True
        assert len(impact.warnings) == 0

    def test_unsafe_delete_with_warnings(self):
        """경고가 있는 삭제"""
        from app.schema.domain.models import DomainSchemaDeleteImpact

        impact = DomainSchemaDeleteImpact(
            subject="prod.user-value",
            current_version=15,
            total_versions=15,
            affected_topics=("prod.user.events",),
            warnings=(
                "다음 토픽이 이 스키마를 사용 중일 수 있습니다: prod.user.events",
                "이 스키마는 15개의 버전이 있습니다.",
            ),
            safe_to_delete=False,
        )

        assert impact.safe_to_delete is False
        assert len(impact.warnings) == 2
        assert len(impact.affected_topics) == 1


class TestDomainSchemaArtifact:
    """DomainSchemaArtifact 테스트"""

    def test_create_artifact(self):
        """아티팩트 생성"""
        from app.schema.domain.models import DomainSchemaArtifact

        artifact = DomainSchemaArtifact(
            subject="dev.user-value",
            version=1,
            storage_url="s3://bucket/dev/user-value/1/schema.avsc",
            checksum="abc123",
        )

        assert artifact.subject == "dev.user-value"
        assert artifact.version == 1
        assert artifact.storage_url == "s3://bucket/dev/user-value/1/schema.avsc"

    def test_artifact_version_must_be_positive(self):
        """버전은 1 이상"""
        from app.schema.domain.models import DomainSchemaArtifact

        with pytest.raises(ValueError, match="artifact version must be >= 1"):
            DomainSchemaArtifact(
                subject="dev.test",
                version=0,
                storage_url="s3://bucket/test",
            )

    def test_artifact_storage_url_required(self):
        """storage_url 필수"""
        from app.schema.domain.models import DomainSchemaArtifact

        with pytest.raises(ValueError, match="storage_url is required"):
            DomainSchemaArtifact(
                subject="dev.test",
                version=1,
                storage_url="",
            )


class TestDomainSchemaUploadResult:
    """DomainSchemaUploadResult 테스트"""

    def test_upload_result_summary(self):
        """업로드 결과 요약"""
        from app.schema.domain.models import (
            DomainSchemaArtifact,
            DomainSchemaUploadResult,
        )

        artifacts = (
            DomainSchemaArtifact(
                subject="user.avro",
                version=1,
                storage_url="s3://bucket/user.avro",
            ),
            DomainSchemaArtifact(
                subject="order.json",
                version=1,
                storage_url="s3://bucket/order.json",
            ),
            DomainSchemaArtifact(
                subject="product.proto",
                version=1,
                storage_url="s3://bucket/product.proto",
            ),
        )

        result = DomainSchemaUploadResult(
            upload_id="upload-123",
            artifacts=artifacts,
        )

        summary = result.summary()
        assert summary["total_files"] == 3
        assert summary["avro_count"] == 1
        assert summary["json_count"] == 1
        assert summary["proto_count"] == 1


class TestEnsureUniqueSubjects:
    """ensure_unique_subjects 함수 테스트"""

    def test_unique_subjects(self):
        """중복 없는 subjects"""
        from app.schema.domain.models import ensure_unique_subjects

        subjects = ["dev.user-value", "dev.order-value", "dev.product-value"]
        # 예외 발생하지 않아야 함
        ensure_unique_subjects(subjects)

    def test_duplicate_subjects(self):
        """중복된 subjects"""
        from app.schema.domain.models import ensure_unique_subjects

        subjects = ["dev.user-value", "dev.order-value", "dev.user-value"]

        with pytest.raises(ValueError, match="duplicate subjects detected"):
            ensure_unique_subjects(subjects)
