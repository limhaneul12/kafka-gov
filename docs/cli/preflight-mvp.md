# Preflight CLI MVP Operator Guide

Use this page for CI-safe command usage and machine-readable output expectations.

## Exact Command Examples

```bash
preflight topic dry-run --cluster-id cl-001 --file ./manifests/topic-batch.yaml --json
preflight topic apply --cluster-id cl-001 --file ./manifests/topic-batch.yaml --json
preflight schema dry-run --registry-id reg-001 --file ./manifests/schema-batch.yaml --json
preflight schema apply --registry-id reg-001 --storage-id stg-001 --file ./manifests/schema-batch.yaml --json

# optional actor provenance flags
preflight topic dry-run --cluster-id cl-001 --user-id u-123 --username alice --source ci --file ./manifests/topic-batch.yaml --json
```

## Actor Provenance

- `preflight` accepts additive actor provenance through `--user-id`, `--username`, and `--source`.
- CLI environment fallbacks are `KAFKA_GOV_USER_ID`, `KAFKA_GOV_USERNAME`, and `KAFKA_GOV_ACTOR_SOURCE`.
- `system` remains a fallback actor only when no user identifier or username is supplied.
- Actor provenance is recorded as execution metadata for audit/history parity; it does not change authorization behavior.

## Rationale Fields

- Topic and schema requests accept canonical `reason`.
- `business_purpose` and `businessPurpose` are accepted as input aliases and normalize to `reason`.
- Normalized rationale is carried into plan/apply details and stored audit snapshot metadata.

## Parked after MVP

The following surfaces are deferred until after this MVP:

- connect workflows
- monitoring workflows
- dashboard-heavy surfaces

No implementation work for these surfaces is in scope for this MVP.

## Policy-Pack V1

`preflight` now acts as a policy decision point for the four MVP commands.

- The policy-pack runs after payload validation and before mutation.
- `dry-run` and `apply` use the same rule families; `apply` does not bypass `dry-run` checks.
- Rule output is deterministic and normalized as `allow`, `warn`, `approval_required`, or `reject`.
- Risk is normalized as `none`, `low`, `medium`, `high`, or `critical`.

### Default Topic Rules

- Active topic naming and guardrail policies from the repo policy store
- Topic name environment must match batch `env`
- Replication factor minimum by environment (`prod>=3`, `stg>=2`, `dev>=1`)
- Replication factor change is rejected in preflight apply
- Partition decrease is rejected
- Partition increase requires approval
- Retention decrease requires approval
- Cleanup policy change requires approval
- Delete requires approval
- `metadata.doc` missing is `warn` in `dev`, `approval_required` in `stg` and `prod`

### Default Schema Rules

- Registry compatibility result is enforced as a blocking rule
- Built-in compatibility guardrail and repo-backed dynamic policies still run through planner
- `compatibility: NONE` is rejected in `prod` and approval-required elsewhere
- Missing schema metadata is `warn` in `dev`, `approval_required` in `stg` and `prod`
- Missing `metadata.doc` is `warn` in `dev`, `approval_required` in `stg` and `prod`
- Added required field without default is rejected
- Field type change is rejected
- Enum narrowing requires approval
- Subject/topic linkage is validated for `TopicNameStrategy` and `TopicRecordNameStrategy`

### Approval Semantics

- `reject` blocks the change outright
- `approval_required` keeps `dry-run` readable but blocks `apply` until `approvalOverride` is provided
- Successful `apply` with an override emits `approval.state = approved`
- Failed `apply` due to missing approval emits exit code `20` with `error.code = approval_required`

## Supported Scope

- `preflight topic dry-run`
- `preflight topic apply`
- `preflight schema dry-run`
- `preflight schema apply`

## Not Supported In This Iteration

- connect workflows
- monitoring or dashboards
- runtime proxy or data-plane enforcement
- cluster operations outside the four preflight commands
- automatic topic rename handling
- consumer lineage beyond current subject/topic linkage and existing planner heuristics

## Exit Code Table

| Exit code | Meaning | Deterministic trigger |
| --- | --- | --- |
| `0` | success | Command completed without a blocking error. |
| `10` | validation failure | Input source, required identifiers, payload parse, or semantic validation failed before execution. |
| `20` | policy or approval rejection | Policy blocked execution, approval is required but missing, or approval was rejected. |
| `30` | runtime dependency failure | External dependency failed at runtime, for example cluster or registry unavailability, auth backend failure, or timeout. |
| `99` | unknown internal error | Unclassified internal failure after known categories were evaluated. |

## JSON Output Samples

### Success Sample (exit `0`)

```json
{
  "contract_version": "preflight.v1",
  "operation": {
    "command": "preflight topic dry-run",
    "mode": "dry-run",
    "request_id": "req-3df26e42",
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

### Failure Sample (exit `10`)

```json
{
  "contract_version": "preflight.v1",
  "operation": {
    "command": "preflight schema apply",
    "mode": "apply",
    "request_id": "req-9d8c44ab",
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

## Failure Code Examples

| Scenario | Exit | `error.code` | Example reason |
| --- | --- | --- | --- |
| Bad input source or invalid payload | `10` | `input_error` / `validation_error` | `Provide either --file or stdin, not both.` |
| Missing approval override | `20` | `approval_required` | `approval_override is required for high-risk apply operations (...)` |
| Expired approval override | `20` | `approval_expired` | `approval override has expired` |
| Policy-pack rejection | `20` | `policy_blocked` | `policy blocked: schema 'prod.orders.created-value' is incompatible...` |
| Runtime dependency failure | `30` | `runtime_dependency_failure` | `database not initialized` |
| Unknown internal error | `99` | `internal_unknown` | unclassified exception |
