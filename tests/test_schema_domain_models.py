from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.schema.domain.models.internal import Reference, SchemaVersionInfo
from app.schema.domain.models.plan_result import (
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaDiff,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaUploadResult,
)
from app.schema.domain.models.policy import (
    DomainPolicyViolation,
    DomainSchemaCompatibilityIssue,
    DomainSchemaCompatibilityReport,
    DomainSchemaDeleteImpact,
    DomainSchemaImpactRecord,
)
from app.schema.domain.models.spec_batch import DomainSchemaBatch, DomainSchemaSpec
from app.schema.domain.models.types_enum import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainPlanAction,
    DomainSchemaSourceType,
    DomainSchemaType,
    DomainSubjectStrategy,
)
from app.schema.domain.models.utils import ensure_unique_subjects
from app.schema.domain.models.value_objects import (
    DomainSchemaMetadata,
    DomainSchemaReference,
    DomainSchemaSource,
)


def test_schema_value_objects_validation() -> None:
    with pytest.raises(ValueError):
        DomainSchemaMetadata(owner="")

    with pytest.raises(ValueError):
        DomainSchemaReference(name="", subject="dev.a", version=1)
    with pytest.raises(ValueError):
        DomainSchemaReference(name="r", subject="", version=1)
    with pytest.raises(ValueError):
        DomainSchemaReference(name="r", subject="dev.a", version=0)

    ref = DomainSchemaReference(name="order", subject="dev.order-value", version=1)
    assert ref.version == 1

    with pytest.raises(ValueError):
        DomainSchemaSource(type=DomainSchemaSourceType.INLINE)
    with pytest.raises(ValueError):
        DomainSchemaSource(type=DomainSchemaSourceType.INLINE, inline='{"type":"record"}', file="f")
    with pytest.raises(ValueError):
        DomainSchemaSource(type=DomainSchemaSourceType.FILE)
    with pytest.raises(ValueError):
        DomainSchemaSource(type=DomainSchemaSourceType.FILE, file="schema.avsc", inline="x")
    with pytest.raises(ValueError):
        DomainSchemaSource(type=DomainSchemaSourceType.YAML)
    with pytest.raises(ValueError):
        DomainSchemaSource(type=DomainSchemaSourceType.YAML, yaml="kind: x", file="f")

    assert (
        DomainSchemaSource(type=DomainSchemaSourceType.FILE, file="schema.avsc").file
        == "schema.avsc"
    )
    assert (
        DomainSchemaSource(type=DomainSchemaSourceType.YAML, yaml="kind: Schema").yaml
        == "kind: Schema"
    )


def test_schema_spec_and_batch_validation_and_fingerprint() -> None:
    inline = DomainSchemaSource(type=DomainSchemaSourceType.INLINE, inline='{"type":"record"}')
    file_source = DomainSchemaSource(type=DomainSchemaSourceType.FILE, file="schema.avsc")

    with pytest.raises(ValueError):
        DomainSchemaSpec(
            subject="dev.orders-value",
            schema_type=DomainSchemaType.AVRO,
            compatibility=DomainCompatibilityMode.BACKWARD,
        )

    with pytest.raises(ValueError):
        DomainSchemaSpec(
            subject="dev.orders-value",
            schema_type=DomainSchemaType.AVRO,
            compatibility=DomainCompatibilityMode.BACKWARD,
            schema='{"type":"record"}',
            source=file_source,
        )

    spec = DomainSchemaSpec(
        subject="dev.orders-value",
        schema_type=DomainSchemaType.AVRO,
        compatibility=DomainCompatibilityMode.BACKWARD,
        source=inline,
        references=(DomainSchemaReference(name="r", subject="dev.ref", version=1),),
    )
    assert spec.environment == DomainEnvironment.DEV
    assert len(spec.fingerprint()) == 16

    with pytest.raises(ValueError):
        DomainSchemaBatch(
            change_id="",
            env=DomainEnvironment.DEV,
            subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
            specs=(spec,),
        )

    with pytest.raises(ValueError):
        DomainSchemaBatch(
            change_id="chg",
            env=DomainEnvironment.DEV,
            subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
            specs=(),
        )

    with pytest.raises(ValueError):
        DomainSchemaBatch(
            change_id="chg",
            env=DomainEnvironment.DEV,
            subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
            specs=(spec, spec),
        )

    prod_spec = DomainSchemaSpec(
        subject="prod.orders-value",
        schema_type=DomainSchemaType.AVRO,
        compatibility=DomainCompatibilityMode.BACKWARD,
        source=inline,
    )
    with pytest.raises(ValueError):
        DomainSchemaBatch(
            change_id="chg",
            env=DomainEnvironment.DEV,
            subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
            specs=(prod_spec,),
        )

    batch = DomainSchemaBatch(
        change_id="chg",
        env=DomainEnvironment.DEV,
        subject_strategy=DomainSubjectStrategy.TOPIC_NAME,
        specs=(spec,),
    )
    assert len(batch.fingerprint()) == 16


