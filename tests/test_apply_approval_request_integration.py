from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import cast

import pytest

import app.schema.application.use_cases.batch.apply as schema_apply_module
from app.infra.kafka.connection_manager import IConnectionManager
from app.schema.application.use_cases.batch.apply import SchemaBatchApplyUseCase
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment as SchemaEnvironment,
    DomainPlanAction as SchemaPlanAction,
    DomainSchemaBatch,
    DomainSchemaCompatibilityReport,
    DomainSchemaDiff,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaSource,
    DomainSchemaSourceType,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSubjectStrategy,
)
from app.schema.domain.policies.policy_pack import DefaultSchemaPolicyPackV1
from app.schema.domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
)
from app.schema.domain.services import SchemaPlannerService
from app.schema.governance_support.use_cases import CreateApprovalRequestUseCase
from app.schema.governance_support.approval import ApprovalRequiredError
from app.shared.database import DatabaseManager
from app.schema.governance_support.infrastructure.repository import SQLApprovalRequestRepository


class _SchemaAuditRepository:
    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

    async def log_operation(self, **kwargs: object) -> None:
        self.entries.append(kwargs)


class _SchemaMetadataRepository:
    async def save_plan(self, plan: object, actor: str) -> None:
        _ = (plan, actor)

    async def save_apply_result(self, result: object, actor: str) -> None:
        _ = (result, actor)

    async def record_artifact(self, artifact: object, change_id: str) -> None:
        _ = (artifact, change_id)


class _SchemaConnectionManager:
    async def get_schema_registry_client(self, registry_id: str) -> object:
        _ = registry_id
        return object()


@pytest.fixture
async def approval_repository(tmp_path: Path) -> AsyncGenerator[SQLApprovalRequestRepository, None]:
    db_path = tmp_path / "apply_approval_requests.db"
    manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
    await manager.initialize()
    await manager.create_tables()
    try:
        yield SQLApprovalRequestRepository(session_factory=manager.get_db_session)
    finally:
        await manager.close()


def _schema_batch() -> DomainSchemaBatch:
    schema_text = '{"type":"record","name":"OrderCreated","fields":[{"name":"status","type":{"type":"enum","name":"Status","symbols":["OPEN"]}}]}'
    spec = DomainSchemaSpec(
        subject="stg.orders.created-value",
        schema_type=DomainSchemaType.AVRO,
        compatibility=DomainCompatibilityMode.BACKWARD,
        source=DomainSchemaSource(
            type=DomainSchemaSourceType.INLINE,
            inline=schema_text,
        ),
        metadata=None,
    )
    return DomainSchemaBatch(
        change_id="chg-schema-approval-auto-001",
        env=SchemaEnvironment.STG,
        subject_strategy=DomainSubjectStrategy.SUBJECT_NAME,
        specs=(spec,),
    )


def _schema_plan(batch: DomainSchemaBatch) -> DomainSchemaPlan:
    spec = batch.specs[0]
    assert spec.source is not None
    schema_text = spec.source.inline
    assert schema_text is not None
    return DomainSchemaPlan(
        change_id=batch.change_id,
        env=batch.env,
        items=(
            DomainSchemaPlanItem(
                subject=spec.subject,
                action=SchemaPlanAction.UPDATE,
                current_version=1,
                target_version=2,
                diff=DomainSchemaDiff(
                    type="update",
                    changes=("narrow enum",),
                    current_version=1,
                    target_compatibility="BACKWARD",
                    schema_type="AVRO",
                ),
                schema=schema_text,
                current_schema='{"type":"record","name":"OrderCreated","fields":[{"name":"status","type":{"type":"enum","name":"Status","symbols":["OPEN","CLOSED"]}}]}',
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
        requested_total=len(batch.specs),
    )


@pytest.mark.asyncio
async def test_schema_apply_creates_approval_request_when_approval_is_required(
    approval_repository: SQLApprovalRequestRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _schema_batch()
    plan = _schema_plan(batch)
    evaluation = DefaultSchemaPolicyPackV1().evaluate(batch, plan).evaluation

    async def fake_create_plan(self: object, batch_arg: DomainSchemaBatch) -> DomainSchemaPlan:
        _ = self
        assert batch_arg.change_id == batch.change_id
        return plan

    def fake_ensure_approval(*args: object, **kwargs: object) -> dict[str, object]:
        _ = (args, kwargs)
        raise ApprovalRequiredError(evaluation)

    monkeypatch.setattr(SchemaPlannerService, "create_plan", fake_create_plan)
    monkeypatch.setattr(schema_apply_module, "ensure_approval", fake_ensure_approval)

    audit_repository = _SchemaAuditRepository()
    use_case = SchemaBatchApplyUseCase(
        connection_manager=cast(IConnectionManager, cast(object, _SchemaConnectionManager())),
        metadata_repository=cast(
            ISchemaMetadataRepository, cast(object, _SchemaMetadataRepository())
        ),
        audit_repository=cast(ISchemaAuditRepository, cast(object, audit_repository)),
        policy_repository=None,
        approval_request_use_case=CreateApprovalRequestUseCase(approval_repository),
    )

    with pytest.raises(ApprovalRequiredError):
        _ = await use_case.execute(
            registry_id="registry-1",
            storage_id=None,
            batch=batch,
            actor="bob",
        )

    requests = await approval_repository.list(status="pending", resource_type="schema")

    assert len(requests) == 1
    assert requests[0].change_ref == batch.change_id
    assert requests[0].metadata is not None
    assert requests[0].metadata["registry_id"] == "registry-1"
    assert requests[0].metadata["requested_items"] == [spec.subject for spec in batch.specs]
    assert audit_repository.entries[-1]["snapshot"] is not None
