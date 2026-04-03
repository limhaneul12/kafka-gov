"""스키마 배치 Apply 유스케이스"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.infra.kafka.connection_manager import IConnectionManager
from app.infra.kafka.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.domain.policies.policy_pack import DefaultSchemaPolicyPackV1
from app.shared.actor import merge_actor_metadata
from app.shared.application.use_cases import CreateApprovalRequestUseCase
from app.shared.approval import (
    ApprovalOverride,
    ApprovalRequiredError,
    assess_schema_batch_risk,
    ensure_approval,
)
from app.shared.constants import AuditAction, AuditStatus, AuditTarget
from app.shared.domain.events import SchemaRegisteredEvent
from app.shared.infrastructure.event_bus import get_event_bus

from ....domain.models import (
    ChangeId,
    DomainPlanAction,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaBatch,
    DomainSchemaPlan,
    DomainSchemaSpec,
)
from ....domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaPolicyRepository,
)
from ....domain.services import SchemaPlannerService


class SchemaBatchApplyUseCase:
    """스키마 배치 Apply 유스케이스 (멀티 레지스트리/스토리지 지원)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
        policy_repository: ISchemaPolicyRepository | None = None,
        approval_request_use_case: CreateApprovalRequestUseCase | None = None,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.policy_repository = policy_repository
        self.approval_request_use_case = approval_request_use_case
        self.event_bus = get_event_bus()

    async def execute(
        self,
        registry_id: str,
        storage_id: str | None,
        batch: DomainSchemaBatch,
        actor: str,
        approval_override: ApprovalOverride | None = None,
        actor_context: dict[str, str] | None = None,
    ) -> DomainSchemaApplyResult:
        audit_id = str(uuid.uuid4())
        approval_context = {
            "risk": {"requires_approval": False, "reasons": []},
            "approval_override": (
                approval_override.to_audit_dict() if approval_override is not None else None
            ),
        }
        await self.audit_repository.log_operation(
            change_id=batch.change_id,
            action=AuditAction.APPLY,
            target=AuditTarget.BATCH,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Schema apply started for {len(batch.specs)} subjects",
            snapshot=merge_actor_metadata(None, actor_context),
        )

        try:
            # 1. ConnectionManager로 Schema Registry Client 획득
            registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
            registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

            # 2. Planner Service 생성 및 계획 수립
            planner_service = SchemaPlannerService(
                registry_repository=registry_repository,
                policy_repository=self.policy_repository,
            )
            plan = await planner_service.create_plan(batch)
            policy_pack_result = DefaultSchemaPolicyPackV1().evaluate(batch, plan)
            plan = DomainSchemaPlan(
                change_id=plan.change_id,
                env=plan.env,
                items=plan.items,
                compatibility_reports=plan.compatibility_reports,
                impacts=plan.impacts,
                violations=policy_pack_result.violations,
                risk=policy_pack_result.evaluation.risk_metadata(),
                approval=policy_pack_result.evaluation.approval_metadata(
                    mode="apply",
                    approval_override_present=approval_override is not None,
                ),
                policy_evaluation=policy_pack_result.evaluation,
                requested_total=plan.requested_total,
                actor_context=actor_context,
            )
            await self.metadata_repository.save_plan(plan, actor)

            approval_context = ensure_approval(
                plan.policy_evaluation
                if plan.policy_evaluation is not None
                else assess_schema_batch_risk(batch, plan),
                approval_override,
            )

            if not plan.can_apply:
                if plan.policy_evaluation is not None:
                    reasons = "; ".join(plan.policy_evaluation.reasons[:3])
                    raise RuntimeError(f"policy blocked: {reasons}")
                raise ValueError("Policy violations or incompatibilities detected; apply aborted")

            registered: list[str] = []
            skipped: list[str] = []
            failed: list[dict[str, str]] = []
            artifacts: list[DomainSchemaArtifact] = []
            specs_by_subject = {spec.subject: spec for spec in batch.specs}
            actionable_items = [
                item
                for item in plan.items
                if item.action is not DomainPlanAction.NONE
                and not specs_by_subject[item.subject].dry_run_only
            ]

            skipped.extend(
                item.subject
                for item in plan.items
                if item.action is DomainPlanAction.NONE
                or specs_by_subject[item.subject].dry_run_only
            )

            for item in actionable_items:
                spec = specs_by_subject[item.subject]

                try:
                    version, schema_id = await registry_repository.register_schema(spec)  # type: ignore[arg-type]

                    # MinIO 사용 없이 Artifact 메타데이터만 저장
                    artifact = await self._persist_artifact(spec, version, batch.change_id)
                    artifacts.append(artifact)
                    registered.append(spec.subject)

                    # 🆕 Domain Event 발행
                    await self._publish_schema_registered_event(
                        spec=spec,
                        version=version,
                        schema_id=schema_id,
                        batch=batch,
                        actor=actor,
                    )

                except Exception as exc:
                    failed.append({"subject": spec.subject, "error": str(exc)})

            result = DomainSchemaApplyResult(
                change_id=batch.change_id,
                env=batch.env,
                registered=tuple(registered),
                skipped=tuple(skipped),
                failed=tuple(failed),
                audit_id=audit_id,
                artifacts=tuple(artifacts),
                risk=plan.policy_evaluation.risk_metadata()
                if plan.policy_evaluation is not None
                else None,
                approval=approval_context.get("approval")
                if isinstance(approval_context.get("approval"), dict)
                else None,
                policy_evaluation=plan.policy_evaluation,
                requested_total=len(batch.specs),
                planned_total=len(actionable_items),
                warning_total=plan.policy_evaluation.warning_count
                if plan.policy_evaluation is not None
                else None,
                details=tuple(self._build_result_details(batch, plan, registered, skipped, failed)),
                actor_context=actor_context,
            )

            await self.metadata_repository.save_apply_result(result, actor)
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message="Schema apply completed",
                snapshot=merge_actor_metadata(
                    {
                        "summary": result.summary(),
                        "requested_items": [
                            {
                                "subject": spec.subject,
                                "reason": spec.reason,
                            }
                            for spec in batch.specs
                        ],
                        "policy_pack": plan.policy_evaluation.to_audit_dict()
                        if plan.policy_evaluation is not None
                        else None,
                        **approval_context,
                    },
                    actor_context,
                ),
            )

            return result
        except ApprovalRequiredError as exc:
            request = await self._create_approval_request(
                registry_id=registry_id,
                batch=batch,
                actor=actor,
                error=exc,
            )
            approval_context = {
                **approval_context,
                "risk": exc.risk,
                "approval": exc.approval,
                "approval_request": request,
            }
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Schema apply failed: {exc!s}",
                snapshot=merge_actor_metadata(approval_context, actor_context),
            )
            raise
        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Schema apply failed: {exc!s}",
                snapshot=merge_actor_metadata(approval_context, actor_context),
            )
            raise

    async def _create_approval_request(
        self,
        *,
        registry_id: str,
        batch: DomainSchemaBatch,
        actor: str,
        error: ApprovalRequiredError,
    ) -> dict[str, str] | None:
        if self.approval_request_use_case is None:
            return None

        resource_name = batch.specs[0].subject if len(batch.specs) == 1 else batch.change_id
        summary = error.approval.get("summary")
        request = await self.approval_request_use_case.execute(
            resource_type="schema",
            resource_name=resource_name,
            change_type="apply",
            change_ref=batch.change_id,
            summary=summary if isinstance(summary, str) else "approval required for schema apply",
            justification="approval required for high-risk schema apply",
            requested_by=actor,
            metadata={
                "registry_id": registry_id,
                "env": batch.env.value,
                "requested_items": [spec.subject for spec in batch.specs],
                "risk": error.risk,
                "approval": error.approval,
            },
        )
        return {
            "request_id": request.request_id,
            "status": request.status,
            "resource_type": request.resource_type,
        }

    def _build_result_details(
        self,
        batch: DomainSchemaBatch,
        plan: DomainSchemaPlan,
        registered: list[str],
        skipped: list[str],
        failed: list[dict[str, str]],
    ) -> list[dict[str, str | None]]:
        plan_items_by_subject = {item.subject: item for item in plan.items}
        failed_by_subject = {
            item.get("subject"): item.get("error")
            for item in failed
            if isinstance(item.get("subject"), str)
        }
        details: list[dict[str, str | None]] = []

        for spec in batch.specs:
            plan_item = plan_items_by_subject.get(spec.subject)
            details.append(
                {
                    "subject": spec.subject,
                    "action": plan_item.action.value
                    if plan_item is not None
                    else DomainPlanAction.NONE.value,
                    "status": (
                        "applied"
                        if spec.subject in registered
                        else "failed"
                        if spec.subject in failed_by_subject
                        else "skipped"
                    ),
                    "reason": spec.reason,
                    "error_message": failed_by_subject.get(spec.subject),
                }
            )

        return details

    async def _persist_artifact(
        self,
        spec: DomainSchemaSpec,
        version: int,
        change_id: ChangeId,
    ) -> DomainSchemaArtifact:
        """스키마 Artifact 메타데이터 저장 (외부 Object Storage 미사용).

        storage_url은 항상 None으로 유지하고, checksum과 기본 메타만 기록한다.
        """
        checksum = spec.schema_hash or spec.fingerprint()

        artifact = DomainSchemaArtifact(
            subject=spec.subject,
            version=version,
            storage_url=None,
            checksum=checksum,
        )
        await self.metadata_repository.record_artifact(artifact, change_id)
        return artifact

    async def _publish_schema_registered_event(
        self,
        spec: DomainSchemaSpec,
        version: int,
        schema_id: int,
        batch: DomainSchemaBatch,
        actor: str,
    ) -> None:
        """스키마 등록 이벤트 발행

        Args:
            schema_id: register_schema에서 받은 스키마 ID (중복 조회 없이 직접 전달)
        """
        event = SchemaRegisteredEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            aggregate_id=batch.change_id,
            occurred_at=datetime.now(),
            subject=spec.subject,
            version=version,
            schema_type=spec.schema_type.value,
            schema_id=schema_id,
            compatibility_mode=spec.compatibility.value,
            subject_strategy=batch.subject_strategy.value,
            environment=batch.env.value,
            actor=actor,
        )

        await self.event_bus.publish(event)
