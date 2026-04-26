from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.routing import APIRoute

import app.schema.application.use_cases.management.upload as upload_module
from app.main import create_app
from app.schema.application.use_cases.management.upload import SchemaUploadUseCase
from app.schema.domain.models.types_enum.enums import DomainEnvironment


class _FakeUploadFile:
    def __init__(
        self, filename: str, content: bytes, content_type: str = "application/json"
    ) -> None:
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content


@dataclass
class _FakeConnectionManager:
    async def get_schema_registry_client(self, registry_id: str) -> object:
        assert registry_id == "registry-1"
        return object()


@dataclass
class _FakeMetadataRepository:
    record_artifact_calls: int = 0
    save_metadata_calls: int = 0
    save_upload_result_calls: int = 0

    async def record_artifact(self, artifact, change_id) -> None:
        self.record_artifact_calls += 1

    async def save_schema_metadata(self, subject, metadata) -> None:
        self.save_metadata_calls += 1

    async def save_upload_result(self, upload, uploaded_by) -> None:
        self.save_upload_result_calls += 1


@dataclass
class _FakeAuditRepository:
    async def log_operation(self, **kwargs) -> str:
        return "audit-id"


class _FakeFailingRegistryAdapter:
    def __init__(self, client: object) -> None:
        self.client = client

    async def register_schema(self, spec):
        raise RuntimeError("registry unavailable")

    async def set_compatibility_mode(self, subject: str, mode: str) -> None:
        return None


@pytest.mark.asyncio
async def test_upload_fails_without_persisting_artifact_on_registry_error(monkeypatch) -> None:
    metadata_repository = _FakeMetadataRepository()
    use_case = SchemaUploadUseCase(
        connection_manager=_FakeConnectionManager(),
        metadata_repository=metadata_repository,  # type: ignore[arg-type]
        audit_repository=_FakeAuditRepository(),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        upload_module, "ConfluentSchemaRegistryAdapter", _FakeFailingRegistryAdapter
    )

    with pytest.raises(RuntimeError, match="Schema Registry registration failed"):
        await use_case.execute(
            registry_id="registry-1",
            storage_id=None,
            env=DomainEnvironment.DEV,
            change_id="chg-1",
            owner="team-data",
            files=[_FakeUploadFile("order.avsc", b'{"type":"record","name":"Order","fields":[]}')],
            actor="alice",
            compatibility_mode=upload_module.DomainCompatibilityMode.BACKWARD,
        )

    assert metadata_repository.record_artifact_calls == 0
    assert metadata_repository.save_metadata_calls == 0
    assert metadata_repository.save_upload_result_calls == 0


def test_upload_route_no_longer_advertises_zip_bundles() -> None:
    app = create_app()
    upload_route = next(
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path == "/api/v1/schemas/upload"
    )

    assert upload_route.description is not None
    assert ".zip" not in upload_route.description.lower()


@pytest.mark.asyncio
async def test_zip_upload_is_rejected_as_unsupported_file_type() -> None:
    use_case = SchemaUploadUseCase(
        connection_manager=_FakeConnectionManager(),
        metadata_repository=_FakeMetadataRepository(),  # type: ignore[arg-type]
        audit_repository=_FakeAuditRepository(),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match=r"Unsupported file type: \.zip"):
        await use_case.execute(
            registry_id="registry-1",
            storage_id=None,
            env=DomainEnvironment.DEV,
            change_id="chg-zip",
            owner="team-data",
            files=[_FakeUploadFile("bundle.zip", b"fake-zip-content", "application/zip")],
            actor="alice",
            compatibility_mode=upload_module.DomainCompatibilityMode.BACKWARD,
        )


@pytest.mark.asyncio
async def test_upload_requires_explicit_compatibility_mode() -> None:
    use_case = SchemaUploadUseCase(
        connection_manager=_FakeConnectionManager(),
        metadata_repository=_FakeMetadataRepository(),  # type: ignore[arg-type]
        audit_repository=_FakeAuditRepository(),  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="Compatibility mode must be explicitly provided"):
        await use_case.execute(
            registry_id="registry-1",
            storage_id=None,
            env=DomainEnvironment.DEV,
            change_id="chg-missing-compat",
            owner="team-data",
            files=[_FakeUploadFile("order.avsc", b'{"type":"record","name":"Order","fields":[]}')],
            actor="alice",
        )
