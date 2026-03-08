# Preflight CLI Command Contract

This contract defines the MVP CLI surface for preflight operations. Scope is limited to four commands only:

- `preflight topic dry-run`
- `preflight topic apply`
- `preflight schema dry-run`
- `preflight schema apply`

## Command Matrix

| Command | Required identifiers | Payload source |
| --- | --- | --- |
| `preflight topic dry-run` | `cluster_id` | `--file <path>` or stdin |
| `preflight topic apply` | `cluster_id` | `--file <path>` or stdin |
| `preflight schema dry-run` | `registry_id` | `--file <path>` or stdin |
| `preflight schema apply` | `registry_id`, `storage_id` | `--file <path>` or stdin |

## Canonical Syntax

```bash
preflight topic dry-run --cluster-id <cluster_id> [--file <path>]
preflight topic apply --cluster-id <cluster_id> [--file <path>]
preflight schema dry-run --registry-id <registry_id> [--file <path>]
preflight schema apply --registry-id <registry_id> --storage-id <storage_id> [--file <path>]
```

Identifier flag mapping:

- `cluster_id` is passed as `--cluster-id` for topic commands.
- `registry_id` is passed as `--registry-id` for schema commands.
- `storage_id` is passed as `--storage-id` for `preflight schema apply`.

## Payload Input Rules

All four commands follow the same deterministic input behavior:

1. If `--file <path>` is provided, read payload from that file.
2. If `--file` is not provided and stdin is piped, read payload from stdin.
3. If both `--file` and piped stdin are provided, fail fast before execution with an input-source conflict error.
4. If neither `--file` nor piped stdin is provided, fail fast with a missing-payload error.

These rules guarantee a single unambiguous input source per invocation, which keeps CI behavior deterministic.

## Dry-run and Apply Parity Rules

For both topic commands and schema commands, `dry-run` and `apply` share one pre-apply contract. A previous `dry-run` success never permits `apply` to skip checks.

Required sequencing for every `apply` invocation:

1. Run all pre-apply validation checks (`--file` or stdin source rules, required identifiers, payload parse, and semantic validation).
2. Run policy and risk evaluation using the same rule set and blocking semantics used by `dry-run`.
3. Run approval gate evaluation using the same required-state semantics used by `dry-run`.
4. Execute mutations only when steps 1 through 3 are non-blocking.
5. Emit envelope and exit code according to the existing matrix, with no apply-only bypass path.

Parity invariants:

- Validation parity: `apply` MUST execute the complete validation path that `dry-run` uses for the same command family.
- Policy or risk parity: `apply` MUST use the same policy predicates, risk classification logic, and blocking thresholds that `dry-run` uses.
- Approval parity: required, expired, or rejected approval states MUST block `apply` under the same approval gate semantics. Expired approval evidence is treated as non-valid approval evidence and cannot authorize execution.
- Deterministic summary and count parity: when identifiers, payload content, policy context, and dependency state are unchanged, both modes MUST produce consistent pre-execution summaries and matching `result.counts.total`, `result.counts.planned`, `result.counts.unchanged`, and `result.counts.warnings`. `result.counts.applied` remains mode-specific (`0` in `dry-run`, runtime-derived in `apply`).

Incompatibility handling rule:

- If payload content, identifiers, execution environment, or policy inputs differ between a prior `dry-run` and a later `apply`, the prior `dry-run` is non-authoritative for gating. `apply` MUST re-run full pre-apply evaluation and MUST NOT inherit pass status or approval outcomes from the prior run.

## Command Examples

```bash
# 1) preflight topic dry-run
preflight topic dry-run --cluster-id cl-001 --file ./manifests/topic-batch.yaml

# 2) preflight topic apply
preflight topic apply --cluster-id cl-001 --file ./manifests/topic-batch.yaml

# 3) preflight schema dry-run
cat ./manifests/schema-batch.yaml | preflight schema dry-run --registry-id reg-001

# 4) preflight schema apply
cat ./manifests/schema-batch.yaml | preflight schema apply --registry-id reg-001 --storage-id stg-001
```

## Shared JSON Response Envelope

All four commands MUST emit one JSON object using this exact top-level envelope:

- `contract_version`
- `operation`
- `risk`
- `approval`
- `result`
- `error`

Top-level rules:

- `contract_version` is fixed to `preflight.v1` for this MVP.
- `error` is `null` on success and a non-null object on failure.
- `result.status` MUST be `success` or `failed`.
- `operation.identifiers` MUST always include `cluster_id`, `registry_id`, and `storage_id` keys. Use `null` for identifiers not used by the command.

## Exit Code Matrix

Each invocation MUST return exactly one process exit code from this matrix:

