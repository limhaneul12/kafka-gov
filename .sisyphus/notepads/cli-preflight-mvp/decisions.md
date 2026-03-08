2026-03-08: Command scope is locked to four operations only, topic dry-run/apply and schema dry-run/apply, to keep Phase 1 MVP narrow.
2026-03-08: `preflight schema apply` requires explicit `--storage-id` in the CLI contract for deterministic invocation and to match current apply use-case parameters.
2026-03-08: When both stdin and `--file` are provided, the command fails fast with an input-source conflict instead of choosing precedence implicitly.
2026-03-08: The shared response contract for all four commands is fixed to six top-level keys, `contract_version`, `operation`, `risk`, `approval`, `result`, and `error`, with required `operation.identifiers` keys always present.
2026-03-08: Exit code contract is fixed to `0` success, `10` validation failure, `20` policy or approval rejection, `30` runtime dependency failure, and `99` unknown internal error.
2026-03-08: Exit code selection order is fixed to validation -> policy/approval -> runtime dependency -> unknown, and `error.code` must map to exactly one class.
2026-03-08: Apply parity is contractually fixed to re-run the full pre-apply pipeline and never inherit pass or approval outcomes from a prior dry-run when payload or environment inputs differ.
2026-03-08: `app/preflight/application/transport.py` defines one `PreflightTransport` seam with exactly four async operations: `topic_dry_run`, `topic_apply`, `schema_dry_run`, and `schema_apply`.
2026-03-08: The seam keeps orchestration minimal by delegating to injected `TopicBatchTransport` and `SchemaBatchTransport` protocols, with no policy/risk decision logic added.
2026-03-08: `TopicTransportAdapter.apply` resolves approval override with explicit-argument priority and falls back to `request.approval_override` when no explicit override is provided.
2026-03-08: `SchemaTransportAdapter.apply` is locked to passthrough semantics for Phase 2 Task 3: it forwards `storage_id` and `request.approval_override` unchanged to `SchemaBatchApplyUseCase.execute(...)` with no extra orchestration logic.
2026-03-08: Chose translator defaults that are explicit and deterministic (risk.level=none, risk.blocking fixed by path, approval.state=not_required) unless caller provides overrides, avoiding new business rules in interface translation.
2026-03-08: Implemented a Typer CLI skeleton at `app/preflight/interface/cli.py` with scope locked to `topic|schema` and `dry-run|apply`, and payload loading only (no transport execution wiring in this task).
2026-03-08: Preflight CLI now builds PreflightTransport with topic/schema adapters per invocation so all four commands execute through the seam without adding domain logic in command handlers.
2026-03-08: Payload parsing was centralized with a top-level mapping guard so all four commands share identical YAML/JSON parse-then-validate behavior without changing command options.
