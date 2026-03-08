from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from typer.testing import CliRunner

from app.preflight.interface import cli


def _topic_payload(change_id: str) -> str:
    return json.dumps(
        {
            "kind": "TopicBatch",
            "env": "dev",
            "change_id": change_id,
            "items": [
                {
                    "name": "dev.orders.created",
                    "action": "create",
                    "config": {"partitions": 1, "replication_factor": 1},
                    "metadata": {"owners": ["team-platform"]},
                }
            ],
        }
    )


def _schema_payload(change_id: str) -> str:
    return json.dumps(
        {
            "kind": "SchemaBatch",
            "env": "dev",
            "change_id": change_id,
            "items": [
                {
                    "subject": "dev.orders.created-value",
                    "type": "AVRO",
                    "schema": '{"type":"record","name":"OrderCreated","fields":[{"name":"id","type":"string"}]}',
                }
            ],
        }
    )


def _parse_envelope(stdout: str) -> dict[str, object]:
    parsed = cast(object, json.loads(stdout.strip()))
    if not isinstance(parsed, dict):
        raise AssertionError("expected JSON envelope object")
    return cast(dict[str, object], parsed)


def test_topic_cli_rejects_file_and_stdin_conflict_with_validation_envelope(tmp_path: Path) -> None:
    runner = CliRunner()
    payload_path = tmp_path / "topic-batch.json"
    payload_path.write_text(_topic_payload("chg-topic-input-001"), encoding="utf-8")

    result = runner.invoke(
        cli.cli_app,
        [
            "topic",
            "dry-run",
            "--cluster-id",
            "cluster-a",
            "--file",
            str(payload_path),
            "--json",
        ],
        input=_topic_payload("chg-topic-input-stdin"),
    )

    assert result.exit_code == 10
    envelope = _parse_envelope(result.stdout)
    operation = cast(dict[str, object], envelope["operation"])
    assert operation["request_id"] != "unknown"
    assert envelope["error"] == {
        "code": "input_error",
        "message": "Provide either --file or stdin, not both.",
        "target": "payload",
        "retryable": False,
        "details": {},
    }


def test_schema_cli_requires_file_or_stdin_before_execution() -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli.cli_app,
        [
            "schema",
            "apply",
            "--registry-id",
            "registry-a",
            "--storage-id",
            "storage-a",
            "--json",
        ],
    )

    assert result.exit_code == 10
    envelope = _parse_envelope(result.stdout)
    operation = cast(dict[str, object], envelope["operation"])
    assert operation["request_id"] != "unknown"
    assert envelope["error"] == {
        "code": "input_error",
        "message": "Provide input via --file or piped stdin.",
        "target": "payload",
        "retryable": False,
        "details": {},
    }
