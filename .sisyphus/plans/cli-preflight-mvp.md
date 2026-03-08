# CLI Preflight MVP Plan

## Goal
Deliver a CLI-first preflight gate for topic and schema dry-run/apply that reuses existing risk and approval semantics, returns deterministic JSON, and behaves safely in CI.

## Scope Lock

### In Scope
- Topic dry-run and apply via CLI
- Schema dry-run and apply via CLI, minimal surface only
- Existing shared risk and approval gate semantics parity
- CLI contract with stable exit codes and machine-readable JSON
- Tests, CI, and docs updates that are directly required for this MVP

### Out of Scope
- RBAC, multi-tenancy, GitOps roadmap work
- Connect workflows, monitoring workflows, dashboard/UI-heavy surfaces
- New product strategy or non-MVP feature expansion

## Ordered Checklist

### Phase 1, Contract First (must finish before Phase 2)
- [x] Define the CLI command contract for exactly four operations: `preflight topic dry-run`, `preflight topic apply`, `preflight schema dry-run`, `preflight schema apply`, including required identifiers and input source rules.
- [x] Define one stable JSON response envelope shared by all commands, including operation metadata, risk/approval fields, result summaries, and error payload shape.
- [x] Define and document a strict exit code matrix for success, validation failure, policy or approval rejection, runtime dependency failure, and unknown internal error.
- [x] Define dry-run/apply parity rules so apply never bypasses checks already enforced by existing use cases and shared approval semantics.

### Phase 2, Transport Seam (starts only after Phase 1 is complete)
- [x] Introduce a CLI-facing transport seam with exactly four methods that delegate to existing topic and schema use cases, without adding domain logic in CLI handlers.
- [x] Implement topic transport adapters that call existing topic dry-run/apply use cases and pass approval overrides through unchanged.
- [x] Implement schema transport adapters that call existing schema dry-run/apply use cases in minimal mode only, with no expansion into schema dashboard or analytics behavior.
- [x] Implement deterministic result and error translators from use-case outputs into the Phase 1 JSON contract.

### Phase 3, CLI Wiring (starts only after Phase 2 is complete)
- [x] Add a CLI entrypoint and command tree for `preflight topic` and `preflight schema` only, with payload input support from file and stdin.
- [x] Wire each CLI command to the transport seam and ensure `--json` mode always emits valid machine-readable output on stdout.
- [x] Map command outcomes to the Phase 1 exit code contract, including approval-required and approval-expired failure paths.
- [x] Add an anti-scope guard test on the command tree so connect, monitoring, and dashboard-heavy surfaces are not exposed in MVP CLI commands.

### Phase 4, Tests, CI, and Docs (starts only after Phase 3 is complete)
- [x] Add unit tests for JSON envelope serialization, error mapping, and exit code mapping.
- [x] Add integration tests for topic dry-run/apply CLI flows against existing use-case seams, including approval-required paths.
- [x] Add integration tests for schema dry-run/apply CLI flows in minimal mode, including approval-required paths.
- [x] Add CI coverage for the new CLI preflight tests and contract snapshots to prevent response-shape drift.
- [x] Add MVP CLI documentation with exact command examples, exit code table, and JSON output samples.
- [x] Add an explicit "Parked after MVP" docs section listing connect, monitoring, and dashboard-heavy surfaces as deferred, with no implementation work in this MVP.

## Done Criteria
- [x] All four CLI commands are implemented and verified with deterministic JSON and documented exit codes.
- [x] Risk and approval behavior matches existing shared semantics, with parity tests passing for topic and schema apply.
- [x] CI enforces CLI contract stability, and docs clearly state MVP scope plus deferred surfaces.
