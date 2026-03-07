from __future__ import annotations

from uuid import uuid4

import pytest
import requests


@pytest.mark.e2e
def test_e2e_api_info_and_health(backend_base_url: str) -> None:
    health = requests.get(f"{backend_base_url}/health", timeout=15)
    api_info = requests.get(f"{backend_base_url}/api/v1", timeout=15)

    assert health.status_code == 200
    assert health.json() == {"status": "healthy"}
    assert api_info.status_code == 200
    assert api_info.json()["message"] == "Kafka Governance API"


@pytest.mark.e2e
def test_e2e_cluster_broker_crud_and_connection_test(backend_base_url: str) -> None:
    base = f"{backend_base_url}/api/v1/clusters"
    cluster_id = f"e2e-{uuid4().hex[:8]}"

    create = requests.post(
        f"{base}/brokers",
        json={
            "cluster_id": cluster_id,
            "name": "E2E Cluster",
            "bootstrap_servers": "kafka1:19092",
        },
        timeout=20,
    )
    assert create.status_code == 201
    assert create.json()["cluster_id"] == cluster_id

    list_resp = requests.get(f"{base}/brokers?active_only=false", timeout=20)
    assert list_resp.status_code == 200
    assert any(item["cluster_id"] == cluster_id for item in list_resp.json())

    test_resp = requests.post(f"{base}/brokers/{cluster_id}/test", timeout=20)
    assert test_resp.status_code == 200
    test_payload = test_resp.json()
    assert isinstance(test_payload["success"], bool)
    assert isinstance(test_payload["message"], str)

    activate_resp = requests.patch(f"{base}/brokers/{cluster_id}/activate", timeout=20)
    assert activate_resp.status_code == 200
    assert activate_resp.json()["is_active"] is True

    delete_resp = requests.delete(f"{base}/brokers/{cluster_id}", timeout=20)
    assert delete_resp.status_code == 204


@pytest.mark.e2e
def test_e2e_schema_registry_crud_and_connection_test(backend_base_url: str) -> None:
    base = f"{backend_base_url}/api/v1/clusters"
    registry_id = f"e2e-reg-{uuid4().hex[:8]}"

    create = requests.post(
        f"{base}/schema-registries",
        json={
            "registry_id": registry_id,
            "name": "E2E Registry",
            "url": "http://schema-registry:8081",
        },
        timeout=20,
    )
    assert create.status_code == 201
    assert create.json()["registry_id"] == registry_id

    list_resp = requests.get(f"{base}/schema-registries?active_only=false", timeout=20)
    assert list_resp.status_code == 200
    assert any(item["registry_id"] == registry_id for item in list_resp.json())

    test_resp = requests.post(f"{base}/schema-registries/{registry_id}/test", timeout=20)
    assert test_resp.status_code == 200
    test_payload = test_resp.json()
    assert isinstance(test_payload["success"], bool)
    assert isinstance(test_payload["message"], str)

    activate_resp = requests.patch(f"{base}/schema-registries/{registry_id}/activate", timeout=20)
    assert activate_resp.status_code == 200
    assert activate_resp.json()["is_active"] is True

    delete_resp = requests.delete(f"{base}/schema-registries/{registry_id}", timeout=20)
    assert delete_resp.status_code == 204
