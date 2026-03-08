from __future__ import annotations

from typing import cast

from app.preflight.interface.result_translator import (
    COMMAND_TOPIC_DRY_RUN,
    MODE_DRY_RUN,
    translate_preflight_error,
    translate_topic_dry_run_result,
)
from app.topic.domain.models import DomainTopicPlan


class _FakeTopicPlan:
    warning_violations: tuple[str, ...] = ("warn-a",)

    def summary(self) -> dict[str, int]:
        return {
            "total_items": 3,
            "create_count": 1,
            "alter_count": 1,
            "delete_count": 0,
        }


def test_translate_topic_dry_run_result_serializes_expected_envelope_shape() -> None:
    payload = translate_topic_dry_run_result(
        request_id="req-1",
        cluster_id="cluster-a",
        result=cast(DomainTopicPlan, cast(object, _FakeTopicPlan())),
        risk={"level": "low", "blocking": False, "summary": "safe"},
        approval={"required": True, "state": "approved", "summary": "ticket approved"},
    )

    assert list(payload.keys()) == [
        "contract_version",
        "operation",
        "risk",
        "approval",
        "result",
        "error",
    ]

    assert payload["contract_version"] == "preflight.v1"
    assert payload["operation"] == {
        "command": "preflight topic dry-run",
        "mode": "dry-run",
        "request_id": "req-1",
        "identifiers": {
            "cluster_id": "cluster-a",
            "registry_id": None,
            "storage_id": None,
        },
    }
    assert payload["risk"] == {"level": "low", "blocking": False, "summary": "safe"}
    assert payload["approval"] == {
        "required": True,
        "state": "approved",
        "summary": "ticket approved",
    }
    assert payload["result"] == {
        "status": "success",
        "summary": "evaluated 3 topic changes",
        "counts": {
            "total": 3,
            "planned": 2,
            "applied": 0,
            "unchanged": 1,
            "failed": 0,
            "warnings": 1,
        },
    }
    assert payload["error"] is None


def test_translate_preflight_error_maps_error_and_defaults() -> None:
    payload = translate_preflight_error(
        command=COMMAND_TOPIC_DRY_RUN,
        mode=MODE_DRY_RUN,
        request_id="req-2",
        cluster_id="cluster-a",
        registry_id=None,
        storage_id=None,
        code="validation_error",
        message="payload invalid",
        target="payload.items[0]",
        retryable=False,
        details={"field": "items"},
    )

    assert list(payload.keys()) == [
        "contract_version",
        "operation",
        "risk",
        "approval",
        "result",
        "error",
    ]
    assert payload["risk"] == {
        "level": "none",
        "blocking": True,
        "summary": "execution stopped before risk evaluation",
    }
    assert payload["approval"] == {
        "required": False,
        "state": "not_required",
        "summary": "approval not evaluated due to failure",
    }
    assert payload["result"] == {
        "status": "failed",
        "summary": "request rejected before execution",
        "counts": {
            "total": 0,
            "planned": 0,
            "applied": 0,
            "unchanged": 0,
            "failed": 1,
            "warnings": 0,
        },
    }
    assert payload["error"] == {
        "code": "validation_error",
        "message": "payload invalid",
        "target": "payload.items[0]",
        "retryable": False,
        "details": {"field": "items"},
    }
