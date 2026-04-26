from __future__ import annotations

from dataclasses import dataclass

from dependency_injector import providers
from fastapi.testclient import TestClient

from app.main import create_app
from app.schema.domain.models import SubjectVersionComparison


@dataclass
class _FakeCompareVersionsUseCase:
    result: SubjectVersionComparison

    async def execute(
        self,
        registry_id: str,
        subject: str,
        from_version: int,
        to_version: int,
    ) -> SubjectVersionComparison:
        assert registry_id == "registry-1"
        assert subject == "prod.orders-value"
        assert from_version == 1
        assert to_version == 2
        return self.result


def test_compare_schema_versions_route_returns_comparison() -> None:
    app = create_app()
    container = app.state.container
    client = TestClient(app)
    container.schema_container.compare_schema_versions_use_case.override(
        providers.Object(
            _FakeCompareVersionsUseCase(
                result=SubjectVersionComparison(
                    subject="prod.orders-value",
                    from_version=1,
                    to_version=2,
                    changed=True,
                    diff_type="update",
                    changes=["Added field: status"],
                    schema_type="AVRO",
                    compatibility_mode="BACKWARD",
                    from_schema='{"type":"record","name":"Order","fields":[]}',
                    to_schema='{"type":"record","name":"Order","fields":[{"name":"status","type":"string"}]}',
                )
            )
        )
    )

    try:
        response = client.get(
            "/api/v1/schemas/subjects/prod.orders-value/compare",
            params={"registry_id": "registry-1", "from_version": 1, "to_version": 2},
        )
    finally:
        container.schema_container.compare_schema_versions_use_case.reset_override()
        client.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["changed"] is True
    assert payload["changes"] == ["Added field: status"]
    assert payload["from_version"] == 1
    assert payload["to_version"] == 2