def test_schema_utils_and_internal_models() -> None:
    ensure_unique_subjects(["dev.a", "dev.b"])
    with pytest.raises(ValueError):
        ensure_unique_subjects(["dev.a", "dev.a"])

    ref = Reference(name="r", subject="dev.a", version=1)
    assert ref.to_dict() == {"name": "r", "subject": "dev.a", "version": 1}

    info = SchemaVersionInfo(
        version=1,
        schema_id=10,
        schema="{}",
        schema_type="AVRO",
        references=[ref],
        hash="h1",
        canonical_hash="c1",
    )
    assert info.version == 1
    assert info.canonical_hash == "c1"


def test_schema_plan_and_results_paths() -> None:
    diff = DomainSchemaDiff(
        type="update",
        changes=("add field",),
        current_version=1,
        target_compatibility="BACKWARD",
        schema_type="AVRO",
    )
    item_register = DomainSchemaPlanItem(
        subject="dev.a",
        action=DomainPlanAction.REGISTER,
        current_version=None,
        target_version=1,
        diff=diff,
    )
    item_update = DomainSchemaPlanItem(
        subject="dev.b",
        action=DomainPlanAction.UPDATE,
        current_version=1,
        target_version=2,
        diff=diff,
    )
    item_none = DomainSchemaPlanItem(
        subject="dev.c",
        action=DomainPlanAction.NONE,
        current_version=2,
        target_version=2,
        diff=diff,
    )

    compatible = DomainSchemaCompatibilityReport(
        subject="dev.a",
        mode=DomainCompatibilityMode.BACKWARD,
        is_compatible=True,
        issues=(DomainSchemaCompatibilityIssue(path="$.f", message="ok", issue_type="none"),),
    )
    incompatible = DomainSchemaCompatibilityReport(
        subject="dev.b",
        mode=DomainCompatibilityMode.BACKWARD,
        is_compatible=False,
        issues=(),
    )

    warning_violation = DomainPolicyViolation(
        subject="dev.a", rule="r", message="m", severity="warning"
    )
    error_violation = DomainPolicyViolation(
        subject="dev.b", rule="r", message="m", severity="error"
    )

    plan_ok = DomainSchemaPlan(
        change_id="chg",
        env=DomainEnvironment.DEV,
        items=(item_register, item_update, item_none),
        compatibility_reports=(compatible,),
        violations=(warning_violation,),
    )
    summary = plan_ok.summary()
    assert summary["register_count"] == 1
    assert summary["update_count"] == 1
    assert summary["none_count"] == 1
    assert plan_ok.can_apply is True

    plan_bad = DomainSchemaPlan(
        change_id="chg",
        env=DomainEnvironment.DEV,
        items=(item_update,),
        compatibility_reports=(incompatible,),
        violations=(),
    )
    assert plan_bad.can_apply is False

    plan_error = DomainSchemaPlan(
        change_id="chg",
        env=DomainEnvironment.DEV,
        items=(item_update,),
        compatibility_reports=(compatible,),
        violations=(error_violation,),
    )
    assert plan_error.can_apply is False

    with pytest.raises(ValueError):
        DomainSchemaArtifact(subject="dev.a", storage_url=None, version=0)

    artifact = DomainSchemaArtifact(
        subject="file.avro",
        storage_url="s3://bucket/file.avro",
        version=1,
        checksum="abc",
        schema_type=DomainSchemaType.AVRO,
        compatibility_mode=DomainCompatibilityMode.BACKWARD,
        owner="team",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    apply_result = DomainSchemaApplyResult(
        change_id="chg",
        env=DomainEnvironment.DEV,
        registered=("dev.a",),
        skipped=("dev.b",),
        failed=({"subject": "dev.c"},),
        audit_id="audit-1",
        artifacts=(artifact,),
    )
    assert apply_result.summary() == {
        "total_items": 3,
        "registered_count": 1,
        "skipped_count": 1,
        "failed_count": 1,
    }

    upload = DomainSchemaUploadResult(
        upload_id="up-1",
        artifacts=(
            artifact,
            DomainSchemaArtifact(subject="x.json", storage_url=None),
            DomainSchemaArtifact(subject="x.proto", storage_url=None),
        ),
    )
    upload_summary = upload.summary()
    assert upload_summary["total_files"] == 3
    assert upload_summary["avro_count"] == 1
    assert upload_summary["json_count"] == 1
    assert upload_summary["proto_count"] == 1

    impact = DomainSchemaImpactRecord(
        subject="dev.a", topics=("t1",), consumers=("g1",), status="success"
    )
    assert impact.status == "success"
    delete_impact = DomainSchemaDeleteImpact(subject="dev.a", current_version=3, total_versions=3)
    assert delete_impact.safe_to_delete is False
