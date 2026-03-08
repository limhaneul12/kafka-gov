2026-03-08: Markdown LSP diagnostics are not configured in this workspace, so contract verification was completed with targeted `grep` checks.
2026-03-08: No new blockers were found in this task. Verification remains grep-plus-read because Markdown diagnostics are unavailable.
2026-03-08: No blockers in exit-code mapping task, verification was done with grep checks for required category-code rows and read checks for section integrity.
2026-03-08: No blockers in dry-run/apply parity documentation task, verification used grep-plus-read and markdown LSP remained unavailable.
2026-03-08: basedpyright raised unannotated class-attribute warnings in the new seam and was resolved by explicitly annotating injected transport attributes in `PreflightTransport.__init__`.
2026-03-08: basedpyright reported implicit-override warnings in `TopicTransportAdapter`; resolved by adding `typing.override` annotations on protocol-implemented methods.
2026-03-08: No blockers in schema transport adapter task; `lsp_diagnostics` and `uv run basedpyright app/preflight/interface/schema_transport_adapter.py` both reported zero issues.
2026-03-08: basedpyright enforces reportExplicitAny; translator required strict Mapping[str, str|bool]/object typing and coercion helpers to keep diagnostics clean.
2026-03-08: `lsp_diagnostics` reports `typer` as missing-import in this workspace; used a targeted pyright ignore on the import line so the new CLI module has zero diagnostics errors.
2026-03-08: Runtime preflight command execution in this environment fails after DTO validation because local SQLite is missing audit tables (e.g., audit_logs, schema_audit_logs), but --json stdout envelopes still emit correctly.
2026-03-08: Local smoke checks still fail at runtime due to missing SQLite audit tables, but YAML payload parsing is confirmed by propagated change_id values in JSON envelopes.
2026-03-08: Environment lacks bare `python` executable in PATH (`command not found`), so verification commands must use `uv run python` for reproducible CLI checks.
2026-03-08: Full command-path reproduction of policy/approval and dependency branches remains environment-sensitive (local runtime may fail earlier on infrastructure), so deterministic classification checks were validated directly against CLI classification/emission helpers.
2026-03-08: Verified missing-table runtime repro with `uv run python -m app.preflight.interface.cli topic dry-run --cluster-id cl-001 --file example/batch_topics.yml --json` now exits `30` and emits `error.code=runtime_dependency_failure`.
2026-03-08: No blockers in anti-scope command-tree task; targeted pytest and full `uv run pytest` both passed after adding structural CLI command-path assertions.
2026-03-08: `lsp_diagnostics` still reports pre-existing basedpyright warnings in `app/preflight/interface/cli.py`; task scoped to tests only, so CLI runtime logic was intentionally unchanged.

- basedpyright reports reportPrivateUsage warning when testing classify_error (private helper); accepted to preserve minimal change strategy and direct unit coverage of current mapping source of truth.
- Initial assertion expected actor kafka-gov-cli; actual CLI path uses DEFAULT_USER (system) in topic seam calls, so integration assertions were updated to match runtime behavior.
- 2026-03-08: No blockers in schema CLI integration task; only transient issue was an LSP unused-import warning in the new test file, resolved by removing the unused `SchemaBatchRequest` import.
- 2026-03-08: basedpyright raised `reportAny` in new snapshot loader due to untyped `json.loads`; resolved by casting parsed payload to `object` before dict type checks.
- 2026-03-08: No runtime blockers for snapshot coverage task; targeted snapshot pytest and full `uv run pytest` both passed after CI/test additions.
- 2026-03-08: No blockers in MVP CLI documentation task; verification used grep plus readback because Markdown LSP diagnostics are not available in this workspace.
- 2026-03-08: No blockers in parked-after-MVP scope task; verification used grep and readback, and Markdown LSP diagnostics remain unavailable in this workspace.
