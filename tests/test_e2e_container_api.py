from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
import requests

SCHEMA_REGISTRY_E2E_URL = os.getenv("E2E_SCHEMA_REGISTRY_URL", "http://schema-registry:8081")


def _upload_schema_version(
    backend_base_url: str,
    *,
    registry_id: str,
    schema_slug: str,
    schema: dict[str, object],
    change_id: str,
    owner: str = "team-e2e",
    compatibility_mode: str = "BACKWARD",
) -> requests.Response:
    return requests.post(
        f"{backend_base_url}/api/v1/schemas/upload",
        params={"registry_id": registry_id},
        data={
            "env": "dev",
            "change_id": change_id,
            "owner": owner,
            "compatibility_mode": compatibility_mode,
            "strategy_id": "gov:EnvPrefixed",
        },
        files={
            "files": (
                f"{schema_slug}.avsc",
                json.dumps(schema),
                "application/json",
            )
        },
        timeout=30,
    )


def _wait_for_json(
    *,
    method: str,
    url: str,
    expected: Callable[[dict[str, Any]], bool],
    timeout_sec: float = 10.0,
    interval_sec: float = 0.5,
    **request_kwargs: object,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_sec
    last_payload: dict[str, Any] | None = None

    while time.monotonic() < deadline:
        response = requests.request(method, url, timeout=20, **request_kwargs)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert isinstance(payload, dict)
        last_payload = payload
        if expected(payload):
            return payload
        time.sleep(interval_sec)

    raise AssertionError(f"Timed out waiting for expected payload from {url}: {last_payload}")


@pytest.mark.e2e
def test_e2e_api_info_and_health(backend_base_url: str) -> None:
    health = requests.get(f"{backend_base_url}/health", timeout=15)
    api_info = requests.get(f"{backend_base_url}/api/v1", timeout=15)

    assert health.status_code == 200
    assert health.json() == {"status": "healthy"}
    assert api_info.status_code == 200
    assert api_info.json()["message"] == "Data Governance API"


@pytest.mark.e2e
def test_e2e_schema_registry_crud_and_connection_test(backend_base_url: str) -> None:
    base = f"{backend_base_url}/api/v1/schema-registries"
    registry_id = f"e2e-reg-{uuid4().hex[:8]}"

    create = requests.post(
        base,
        json={
            "registry_id": registry_id,
            "name": "E2E Registry",
            "url": SCHEMA_REGISTRY_E2E_URL,
        },
        timeout=20,
    )
    assert create.status_code == 201
    assert create.json()["registry_id"] == registry_id

    list_resp = requests.get(f"{base}?active_only=false", timeout=20)
    assert list_resp.status_code == 200
    assert any(item["registry_id"] == registry_id for item in list_resp.json())

    test_resp = requests.post(f"{base}/{registry_id}/test", timeout=20)
    assert test_resp.status_code == 200
    test_payload = test_resp.json()
    assert isinstance(test_payload["success"], bool)
    assert isinstance(test_payload["message"], str)

    activate_resp = requests.patch(f"{base}/{registry_id}/activate", timeout=20)
    assert activate_resp.status_code == 200
    assert activate_resp.json()["is_active"] is True

    delete_resp = requests.delete(f"{base}/{registry_id}", timeout=20)
    assert delete_resp.status_code == 204


def _create_schema_registry(backend_base_url: str, registry_id: str) -> None:
    create = requests.post(
        f"{backend_base_url}/api/v1/schema-registries",
        json={
            "registry_id": registry_id,
            "name": f"E2E Registry {registry_id}",
            "url": SCHEMA_REGISTRY_E2E_URL,
        },
        timeout=20,
    )
    if create.status_code != 201:
        pytest.skip(f"schema registry stack unavailable for container e2e: {create.text}")

    test_resp = requests.post(
        f"{backend_base_url}/api/v1/schema-registries/{registry_id}/test",
        timeout=20,
    )
    if test_resp.status_code != 200:
        pytest.skip(f"schema registry test endpoint unavailable: {test_resp.text}")

    payload = test_resp.json()
    if payload.get("success") is not True:
        pytest.skip(f"schema registry connection not ready: {payload}")


@pytest.mark.e2e
def test_e2e_schema_registry_governance_routes_against_live_registry(backend_base_url: str) -> None:
    registry_id = f"e2e-reg-live-{uuid4().hex[:8]}"
    schema_slug = f"orders_e2e_{uuid4().hex[:8]}"
    subject = f"dev.{schema_slug}"
    schema = {
        "type": "record",
        "name": "OrderE2E",
        "namespace": "dev.e2e",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "status", "type": ["null", "string"], "default": None},
        ],
    }

    try:
        _create_schema_registry(backend_base_url, registry_id)

        upload = _upload_schema_version(
            backend_base_url,
            registry_id=registry_id,
            schema_slug=schema_slug,
            schema=schema,
            change_id=f"chg-{schema_slug}",
        )
        assert upload.status_code == 201, upload.text
        assert upload.json()["artifacts"][0]["subject"] == subject

        search = requests.get(
            f"{backend_base_url}/api/v1/schemas/search",
            params={"query": subject, "limit": 10},
            timeout=20,
        )
        assert search.status_code == 200, search.text
        assert any(item["subject"] == subject for item in search.json()["items"])

        detail = requests.get(
            f"{backend_base_url}/api/v1/schemas/detail/{subject}",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["subject"] == subject

        versions = requests.get(
            f"{backend_base_url}/api/v1/schemas/subjects/{subject}/versions",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert versions.status_code == 200, versions.text
        latest_version = versions.json()["versions"][0]["version"]
        assert latest_version >= 1

        compare = requests.get(
            f"{backend_base_url}/api/v1/schemas/subjects/{subject}/compare",
            params={
                "registry_id": registry_id,
                "from_version": latest_version,
                "to_version": latest_version,
            },
            timeout=20,
        )
        assert compare.status_code == 200, compare.text
        assert compare.json()["changed"] is False

        export = requests.get(
            f"{backend_base_url}/api/v1/schemas/subjects/{subject}/export",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert export.status_code == 200, export.text
        assert "attachment" in export.headers["content-disposition"]
        assert json.loads(export.text)["name"] == "OrderE2E"

        zip_upload = requests.post(
            f"{backend_base_url}/api/v1/schemas/upload",
            params={"registry_id": registry_id},
            data={
                "env": "dev",
                "change_id": f"chg-zip-{uuid4().hex[:8]}",
                "owner": "team-e2e",
                "compatibility_mode": "BACKWARD",
                "strategy_id": "gov:EnvPrefixed",
            },
            files={"files": ("bundle.zip", b"not-a-real-zip", "application/zip")},
            timeout=30,
        )
        assert zip_upload.status_code in {400, 422}, zip_upload.text
        assert "Unsupported file type" in zip_upload.text
    finally:
        requests.delete(
            f"{backend_base_url}/api/v1/schemas/delete/{subject}",
            params={"registry_id": registry_id, "force": "true"},
            timeout=20,
        )
        requests.delete(f"{backend_base_url}/api/v1/schema-registries/{registry_id}", timeout=20)


@pytest.mark.e2e
def test_e2e_schema_registry_version_lifecycle_and_settings_against_live_registry(
    backend_base_url: str,
) -> None:
    registry_id = f"e2e-reg-lifecycle-{uuid4().hex[:8]}"
    schema_slug = f"orders_lifecycle_{uuid4().hex[:8]}"
    subject = f"dev.{schema_slug}"
    v1_schema = {
        "type": "record",
        "name": "OrderLifecycleE2E",
        "namespace": "dev.e2e",
        "fields": [
            {"name": "id", "type": "string"},
        ],
    }
    v2_schema = {
        "type": "record",
        "name": "OrderLifecycleE2E",
        "namespace": "dev.e2e",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "status", "type": ["null", "string"], "default": None},
        ],
    }

    try:
        _create_schema_registry(backend_base_url, registry_id)

        upload_v1 = _upload_schema_version(
            backend_base_url,
            registry_id=registry_id,
            schema_slug=schema_slug,
            schema=v1_schema,
            change_id=f"chg-{schema_slug}-v1",
        )
        assert upload_v1.status_code == 201, upload_v1.text

        upload_v2 = _upload_schema_version(
            backend_base_url,
            registry_id=registry_id,
            schema_slug=schema_slug,
            schema=v2_schema,
            change_id=f"chg-{schema_slug}-v2",
        )
        assert upload_v2.status_code == 201, upload_v2.text

        history = requests.get(
            f"{backend_base_url}/api/v1/schemas/history/{subject}",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert history.status_code == 200, history.text
        history_payload = history.json()
        assert history_payload["subject"] == subject
        assert len(history_payload["history"]) >= 2

        versions = requests.get(
            f"{backend_base_url}/api/v1/schemas/subjects/{subject}/versions",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert versions.status_code == 200, versions.text
        versions_payload = versions.json()
        assert [item["version"] for item in versions_payload["versions"][:2]] == [2, 1]

        version_one = requests.get(
            f"{backend_base_url}/api/v1/schemas/subjects/{subject}/versions/1",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert version_one.status_code == 200, version_one.text
        assert version_one.json()["version"] == 1

        compare = requests.get(
            f"{backend_base_url}/api/v1/schemas/subjects/{subject}/compare",
            params={"registry_id": registry_id, "from_version": 1, "to_version": 2},
            timeout=20,
        )
        assert compare.status_code == 200, compare.text
        compare_payload = compare.json()
        assert compare_payload["changed"] is True
        assert compare_payload["from_version"] == 1
        assert compare_payload["to_version"] == 2
        assert compare_payload["changes"]

        export_v1 = requests.get(
            f"{backend_base_url}/api/v1/schemas/subjects/{subject}/versions/1/export",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert export_v1.status_code == 200, export_v1.text
        assert json.loads(export_v1.text)["fields"] == [{"name": "id", "type": "string"}]

        drift_payload = _wait_for_json(
            method="GET",
            url=f"{backend_base_url}/api/v1/schemas/drift/{subject}",
            params={"registry_id": registry_id},
            expected=lambda payload: int(payload["registry_latest_version"]) >= 2,
        )
        assert drift_payload["subject"] == subject
        assert drift_payload["registry_latest_version"] >= 2

        settings = requests.patch(
            f"{backend_base_url}/api/v1/schemas/settings/{subject}",
            params={"registry_id": registry_id},
            json={
                "owner": "team-governance",
                "doc": "https://docs.example/order-lifecycle",
                "tags": ["golden", "customer-facing"],
                "description": "Lifecycle QA subject",
                "compatibilityMode": "FULL",
            },
            timeout=20,
        )
        assert settings.status_code == 200, settings.text
        settings_payload = settings.json()
        assert settings_payload["owner"] == "team-governance"
        assert settings_payload["compatibility_mode"] == "FULL"

        detail = requests.get(
            f"{backend_base_url}/api/v1/schemas/detail/{subject}",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert detail.status_code == 200, detail.text
        detail_payload = detail.json()
        assert detail_payload["owner"] == "team-governance"
        assert detail_payload["doc"] == "https://docs.example/order-lifecycle"
        assert detail_payload["description"] == "Lifecycle QA subject"

        rollback_plan = requests.post(
            f"{backend_base_url}/api/v1/schemas/rollback/plan",
            params={"registry_id": registry_id},
            json={
                "subject": subject,
                "version": 1,
                "reason": "Revert lifecycle test subject to v1",
            },
            timeout=20,
        )
        assert rollback_plan.status_code == 200, rollback_plan.text
        assert rollback_plan.json()["plan"][0]["subject"] == subject

        rollback_execute = requests.post(
            f"{backend_base_url}/api/v1/schemas/rollback/execute",
            params={"registry_id": registry_id},
            json={
                "subject": subject,
                "version": 1,
                "reason": "Execute lifecycle rollback",
                "approvalOverride": {
                    "reason": "container e2e rollback approval",
                    "approver": "schema-admin",
                    "expiresAt": "2027-04-30T00:00:00.000Z",
                },
            },
            timeout=30,
        )
        assert rollback_execute.status_code == 200, rollback_execute.text
        rollback_payload = rollback_execute.json()
        assert subject in rollback_payload["registered"]
        assert rollback_payload["artifacts"][0]["version"] == 1

        versions_after_rollback = _wait_for_json(
            method="GET",
            url=f"{backend_base_url}/api/v1/schemas/subjects/{subject}/versions",
            params={"registry_id": registry_id},
            expected=lambda payload: bool(payload["versions"])
            and int(payload["versions"][0]["version"]) == 1,
        )
        assert versions_after_rollback["versions"][0]["version"] == 1

        latest_export = requests.get(
            f"{backend_base_url}/api/v1/schemas/subjects/{subject}/export",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert latest_export.status_code == 200, latest_export.text
        assert json.loads(latest_export.text)["fields"] == [{"name": "id", "type": "string"}]
    finally:
        requests.delete(
            f"{backend_base_url}/api/v1/schemas/delete/{subject}",
            params={"registry_id": registry_id, "force": "true"},
            timeout=20,
        )
        requests.delete(f"{backend_base_url}/api/v1/schema-registries/{registry_id}", timeout=20)
