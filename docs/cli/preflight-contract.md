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

Optional actor provenance flags for all four commands:

- `--user-id <user_id>`
- `--username <username>`
- `--source <source>`

Identifier flag mapping:

- `cluster_id` is passed as `--cluster-id` for topic commands.
- `registry_id` is passed as `--registry-id` for schema commands.
- `storage_id` is passed as `--storage-id` for `preflight schema apply`.

Actor provenance mapping:

- Explicit CLI flags take precedence over environment fallbacks.
- Environment fallbacks are `KAFKA_GOV_USER_ID`, `KAFKA_GOV_USERNAME`, and `KAFKA_GOV_ACTOR_SOURCE`.
- Resolved actor identity prefers `username`, then `user_id`, and falls back to `system` only when neither is supplied.
- Provenance is additive audit metadata only; it does not introduce new authorization semantics.

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

## Policy-Pack V1 Decision Contract

The four in-scope commands share one deterministic policy evaluation model.

- Policy decision precedence is fixed: `reject` -> `approval_required` -> `warn` -> `allow`.
- Risk is normalized as `none`, `low`, `medium`, `high`, or `critical`.
- A blocking policy result sets `risk.blocking = true` and prevents mutation.
- An approval-required result is non-blocking for `dry-run` visibility but blocks `apply` until a valid approval override is provided.
- Rule ordering and summary generation MUST be deterministic for identical inputs.

Default rule families currently enforced by `policy-pack v1`:

- Topic preflight: naming and guardrail policy reuse, batch `env`/topic name parity, replication minimum, replication-factor change rejection, partition decrease rejection, partition increase approval gate, retention decrease approval gate, cleanup-policy change approval gate, delete approval gate, and environment-sensitive `metadata.doc` coverage.
- Schema preflight: compatibility planner enforcement, repo-backed dynamic schema policy reuse, `compatibility: NONE` gating, metadata and `metadata.doc` coverage, required-field-without-default rejection, type-change rejection, enum narrowing approval gate, and subject/topic linkage validation.

## Request Rationale Contract

- Topic and schema requests use canonical `reason` for change rationale.
- `business_purpose` and `businessPurpose` are accepted as backward-compatible input aliases and normalize to `reason`.
- Normalized rationale is expected to flow through plan/apply details and audit snapshot metadata so dry-run, apply, and history views stay aligned.

Out-of-scope policy surfaces remain unchanged for this MVP:

- connect workflows
- monitoring or dashboard behavior
- runtime proxy or data-plane enforcement
- cluster operations outside the four preflight commands

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
| validation failure | `10` | Input source, identifier, payload, or semantic validation failed before execution can proceed. | `result.status` is `failed`; `error.code` is a validation-class code such as `input_error` or `validation_error`. |
| policy or approval rejection | `20` | Policy gate blocked execution, required approval missing, approval expired, or approval explicitly rejected. | `result.status` is `failed`; `error.code` is a policy or approval-class code such as `policy_blocked`, `approval_required`, or `approval_expired`. |
| runtime dependency failure | `30` | External dependency failure at runtime, including cluster or registry unavailability, auth backend failure, or dependency timeout. | `result.status` is `failed`; `error.code` is `runtime_dependency_failure`. |
| unknown internal error | `99` | Unclassified internal failure after known categories are evaluated. | `result.status` is `failed`; `error.code` is `internal_unknown`. |

Deterministic mapping notes:

1. Classification order is fixed: validation failure -> policy or approval rejection -> runtime dependency failure -> unknown internal error.
2. The first matched failure category in that order determines the single non-zero exit code.
3. `error.code` values MUST remain machine-stable and map to exactly one category in this matrix.
4. `error` MUST be non-null for any non-zero exit code.

Stable failure codes currently emitted by the CLI:

- Validation class: `input_error`, `validation_error`
- Policy and approval class: `policy_blocked`, `approval_required`, `approval_expired`
- Runtime dependency class: `runtime_dependency_failure`
- Internal class: `internal_unknown`

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
    "summary": "approval gate not required for this evaluation"
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
    "summary": "approval not evaluated due to failure"
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
    "code": "input_error",
    "message": "Provide either --file or stdin, not both.",
    "target": "payload",
    "retryable": false,
    "details": {}
  }
}
```

## Approval Semantics

- `approval.required = false` with `approval.state = not_required` means the requested operation is policy-clean enough to proceed without an override.
- `approval.required = true` with `approval.state = pending` means `dry-run` completed, but `apply` must not mutate until approval evidence is supplied.
- `approval.required = true` with `approval.state = approved` means a valid override was supplied and the apply request can continue.
- `approval.state = rejected` is reserved for blocking policy outcomes where mutation is denied by policy rather than held for approval.

Representative approval summaries:

- `approval gate not required for this evaluation`
- `approval required before apply for 1 rule(s)`
- `approval required for 1 rule(s)`
- `approval override supplied for 1 rule(s)`
- `policy pack rejected the requested change`
