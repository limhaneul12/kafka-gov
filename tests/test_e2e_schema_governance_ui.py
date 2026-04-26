from __future__ import annotations

import json
import os
import time
from urllib.parse import quote
from uuid import uuid4

import pytest
import requests
from playwright.sync_api import Page, expect

SCHEMA_REGISTRY_E2E_URL = os.getenv("E2E_SCHEMA_REGISTRY_URL", "http://schema-registry:8081")


def _expect_schema_metadata(
    page: Page,
    *,
    owner: str,
    compatibility: str,
    documentation: str,
    description: str,
    tags: list[str],
) -> None:
    expect(page.get_by_text(owner).first).to_be_visible()
    expect(page.get_by_text(compatibility)).to_be_visible()
    expect(page.get_by_text(documentation)).to_be_visible()
    expect(page.get_by_text(description)).to_be_visible()
    for tag in tags:
        expect(page.get_by_text(tag)).to_be_visible()


def _create_active_registry(backend_base_url: str, registry_id: str) -> None:
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
        pytest.skip(f"schema registry stack unavailable for container ui e2e: {create.text}")

    test_resp = requests.post(
        f"{backend_base_url}/api/v1/schema-registries/{registry_id}/test",
        timeout=20,
    )
    if test_resp.status_code != 200 or test_resp.json().get("success") is not True:
        pytest.skip(f"schema registry connection not ready: {test_resp.text}")

    activate = requests.patch(
        f"{backend_base_url}/api/v1/schema-registries/{registry_id}/activate",
        timeout=20,
    )
    assert activate.status_code == 200, activate.text


