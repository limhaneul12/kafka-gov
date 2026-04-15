from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.registry_connections.domain.models.entities import SchemaRegistry
from app.schema.domain.models.plan_result import (
    DomainSchemaDiff,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
)
from app.schema.domain.models.policy import DomainPolicyViolation as SchemaPolicyViolation
from app.schema.domain.models.policy import DomainSchemaCompatibilityReport
from app.schema.domain.models.spec_batch import DomainSchemaBatch, DomainSchemaSpec
from app.schema.domain.models.types_enum import (
    DomainCompatibilityMode,
    DomainEnvironment as SchemaEnvironment,
    DomainPlanAction as SchemaPlanAction,
    DomainSchemaSourceType,
    DomainSchemaType,
    DomainSubjectStrategy,
)
from app.schema.domain.models.value_objects import DomainSchemaSource
from app.shared.approval import ApprovalOverride, assess_schema_batch_risk, ensure_approval


def _fixture_test_value(label: str) -> str:
    return f"test-{label}-placeholder"


class DomainMockFactory:
    @staticmethod
    def schema_registry(*, with_auth: bool = False) -> SchemaRegistry:
        return SchemaRegistry(
            registry_id="registry-a",
            name="registry-a",
            url="http://localhost:8081",
            auth_username="sr-user" if with_auth else None,
            auth_password=_fixture_test_value("schema-registry") if with_auth else None,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

    @staticmethod
    def schema_source_inline(
        schema_text: str = '{"type":"record","name":"Order","fields":[]}',
    ) -> DomainSchemaSource:
        return DomainSchemaSource(type=DomainSchemaSourceType.INLINE, inline=schema_text)

    @staticmethod
    def schema_spec(
        *,
        subject: str = "dev.orders-value",
        compatibility: DomainCompatibilityMode = DomainCompatibilityMode.BACKWARD,
        dry_run_only: bool = False,
    ) -> DomainSchemaSpec:
        return DomainSchemaSpec(
            subject=subject,
            schema_type=DomainSchemaType.AVRO,
            compatibility=compatibility,
            source=DomainMockFactory.schema_source_inline(),
            dry_run_only=dry_run_only,
        )

    @staticmethod
    def schema_batch(
        specs: tuple[DomainSchemaSpec, ...], env: SchemaEnvironment = SchemaEnvironment.DEV
    ) -> DomainSchemaBatch:
        return DomainSchemaBatch(
            change_id="chg-schema-001",
            env=env,
            subject_strategy=DomainSubjectStrategy.SUBJECT_NAME,
            specs=specs,
        )

    @staticmethod
    def schema_plan(*, compatible: bool) -> DomainSchemaPlan:
        item = DomainSchemaPlanItem(
            subject="dev.orders-value",
            action=SchemaPlanAction.UPDATE,
            current_version=1,
            target_version=2,
            diff=DomainSchemaDiff(
                type="update",
                changes=("add field email",),
                current_version=1,
                target_compatibility="BACKWARD",
                schema_type="AVRO",
            ),
            schema='{"type":"record","name":"OrderV2","fields":[]}',
            current_schema='{"type":"record","name":"Order","fields":[]}',
        )
        report = DomainSchemaCompatibilityReport(
            subject="dev.orders-value",
            mode=DomainCompatibilityMode.BACKWARD,
            is_compatible=compatible,
            issues=(),
        )
        violations: tuple[SchemaPolicyViolation, ...] = ()
        return DomainSchemaPlan(
            change_id="plan-schema-001",
            env=SchemaEnvironment.DEV,
            items=(item,),
            compatibility_reports=(report,),
            violations=violations,
        )

    @staticmethod
    def approval_override(hours: int = 1) -> ApprovalOverride:
        return ApprovalOverride(
            reason="Emergency production governance change",
            approver="oncall-platform",
            expires_at=datetime.now(UTC) + timedelta(hours=hours),
        )


@dataclass(slots=True)
class DomainCaseBuilder:
    domain: str
    name: str
    payload: dict[str, Any]

    def build(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "name": self.name,
            **self.payload,
        }


def build_domain_case_matrix() -> dict[str, list[dict[str, Any]]]:
    factory = DomainMockFactory()

    registry_connection_cases = [
        DomainCaseBuilder(
            domain="registry_connections",
            name="schema_registry_client_config_without_auth",
            payload={
                "run": lambda: factory.schema_registry(with_auth=False).to_client_config(),
                "assert": lambda cfg: cfg["url"] == "http://localhost:8081"
                and "basic.auth.user.info" not in cfg,
            },
        ).build(),
        DomainCaseBuilder(
            domain="registry_connections",
            name="schema_registry_client_config_with_auth",
            payload={
                "run": lambda: factory.schema_registry(with_auth=True).to_client_config(),
                "assert": lambda cfg: cfg["basic.auth.user.info"]
                == f"sr-user:{_fixture_test_value('schema-registry')}",
            },
        ).build(),
    ]

    schema_cases = [
        DomainCaseBuilder(
            domain="schema",
            name="schema_source_file_requires_file_reference",
            payload={
                "expect_error": ValueError,
                "run": lambda: DomainSchemaSource(type=DomainSchemaSourceType.FILE),
            },
        ).build(),
        DomainCaseBuilder(
            domain="schema",
            name="schema_batch_env_mismatch_rejected",
            payload={
                "expect_error": ValueError,
                "run": lambda: factory.schema_batch(
                    (factory.schema_spec(subject="prod.orders-value"),),
                    env=SchemaEnvironment.DEV,
                ),
            },
        ).build(),
        DomainCaseBuilder(
            domain="schema",
            name="schema_plan_can_apply_reflects_compatibility",
            payload={
                "run": lambda: (
                    factory.schema_plan(compatible=True).can_apply,
                    factory.schema_plan(compatible=False).can_apply,
                ),
                "assert": lambda result: result == (True, False),
            },
        ).build(),
    ]

    shared_cases = [
        DomainCaseBuilder(
            domain="shared",
            name="ensure_approval_requires_override_for_high_risk",
            payload={
                "expect_error": ValueError,
                "run": lambda: ensure_approval(
                    assess_schema_batch_risk(
                        factory.schema_batch(
                            (
                                factory.schema_spec(
                                    subject="prod.orders-value",
                                    compatibility=DomainCompatibilityMode.NONE,
                                ),
                            ),
                            env=SchemaEnvironment.PROD,
                        ),
                        factory.schema_plan(compatible=True),
                    ),
                    approval_override=None,
                ),
            },
        ).build(),
        DomainCaseBuilder(
            domain="shared",
            name="ensure_approval_accepts_override_for_high_risk",
            payload={
                "run": lambda: ensure_approval(
                    assess_schema_batch_risk(
                        factory.schema_batch(
                            (
                                factory.schema_spec(
                                    subject="prod.orders-value",
                                    compatibility=DomainCompatibilityMode.NONE,
                                ),
                            ),
                            env=SchemaEnvironment.PROD,
                        ),
                        factory.schema_plan(compatible=True),
                    ),
                    approval_override=factory.approval_override(),
                ),
                "assert": lambda payload: payload["risk"]["requires_approval"] is True
                and payload["approval_override"]["approver"] == "oncall-platform",
            },
        ).build(),
    ]

    return {
        "registry_connections": registry_connection_cases,
        "schema": schema_cases,
        "shared": shared_cases,
    }
