from __future__ import annotations

from collections.abc import Mapping

from app.schema.domain.models import DomainSchemaApplyResult, DomainSchemaPlan
from app.topic.domain.models import DomainTopicApplyResult, DomainTopicPlan

CONTRACT_VERSION = "preflight.v1"

COMMAND_TOPIC_DRY_RUN = "preflight topic dry-run"
COMMAND_TOPIC_APPLY = "preflight topic apply"
COMMAND_SCHEMA_DRY_RUN = "preflight schema dry-run"
COMMAND_SCHEMA_APPLY = "preflight schema apply"

MODE_DRY_RUN = "dry-run"
MODE_APPLY = "apply"

RiskValue = str | bool
ApprovalValue = str | bool


def translate_topic_dry_run_result(
    *,
    request_id: str,
    cluster_id: str,
    result: DomainTopicPlan,
    risk: Mapping[str, RiskValue] | None = None,
    approval: Mapping[str, ApprovalValue] | None = None,
) -> dict[str, object]:
    summary = result.summary()
    total = _to_non_negative_int(summary.get("total_items", 0))
    planned = _to_non_negative_int(
        summary.get("create_count", 0)
        + summary.get("alter_count", 0)
        + summary.get("delete_count", 0)
    )
    warnings = _to_non_negative_int(len(result.warning_violations))

    return _build_success_envelope(
        command=COMMAND_TOPIC_DRY_RUN,
        mode=MODE_DRY_RUN,
        request_id=request_id,
        cluster_id=cluster_id,
        registry_id=None,
        storage_id=None,
        risk=risk,
        approval=approval,
        summary=f"evaluated {total} topic changes",
        counts={
            "total": total,
            "planned": planned,
            "applied": 0,
            "unchanged": _to_non_negative_int(total - planned),
            "failed": 0,
            "warnings": warnings,
        },
    )


def translate_topic_apply_result(
    *,
    request_id: str,
    cluster_id: str,
    result: DomainTopicApplyResult,
    risk: Mapping[str, RiskValue] | None = None,
    approval: Mapping[str, ApprovalValue] | None = None,
) -> dict[str, object]:
    summary = result.summary()
    total = _to_non_negative_int(summary.get("total_items", 0))
    applied = _to_non_negative_int(summary.get("applied_count", 0))
    unchanged = _to_non_negative_int(summary.get("skipped_count", 0))
    failed = _to_non_negative_int(summary.get("failed_count", 0))
    planned = _to_non_negative_int(total - unchanged)

    return _build_success_envelope(
        command=COMMAND_TOPIC_APPLY,
        mode=MODE_APPLY,
        request_id=request_id,
        cluster_id=cluster_id,
        registry_id=None,
        storage_id=None,
        risk=risk,
        approval=approval,
        summary=f"applied {applied} of {planned} topic changes",
        counts={
            "total": total,
            "planned": planned,
            "applied": applied,
            "unchanged": unchanged,
            "failed": failed,
            "warnings": 0,
        },
    )


def translate_schema_dry_run_result(
    *,
    request_id: str,
    registry_id: str,
    result: DomainSchemaPlan,
    risk: Mapping[str, RiskValue] | None = None,
    approval: Mapping[str, ApprovalValue] | None = None,
) -> dict[str, object]:
    summary = result.summary()
    total = _to_non_negative_int(summary.get("total_items", 0))
    planned = _to_non_negative_int(
        summary.get("register_count", 0)
        + summary.get("update_count", 0)
        + summary.get("delete_count", 0)
    )
    unchanged = _to_non_negative_int(summary.get("none_count", 0))
    warnings = _to_non_negative_int(summary.get("violation_count", 0))

    return _build_success_envelope(
        command=COMMAND_SCHEMA_DRY_RUN,
        mode=MODE_DRY_RUN,
        request_id=request_id,
        cluster_id=None,
        registry_id=registry_id,
        storage_id=None,
        risk=risk,
        approval=approval,
        summary=f"evaluated {total} schema changes",
        counts={
            "total": total,
            "planned": planned,
            "applied": 0,
            "unchanged": unchanged,
            "failed": 0,
            "warnings": warnings,
        },
    )


def translate_schema_apply_result(
    *,
    request_id: str,
    registry_id: str,
    storage_id: str,
    result: DomainSchemaApplyResult,
    risk: Mapping[str, RiskValue] | None = None,
    approval: Mapping[str, ApprovalValue] | None = None,
) -> dict[str, object]:
    summary = result.summary()
    total = _to_non_negative_int(summary.get("total_items", 0))
    applied = _to_non_negative_int(summary.get("registered_count", 0))
    unchanged = _to_non_negative_int(summary.get("skipped_count", 0))
    failed = _to_non_negative_int(summary.get("failed_count", 0))
    planned = _to_non_negative_int(total - unchanged)

    return _build_success_envelope(
        command=COMMAND_SCHEMA_APPLY,
        mode=MODE_APPLY,
        request_id=request_id,
        cluster_id=None,
        registry_id=registry_id,
        storage_id=storage_id,
        risk=risk,
        approval=approval,
        summary=f"applied {applied} of {planned} schema changes",
        counts={
            "total": total,
            "planned": planned,
            "applied": applied,
            "unchanged": unchanged,
            "failed": failed,
            "warnings": 0,
        },
    )