def _seed_live_schema(backend_base_url: str, registry_id: str) -> str:
    schema_slug = f"orders_ui_{uuid4().hex[:8]}"
    subject = f"dev.{schema_slug}"
    schema = {
        "type": "record",
        "name": "OrderUiE2E",
        "namespace": "dev.e2e",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "status", "type": ["null", "string"], "default": None},
        ],
    }

    upload = requests.post(
        f"{backend_base_url}/api/v1/schemas/upload",
        params={"registry_id": registry_id},
        data={
            "env": "dev",
            "change_id": f"chg-{schema_slug}",
            "owner": "team-ui-e2e",
            "compatibility_mode": "BACKWARD",
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
    assert upload.status_code == 201, upload.text
    return subject


def _upload_live_schema_version(
    backend_base_url: str,
    *,
    registry_id: str,
    schema_slug: str,
    schema: dict[str, object],
    change_id: str,
) -> None:
    upload = requests.post(
        f"{backend_base_url}/api/v1/schemas/upload",
        params={"registry_id": registry_id},
        data={
            "env": "dev",
            "change_id": change_id,
            "owner": "team-ui-e2e",
            "compatibility_mode": "BACKWARD",
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
    assert upload.status_code == 201, upload.text


def _wait_for_history_length(
    backend_base_url: str,
    *,
    registry_id: str,
    subject: str,
    expected_length: int,
    timeout_sec: float = 20.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_sec
    last_payload: dict[str, object] | None = None

    while time.monotonic() < deadline:
        response = requests.get(
            f"{backend_base_url}/api/v1/schemas/history/{subject}",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        last_payload = payload
        if len(payload["history"]) >= expected_length:
            return payload
        time.sleep(0.5)

    raise AssertionError(f"Timed out waiting for history on {subject}: {last_payload}")


def _wait_for_latest_schema_fields(
    backend_base_url: str,
    *,
    registry_id: str,
    subject: str,
    expected_fields: list[dict[str, object]],
    timeout_sec: float = 20.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_sec
    last_payload: dict[str, object] | None = None

    while time.monotonic() < deadline:
        response = requests.get(
            f"{backend_base_url}/api/v1/schemas/subjects/{subject}/export",
            params={"registry_id": registry_id},
            timeout=20,
        )
        assert response.status_code == 200, response.text
        payload = json.loads(response.text)
        last_payload = payload
        if payload["fields"] == expected_fields:
            return payload
        time.sleep(0.5)

    raise AssertionError(f"Timed out waiting for export payload on {subject}: {last_payload}")


@pytest.mark.e2e
def test_e2e_approvals_and_audit_page_loads(page: Page, e2e_urls: dict[str, str]) -> None:
    _ = page.goto("/", wait_until="domcontentloaded")

    page.locator("aside").get_by_role("link", name="Approvals & Audit", exact=True).click()

    expect(page).to_have_url(f"{e2e_urls['frontend_url']}/schemas/operations")
    expect(page.get_by_role("heading", name="Approvals & Audit")).to_be_visible()
    expect(page.get_by_text("Pending Approval Requests")).to_be_visible()
    expect(page.get_by_text("Recent Audit Activity")).to_be_visible()


@pytest.mark.e2e
def test_e2e_live_schema_detail_page_loads(page: Page, backend_base_url: str) -> None:
    registry_id = f"e2e-reg-ui-{uuid4().hex[:8]}"
    subject = ""

    try:
        _create_active_registry(backend_base_url, registry_id)
        subject = _seed_live_schema(backend_base_url, registry_id)

        _ = page.goto(f"/schemas/{quote(subject, safe='')}", wait_until="domcontentloaded")

        expect(page.get_by_role("heading", name=subject)).to_be_visible()
        expect(page.get_by_role("button", name="Download Latest")).to_be_visible()
        expect(page.get_by_role("button", name="Edit Metadata")).to_be_visible()
        expect(page.get_by_text("Drift Status")).to_be_visible()

        page.get_by_role("button", name="History").click()
        expect(page.get_by_text("Version Activity")).to_be_visible()
        page.get_by_role("button", name="Preview").click()
        expect(page.get_by_role("heading", name=f"{subject} v1")).to_be_visible()
    finally:
        if subject:
            requests.delete(
                f"{backend_base_url}/api/v1/schemas/delete/{subject}",
                params={"registry_id": registry_id, "force": "true"},
                timeout=20,
            )
        requests.delete(f"{backend_base_url}/api/v1/schema-registries/{registry_id}", timeout=20)


@pytest.mark.e2e
def test_e2e_schema_detail_settings_and_apply_flow(page: Page, backend_base_url: str) -> None:
    registry_id = f"e2e-reg-ui-flow-{uuid4().hex[:8]}"
    schema_slug = f"orders_ui_flow_{uuid4().hex[:8]}"
    subject = f"dev.{schema_slug}"
    schema_name = "OrderUiFlow"
    v1_schema = {
        "type": "record",
        "name": schema_name,
        "namespace": "dev.e2e",
        "fields": [
            {"name": "id", "type": "string"},
        ],
    }
    v2_schema = {
        "type": "record",
        "name": schema_name,
        "namespace": "dev.e2e",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "status", "type": ["null", "string"], "default": None},
        ],
    }

    try:
        _create_active_registry(backend_base_url, registry_id)
        _upload_live_schema_version(
            backend_base_url,
            registry_id=registry_id,
            schema_slug=schema_slug,
            schema=v1_schema,
            change_id=f"chg-{schema_slug}-v1",
        )

        _ = page.goto(f"/schemas/{quote(subject, safe='')}", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name=subject)).to_be_visible()
        page.wait_for_timeout(500)

        metadata_button = page.get_by_role("button", name="Edit Metadata")
        expect(metadata_button).to_be_visible()
        metadata_button.click()
        expect(page.get_by_role("heading", name="Edit Schema Metadata")).to_be_visible()
        page.locator("#schema-settings-owner").fill("team-governance-ui")
        page.locator("#schema-settings-doc").fill("https://docs.example/ui-flow")
        page.locator("#schema-settings-description").fill("UI flow governance schema")
        page.locator("#schema-settings-tags").fill("golden, customer-facing")
        page.locator("#schema-settings-compatibility").select_option("FULL")
        page.get_by_role("button", name="Save Metadata").click()

        _expect_schema_metadata(
            page,
            owner="team-governance-ui",
            compatibility="FULL",
            documentation="https://docs.example/ui-flow",
            description="UI flow governance schema",
            tags=["golden", "customer-facing"],
        )

        _ = page.reload(wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name=subject)).to_be_visible()
        _expect_schema_metadata(
            page,
            owner="team-governance-ui",
            compatibility="FULL",
            documentation="https://docs.example/ui-flow",
            description="UI flow governance schema",
            tags=["golden", "customer-facing"],
        )

        page.get_by_role("button", name="Edit", exact=True).click()
        editor = page.locator("textarea").first
        editor.fill(json.dumps(v2_schema, indent=2))
        page.get_by_role("button", name="Analyze Changes").click()
        expect(page.get_by_role("button", name="Apply v2")).to_be_visible()

        page.evaluate(
            """
            () => {
              const answers = ["approved ui flow", "schema-admin", ""];
              window.prompt = () => answers.shift() ?? "";
            }
            """
        )
        page.get_by_role("button", name="Apply v2").click()

        _wait_for_history_length(
            backend_base_url,
            registry_id=registry_id,
            subject=subject,
            expected_length=2,
        )
        page.get_by_role("button", name="History").click()
        expect(page.get_by_text("Version Activity")).to_be_visible()
        expect(page.get_by_text("v2").first).to_be_visible()
    finally:
        requests.delete(
            f"{backend_base_url}/api/v1/schemas/delete/{subject}",
            params={"registry_id": registry_id, "force": "true"},
            timeout=20,
        )
        requests.delete(f"{backend_base_url}/api/v1/schema-registries/{registry_id}", timeout=20)


@pytest.mark.e2e
def test_e2e_schema_detail_history_compare_flow(page: Page, backend_base_url: str) -> None:
    registry_id = f"e2e-reg-ui-compare-{uuid4().hex[:8]}"
    schema_slug = f"orders_ui_compare_{uuid4().hex[:8]}"
    subject = f"dev.{schema_slug}"
    schema_name = "OrderUiCompare"
    v1_schema = {
        "type": "record",
        "name": schema_name,
        "namespace": "dev.e2e",
        "fields": [
            {"name": "id", "type": "string"},
        ],
    }
    v2_schema = {
        "type": "record",
        "name": schema_name,
        "namespace": "dev.e2e",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "status", "type": ["null", "string"], "default": None},
        ],
    }

    try:
        _create_active_registry(backend_base_url, registry_id)
        _upload_live_schema_version(
            backend_base_url,
            registry_id=registry_id,
            schema_slug=schema_slug,
            schema=v1_schema,
            change_id=f"chg-{schema_slug}-v1",
        )
        _upload_live_schema_version(
            backend_base_url,
            registry_id=registry_id,
            schema_slug=schema_slug,
            schema=v2_schema,
            change_id=f"chg-{schema_slug}-v2",
        )

        _ = page.goto(f"/schemas/{quote(subject, safe='')}", wait_until="domcontentloaded")
        page.get_by_role("button", name="History").click()
        expect(page.get_by_text("Version Activity")).to_be_visible()

        page.get_by_role("button", name="Compare to Latest").click()

        expect(page.get_by_role("heading", name=f"{subject} comparison v1 → v2")).to_be_visible()
        expect(page.get_by_text("Change Summary")).to_be_visible()
        expect(page.get_by_text("Hide Unchanged Lines")).to_be_visible()
        expect(page.get_by_text("Changed", exact=True)).to_be_visible()
        expect(page.locator("text=status").first).to_be_visible()
    finally:
        requests.delete(
            f"{backend_base_url}/api/v1/schemas/delete/{subject}",
            params={"registry_id": registry_id, "force": "true"},
            timeout=20,
        )
        requests.delete(f"{backend_base_url}/api/v1/schema-registries/{registry_id}", timeout=20)


@pytest.mark.e2e
def test_e2e_schema_detail_rollback_flow(page: Page, backend_base_url: str) -> None:
    registry_id = f"e2e-reg-ui-rollback-{uuid4().hex[:8]}"
    schema_slug = f"orders_ui_rollback_{uuid4().hex[:8]}"
    subject = f"dev.{schema_slug}"
    schema_name = "OrderUiRollback"
    v1_schema = {
        "type": "record",
        "name": schema_name,
        "namespace": "dev.e2e",
        "fields": [
            {"name": "id", "type": "string"},
        ],
    }
    v2_schema = {
        "type": "record",
        "name": schema_name,
        "namespace": "dev.e2e",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "status", "type": ["null", "string"], "default": None},
        ],
    }

    try:
        _create_active_registry(backend_base_url, registry_id)
        _upload_live_schema_version(
            backend_base_url,
            registry_id=registry_id,
            schema_slug=schema_slug,
            schema=v1_schema,
            change_id=f"chg-{schema_slug}-v1",
        )
        _upload_live_schema_version(
            backend_base_url,
            registry_id=registry_id,
            schema_slug=schema_slug,
            schema=v2_schema,
            change_id=f"chg-{schema_slug}-v2",
        )

        _ = page.goto(f"/schemas/{quote(subject, safe='')}", wait_until="domcontentloaded")
        page.get_by_role("button", name="History").click()
        page.evaluate(
            """
            () => {
              const answers = ["approved rollback", "schema-admin", ""];
              window.confirm = () => true;
              window.prompt = () => answers.shift() ?? "";
            }
            """
        )
        page.get_by_role("button", name="Restore this version").click()
        expect(page.get_by_role("button", name="Apply v3")).to_be_visible()
        page.get_by_role("button", name="Apply v3").click()

        latest_payload = _wait_for_latest_schema_fields(
            backend_base_url,
            registry_id=registry_id,
            subject=subject,
            expected_fields=[{"name": "id", "type": "string"}],
        )
        assert latest_payload["fields"] == [{"name": "id", "type": "string"}]
    finally:
        requests.delete(
            f"{backend_base_url}/api/v1/schemas/delete/{subject}",
            params={"registry_id": registry_id, "force": "true"},
            timeout=20,
        )
        requests.delete(f"{backend_base_url}/api/v1/schema-registries/{registry_id}", timeout=20)
