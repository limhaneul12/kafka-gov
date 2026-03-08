2026-03-08: The CLI preflight MVP contract is easier to implement when written as a command matrix plus canonical syntax and fixed input-source precedence rules.
2026-03-08: Existing docs style in this repo favors short sections, direct command examples, and explicit required identifiers.
2026-03-08: A fixed JSON envelope with always-present top-level keys and null-filled unused identifiers keeps parsing deterministic across all four preflight commands.
2026-03-08: CI-friendly exit behavior is easiest to consume when each failure class maps to one numeric code with explicit classification precedence.
2026-03-08: Dry-run/apply parity is clearest when expressed as fixed sequencing plus invariants, validation, policy/risk, approval, and deterministic summary/count alignment.
2026-03-08: A transport seam can stay domain-agnostic by accepting request DTO payloads and delegating directly to injected topic/schema transport ports.
2026-03-08: Topic preflight transport can remain thin by reusing `safe_convert_request_to_batch` and forwarding domain batches to existing topic use-case `execute(...)` methods.
2026-03-08: Schema preflight transport should mirror topic transport by converting `SchemaBatchRequest` with `safe_convert_request_to_batch` and delegating directly to existing schema dry-run/apply use-case `execute(...)` calls.
2026-03-08: Added app/preflight/interface/result_translator.py with deterministic envelope builders and fixed top-level key order (contract_version, operation, risk, approval, result, error) for all four preflight operations.
2026-03-08: For deterministic CLI input-source handling in CI and subprocess contexts, stdin should be treated as provided only when actual text is present, not only when `isatty()` is false.
2026-03-08: CLI command handlers can keep deterministic JSON output by routing both parse-time and runtime exceptions through translate_preflight_error and writing envelopes to stdout in --json mode.
2026-03-08: Replacing model_validate_json with yaml.safe_load + model_validate enables deterministic YAML and JSON payload acceptance from both --file and stdin in preflight CLI commands.
2026-03-08: Verified all four CLI preflight commands (`topic dry-run/apply`, `schema dry-run/apply`) emit parseable JSON envelopes on stdout in `--json` mode, with deterministic top-level keys and operation metadata present.
2026-03-08: Exit-code contract in the CLI layer is safest when classification returns both envelope `error.code` and process exit code together, preventing drift where failures emit the right JSON but wrong shell status.
2026-03-08: SQL/DB runtime operational errors can arrive as non-`RuntimeError` types (e.g., `OperationalError`), so dependency classification must include exception-name matching plus message cues like `no such table` to satisfy exit-code contract.
2026-03-08: Anti-scope CLI guard is most deterministic when asserting Typer's compiled Click command tree (`typer.main.get_command(cli_app)`) rather than parsing `--help` text output.
2026-03-08: Recursive command-path collection makes MVP scope checks explicit (`topic|schema` groups and `dry-run|apply` operations) while preventing accidental exposure of connect/monitoring/dashboard surfaces.

- Added deterministic unit tests for preflight JSON envelope contracts using pure translator function calls (no transport/container execution).
- Exit-code classification tests directly cover classify_error for validation(10), policy/approval(20), runtime dependency(30), and unknown(99), including approval-required and approval-expired paths.
- Kept tests isolated from DB/external runtime by using local fake plan object and synthetic exceptions only.
- Added deterministic topic CLI integration coverage with Typer CliRunner by monkeypatching app.preflight.interface.cli._build_transport to return PreflightTransport using in-memory stub transports, avoiding DB/Kafka/network dependencies.
- Validated JSON envelope contracts for both topic dry-run and topic apply: operation command/mode/request_id identifiers plus explicit result counts and success status assertions.
- Covered approval-required apply failure path via seam error RuntimeError("approval_override is required for this operation") and asserted CLI classification emits error code approval_required with process exit code 20.
- 2026-03-08: Added schema CLI integration seam tests mirroring topic flow; monkeypatching `app.preflight.interface.cli._build_transport` with `PreflightTransport` stubs keeps tests deterministic and isolated from DB/Kafka/network.
- 2026-03-08: Minimal valid schema payload for `SchemaBatchRequest` in integration tests can use `kind/env/change_id/items` with one AVRO `schema` literal and env-prefixed subject (`dev.*`).
- 2026-03-08: Approval-required schema apply path is reproducible by raising `RuntimeError("approval_override is required for this operation")` from the schema seam stub and asserting JSON envelope `error.code=approval_required` with process exit code 20.
- 2026-03-08: Contract-drift protection is strongest when CLI envelopes are compared against committed JSON snapshots from deterministic seam stubs, covering one representative success and one representative failure path.
- 2026-03-08: CI guard is clearer when preflight CLI tests are executed explicitly (`uv run pytest tests/test_preflight_*.py`) before full-suite pytest, so contract snapshot drift fails fast with focused logs.
- 2026-03-08: MVP operator docs are easiest to consume when they keep three short sections only, exact command invocations, strict exit code mapping, and one success plus one failure envelope sample.
- 2026-03-08: Keeping JSON sample key order aligned to the contract (`contract_version`, `operation`, `risk`, `approval`, `result`, `error`) reduces ambiguity for CI parsers and reviewers.
- 2026-03-08: Explicit deferred-scope sections in MVP docs should name parked surfaces and clearly state that no implementation work is included in this MVP.
- 2026-03-08: Done-criteria closeout is evidence-complete when all four CLI commands are present in command tree/tests, approval behavior passes for both topic/schema apply paths, CI runs `tests/test_preflight_*.py`, and docs include deferred-scope MVP boundaries.
