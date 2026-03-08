from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Callable, Coroutine, Mapping
from pathlib import Path
from typing import Annotated, NoReturn

import typer
import yaml
from pydantic import ValidationError

from app.container import AppContainer
from app.preflight.application.transport import PreflightTransport
from app.preflight.interface.result_translator import (
    COMMAND_SCHEMA_APPLY,
    COMMAND_SCHEMA_DRY_RUN,
    COMMAND_TOPIC_APPLY,
    COMMAND_TOPIC_DRY_RUN,
    MODE_APPLY,
    MODE_DRY_RUN,
    translate_preflight_error,
    translate_schema_apply_result,
    translate_schema_dry_run_result,
    translate_topic_apply_result,
    translate_topic_dry_run_result,
)
from app.preflight.interface.schema_transport_adapter import SchemaTransportAdapter
from app.preflight.interface.topic_transport_adapter import TopicTransportAdapter
from app.schema.domain.models import DomainSchemaApplyResult, DomainSchemaPlan
from app.schema.interface.schemas.request import SchemaBatchRequest
from app.shared.roles import DEFAULT_USER
from app.topic.domain.models import DomainTopicApplyResult, DomainTopicPlan
from app.topic.interface.schemas.request import TopicBatchRequest

cli_app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
topic_app = typer.Typer(no_args_is_help=True)
schema_app = typer.Typer(no_args_is_help=True)

cli_app.add_typer(topic_app, name="topic")
cli_app.add_typer(schema_app, name="schema")

FileOption = Annotated[
    Path | None,
    typer.Option(
        "--file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Read request payload from file.",
    ),
]

JsonOption = Annotated[
    bool,
    typer.Option(
        "--json/--no-json",
        help="Emit machine-readable JSON envelope output.",
    ),
]

EXIT_VALIDATION_FAILURE = 10
EXIT_POLICY_OR_APPROVAL_REJECTION = 20
EXIT_RUNTIME_DEPENDENCY_FAILURE = 30
EXIT_UNKNOWN_INTERNAL_ERROR = 99

_POLICY_BLOCK_KEYWORDS = (
    "policy violation",
    "policy violations",
    "policy blocked",
    "cannot apply due to policy violations",
)
_DEPENDENCY_FAILURE_KEYWORDS = (
    "connection",
    "unreachable",
    "unavailable",
    "timeout",
    "timed out",
    "auth provider",
    "database not initialized",
    "failed to retrieve",
    "no such table",
)

_DEPENDENCY_EXCEPTION_NAMES = {
    "DatabaseError",
    "InterfaceError",
    "OperationalError",
}


def _read_stdin_payload() -> str | None:
    if sys.stdin.isatty():
        return None

    payload = sys.stdin.read()
    if payload == "":
        return None

    return payload


def _load_payload(*, file_path: Path | None) -> str:
    stdin_payload = _read_stdin_payload()
    if file_path is not None and stdin_payload is not None:
        raise typer.BadParameter("Provide either --file or stdin, not both.")

    if file_path is not None:
        return file_path.read_text(encoding="utf-8")

    if stdin_payload is not None:
        return stdin_payload

    raise typer.BadParameter("Provide input via --file or piped stdin.")


def _parse_payload_mapping(payload: str) -> dict[str, object]:
    try:
        parsed = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        raise typer.BadParameter(f"Invalid YAML/JSON payload: {exc}") from exc

    if not isinstance(parsed, dict):
        raise typer.BadParameter("Payload must be a mapping/object at the top level.")

    normalized: dict[str, object] = {}
    for key, value in parsed.items():
        if not isinstance(key, str):
            raise typer.BadParameter("Payload object keys must be strings.")
        normalized[key] = value

    return normalized


def _build_transport() -> PreflightTransport:
    container = AppContainer()
    topic_transport = TopicTransportAdapter(
        dry_run_use_case=container.topic_container.dry_run_use_case(),
        apply_use_case=container.topic_container.apply_use_case(),
    )
    schema_transport = SchemaTransportAdapter(
        dry_run_use_case=container.schema_container.dry_run_use_case(),
        apply_use_case=container.schema_container.apply_use_case(),
    )
    return PreflightTransport(topic_transport=topic_transport, schema_transport=schema_transport)


def _emit_output(*, payload: Mapping[str, object], as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(payload, ensure_ascii=True), err=False)
        return

    result = payload.get("result")
    error = payload.get("error")

    if isinstance(error, Mapping) and error:
        message = error.get("message")
        typer.echo(str(message) if message is not None else "request failed", err=True)
        return

    if isinstance(result, Mapping):
        summary = result.get("summary")
        typer.echo(str(summary) if summary is not None else "request completed", err=False)
        return

    typer.echo("request completed", err=False)


def _extract_metadata(result: object, key: str) -> Mapping[str, str | bool] | None:
    if not hasattr(result, key):
        return None

    raw = getattr(result, key)
    if not isinstance(raw, Mapping):
        return None

    return {
        item_key: item_value
        for item_key, item_value in raw.items()
        if isinstance(item_key, str) and isinstance(item_value, str | bool)
    }