| Category | Exit code | Deterministic trigger | JSON envelope alignment |
| --- | --- | --- | --- |
| success | `0` | Command completed without any blocking error condition. | `result.status` is `success` and `error` is `null`. |
| validation failure | `10` | Input source, identifier, payload, or semantic validation failed before execution can proceed. | `result.status` is `failed`; `error.code` MUST be a validation-class code such as `INPUT_SOURCE_CONFLICT` or `PAYLOAD_VALIDATION_FAILED`. |
| policy or approval rejection | `20` | Policy gate blocked execution, required approval missing, or approval explicitly rejected. | `result.status` is `failed`; `error.code` MUST be a policy or approval-class code such as `POLICY_BLOCKED` or `APPROVAL_REJECTED`. |
| runtime dependency failure | `30` | External dependency failure at runtime, including cluster or registry unavailability, auth backend failure, or dependency timeout. | `result.status` is `failed`; `error.code` MUST be a dependency-class code such as `KAFKA_UNREACHABLE`, `REGISTRY_TIMEOUT`, or `AUTH_PROVIDER_UNAVAILABLE`. |
| unknown internal error | `99` | Unclassified internal failure after known categories are evaluated. | `result.status` is `failed`; `error.code` MUST be `INTERNAL_UNKNOWN` or another stable internal-class code. |

Deterministic mapping notes:

1. Classification order is fixed: validation failure -> policy or approval rejection -> runtime dependency failure -> unknown internal error.
2. The first matched failure category in that order determines the single non-zero exit code.
3. `error.code` values MUST remain machine-stable and map to exactly one category in this matrix.
4. `error` MUST be non-null for any non-zero exit code.

### Envelope Shape

| Path | Type | Required | Semantics |
| --- | --- | --- | --- |
| `contract_version` | string | yes | Fixed contract marker, `preflight.v1`. |
| `operation.command` | string | yes | Exact invoked command, one of the four allowed commands. |
| `operation.mode` | string | yes | `dry-run` or `apply`. |
| `operation.request_id` | string | yes | Stable per-invocation identifier for traceability. |
| `operation.identifiers.cluster_id` | string or null | yes | Cluster identifier for topic commands, else `null`. |
| `operation.identifiers.registry_id` | string or null | yes | Registry identifier for schema commands, else `null`. |
| `operation.identifiers.storage_id` | string or null | yes | Storage identifier for `preflight schema apply`, else `null`. |
| `risk.level` | string | yes | `none`, `low`, `medium`, `high`, or `critical`. |
| `risk.blocking` | boolean | yes | `true` when execution is blocked by risk or policy gate. |
| `risk.summary` | string | yes | Deterministic one-line risk assessment summary. |
| `approval.required` | boolean | yes | Whether an approval gate is required for this operation. |
| `approval.state` | string | yes | `not_required`, `pending`, `approved`, or `rejected`. |
| `approval.summary` | string | yes | Deterministic one-line approval state summary. |
| `result.status` | string | yes | `success` or `failed`. |
| `result.summary` | string | yes | Deterministic one-line execution summary. |
| `result.counts.total` | integer | yes | Total items parsed from input payload. |
| `result.counts.planned` | integer | yes | Items planned for change after validation. |
| `result.counts.applied` | integer | yes | Items actually applied, `0` for dry-run. |
| `result.counts.unchanged` | integer | yes | Items that required no change. |
| `result.counts.failed` | integer | yes | Items that failed processing. |
| `result.counts.warnings` | integer | yes | Non-blocking warnings count. |
| `error.code` | string | conditional | Machine-stable failure code when `error` is non-null. |
| `error.message` | string | conditional | Human-readable failure message when `error` is non-null. |
| `error.target` | string or null | conditional | Field or domain target related to failure. |
| `error.retryable` | boolean | conditional | Whether retry can succeed without payload changes. |
| `error.details` | object | conditional | Structured failure details for CI parsing. |

### Success Example

```json
{
  "contract_version": "preflight.v1",
  "operation": {
    "command": "preflight topic dry-run",
    "mode": "dry-run",
    "request_id": "req-9fd9e5b2",
    "identifiers": {
      "cluster_id": "cl-001",
      "registry_id": null,
      "storage_id": null
    }
  },
  "risk": {
    "level": "low",
    "blocking": false,
    "summary": "1 warning, no blocking violations"
  },
  "approval": {
    "required": false,
    "state": "not_required",
    "summary": "approval gate not required for dry-run"
  },
  "result": {
    "status": "success",
    "summary": "evaluated 3 topic changes",
    "counts": {
      "total": 3,
      "planned": 3,
      "applied": 0,
      "unchanged": 0,
      "failed": 0,
      "warnings": 1
    }
  },
  "error": null
}
```

### Failure Example

```json
{
  "contract_version": "preflight.v1",
  "operation": {
    "command": "preflight schema apply",
    "mode": "apply",
    "request_id": "req-b8f74163",
    "identifiers": {
      "cluster_id": null,
      "registry_id": "reg-001",
      "storage_id": "stg-001"
    }
  },
  "risk": {
    "level": "none",
    "blocking": true,
    "summary": "execution stopped before risk evaluation"
  },
  "approval": {
    "required": false,
    "state": "not_required",
    "summary": "approval not evaluated due to input error"
  },
  "result": {
    "status": "failed",
    "summary": "request rejected before execution",
    "counts": {
      "total": 0,
      "planned": 0,
      "applied": 0,
      "unchanged": 0,
      "failed": 1,
      "warnings": 0
    }
  },
  "error": {
    "code": "INPUT_SOURCE_CONFLICT",
    "message": "Provide either --file or stdin, not both.",
    "target": "input_source",
    "retryable": true,
    "details": {
      "provided_sources": [
        "--file",
        "stdin"
      ]
    }
  }
}
```
