from __future__ import annotations

from dataclasses import dataclass

from dependency_injector import providers
from fastapi.testclient import TestClient

from app.main import create_app
from app.schema.application.use_cases.management.settings import SchemaSettingsResult


@dataclass
class _FakeUpdateSchemaSettingsUseCase:
    result: SchemaSettingsResult

    async def execute(
        self,
        *,
        registry_id: str,
        subject: str,
        actor: str,
        owner: str | None = None,
        doc: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
        compatibility_mode: str | None = None,
        actor_context: dict[str, str] | None = None,
    ) -> SchemaSettingsResult:
        assert registry_id == "registry-1"
        assert subject == "prod.orders-value"
        assert actor == "system"
        assert owner == "team-updated"
        assert doc == "https://docs.example/schema"
        assert tags == ["pii", "critical"]
        assert description == "Updated schema metadata"
        assert compatibility_mode == "FULL"
        assert actor_context is not None
        return self.result


def test_update_schema_settings_route_returns_updated_metadata() -> None:
    app = create_app()
    container = app.state.container
    client = TestClient(app)
    container.schema_container.update_schema_settings_use_case.override(
        providers.Object(
            _FakeUpdateSchemaSettingsUseCase(
                result=SchemaSettingsResult(
                    subject="prod.orders-value",
                    owner="team-updated",
                    doc="https://docs.example/schema",
                    tags=["pii", "critical"],
                    description="Updated schema metadata",
                    compatibility_mode="FULL",
                )
            )
        )
    )
    try:
        response = client.patch(
            "/api/v1/schemas/settings/prod.orders-value",
            params={"registry_id": "registry-1"},
            json={
                "owner": "team-updated",
                "doc": "https://docs.example/schema",
                "tags": ["pii", "critical"],
                "description": "Updated schema metadata",
                "compatibilityMode": "FULL",
            },
        )
    finally:
        container.schema_container.update_schema_settings_use_case.reset_override()
        client.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["owner"] == "team-updated"
    assert payload["compatibility_mode"] == "FULL"
    assert payload["tags"] == ["pii", "critical"]