def _classify_error(error: Exception) -> tuple[str, str, bool, str | None, int]:
    normalized_message = str(error).strip().lower()

    if isinstance(error, typer.BadParameter):
        return ("input_error", str(error), False, "payload", EXIT_VALIDATION_FAILURE)

    if isinstance(error, ValidationError):
        return ("validation_error", str(error), False, "payload", EXIT_VALIDATION_FAILURE)

    if "approval override has expired" in normalized_message:
        return (
            "approval_expired",
            str(error),
            False,
            "approvalOverride.expiresAt",
            EXIT_POLICY_OR_APPROVAL_REJECTION,
        )

    if "approval_override is required" in normalized_message:
        return (
            "approval_required",
            str(error),
            False,
            "approvalOverride",
            EXIT_POLICY_OR_APPROVAL_REJECTION,
        )

    if any(keyword in normalized_message for keyword in _POLICY_BLOCK_KEYWORDS):
        return (
            "policy_blocked",
            str(error),
            False,
            None,
            EXIT_POLICY_OR_APPROVAL_REJECTION,
        )

    if isinstance(error, ConnectionError | TimeoutError | ImportError | ModuleNotFoundError):
        return (
            "runtime_dependency_failure",
            str(error),
            True,
            None,
            EXIT_RUNTIME_DEPENDENCY_FAILURE,
        )

    if isinstance(error, RuntimeError) and any(
        keyword in normalized_message for keyword in _DEPENDENCY_FAILURE_KEYWORDS
    ):
        return (
            "runtime_dependency_failure",
            str(error),
            True,
            None,
            EXIT_RUNTIME_DEPENDENCY_FAILURE,
        )

    if error.__class__.__name__ in _DEPENDENCY_EXCEPTION_NAMES and any(
        keyword in normalized_message for keyword in _DEPENDENCY_FAILURE_KEYWORDS
    ):
        return (
            "runtime_dependency_failure",
            str(error),
            True,
            None,
            EXIT_RUNTIME_DEPENDENCY_FAILURE,
        )

    if isinstance(error, ValueError):
        return ("validation_error", str(error), False, "payload", EXIT_VALIDATION_FAILURE)

    return ("internal_unknown", str(error), False, None, EXIT_UNKNOWN_INTERNAL_ERROR)


def _run_with_envelope(
    *,
    command: str,
    mode: str,
    cluster_id: str | None,
    registry_id: str | None,
    storage_id: str | None,
    request_id: str,
    as_json: bool,
    runner: Callable[[], Coroutine[object, object, dict[str, object]]],
) -> None:
    try:
        envelope = asyncio.run(runner())
        _emit_output(payload=envelope, as_json=as_json)
    except Exception as exc:
        _emit_error_envelope(
            command=command,
            mode=mode,
            cluster_id=cluster_id,
            registry_id=registry_id,
            storage_id=storage_id,
            request_id=request_id,
            as_json=as_json,
            error=exc,
        )


def _emit_error_envelope(
    *,
    command: str,
    mode: str,
    cluster_id: str | None,
    registry_id: str | None,
    storage_id: str | None,
    request_id: str,
    as_json: bool,
    error: Exception,
) -> NoReturn:
    code, message, retryable, target, exit_code = _classify_error(error)
    error_payload = translate_preflight_error(
        command=command,
        mode=mode,
        request_id=request_id,
        cluster_id=cluster_id,
        registry_id=registry_id,
        storage_id=storage_id,
        code=code,
        message=message,
        target=target,
        retryable=retryable,
    )
    _emit_output(payload=error_payload, as_json=as_json)
    raise typer.Exit(code=exit_code) from error


@topic_app.command("dry-run")
def topic_dry_run(
    cluster_id: Annotated[str, typer.Option("--cluster-id", help="Kafka cluster identifier")],
    file_path: FileOption = None,
    as_json: JsonOption = False,
) -> None:
    try:
        payload = _load_payload(file_path=file_path)
        parsed = _parse_payload_mapping(payload)
        request = TopicBatchRequest.model_validate(parsed)
    except Exception as exc:
        _emit_error_envelope(
            command=COMMAND_TOPIC_DRY_RUN,
            mode=MODE_DRY_RUN,
            cluster_id=cluster_id,
            registry_id=None,
            storage_id=None,
            request_id="unknown",
            as_json=as_json,
            error=exc,
        )
    request_id = str(request.change_id)
    transport = _build_transport()

    async def _runner() -> dict[str, object]:
        raw_result = await transport.topic_dry_run(cluster_id, request, DEFAULT_USER)
        if not isinstance(raw_result, DomainTopicPlan):
            raise TypeError("unexpected topic dry-run result type")
        return translate_topic_dry_run_result(
            request_id=request_id,
            cluster_id=cluster_id,
            result=raw_result,
            risk=_extract_metadata(raw_result, "risk"),
            approval=_extract_metadata(raw_result, "approval"),
        )

    _run_with_envelope(
        command=COMMAND_TOPIC_DRY_RUN,
        mode=MODE_DRY_RUN,
        cluster_id=cluster_id,
        registry_id=None,
        storage_id=None,
        request_id=request_id,
        as_json=as_json,
        runner=_runner,
    )


