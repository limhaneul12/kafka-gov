from __future__ import annotations

from dataclasses import dataclass

from dependency_injector import providers
from fastapi.testclient import TestClient

from app.main import create_app
from app.schema.domain.models import (
    DomainEnvironment,
    DomainPlanAction,
    DomainSchemaDiff,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
)


@dataclass
class _FakeRollbackUseCase:
    result: DomainSchemaPlan

    async def execute(
        self,
        *,
        registry_id: str,
        subject: str,
        version: int,
        actor: str,
        reason: str | None = None,
        actor_context: dict[str, str] | None = None,
    ) -> DomainSchemaPlan:
        assert registry_id == "registry-1"
        assert subject == "prod.orders-value"
        assert version == 1
        assert actor == "system"
        assert reason == "Rollback to v1"
        assert actor_context is not None
        return self.result


def test_plan_schema_rollback_route_serializes_schema_field() -> None:
    app = create_app()
    container = app.state.container
    client = TestClient(app)
    container.schema_container.rollback_use_case.override(
        providers.Object(
            _FakeRollbackUseCase(
                result=DomainSchemaPlan(
                    change_id="rollback_prod.orders-value_1_123456",
                    env=DomainEnvironment.PROD,
                    items=(
                        DomainSchemaPlanItem(
                            subject="prod.orders-value",
                            action=DomainPlanAction.UPDATE,
                            current_version=2,
                            target_version=3,
                            diff=DomainSchemaDiff(
                                type="update",
                                changes=("Rollback to previous version",),
                                current_version=2,
                                target_compatibility="BACKWARD",
                                schema_type="AVRO",
                            ),
                            schema='{"type":"record","name":"Order","fields":[]}',
                            current_schema='{"type":"record","name":"Order","fields":[{"name":"status","type":"string"}]}',
                            reason="Rollback to v1",
                        ),
                    ),
                )
            )
        )
    )
    try:
        response = client.post(
            "/api/v1/schemas/rollback/plan",
            params={"registry_id": "registry-1"},
            json={
                "subject": "prod.orders-value",
                "version": 1,
                "reason": "Rollback to v1",
            },
        )
    finally:
        container.schema_container.rollback_use_case.reset_override()
        client.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan"][0]["schema"] == '{"type":"record","name":"Order","fields":[]}'
    assert "schema_definition" not in payload["plan"][0]
