from __future__ import annotations

from app.preflight.application.transport import SchemaBatchTransport
from app.schema.application.use_cases.batch.apply import SchemaBatchApplyUseCase
from app.schema.application.use_cases.batch.dry_run import SchemaBatchDryRunUseCase
from app.schema.interface.adapters import safe_convert_request_to_batch
from app.schema.interface.schemas.request import SchemaBatchRequest


class SchemaTransportAdapter(SchemaBatchTransport):
    def __init__(
        self,
        dry_run_use_case: SchemaBatchDryRunUseCase,
        apply_use_case: SchemaBatchApplyUseCase,
    ) -> None:
        self._dry_run_use_case: SchemaBatchDryRunUseCase = dry_run_use_case
        self._apply_use_case: SchemaBatchApplyUseCase = apply_use_case

    async def dry_run(
        self,
        registry_id: str,
        request: SchemaBatchRequest,
        actor: str,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        batch = safe_convert_request_to_batch(request)
        return await self._dry_run_use_case.execute(registry_id, batch, actor, actor_context)

    async def apply(
        self,
        registry_id: str,
        request: SchemaBatchRequest,
        actor: str,
        storage_id: str | None,
        *,
        actor_context: dict[str, str] | None = None,
    ) -> object:
        batch = safe_convert_request_to_batch(request)
        return await self._apply_use_case.execute(
            registry_id,
            storage_id,
            batch,
            actor,
            request.approval_override,
            actor_context,
        )
