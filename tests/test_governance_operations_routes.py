from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from dependency_injector import providers
from fastapi.testclient import TestClient

from app.main import create_app
from app.schema.governance_support.models import ApprovalRequest, AuditActivity


@dataclass
class _FakeListApprovalRequestsUseCase:
    result: list[ApprovalRequest]

    async def execute(self, **_: object) -> list[ApprovalRequest]:
        return self.result


@dataclass
class _FakeGetApprovalRequestUseCase:
    result: ApprovalRequest

    async def execute(self, request_id: str) -> ApprovalRequest:
        assert request_id == self.result.request_id
        return self.result


@dataclass
class _FakeDecisionUseCase:
    result: ApprovalRequest

    async def execute(
        self,
        *,
        request_id: str,
        approver: str,
        decision_reason: str | None = None,
    ) -> ApprovalRequest:
        assert request_id == self.result.request_id
        assert approver == "schema-admin"
        assert decision_reason == "reviewed"
        return self.result


@dataclass
class _FakeRecentActivitiesUseCase:
    result: list[AuditActivity]

    async def execute(self, limit: int = 20) -> list[AuditActivity]:
        assert limit == 10
        return self.result


def _sample_approval_request() -> ApprovalRequest:
    return ApprovalRequest(
        request_id="req-1",
        resource_type="schema",
        resource_name="prod.orders-value",
        change_type="apply",
        change_ref="chg-1",
        summary="Schema apply requires approval",
        justification="High risk schema change",
        requested_by="alice",
        status="pending",
        requested_at=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
    )


def _sample_activity() -> AuditActivity:
    return AuditActivity(
        activity_type="approval",
        action="REQUESTED",
        target="prod.orders-value",
        message="approval required for schema apply",
        actor="alice",
        team=None,
        timestamp=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
        metadata={"registry_id": "registry-1"},
    )


def test_governance_operation_routes_expose_public_surfaces() -> None:
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/approval-requests" in paths
    assert "/api/v1/approval-requests/{request_id}" in paths
    assert "/api/v1/approval-requests/{request_id}/approve" in paths
    assert "/api/v1/approval-requests/{request_id}/reject" in paths
    assert "/api/v1/audit/recent" in paths
    assert "/api/v1/audit/history" in paths


def test_list_approval_requests_route_returns_items() -> None:
    app = create_app()
    container = app.state.container
    client = TestClient(app)
    container.schema_container.list_approval_requests_use_case.override(
        providers.Object(_FakeListApprovalRequestsUseCase(result=[_sample_approval_request()]))
    )
    try:
        response = client.get("/api/v1/approval-requests")
    finally:
        container.schema_container.list_approval_requests_use_case.reset_override()
        client.close()

    assert response.status_code == 200
    assert response.json()[0]["request_id"] == "req-1"


def test_approve_approval_request_route_returns_updated_item() -> None:
    app = create_app()
    container = app.state.container
    client = TestClient(app)
    sample = _sample_approval_request()
    approved = ApprovalRequest(
        request_id=sample.request_id,
        resource_type=sample.resource_type,
        resource_name=sample.resource_name,
        change_type=sample.change_type,
        change_ref=sample.change_ref,
        summary=sample.summary,
        justification=sample.justification,
        requested_by=sample.requested_by,
        status="approved",
        approver="schema-admin",
        decision_reason="reviewed",
        metadata=sample.metadata,
        requested_at=sample.requested_at,
        decided_at=datetime(2026, 4, 25, 13, 0, tzinfo=UTC),
    )
    container.schema_container.approve_approval_request_use_case.override(
        providers.Object(_FakeDecisionUseCase(result=approved))
    )
    try:
        response = client.post(
            "/api/v1/approval-requests/req-1/approve",
            json={"approver": "schema-admin", "decision_reason": "reviewed"},
        )
    finally:
        container.schema_container.approve_approval_request_use_case.reset_override()
        client.close()

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_recent_audit_activities_route_returns_entries() -> None:
    app = create_app()
    container = app.state.container
    client = TestClient(app)
    container.schema_container.recent_activities_use_case.override(
        providers.Object(_FakeRecentActivitiesUseCase(result=[_sample_activity()]))
    )
    try:
        response = client.get("/api/v1/audit/recent", params={"limit": 10})
    finally:
        container.schema_container.recent_activities_use_case.reset_override()
        client.close()

    assert response.status_code == 200
    assert response.json()[0]["activity_type"] == "approval"
