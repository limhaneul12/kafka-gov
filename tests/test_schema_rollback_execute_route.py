from __future__ import annotations

from dataclasses import dataclass

from dependency_injector import providers
from fastapi.testclient import TestClient

from app.main import create_app
from app.schema.domain.models import (
    DomainEnvironment,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
)


@dataclass
class _FakeExecuteRollbackUseCase:
    result: DomainSchemaApplyResult

    async def execute(
        self,
        registry_id: str,
        subject: str,
        version: int,
        actor: str,
        approval_override: object | None = None,
        reason: str | None = None,
        actor_context: dict[str, str] | None = None,
    ) -> DomainSchemaApplyResult:
        assert registry_id == "registry-1"
        assert subject == "prod.orders-value"
        assert version == 1
        assert actor == "system"
        assert reason == "Rollback to v1"
        assert approval_override is not None
        assert actor_context is not None
        return self.result


def test_execute_schema_rollback_route_returns_apply_response() -> None:
    app = create_app()
    container = app.state.container
    client = TestClient(app)
    fake_use_case = _FakeExecuteRollbackUseCase(
        result=DomainSchemaApplyResult(
            change_id="rollback_prod.orders-value_1_123456",
            env=DomainEnvironment.PROD,
            registered=("prod.orders-value",),
            skipped=(),
            failed=(),
            audit_id="audit-1",
            artifacts=(
                DomainSchemaArtifact(
                    subject="prod.orders-value",
                    version=3,
                    storage_url=None,
                    checksum="checksum-1",
                ),
            ),
        )
    )
    container.schema_container.execute_rollback_use_case.override(providers.Object(fake_use_case))

    try:
        response = client.post(
            "/api/v1/schemas/rollback/execute",
            params={"registry_id": "registry-1"},
            json={
                "subject": "prod.orders-value",
                "version": 1,
                "reason": "Rollback to v1",
                "approvalOverride": {
                    "reason": "approved rollback",
                    "approver": "schema-admin",
                    "expiresAt": "2027-03-11T00:00:00.000Z",
                },
            },
        )
    finally:
        container.schema_container.execute_rollback_use_case.reset_override()
        client.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["registered"] == ["prod.orders-value"]
    assert payload["artifacts"][0]["version"] == 3
    assert payload["summary"]["registered_count"] == 1
