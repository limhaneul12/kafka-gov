from __future__ import annotations

from dataclasses import dataclass

from dependency_injector import providers
from fastapi.testclient import TestClient

from app.main import create_app
from app.schema.domain.models import (
    SchemaVersionExport,
    SubjectVersionDetail,
    SubjectVersionList,
    SubjectVersionSummary,
)


@dataclass
class _FakeListVersionsUseCase:
    result: SubjectVersionList

    async def execute(self, registry_id: str, subject: str) -> SubjectVersionList:
        assert registry_id == "registry-1"
        assert subject == "prod.orders-value"
        return self.result


@dataclass
class _FakeGetVersionUseCase:
    result: SubjectVersionDetail

    async def execute(self, registry_id: str, subject: str, version: int) -> SubjectVersionDetail:
        assert registry_id == "registry-1"
        assert subject == "prod.orders-value"
        assert version == 2
        return self.result


@dataclass
class _FakeExportVersionUseCase:
    result: SchemaVersionExport
    latest_result: SchemaVersionExport

    async def execute(self, registry_id: str, subject: str, version: int) -> SchemaVersionExport:
        assert registry_id == "registry-1"
        assert subject == "prod.orders-value"
        assert version == 2
        return self.result

    async def execute_latest(self, registry_id: str, subject: str) -> SchemaVersionExport:
        assert registry_id == "registry-1"
        assert subject == "prod.orders-value"
        return self.latest_result


def _build_client() -> tuple[TestClient, object]:
    app = create_app()
    return TestClient(app), app.state.container


def test_schema_version_routes_are_registered() -> None:
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/v1/schemas/subjects/{subject}/versions" in paths
    assert "/api/v1/schemas/subjects/{subject}/versions/{version}" in paths
    assert "/api/v1/schemas/subjects/{subject}/versions/{version}/export" in paths
    assert "/api/v1/schemas/subjects/{subject}/export" in paths


def test_list_schema_versions_route_returns_versions() -> None:
    client, container = _build_client()
    fake_use_case = _FakeListVersionsUseCase(
        result=SubjectVersionList(
            subject="prod.orders-value",
            versions=[
                SubjectVersionSummary(
                    version=2,
                    schema_id=102,
                    schema_type="AVRO",
                    hash="hash-2",
                    canonical_hash="canonical-2",
                    created_at="2026-04-25T10:00:00Z",
                    author="schema-admin",
                    commit_message="Add status",
                )
            ],
        )
    )
    container.schema_container.schema_versions_use_case.override(providers.Object(fake_use_case))

    try:
        response = client.get(
            "/api/v1/schemas/subjects/prod.orders-value/versions",
            params={"registry_id": "registry-1"},
        )
    finally:
        container.schema_container.schema_versions_use_case.reset_override()
        client.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["subject"] == "prod.orders-value"
    assert payload["versions"][0]["version"] == 2
    assert payload["versions"][0]["canonical_hash"] == "canonical-2"


def test_get_schema_version_route_returns_exact_version() -> None:
    client, container = _build_client()
    fake_use_case = _FakeGetVersionUseCase(
        result=SubjectVersionDetail(
            subject="prod.orders-value",
            version=2,
            schema_id=102,
            schema_str='{"type":"record","name":"Order","fields":[]}',
            schema_type="AVRO",
            hash="hash-2",
            canonical_hash="canonical-2",
            references=[
                {"name": "common.Customer", "subject": "prod.customer-value", "version": 1}
            ],
            owner="team-order",
            compatibility_mode="BACKWARD",
            created_at="2026-04-25T10:00:00Z",
            author="schema-admin",
            commit_message="Add status",
        )
    )
    container.schema_container.schema_version_use_case.override(providers.Object(fake_use_case))

    try:
        response = client.get(
            "/api/v1/schemas/subjects/prod.orders-value/versions/2",
            params={"registry_id": "registry-1"},
        )
    finally:
        container.schema_container.schema_version_use_case.reset_override()
        client.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 2
    assert payload["owner"] == "team-order"
    assert payload["references"][0]["name"] == "common.Customer"


def test_export_routes_return_download_headers() -> None:
    client, container = _build_client()
    fake_use_case = _FakeExportVersionUseCase(
        result=SchemaVersionExport(
            subject="prod.orders-value",
            version=2,
            schema_type="AVRO",
            filename="prod.orders-value.v2.avsc",
            media_type="application/json",
            schema_str='{"type":"record","name":"Order","fields":[]}',
        ),
        latest_result=SchemaVersionExport(
            subject="prod.orders-value",
            version=3,
            schema_type="AVRO",
            filename="prod.orders-value.v3.avsc",
            media_type="application/json",
            schema_str='{"type":"record","name":"Order","fields":[{"name":"status","type":"string"}]}',
        ),
    )
    container.schema_container.export_schema_version_use_case.override(
        providers.Object(fake_use_case)
    )

    try:
        response_version = client.get(
            "/api/v1/schemas/subjects/prod.orders-value/versions/2/export",
            params={"registry_id": "registry-1"},
        )
        response_latest = client.get(
            "/api/v1/schemas/subjects/prod.orders-value/export",
            params={"registry_id": "registry-1"},
        )
    finally:
        container.schema_container.export_schema_version_use_case.reset_override()
        client.close()

    assert response_version.status_code == 200
    assert (
        response_version.headers["content-disposition"]
        == 'attachment; filename="prod.orders-value.v2.avsc"'
    )
    assert response_version.text == '{"type":"record","name":"Order","fields":[]}'

    assert response_latest.status_code == 200
    assert (
        response_latest.headers["content-disposition"]
        == 'attachment; filename="prod.orders-value.v3.avsc"'
    )
    assert "status" in response_latest.text
