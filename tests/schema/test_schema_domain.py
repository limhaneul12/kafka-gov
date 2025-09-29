"""Schema 도메인 레이어 테스트 (재구성)"""

from __future__ import annotations

import pytest

from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainPlanAction,
    DomainPolicyViolation,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaBatch,
    DomainSchemaCompatibilityReport,
    DomainSchemaMetadata,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaReference,
    DomainSchemaSource,
    DomainSchemaSourceType,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSchemaUploadResult,
    DomainSubjectStrategy,
    ensure_unique_subjects,
)


class TestSchemaMetadata:
    @pytest.mark.unit
    def test_create_and_validate(self) -> None:
        meta = DomainSchemaMetadata(owner="team-data")
        assert meta.owner == "team-data"
        assert meta.tags == ()
        with pytest.raises(ValueError):
            DomainSchemaMetadata(owner="")


class TestSchemaReference:
    @pytest.mark.unit
    def test_reference_validation(self) -> None:
        ref = DomainSchemaReference(name="User", subject="dev.user", version=1)
        assert ref.version == 1
        with pytest.raises(ValueError):
            DomainSchemaReference(name="", subject="dev.user", version=1)
        with pytest.raises(ValueError):
            DomainSchemaReference(name="User", subject="", version=1)
        with pytest.raises(ValueError):
            DomainSchemaReference(name="User", subject="dev.user", version=0)


class TestSchemaSource:
    @pytest.mark.unit
    def test_source_variants(self) -> None:
        inline = DomainSchemaSource(type=DomainSchemaSourceType.INLINE, inline="{}")
        assert inline.inline == "{}"
        with pytest.raises(ValueError):
            DomainSchemaSource(type=DomainSchemaSourceType.INLINE)
        file = DomainSchemaSource(type=DomainSchemaSourceType.FILE, file="schemas/a.avsc")
        assert file.file == "schemas/a.avsc"
        with pytest.raises(ValueError):
            DomainSchemaSource(type=DomainSchemaSourceType.FILE)
        yaml = DomainSchemaSource(type=DomainSchemaSourceType.YAML, yaml="a: 1")
        assert yaml.yaml == "a: 1"
        with pytest.raises(ValueError):
            DomainSchemaSource(type=DomainSchemaSourceType.YAML)


class TestSchemaSpec:
    @pytest.mark.unit
    def test_spec_with_schema_or_source(self) -> None:
        spec = DomainSchemaSpec(
            subject="dev.user.event",
            schema_type=DomainSchemaType.AVRO,
            compatibility=DomainCompatibilityMode.BACKWARD,
            schema='{"type": "record", "name": "User"}',
        )
        assert spec.environment == DomainEnvironment.DEV
        assert len(spec.fingerprint()) == 16
        with pytest.raises(ValueError):
            DomainSchemaSpec(
                subject="",
                schema_type=DomainSchemaType.AVRO,
                compatibility=DomainCompatibilityMode.BACKWARD,
            )
        with pytest.raises(ValueError):
            DomainSchemaSpec(
                subject="dev.x",
                schema_type=DomainSchemaType.AVRO,
                compatibility=DomainCompatibilityMode.BACKWARD,
            )


class TestSchemaBatch:
    @pytest.mark.unit
    def test_batch_validation(self) -> None:
        spec1 = DomainSchemaSpec(
            subject="dev.user.event",
            schema_type=DomainSchemaType.AVRO,
            compatibility=DomainCompatibilityMode.BACKWARD,
            schema="{}",
        )
        spec2 = DomainSchemaSpec(
            subject="dev.order.event",
            schema_type=DomainSchemaType.AVRO,
            compatibility=DomainCompatibilityMode.BACKWARD,
            schema="{}",
        )
        batch = DomainSchemaBatch(
            change_id="chg-1",
            env=DomainEnvironment.DEV,
            subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
            specs=(spec1, spec2),
        )
        assert len(batch.fingerprint()) == 16
        with pytest.raises(ValueError):
            DomainSchemaBatch(
                change_id="",
                env=DomainEnvironment.DEV,
                subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
                specs=(spec1,),
            )
        with pytest.raises(ValueError):
            DomainSchemaBatch(
                change_id="chg-1",
                env=DomainEnvironment.DEV,
                subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
                specs=(),
            )
        with pytest.raises(ValueError):
            DomainSchemaBatch(
                change_id="chg-1",
                env=DomainEnvironment.DEV,
                subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
                specs=(spec1, spec1),
            )
        wrong_env_spec = DomainSchemaSpec(
            subject="prod.user.event",
            schema_type=DomainSchemaType.AVRO,
            compatibility=DomainCompatibilityMode.BACKWARD,
            schema="{}",
        )
        with pytest.raises(ValueError):
            DomainSchemaBatch(
                change_id="chg-1",
                env=DomainEnvironment.DEV,
                subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
                specs=(wrong_env_spec,),
            )


class TestSchemaPlanAndResult:
    @pytest.mark.unit
    def test_plan_and_apply_result(self) -> None:
        items = (
            DomainSchemaPlanItem(
                subject="dev.user.event",
                action=DomainPlanAction.REGISTER,
                current_version=None,
                target_version=1,
                diff={"action": "create"},
            ),
        )
        plan = DomainSchemaPlan(change_id="chg-1", env=DomainEnvironment.DEV, items=items)
        s = plan.summary()
        assert s["total_items"] == 1
        assert plan.can_apply is True

        violation = DomainPolicyViolation(
            subject="dev.user.event",
            rule="naming",
            message="bad",
            severity="error",
        )
        plan2 = DomainSchemaPlan(
            change_id="chg-2", env=DomainEnvironment.DEV, items=(), violations=(violation,)
        )
        assert plan2.can_apply is False

        report = DomainSchemaCompatibilityReport(
            subject="dev.user.event", mode=DomainCompatibilityMode.BACKWARD, is_compatible=False
        )
        plan3 = DomainSchemaPlan(
            change_id="chg-3", env=DomainEnvironment.DEV, items=(), compatibility_reports=(report,)
        )
        assert plan3.can_apply is False

        result = DomainSchemaApplyResult(
            change_id="chg-1",
            env=DomainEnvironment.DEV,
            registered=("dev.user.event",),
            skipped=(),
            failed=(),
            audit_id="audit-1",
        )
        sr = result.summary()
        assert sr["total_items"] == 1

    @pytest.mark.unit
    def test_artifact_and_upload_result(self) -> None:
        art = DomainSchemaArtifact(subject="dev.user", version=1, storage_url="s3://bucket/key")
        assert art.version == 1
        with pytest.raises(ValueError):
            DomainSchemaArtifact(subject="dev.user", version=0, storage_url="s3://bucket/key")
        with pytest.raises(ValueError):
            DomainSchemaArtifact(subject="dev.user", version=1, storage_url="")

        upload = DomainSchemaUploadResult(upload_id="u1", artifacts=(art,))
        assert upload.upload_id == "u1"


class TestUtils:
    @pytest.mark.unit
    def test_unique_subjects(self) -> None:
        ensure_unique_subjects(["a", "b", "c"])  # no raise
        with pytest.raises(ValueError):
            ensure_unique_subjects(["a", "b", "a"])
