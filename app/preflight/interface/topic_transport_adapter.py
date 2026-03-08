from __future__ import annotations

from typing import override

from app.preflight.application.transport import TopicBatchTransport
from app.shared.approval import ApprovalOverride
from app.topic.application.batch_use_cases.batch_apply import TopicBatchApplyUseCase
from app.topic.application.batch_use_cases.batch_dry_run import TopicBatchDryRunUseCase
from app.topic.interface.adapters import safe_convert_request_to_batch
from app.topic.interface.schemas.request import TopicBatchRequest


class TopicTransportAdapter(TopicBatchTransport):
    def __init__(
        self,
        dry_run_use_case: TopicBatchDryRunUseCase,
        apply_use_case: TopicBatchApplyUseCase,
    ) -> None:
        self._dry_run_use_case: TopicBatchDryRunUseCase = dry_run_use_case
        self._apply_use_case: TopicBatchApplyUseCase = apply_use_case

    @override
    async def dry_run(self, cluster_id: str, request: TopicBatchRequest, actor: str) -> object:
        batch = safe_convert_request_to_batch(request)
        return await self._dry_run_use_case.execute(cluster_id, batch, actor)

    @override
    async def apply(
        self,
        cluster_id: str,
        request: TopicBatchRequest,
        actor: str,
        approval_override: ApprovalOverride | None = None,
    ) -> object:
        batch = safe_convert_request_to_batch(request)
        override_to_use = (
            approval_override if approval_override is not None else request.approval_override
        )
        return await self._apply_use_case.execute(cluster_id, batch, actor, override_to_use)
