from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.schema.application.use_cases.management.upload import SchemaUploadUseCase, UploadContext
from app.schema.domain.services import SchemaDeleteAnalyzer
from app.schema.domain.models.plan_result import (
    DomainSchemaDiff,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
)
from app.schema.domain.models.policy import DomainSchemaCompatibilityReport
from app.schema.domain.models.spec_batch import DomainSchemaBatch, DomainSchemaSpec
from app.schema.domain.models.types_enum import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainPlanAction,
    DomainSchemaSourceType,
    DomainSchemaType,
    DomainSubjectStrategy,
)
from app.schema.domain.models.value_objects import DomainSchemaMetadata, DomainSchemaSource
from app.schema.domain.policies.policy_pack import DefaultSchemaPolicyPackV1
from app.schema.interface.routers.governance_router import get_known_topic_names


class FakeKnownTopicNamesUseCase:
    async def execute(self, registry_id: str, subject: str) -> list[str]:
        assert registry_id == "registry-1"
        assert subject == "dev.orders-com.example.Order"
        return ["dev.orders"]


@dataclass
class FakeSubjectInfo:
    version: int


class FakeRegistryRepository:
    async def describe_subjects(
        self, subjects: list[str] | tuple[str, ...]
    ) -> dict[str, FakeSubjectInfo]:
        return {subject: FakeSubjectInfo(version=3) for subject in subjects}


@pytest.mark.asyncio
async def test_known_topic_names_route_returns_flat_response() -> None:
    response = await get_known_topic_names(
        subject="dev.orders-com.example.Order",
        registry_id="registry-1",
        known_topic_names_use_case=FakeKnownTopicNamesUseCase(),
    )

    assert response.subject == "dev.orders-com.example.Order"
    assert response.topic_names == ["dev.orders"]


def test_schema_policy_pack_does_not_emit_topic_link_rules() -> None:
    spec = DomainSchemaSpec(
        subject="dev.orders-com.example.Order",
        schema_type=DomainSchemaType.AVRO,
        compatibility=DomainCompatibilityMode.BACKWARD,
        source=DomainSchemaSource(type=DomainSchemaSourceType.INLINE, inline='{"type":"record"}'),
        metadata=DomainSchemaMetadata(owner="team-data", doc="https://wiki/schema/orders"),
    )
    batch = DomainSchemaBatch(
        change_id="chg-known-topics",
        env=DomainEnvironment.DEV,
        subject_strategy=DomainSubjectStrategy.TOPIC_RECORD_NAME,
        specs=(spec,),
    )
    plan = DomainSchemaPlan(
        change_id="chg-known-topics",
        env=DomainEnvironment.DEV,
        items=(
            DomainSchemaPlanItem(
                subject=spec.subject,
                action=DomainPlanAction.REGISTER,
                current_version=None,
                target_version=1,
                diff=DomainSchemaDiff(
                    type="new_registration",
                    changes=("register schema",),
                    current_version=None,
                    target_compatibility="BACKWARD",
                    schema_type="AVRO",
                ),
            ),
        ),
        compatibility_reports=(
            DomainSchemaCompatibilityReport(
                subject=spec.subject,
                mode=DomainCompatibilityMode.BACKWARD,
                is_compatible=True,
                issues=(),
            ),
        ),
        violations=(),
    )

    evaluation = DefaultSchemaPolicyPackV1().evaluate(batch, plan).evaluation
    codes = {rule.code for rule in evaluation.rules}

    assert "schema.subject.topic_link.invalid" not in codes
    assert "schema.subject.topic_env.mismatch" not in codes


def test_schema_upload_builds_env_prefixed_subject_name() -> None:
    use_case = SchemaUploadUseCase(
        connection_manager=object(),
        metadata_repository=object(),
        audit_repository=object(),
    )
    context = UploadContext(
        registry_repository=object(),
        env=DomainEnvironment.DEV,
        change_id="chg-upload",
        upload_id="upload-1",
        owner="team-data",
        actor="alice",
        compatibility_mode=DomainCompatibilityMode.BACKWARD,
        strategy_id="gov:EnvPrefixed",
    )

    subject = use_case._build_subject_name(context, "orders.avsc", '{"type":"record"}')

    assert subject == "dev.orders"


@pytest.mark.asyncio
async def test_schema_delete_impact_uses_prefix_environment_not_substring() -> None:
    analyzer = SchemaDeleteAnalyzer(FakeRegistryRepository())

    impact = await analyzer.analyze_delete_impact(
        "dev.products-value",
        DomainSubjectStrategy.TOPIC_NAME,
    )

    assert impact.affected_topics == ("dev.products",)
    assert all("프로덕션 환경" not in warning for warning in impact.warnings)
    assert impact.safe_to_delete is True


@pytest.mark.asyncio
async def test_schema_delete_impact_warns_for_true_prod_subject() -> None:
    analyzer = SchemaDeleteAnalyzer(FakeRegistryRepository())

    impact = await analyzer.analyze_delete_impact(
        "prod.orders-value",
        DomainSubjectStrategy.TOPIC_NAME,
    )

    assert any("프로덕션 환경" in warning for warning in impact.warnings)
    assert impact.safe_to_delete is False
