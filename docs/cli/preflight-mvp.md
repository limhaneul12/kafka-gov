# Preflight CLI MVP Operator Guide

Use this page for CI-safe command usage and machine-readable output expectations.

## Exact Command Examples

```bash
preflight topic dry-run --cluster-id cl-001 --file ./manifests/topic-batch.yaml --json
preflight topic apply --cluster-id cl-001 --file ./manifests/topic-batch.yaml --json
preflight schema dry-run --registry-id reg-001 --file ./manifests/schema-batch.yaml --json
preflight schema apply --registry-id reg-001 --storage-id stg-001 --file ./manifests/schema-batch.yaml --json
```

## Parked after MVP

The following surfaces are deferred until after this MVP:

- connect workflows
- monitoring workflows
- dashboard-heavy surfaces

No implementation work for these surfaces is in scope for this MVP.

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
