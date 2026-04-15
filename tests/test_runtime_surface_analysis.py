from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import create_app


def _api_paths() -> set[str]:
    app = create_app()
    return {route.path for route in app.routes if isinstance(route, APIRoute)}


def test_active_http_surface_matches_schema_governance_boundary() -> None:
    paths = _api_paths()

    assert "/api/v1/schemas/governance/dashboard" in paths
    assert "/api/v1/schemas/history/{subject}" in paths
    assert "/api/v1/schemas/known-topics/{subject}" in paths
    assert "/api/v1/schemas/upload" in paths
    assert "/api/v1/schemas/policies" in paths
    assert "/api/v1/clusters/brokers" in paths
    assert "/api/v1/clusters/schema-registries" in paths
    assert "/api/v1/audit/recent" in paths
    assert "/api/v1/approval-requests" in paths


def test_legacy_and_future_domain_surfaces_are_not_shipped_routes() -> None:
    paths = _api_paths()

    assert "/api/v1/topics" not in paths
    assert "/api/v1/consumers" not in paths
    assert "/api/v1/ws" not in paths
    assert "/api/v1/products" not in paths
    assert "/api/v1/contracts" not in paths
    assert "/api/v1/catalog" not in paths
    assert "/api/v1/lineage" not in paths
