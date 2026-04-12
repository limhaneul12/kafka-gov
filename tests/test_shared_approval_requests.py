from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from app.shared.application.use_cases import (
    ApproveApprovalRequestUseCase,
    CreateApprovalRequestUseCase,
    GetApprovalRequestUseCase,
    ListApprovalRequestsUseCase,
    RejectApprovalRequestUseCase,
)
from app.shared.database import DatabaseManager
from app.shared.infrastructure.repository import (
    MySQLAuditActivityRepository,
    SQLApprovalRequestRepository,
)


@pytest.fixture
async def approval_repository(tmp_path: Path) -> AsyncGenerator[SQLApprovalRequestRepository, None]:
    db_path = tmp_path / "approval_requests.db"
    manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
    await manager.initialize()
    await manager.create_tables()
    try:
        yield SQLApprovalRequestRepository(session_factory=manager.get_db_session)
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_create_and_get_approval_request(
    approval_repository: SQLApprovalRequestRepository,
) -> None:
    create_use_case = CreateApprovalRequestUseCase(approval_repository)
    get_use_case = GetApprovalRequestUseCase(approval_repository)

    created = await create_use_case.execute(
        resource_type="schema",
        resource_name="prod.orders-value",
        change_type="delete",
        change_ref="chg-001",
        summary="Delete production schema",
        justification="Cleanup after migration",
        requested_by="alice",
        metadata={"risk_level": "high"},
    )

    fetched = await get_use_case.execute(created.request_id)

    assert fetched.request_id == created.request_id
    assert fetched.status == "pending"
    assert fetched.metadata == {"risk_level": "high"}


@pytest.mark.asyncio
async def test_list_approval_requests_filters_by_status_and_resource(
    approval_repository: SQLApprovalRequestRepository,
) -> None:
    create_use_case = CreateApprovalRequestUseCase(approval_repository)
    list_use_case = ListApprovalRequestsUseCase(approval_repository)
    approve_use_case = ApproveApprovalRequestUseCase(approval_repository)

    pending = await create_use_case.execute(
        resource_type="schema",
        resource_name="prod.orders-value",
        change_type="delete",
        summary="Delete production schema",
        justification="Cleanup",
        requested_by="alice",
    )
    approved = await create_use_case.execute(
        resource_type="schema",
        resource_name="prod.orders-value",
        change_type="compatibility-none",
        summary="Relax compatibility",
        justification="Hotfix rollout",
        requested_by="bob",
    )
    _ = await approve_use_case.execute(
        request_id=approved.request_id,
        approver="lead",
        decision_reason="reviewed",
    )

    pending_topics = await list_use_case.execute(status="pending", resource_type="schema")

    assert [item.request_id for item in pending_topics] == [pending.request_id]


@pytest.mark.asyncio
async def test_approve_and_reject_approval_requests(
    approval_repository: SQLApprovalRequestRepository,
) -> None:
    create_use_case = CreateApprovalRequestUseCase(approval_repository)
    approve_use_case = ApproveApprovalRequestUseCase(approval_repository)
    reject_use_case = RejectApprovalRequestUseCase(approval_repository)

    approvable = await create_use_case.execute(
        resource_type="schema",
        resource_name="prod.orders-value",
        change_type="delete",
        summary="Delete schema",
        justification="Cleanup",
        requested_by="alice",
    )
    rejectable = await create_use_case.execute(
        resource_type="schema",
        resource_name="prod.orders-value",
        change_type="breaking-change",
        summary="Breaking schema change",
        justification="Experiment",
        requested_by="bob",
    )

    approved = await approve_use_case.execute(
        request_id=approvable.request_id,
        approver="platform-lead",
        decision_reason="safe to proceed",
    )
    rejected = await reject_use_case.execute(
        request_id=rejectable.request_id,
        approver="governance-lead",
        decision_reason="too risky",
    )

    assert approved.status == "approved"
    assert approved.approver == "platform-lead"
    assert approved.decision_reason == "safe to proceed"
    assert approved.decided_at is not None

    assert rejected.status == "rejected"
    assert rejected.approver == "governance-lead"
    assert rejected.decision_reason == "too risky"
    assert rejected.decided_at is not None


@pytest.mark.asyncio
async def test_approval_requests_appear_in_activity_history(
    approval_repository: SQLApprovalRequestRepository,
) -> None:
    create_use_case = CreateApprovalRequestUseCase(approval_repository)
    audit_repository = MySQLAuditActivityRepository(
        session_factory=approval_repository.session_factory
    )

    created = await create_use_case.execute(
        resource_type="schema",
        resource_name="prod.orders-value",
        change_type="apply",
        change_ref="chg-approval-001",
        summary="approval required for schema apply",
        justification="high-risk schema change",
        requested_by="alice",
        metadata={"registry_id": "registry-1"},
    )

    recent = await audit_repository.get_recent_activities(limit=10)
    history = await audit_repository.get_activity_history(activity_type="approval", limit=10)

    assert recent[0].activity_type == "approval"
    assert recent[0].action == "REQUESTED"
    assert recent[0].target == "prod.orders-value"
    assert recent[0].metadata == {
        "registry_id": "registry-1",
        "approval_request": {
            "request_id": created.request_id,
            "resource_type": "schema",
            "change_type": "apply",
            "change_ref": "chg-approval-001",
            "status": "pending",
            "requested_by": "alice",
            "approver": None,
            "decision_reason": None,
        },
    }
    assert [item.activity_type for item in history] == ["approval"]
