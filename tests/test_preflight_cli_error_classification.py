from __future__ import annotations

import typer
from pydantic import BaseModel, ValidationError

from app.preflight.interface.cli import (
    EXIT_POLICY_OR_APPROVAL_REJECTION,
    EXIT_RUNTIME_DEPENDENCY_FAILURE,
    EXIT_UNKNOWN_INTERNAL_ERROR,
    EXIT_VALIDATION_FAILURE,
    _classify_error,
)


class _PayloadModel(BaseModel):
    count: int


def _build_validation_error() -> ValidationError:
    try:
        _ = _PayloadModel.model_validate({"count": "not-an-int"})
    except ValidationError as exc:
        return exc
    raise AssertionError("expected pydantic ValidationError")


def test_classify_error_maps_validation_failures_to_exit_10() -> None:
    bad_parameter = typer.BadParameter("missing payload")
    code, message, retryable, target, exit_code = _classify_error(bad_parameter)
    assert code == "input_error"
    assert message == "missing payload"
    assert retryable is False
    assert target == "payload"
    assert exit_code == EXIT_VALIDATION_FAILURE == 10

    validation_error = _build_validation_error()
    code, message, retryable, target, exit_code = _classify_error(validation_error)
    assert code == "validation_error"
    assert "count" in message
    assert retryable is False
    assert target == "payload"
    assert exit_code == EXIT_VALIDATION_FAILURE == 10

    value_error = ValueError("invalid value")
    code, message, retryable, target, exit_code = _classify_error(value_error)
    assert code == "validation_error"
    assert message == "invalid value"
    assert retryable is False
    assert target == "payload"
    assert exit_code == EXIT_VALIDATION_FAILURE == 10


def test_classify_error_maps_policy_and_approval_failures_to_exit_20() -> None:
    approval_required = RuntimeError("approval_override is required for this operation")
    code, _message, retryable, target, exit_code = _classify_error(approval_required)
    assert code == "approval_required"
    assert retryable is False
    assert target == "approvalOverride"
    assert exit_code == EXIT_POLICY_OR_APPROVAL_REJECTION == 20

    approval_expired = RuntimeError("approval override has expired and must be renewed")
    code, _message, retryable, target, exit_code = _classify_error(approval_expired)
    assert code == "approval_expired"
    assert retryable is False
    assert target == "approvalOverride.expiresAt"
    assert exit_code == EXIT_POLICY_OR_APPROVAL_REJECTION == 20

    policy_blocked = RuntimeError("cannot apply due to policy violations")
    code, _message, retryable, target, exit_code = _classify_error(policy_blocked)
    assert code == "policy_blocked"
    assert retryable is False
    assert target is None
    assert exit_code == EXIT_POLICY_OR_APPROVAL_REJECTION == 20


def test_classify_error_maps_runtime_dependency_and_unknown_to_expected_codes() -> None:
    dependency_error = RuntimeError("database not initialized")
    code, _message, retryable, target, exit_code = _classify_error(dependency_error)
    assert code == "runtime_dependency_failure"
    assert retryable is True
    assert target is None
    assert exit_code == EXIT_RUNTIME_DEPENDENCY_FAILURE == 30

    unknown_error = RuntimeError("completely unexpected failure")
    code, _message, retryable, target, exit_code = _classify_error(unknown_error)
    assert code == "internal_unknown"
    assert retryable is False
    assert target is None
    assert exit_code == EXIT_UNKNOWN_INTERNAL_ERROR == 99