def translate_preflight_error(
    *,
    command: str,
    mode: str,
    request_id: str,
    cluster_id: str | None,
    registry_id: str | None,
    storage_id: str | None,
    code: str,
    message: str,
    target: str | None = None,
    retryable: bool = False,
    details: Mapping[str, object] | None = None,
    risk: Mapping[str, RiskValue] | None = None,
    approval: Mapping[str, ApprovalValue] | None = None,
) -> dict[str, object]:
    return {
        "contract_version": CONTRACT_VERSION,
        "operation": _build_operation(
            command=command,
            mode=mode,
            request_id=request_id,
            cluster_id=cluster_id,
            registry_id=registry_id,
            storage_id=storage_id,
        ),
        "risk": _merge_risk(
            risk,
            default={
                "level": "none",
                "blocking": True,
                "summary": "execution stopped before risk evaluation",
            },
        ),
        "approval": _merge_approval(
            approval,
            default={
                "required": False,
                "state": "not_required",
                "summary": "approval not evaluated due to failure",
            },
        ),
        "result": {
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
        },
        "error": {
            "code": code,
            "message": message,
            "target": target,
            "retryable": retryable,
            "details": details if details is not None else {},
        },
    }


def _build_success_envelope(
    *,
    command: str,
    mode: str,
    request_id: str,
    cluster_id: str | None,
    registry_id: str | None,
    storage_id: str | None,
    risk: Mapping[str, RiskValue] | None,
    approval: Mapping[str, ApprovalValue] | None,
    summary: str,
    counts: dict[str, int],
) -> dict[str, object]:
    return {
        "contract_version": CONTRACT_VERSION,
        "operation": _build_operation(
            command=command,
            mode=mode,
            request_id=request_id,
            cluster_id=cluster_id,
            registry_id=registry_id,
            storage_id=storage_id,
        ),
        "risk": _merge_risk(
            risk,
            default={
                "level": "none",
                "blocking": False,
                "summary": "risk evaluation not provided by transport result",
            },
        ),
        "approval": _merge_approval(
            approval,
            default={
                "required": False,
                "state": "not_required",
                "summary": "approval state not provided by transport result",
            },
        ),
        "result": {
            "status": "success",
            "summary": summary,
            "counts": {
                "total": _to_non_negative_int(counts.get("total", 0)),
                "planned": _to_non_negative_int(counts.get("planned", 0)),
                "applied": _to_non_negative_int(counts.get("applied", 0)),
                "unchanged": _to_non_negative_int(counts.get("unchanged", 0)),
                "failed": _to_non_negative_int(counts.get("failed", 0)),
                "warnings": _to_non_negative_int(counts.get("warnings", 0)),
            },
        },
        "error": None,
    }


def _build_operation(
    *,
    command: str,
    mode: str,
    request_id: str,
    cluster_id: str | None,
    registry_id: str | None,
    storage_id: str | None,
) -> dict[str, object]:
    return {
        "command": command,
        "mode": mode,
        "request_id": request_id,
        "identifiers": {
            "cluster_id": cluster_id,
            "registry_id": registry_id,
            "storage_id": storage_id,
        },
    }


def _merge_risk(
    source: Mapping[str, RiskValue] | None,
    default: Mapping[str, RiskValue],
) -> dict[str, object]:
    source_to_use: Mapping[str, RiskValue] = source if source is not None else {}
    return {
        "level": _string_value(source_to_use, "level", str(default["level"])),
        "blocking": _bool_value(source_to_use, "blocking", bool(default["blocking"])),
        "summary": _string_value(source_to_use, "summary", str(default["summary"])),
    }


def _merge_approval(
    source: Mapping[str, ApprovalValue] | None,
    default: Mapping[str, ApprovalValue],
) -> dict[str, object]:
    source_to_use: Mapping[str, ApprovalValue] = source if source is not None else {}
    return {
        "required": _bool_value(source_to_use, "required", bool(default["required"])),
        "state": _string_value(source_to_use, "state", str(default["state"])),
        "summary": _string_value(source_to_use, "summary", str(default["summary"])),
    }


def _to_non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        normalized = int(value)
    elif isinstance(value, int):
        normalized = value
    elif isinstance(value, str):
        normalized = int(value) if value.strip().lstrip("-").isdigit() else 0
    else:
        normalized = 0

    return normalized if normalized >= 0 else 0


def _string_value(mapping: Mapping[str, str | bool], key: str, default: str) -> str:
    raw = mapping.get(key)
    if isinstance(raw, str):
        return raw

    return default


def _bool_value(mapping: Mapping[str, str | bool], key: str, default: bool) -> bool:
    raw = mapping.get(key)
    if isinstance(raw, bool):
        return raw

    return default
