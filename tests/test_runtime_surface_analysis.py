from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import create_app

SCHEMA_RUNTIME_PATHS = {
    "/api/v1/schemas/governance/dashboard",
    "/api/v1/schemas/history/{subject}",
    "/api/v1/schemas/drift/{subject}",
    "/api/v1/schemas/settings/{subject}",
    "/api/v1/schemas/subjects/{subject}/versions",
    "/api/v1/schemas/subjects/{subject}/compare",
    "/api/v1/schemas/subjects/{subject}/versions/{version}",
    "/api/v1/schemas/subjects/{subject}/versions/{version}/export",
    "/api/v1/schemas/subjects/{subject}/export",
    "/api/v1/schemas/upload",
    "/api/v1/schemas/sync",
    "/api/v1/schemas/detail/{subject}",
    "/api/v1/schemas/search",
    "/api/v1/schemas/plan-change",
    "/api/v1/schemas/rollback/plan",
    "/api/v1/schemas/rollback/execute",
    "/api/v1/schemas/delete/analyze",
    "/api/v1/schemas/delete/{subject}",
    "/api/v1/schemas/policies",
    "/api/v1/schemas/policies/{policy_id}",
    "/api/v1/schemas/policies/{policy_id}/history",
    "/api/v1/approval-requests",
    "/api/v1/approval-requests/{request_id}",
    "/api/v1/approval-requests/{request_id}/approve",
    "/api/v1/approval-requests/{request_id}/reject",
    "/api/v1/audit/recent",
    "/api/v1/audit/history",
    "/api/v1/schema-registries",
}

REMOVED_PATHS = {
    "/api/v1/schemas/known-topics/{subject}",
    "/api/v1/topics",
    "/api/v1/consumers",
    "/api/v1/ws",
    "/api/v1/clusters/brokers",
    "/api/v1/clusters/schema-registries",
    "/api/v1/products",
    "/api/v1/contracts",
    "/api/v1/catalog",
    "/api/v1/lineage",
}


def _api_paths() -> set[str]:
    app = create_app()
    return {route.path for route in app.routes if isinstance(route, APIRoute)}


def test_active_http_surface_matches_schema_registry_boundary() -> None:
    paths = _api_paths()

    for path in SCHEMA_RUNTIME_PATHS:
        assert path in paths


def test_removed_http_surfaces_stay_out_of_the_shipped_runtime() -> None:
    paths = _api_paths()

    for path in REMOVED_PATHS:
        assert path not in paths