@topic_app.command("apply")
def topic_apply(
    cluster_id: Annotated[str, typer.Option("--cluster-id", help="Kafka cluster identifier")],
    file_path: FileOption = None,
    as_json: JsonOption = False,
) -> None:
    try:
        payload = _load_payload(file_path=file_path)
        parsed = _parse_payload_mapping(payload)
        request = TopicBatchRequest.model_validate(parsed)
    except Exception as exc:
        _emit_error_envelope(
            command=COMMAND_TOPIC_APPLY,
            mode=MODE_APPLY,
            cluster_id=cluster_id,
            registry_id=None,
            storage_id=None,
            request_id="unknown",
            as_json=as_json,
            error=exc,
        )

    request_id = str(request.change_id)
    transport = _build_transport()

    async def _runner() -> dict[str, object]:
        raw_result = await transport.topic_apply(cluster_id, request, DEFAULT_USER)
        if not isinstance(raw_result, DomainTopicApplyResult):
            raise TypeError("unexpected topic apply result type")
        return translate_topic_apply_result(
            request_id=request_id,
            cluster_id=cluster_id,
            result=raw_result,
            risk=_extract_metadata(raw_result, "risk"),
            approval=_extract_metadata(raw_result, "approval"),
        )

    _run_with_envelope(
        command=COMMAND_TOPIC_APPLY,
        mode=MODE_APPLY,
        cluster_id=cluster_id,
        registry_id=None,
        storage_id=None,
        request_id=request_id,
        as_json=as_json,
        runner=_runner,
    )


@schema_app.command("dry-run")
def schema_dry_run(
    registry_id: Annotated[str, typer.Option("--registry-id", help="Schema registry identifier")],
    file_path: FileOption = None,
    as_json: JsonOption = False,
) -> None:
    try:
        payload = _load_payload(file_path=file_path)
        parsed = _parse_payload_mapping(payload)
        request = SchemaBatchRequest.model_validate(parsed)
    except Exception as exc:
        _emit_error_envelope(
            command=COMMAND_SCHEMA_DRY_RUN,
            mode=MODE_DRY_RUN,
            cluster_id=None,
            registry_id=registry_id,
            storage_id=None,
            request_id="unknown",
            as_json=as_json,
            error=exc,
        )

    request_id = str(request.change_id)
    transport = _build_transport()

    async def _runner() -> dict[str, object]:
        raw_result = await transport.schema_dry_run(registry_id, request, DEFAULT_USER)
        if not isinstance(raw_result, DomainSchemaPlan):
            raise TypeError("unexpected schema dry-run result type")
        return translate_schema_dry_run_result(
            request_id=request_id,
            registry_id=registry_id,
            result=raw_result,
            risk=_extract_metadata(raw_result, "risk"),
            approval=_extract_metadata(raw_result, "approval"),
        )

    _run_with_envelope(
        command=COMMAND_SCHEMA_DRY_RUN,
        mode=MODE_DRY_RUN,
        cluster_id=None,
        registry_id=registry_id,
        storage_id=None,
        request_id=request_id,
        as_json=as_json,
        runner=_runner,
    )


@schema_app.command("apply")
def schema_apply(
    registry_id: Annotated[str, typer.Option("--registry-id", help="Schema registry identifier")],
    storage_id: Annotated[str, typer.Option("--storage-id", help="Storage identifier")],
    file_path: FileOption = None,
    as_json: JsonOption = False,
) -> None:
    try:
        payload = _load_payload(file_path=file_path)
        parsed = _parse_payload_mapping(payload)
        request = SchemaBatchRequest.model_validate(parsed)
    except Exception as exc:
        _emit_error_envelope(
            command=COMMAND_SCHEMA_APPLY,
            mode=MODE_APPLY,
            cluster_id=None,
            registry_id=registry_id,
            storage_id=storage_id,
            request_id="unknown",
            as_json=as_json,
            error=exc,
        )

    request_id = str(request.change_id)
    transport = _build_transport()

    async def _runner() -> dict[str, object]:
        raw_result = await transport.schema_apply(registry_id, request, DEFAULT_USER, storage_id)
        if not isinstance(raw_result, DomainSchemaApplyResult):
            raise TypeError("unexpected schema apply result type")
        return translate_schema_apply_result(
            request_id=request_id,
            registry_id=registry_id,
            storage_id=storage_id,
            result=raw_result,
            risk=_extract_metadata(raw_result, "risk"),
            approval=_extract_metadata(raw_result, "approval"),
        )

    _run_with_envelope(
        command=COMMAND_SCHEMA_APPLY,
        mode=MODE_APPLY,
        cluster_id=None,
        registry_id=registry_id,
        storage_id=storage_id,
        request_id=request_id,
        as_json=as_json,
        runner=_runner,
    )


def main() -> None:
    cli_app()


if __name__ == "__main__":
    main()
