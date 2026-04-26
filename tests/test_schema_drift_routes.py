from __future__ import annotations

from dataclasses import dataclass

from dependency_injector import providers
from fastapi.testclient import TestClient

from app.main import create_app
from app.schema.domain.models import SubjectDriftReport


@dataclass
class _FakeDriftUseCase:
    result: SubjectDriftReport

    async def execute(self, registry_id: str, subject: str) -> SubjectDriftReport:
        assert registry_id == "registry-1"
        assert subject == "prod.orders-value"
        return self.result


def test_schema_drift_route_returns_report() -> None:
    app = create_app()
    container = app.state.container
    client = TestClient(app)
    container.schema_container.schema_drift_use_case.override(
        providers.Object(
            _FakeDriftUseCase(
                result=SubjectDriftReport(
                    subject="prod.orders-value",
                    registry_latest_version=3,
                    registry_canonical_hash="registry-hash",
                    catalog_latest_version=2,
                    catalog_canonical_hash="catalog-hash",
                    observed_version=1,
                    last_synced_at="2026-04-25T12:00:00Z",
                    drift_flags=[
                        "catalog_snapshot_version_mismatch",
                        "observed_usage_on_non_latest_version",
                    ],
                    has_drift=True,
                )
            )
        )
    )
    try:
        response = client.get(
            "/api/v1/schemas/drift/prod.orders-value",
            params={"registry_id": "registry-1"},
        )
    finally:
        container.schema_container.schema_drift_use_case.reset_override()
        client.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_drift"] is True
    assert payload["registry_latest_version"] == 3
    assert "catalog_snapshot_version_mismatch" in payload["drift_flags"]
