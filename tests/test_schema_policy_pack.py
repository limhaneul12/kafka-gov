from __future__ import annotations

from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainPlanAction,
    DomainSchemaBatch,
    DomainSchemaCompatibilityIssue,
    DomainSchemaCompatibilityReport,
    DomainSchemaDiff,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaSpec,
    DomainSchemaSource,
    DomainSchemaSourceType,
    DomainSchemaType,
    DomainSubjectStrategy,
)
from app.schema.domain.policies.policy_pack import DefaultSchemaPolicyPackV1


def _build_plan(
    *,
    env: DomainEnvironment,
    compatibility_report: DomainSchemaCompatibilityReport,
) -> DomainSchemaPlan:
    return DomainSchemaPlan(
        change_id="chg-policy-pack",
        env=env,
        items=(
            DomainSchemaPlanItem(
                subject="prod.orders-value",
                action=DomainPlanAction.UPDATE,
                current_version=1,
                target_version=2,
                diff=DomainSchemaDiff(
                    type="update",
                    changes=("added optional status field",),
                    current_version=1,
                    target_compatibility=compatibility_report.mode.value,
                    schema_type="AVRO",
                ),
                current_schema='{"type":"record","name":"Order","fields":[{"name":"id","type":"string"}]}',
                schema='{"type":"record","name":"Order","fields":[{"name":"id","type":"string"},{"name":"status","type":["null","string"],"default":null}]}',
            ),
        ),
        compatibility_reports=(compatibility_report,),
        violations=(),
    )


def test_policy_pack_flags_prod_none_and_missing_metadata() -> None:
    batch = DomainSchemaBatch(
        change_id="chg-policy-pack",
        env=DomainEnvironment.PROD,
        subject_strategy=DomainSubjectStrategy.SUBJECT_NAME,
        specs=(
            DomainSchemaSpec(
                subject="prod.orders-value",
                schema_type=DomainSchemaType.AVRO,
                compatibility=DomainCompatibilityMode.NONE,
                source=DomainSchemaSource(
                    type=DomainSchemaSourceType.INLINE,
                    inline='{"type":"record","name":"Order","fields":[{"name":"id","type":"string"}]}',
                ),
            ),
        ),
    )
    plan = _build_plan(
        env=DomainEnvironment.PROD,
        compatibility_report=DomainSchemaCompatibilityReport(
            subject="prod.orders-value",
            mode=DomainCompatibilityMode.NONE,
            is_compatible=True,
        ),
    )

    result = DefaultSchemaPolicyPackV1().evaluate(batch, plan)
    rule_codes = {rule.code for rule in result.evaluation.rules}

    assert "schema.compatibility.none.forbidden" in rule_codes
    assert "schema.metadata.missing" in rule_codes


def test_policy_pack_emits_backward_incompatibility_rule() -> None:
    batch = DomainSchemaBatch(
        change_id="chg-policy-pack",
        env=DomainEnvironment.STG,
        subject_strategy=DomainSubjectStrategy.SUBJECT_NAME,
        specs=(
            DomainSchemaSpec(
                subject="stg.orders-value",
                schema_type=DomainSchemaType.AVRO,
                compatibility=DomainCompatibilityMode.BACKWARD,
                source=DomainSchemaSource(
                    type=DomainSchemaSourceType.INLINE,
                    inline='{"type":"record","name":"Order","fields":[{"name":"id","type":"string"}]}',
                ),
            ),
        ),
    )
    plan = DomainSchemaPlan(
        change_id="chg-policy-pack",
        env=DomainEnvironment.STG,
        items=(
            DomainSchemaPlanItem(
                subject="stg.orders-value",
                action=DomainPlanAction.UPDATE,
                current_version=1,
                target_version=2,
                diff=DomainSchemaDiff(
                    type="update",
                    changes=("remove required id field",),
                    current_version=1,
                    target_compatibility="BACKWARD",
                    schema_type="AVRO",
                ),
                current_schema='{"type":"record","name":"Order","fields":[{"name":"id","type":"string"}]}',
                schema='{"type":"record","name":"Order","fields":[]}',
            ),
        ),
        compatibility_reports=(
            DomainSchemaCompatibilityReport(
                subject="stg.orders-value",
                mode=DomainCompatibilityMode.BACKWARD,
                is_compatible=False,
                issues=(
                    DomainSchemaCompatibilityIssue(
                        path="$.fields[0]",
                        message="required field removed",
                        issue_type="field_removed",
                    ),
                ),
            ),
        ),
        violations=(),
    )

    result = DefaultSchemaPolicyPackV1().evaluate(batch, plan)

    assert any(
        rule.code == "schema.compatibility.backward_incompatible"
        for rule in result.evaluation.rules
    )
    assert any(
        violation.rule == "schema.compatibility.backward_incompatible"
        for violation in result.violations
    )
