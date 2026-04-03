"""토픽 배치 Apply 유스케이스"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import asdict

from app.infra.kafka.connection_manager import IConnectionManager
from app.infra.kafka.kafka_adapter import KafkaTopicAdapter
from app.shared.actor import merge_actor_metadata
from app.shared.application.use_cases import CreateApprovalRequestUseCase
from app.shared.approval import (
    ApprovalOverride,
    ApprovalRequiredError,
    assess_topic_batch_risk,
    ensure_approval,
)
from app.shared.constants import AuditAction, AuditStatus, AuditTarget, MethodType
from app.shared.domain.policy_types import (
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
)
from app.topic.domain.models import (
    ChangeId,
    DomainTopicApplyResult,
    DomainTopicBatch,
    DomainTopicPlan,
    DomainTopicPlanItem,
    DomainTopicSpec,
    TopicName,
)
from app.topic.domain.policies.management import (
    IPolicyRepository,
    PolicyReference,
    PolicyStatus,
    PolicyType,
)
from app.topic.domain.policies.policy_pack import DefaultTopicPolicyPackV1
from app.topic.domain.policies.validation import PolicyResolver
from app.topic.domain.repositories.interfaces import IAuditRepository, ITopicMetadataRepository
from app.topic.domain.services import TopicPlannerService


def _translate_policy_error(error: Exception) -> str:
    """정책 검증 에러를 사용자 친화적인 메시지로 변환

    Args:
        error: 원본 에러

    Returns:
        사용자 친화적인 에러 메시지
    """
    error_str = str(error)

    # Pydantic ValidationError 파싱
    if "validation error" in error_str.lower():
        # 정책 타입 추출
        policy_type = "정책"
        if "CustomNamingRules" in error_str:
            policy_type = "Naming 정책"
        elif "CustomGuardrailPreset" in error_str:
            policy_type = "Guardrail 정책"

        # 필수 필드 추출
        missing_fields = []
        if "pattern" in error_str and "required" in error_str:
            missing_fields.append("pattern (토픽 이름 패턴)")
        if "preset_name" in error_str and "required" in error_str:
            missing_fields.append("preset_name (프리셋 이름)")
        if "version" in error_str and "required" in error_str:
            missing_fields.append("version (버전)")

        if missing_fields:
            fields_str = "\n".join(f"  • {field}" for field in missing_fields)
            return f"{policy_type}의 필수 항목이 누락되었습니다:\n{fields_str}\n\n관리자에게 문의하거나 정책을 다시 설정해주세요."

        # 기타 검증 에러
        return f"{policy_type} 설정이 올바르지 않습니다. 관리자에게 문의해주세요."

    # Guardrail policy 필드 누락
    if "missing required fields" in error_str.lower():
        return "Guardrail 정책의 필수 항목(preset_name, version)이 누락되었습니다.\n\n정책을 다시 생성하거나 관리자에게 문의해주세요."

    # 일반 에러
    return "정책 검증 중 오류가 발생했습니다. 관리자에게 문의해주세요."


class TopicBatchApplyUseCase:
    """토픽 배치 Apply 유스케이스 (멀티 클러스터 지원)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ITopicMetadataRepository,
        audit_repository: IAuditRepository,
        policy_repository: IPolicyRepository,
        approval_request_use_case: CreateApprovalRequestUseCase | None = None,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.policy_repository = policy_repository
        self.approval_request_use_case = approval_request_use_case

    async def execute(
        self,
        cluster_id: str,
        batch: DomainTopicBatch,
        actor: str,
        approval_override: ApprovalOverride | None = None,
        actor_context: dict[str, str] | None = None,
    ) -> DomainTopicApplyResult:
        """배치 적용 실행 (트랜잭션 보장 개선)"""
        audit_id = str(uuid.uuid4())
        approval_context = {
            "risk": {"requires_approval": False, "reasons": []},
            "approval_override": (
                approval_override.to_audit_dict() if approval_override is not None else None
            ),
        }

        # 감사 로그 기록
        await self.audit_repository.log_topic_operation(
            change_id=batch.change_id,
            action=AuditAction.APPLY,
            target=AuditTarget.BATCH,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Apply started for {len(batch.specs)} topics",
            snapshot=merge_actor_metadata(None, actor_context),
        )

        try:
            # 1. ConnectionManager로 AdminClient 획득
            admin_client = await self.connection_manager.get_kafka_admin_client(cluster_id)

            # 2. Adapter 생성
            topic_repository = KafkaTopicAdapter(admin_client)

            # 3. 정책 검증 (Naming + Guardrail)
            # Note: violations가 있어도 사용자가 강제 실행을 선택하면 계속 진행
            violations = await self._validate_policies(batch.specs, batch.env.value)
            if violations:
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Policy violations detected ({len(violations)} specs), "
                    "but proceeding with user confirmation (force apply)"
                )

            # 4. Planner Service 생성 및 계획 재생성
            planner_service = TopicPlannerService(topic_repository)  # type: ignore[arg-type]
            plan = await planner_service.create_plan(batch, actor)
            base_plan = DomainTopicPlan(
                change_id=plan.change_id,
                env=plan.env,
                items=plan.items,
                violations=tuple(violations) if violations else plan.violations,
                requested_total=len(batch.specs),
            )
            policy_pack_result = DefaultTopicPolicyPackV1().evaluate(batch, base_plan)
            plan = DomainTopicPlan(
                change_id=base_plan.change_id,
                env=base_plan.env,
                items=base_plan.items,
                violations=policy_pack_result.violations,
                risk=policy_pack_result.evaluation.risk_metadata(),
                approval=policy_pack_result.evaluation.approval_metadata(
                    mode="apply",
                    approval_override_present=approval_override is not None,
                ),
                policy_evaluation=policy_pack_result.evaluation,
                requested_total=base_plan.requested_total,
                actor_context=actor_context,
            )

            approval_context = ensure_approval(
                plan.policy_evaluation
                if plan.policy_evaluation is not None
                else assess_topic_batch_risk(batch, plan),
                approval_override,
            )

            # 에러 위반이 있으면 적용 중단
            if not plan.can_apply:
                if plan.policy_evaluation is not None:
                    reasons = "; ".join(plan.policy_evaluation.reasons[:3])
                    raise RuntimeError(f"policy blocked: {reasons}")
                error_violations = [v.message for v in plan.error_violations]
                raise ValueError(f"Cannot apply due to policy violations: {error_violations}")

            # Plan과 현재 상태 일치 검증 (경쟁 조건 방지)
            await self._validate_plan_consistency(topic_repository, plan)

            # 토픽 적용 실행
            applied, skipped, failed = await self._apply_topics(
                topic_repository=topic_repository,
                plan=plan,
                specs=batch.specs,
                actor=actor,
                change_id=batch.change_id,
            )

            # 결과 생성
            result = DomainTopicApplyResult(
                change_id=batch.change_id,
                env=batch.env,
                applied=tuple(applied),
                skipped=tuple(skipped),
                failed=tuple(failed),
                audit_id=audit_id,
                risk=plan.policy_evaluation.risk_metadata()
                if plan.policy_evaluation is not None
                else None,
                approval=approval_context.get("approval")
                if isinstance(approval_context.get("approval"), dict)
                else None,
                policy_evaluation=plan.policy_evaluation,
                requested_total=len(batch.specs),
                planned_total=len(plan.items),
                warning_total=plan.policy_evaluation.warning_count
                if plan.policy_evaluation is not None
                else None,
                details=tuple(self._build_result_details(batch, plan, applied, skipped, failed)),
                actor_context=actor_context,
            )

            # 결과 저장
            await self.metadata_repository.save_apply_result(result, actor)

            # 단일 vs 배치 판단
            is_single = len(batch.specs) == 1
            method = MethodType.SINGLE if is_single else MethodType.BATCH

            # 액션별로 그룹화 (스냅샷용)
            plan_actions_by_name = {item.name: item.action.value for item in plan.items}
            actions_map: defaultdict[str, list[str]] = defaultdict(list)
            for spec in batch.specs:
                if spec.name in applied:
                    actions_map[
                        plan_actions_by_name.get(spec.name, spec.action.value.upper())
                    ].append(spec.name)

            # 상태 결정: 실패가 있으면 PARTIALLY_COMPLETED
            if len(failed) > 0 and (len(applied) > 0 or len(skipped) > 0):
                final_status = AuditStatus.PARTIALLY_COMPLETED
            elif len(failed) > 0:
                final_status = AuditStatus.FAILED
            else:
                final_status = AuditStatus.COMPLETED

            # 메시지 및 대상 생성
            if is_single:
                # 단일 작업
                spec = batch.specs[0]
                action_str = spec.action.value.upper()

                # 실패 딕셔너리로 변환하여 O(n) → O(1)
                failed_dict = {f["name"]: f["error"] for f in failed}

                if spec.name in applied:
                    message = f"토픽 {action_str}: {spec.name}"
                elif spec.name in failed_dict:
                    error_msg = failed_dict[spec.name]
                    message = f"토픽 {action_str} 실패: {spec.name} - {error_msg}"
                elif spec.name in skipped:
                    message = f"토픽 변경 없음: {spec.name}"
                else:
                    message = f"토픽 {action_str}: {spec.name}"

                target = spec.name
            else:
                # 배치 작업
                action_summary = ", ".join(
                    [f"{len(topics)}개 {action}" for action, topics in actions_map.items()]
                )
                if len(failed) > 0:
                    message = f"배치 작업 부분 성공: {len(applied)}개 성공, {len(failed)}개 실패 ({action_summary})"
                elif len(skipped) > 0 and len(applied) == 0:
                    message = f"배치 작업 완료: {len(skipped)}개 변경 없음"
                else:
                    message = f"배치 작업 완료: {action_summary}"
                target = AuditTarget.BATCH

            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=target,
                actor=actor,
                status=final_status,  # 동적 상태
                message=message,
                snapshot=merge_actor_metadata(
                    {
                        "method": method,
                        "total_count": len(applied),
                        "failed_count": len(failed),
                        "actions": dict(actions_map),
                        "failed_details": failed,
                        "requested_items": [
                            {
                                "name": spec.name,
                                "action": spec.action.value.upper(),
                                "reason": spec.reason,
                            }
                            for spec in batch.specs
                        ],
                        "apply_summary": result.summary(),
                        "policy_pack": plan.policy_evaluation.to_audit_dict()
                        if plan.policy_evaluation is not None
                        else None,
                        **approval_context,
                    },
                    actor_context,
                ),
            )

            # 부분 실패 허용 - 결과 반환 (failed 포함)
            return result

        except ApprovalRequiredError as exc:
            request = await self._create_approval_request(
                cluster_id=cluster_id,
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
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Apply failed: {exc!s}",
                snapshot=merge_actor_metadata(approval_context, actor_context),
            )
            raise
        except Exception as e:
            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Apply failed: {e!s}",
                snapshot=merge_actor_metadata(approval_context, actor_context),
            )
            raise

    async def _create_approval_request(
        self,
        *,
        cluster_id: str,
        batch: DomainTopicBatch,
        actor: str,
        error: ApprovalRequiredError,
    ) -> dict[str, str] | None:
        if self.approval_request_use_case is None:
            return None

        resource_name = batch.specs[0].name if len(batch.specs) == 1 else batch.change_id
        summary = error.approval.get("summary")
        request = await self.approval_request_use_case.execute(
            resource_type="topic",
            resource_name=resource_name,
            change_type="apply",
            change_ref=batch.change_id,
            summary=summary if isinstance(summary, str) else "approval required for topic apply",
            justification="approval required for high-risk topic apply",
            requested_by=actor,
            metadata={
                "cluster_id": cluster_id,
                "env": batch.env.value,
                "requested_items": [spec.name for spec in batch.specs],
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
        batch: DomainTopicBatch,
        plan: DomainTopicPlan,
        applied: list[TopicName],
        skipped: list[TopicName],
        failed: list[dict[str, str]],
    ) -> list[dict[str, str | None]]:
        plan_items_by_name = {item.name: item for item in plan.items}
        failed_by_name = {
            item.get("name"): item.get("error")
            for item in failed
            if isinstance(item.get("name"), str)
        }
        details: list[dict[str, str | None]] = []

        for spec in batch.specs:
            plan_item = plan_items_by_name.get(spec.name)
            details.append(
                {
                    "name": spec.name,
                    "action": (
                        plan_item.action.value
                        if plan_item is not None
                        else spec.action.value.upper()
                    ),
                    "status": (
                        "applied"
                        if spec.name in applied
                        else "failed"
                        if spec.name in failed_by_name
                        else "skipped"
                    ),
                    "reason": spec.reason,
                    "error_message": failed_by_name.get(spec.name),
                }
            )

        return details

    async def _validate_plan_consistency(
        self,
        topic_repository: KafkaTopicAdapter,
        plan: DomainTopicPlan,
    ) -> None:
        """계획 일관성 검증 (경쟁 조건 방지)

        Plan 생성 시점과 Apply 시점 사이에 토픽 상태 변경 검증
        """
        topic_names = [item.name for item in plan.items]
        current_state = await topic_repository.describe_topics(topic_names)

        for item in plan.items:
            current_topic = current_state.get(item.name)

            # CREATE: 토픽이 이미 존재하면 경고
            if item.action.value == "CREATE" and current_topic is not None:
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Topic {item.name} already exists (created by another user). "
                    "Will be skipped or fail during apply."
                )

            # UPDATE: 파티션 수가 변경되었는지 확인
            if item.action.value == "ALTER" and current_topic:
                current_partitions = current_topic.get("partition_count", 0)
                expected_partitions = int(
                    item.current_config.get("partitions", 0) if item.current_config else 0
                )
                if current_partitions != expected_partitions:
                    raise ValueError(
                        f"Topic {item.name} partition count changed during dry-run. "
                        f"Expected {expected_partitions}, got {current_partitions}. "
                        "Please re-run dry-run."
                    )

    async def _apply_topics(
        self,
        topic_repository: KafkaTopicAdapter,
        plan: DomainTopicPlan,
        specs: tuple[DomainTopicSpec, ...],
        actor: str,
        change_id: ChangeId,
    ) -> tuple[list[TopicName], list[TopicName], list[dict[str, str]]]:
        """토픽 적용 실행 (트랜잭션 개선)"""
        spec_by_name = {spec.name: spec for spec in specs}
        planned_names = {item.name for item in plan.items}
        created_topics: list[TopicName] = []  # 롤백용
        applied: list[TopicName] = []
        skipped: list[TopicName] = [spec.name for spec in specs if spec.name not in planned_names]
        failed: list[dict[str, str]] = []

        # 액션별로 그룹화
        create_specs: list[DomainTopicSpec] = [
            spec_by_name[item.name] for item in plan.items if item.action.value == "CREATE"
        ]
        delete_specs: list[DomainTopicSpec] = [
            spec_by_name[item.name] for item in plan.items if item.action.value == "DELETE"
        ]
        update_plan_specs: list[tuple[DomainTopicPlanItem, DomainTopicSpec]] = [
            (item, spec_by_name[item.name]) for item in plan.items if item.action.value == "ALTER"
        ]

        # 토픽 생성 (트랜잭션 보장)
        if create_specs:
            create_results = await topic_repository.create_topics(create_specs)  # type: ignore[arg-type]
            for spec in create_specs:
                name = spec.name
                error = create_results.get(name)
                if error is None:
                    try:
                        # Kafka 생성 성공 -> 메타데이터 저장 (Critical)
                        await self._save_topic_metadata(spec, actor)
                        # 둘 다 성공하면 applied에 추가
                        applied.append(name)
                        created_topics.append(name)  # 롤백용
                        team = (
                            spec.metadata.owners[0]
                            if spec.metadata and spec.metadata.owners
                            else None
                        )
                        await self._log_topic_operation(
                            name,
                            AuditAction.CREATE,
                            actor,
                            change_id,
                            AuditStatus.COMPLETED,
                            team=team,
                        )
                    except Exception as meta_error:
                        # 메타데이터 저장 실패 -> 토픽 롤백
                        logger = logging.getLogger(__name__)
                        logger.error(
                            f"CRITICAL: Metadata save failed for {name}, rolling back topic creation",
                            exc_info=True,
                        )
                        # 토픽 삭제 시도
                        await self._rollback_topic(topic_repository, name)
                        failed.append(
                            {
                                "name": name,
                                "error": f"메타데이터 저장 실패: {meta_error!s}",
                                "action": "CREATE",
                            }
                        )
                        await self._log_topic_operation(
                            name,
                            AuditAction.CREATE,
                            actor,
                            change_id,
                            AuditStatus.FAILED,
                            f"메타데이터 저장 실패: {meta_error!s}",
                        )
                else:
                    error_str = str(error)
                    # 중복 토픽 에러 메시지 개선
                    if "already exists" in error_str or "TOPIC_ALREADY_EXISTS" in error_str:
                        error_msg = (
                            f"토픽 '{name}'이(가) 이미 존재합니다. 다른 이름을 사용해주세요."
                        )
                    else:
                        error_msg = error_str

                    failed.append({"name": name, "error": error_msg, "action": "CREATE"})
                    await self._log_topic_operation(
                        name, AuditAction.CREATE, actor, change_id, AuditStatus.FAILED, error_msg
                    )

        # 토픽 삭제
        if delete_specs:
            delete_names = [s.name for s in delete_specs]
            delete_results = await topic_repository.delete_topics(delete_names)
            for spec in delete_specs:
                name = spec.name
                error = delete_results.get(name)
                team = spec.metadata.owners[0] if spec.metadata and spec.metadata.owners else None
                if error is None:
                    applied.append(name)
                    await self._log_topic_operation(
                        name, AuditAction.DELETE, actor, change_id, AuditStatus.COMPLETED, team=team
                    )
                    # 메타데이터도 삭제
                    await self._delete_topic_metadata(name)
                else:
                    failed.append({"name": name, "error": str(error), "action": "DELETE"})
                    await self._log_topic_operation(
                        name=name,
                        action=AuditAction.DELETE,
                        actor=actor,
                        change_id=change_id,
                        status=AuditStatus.FAILED,
                        message=str(error),
                        team=team,
                    )

        # 토픽 설정 변경
        if update_plan_specs:
            # 파티션 수 변경
            partition_changes = {}
            config_changes = {}

            for item, spec in update_plan_specs:
                if spec.config is None:
                    continue

                current_partitions = int(
                    item.current_config.get("partitions", 0) if item.current_config else 0
                )
                target_partitions = int(
                    item.target_config.get("partitions", current_partitions)
                    if item.target_config
                    else current_partitions
                )
                if target_partitions > current_partitions:
                    partition_changes[spec.name] = target_partitions

                target_config = item.target_config or {}
                mutable_config = {
                    key: value
                    for key, value in target_config.items()
                    if key not in {"partitions", "replication_factor", "replication.factor"}
                }
                if mutable_config:
                    config_changes[spec.name] = mutable_config

            # 파티션 수 변경 실행
            if partition_changes:
                partition_results = await topic_repository.create_partitions(partition_changes)
                for _item, spec in update_plan_specs:
                    if spec.name in partition_results:
                        error = partition_results[spec.name]
                        team = (
                            spec.metadata.owners[0]
                            if spec.metadata and spec.metadata.owners
                            else None
                        )
                        if error is not None:
                            failed.append(
                                {
                                    "name": spec.name,
                                    "error": str(error),
                                    "action": "ALTER_PARTITIONS",
                                }
                            )
                            await self._log_topic_operation(
                                name=spec.name,
                                action="ALTER_PARTITIONS",
                                actor=actor,
                                change_id=change_id,
                                status=AuditStatus.FAILED,
                                message=str(error),
                                team=team,
                            )

            # 설정 변경 실행
            if config_changes:
                config_results = await topic_repository.alter_topic_configs(config_changes)

                for _item, spec in update_plan_specs:
                    if spec.name in config_results:
                        error = config_results[spec.name]
                        team = (
                            spec.metadata.owners[0]
                            if spec.metadata and spec.metadata.owners
                            else None
                        )
                        if error is None:
                            # 설정 변경 성공 시 무조건 applied에 추가 (파티션 실패 여부와 무관)
                            if spec.name not in applied:  # 중복 방지
                                applied.append(spec.name)
                            await self._log_topic_operation(
                                name=spec.name,
                                action="ALTER_CONFIG",
                                actor=actor,
                                change_id=change_id,
                                status=AuditStatus.COMPLETED,
                                team=team,
                            )
                        else:
                            failed.append(
                                {"name": spec.name, "error": str(error), "action": "ALTER_CONFIG"}
                            )
                            await self._log_topic_operation(
                                name=spec.name,
                                action="ALTER_CONFIG",
                                actor=actor,
                                change_id=change_id,
                                status=AuditStatus.FAILED,
                                message=str(error),
                                team=team,
                            )

        return applied, skipped, failed

    async def _log_topic_operation(
        self,
        name: TopicName,
        action: str,
        actor: str,
        change_id: ChangeId,
        status: str,
        message: str | None = None,
        team: str | None = None,
    ) -> None:
        """토픽 작업 로그 기록"""
        await self.audit_repository.log_topic_operation(
            change_id=change_id,
            action=action,
            target=name,
            actor=actor,
            status=status,
            message=message,
            team=team,
        )

    async def _rollback_topic(
        self, topic_repository: KafkaTopicAdapter, topic_name: TopicName
    ) -> None:
        """토픽 롤백 (메타데이터 저장 실패 시)"""
        try:
            logger = logging.getLogger(__name__)
            logger.warning(f"Rolling back topic creation: {topic_name}")
            await topic_repository.delete_topics([topic_name])
            logger.info(f"Successfully rolled back topic: {topic_name}")
        except Exception as rollback_error:
            logger = logging.getLogger(__name__)
            logger.error(
                f"CRITICAL: Failed to rollback topic {topic_name}: {rollback_error}",
                exc_info=True,
            )
            # 롤백 실패는 예외를 발생시키지 않음 (운영 개입 필요)

    async def _save_topic_metadata(self, spec: DomainTopicSpec, actor: str) -> None:
        """토픽 메타데이터 저장 (Critical - 예외 발생)"""
        # 메타데이터 딕셔너리 생성
        # dataclasses.asdict()를 사용하여 딕셔너리로 변환
        config_dict = asdict(spec.config) if spec.config else None

        metadata_dict = {
            "topic_name": spec.name,
            "owners": list(spec.metadata.owners) if spec.metadata and spec.metadata.owners else [],
            "doc": spec.metadata.doc if spec.metadata else None,
            "tags": list(spec.metadata.tags) if spec.metadata and spec.metadata.tags else [],
            "slo": spec.metadata.slo if spec.metadata else None,
            "sla": spec.metadata.sla if spec.metadata else None,
            "config": config_dict,
            "created_by": actor,
            "updated_by": actor,
        }

        logger = logging.getLogger(__name__)
        logger.info(
            f"Saving topic metadata for {spec.name}: "
            f"owners={metadata_dict['owners']}, tags={metadata_dict['tags']}"
        )

        # 예외를 호출자에게 전파 (트랜잭션 보장)
        await self.metadata_repository.save_topic_metadata(spec.name, metadata_dict)

        logger.info(f"Successfully saved topic metadata for {spec.name}")

    async def _delete_topic_metadata(self, topic_name: TopicName) -> None:
        """토픽 메타데이터 삭제"""
        try:
            logger = logging.getLogger(__name__)
            logger.info(f"Deleting topic metadata for {topic_name}")

            await self.metadata_repository.delete_topic_metadata(topic_name)

            logger.info(f"Successfully deleted topic metadata for {topic_name}")

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to delete topic metadata for {topic_name}: {e}", exc_info=True)

    async def _validate_policies(
        self, specs: tuple[DomainTopicSpec, ...], env: str
    ) -> list[DomainPolicyViolation]:
        """정책 검증 (Naming + Guardrail)

        로직:
        1. ACTIVE naming 정책이 있으면 naming 검증
        2. ACTIVE guardrail 정책이 있으면 guardrail 검증
        3. 둘 다 없으면 스킵

        Returns:
            violations 리스트 (빈 리스트면 정책 없음 또는 모두 통과)
        """
        logger = logging.getLogger(__name__)

        try:
            naming_policy = await self._get_active_policy(PolicyType.NAMING, env)
            guardrail_policy = await self._get_active_policy(PolicyType.GUARDRAIL, env)

            # 2. 정책이 하나도 없으면 스킵
            if not naming_policy and not guardrail_policy:
                logger.info("No active policies found. Skipping policy validation.")
                return []

            # 3. PolicyResolver로 Validator 생성
            resolver = PolicyResolver(
                naming_policy_repo=self.policy_repository,
                guardrail_policy_repo=self.policy_repository,
            )

            # PolicyReference 생성
            naming_ref = (
                PolicyReference(policy_id=naming_policy.policy_id) if naming_policy else None
            )
            guardrail_ref = (
                PolicyReference(policy_id=guardrail_policy.policy_id) if guardrail_policy else None
            )

            validator = await resolver.resolve(naming_ref, guardrail_ref)

            if not validator:
                logger.info("No validator created. Skipping policy validation.")
                return []

            # 4. 각 spec에 대해 검증
            all_violations: list[DomainPolicyViolation] = []
            for spec in specs:
                violations = validator.validate(spec)
                if violations:
                    all_violations.extend(violations)
                    logger.warning(
                        f"Policy violations for {spec.name}: {[v.message for v in violations]}"
                    )

            if all_violations:
                logger.error(f"Total {len(all_violations)} policy violations found")
            else:
                logger.info("All specs passed policy validation")

            return all_violations

        except Exception as e:
            logger.error(f"Policy validation error: {e}", exc_info=True)
            # 정책 검증 에러를 violations로 반환 (사용자 확인 후 강제 실행 가능)
            logger.warning(
                "Policy validation failed, returning as violations for user confirmation"
            )

            # 사용자 친화적인 에러 메시지 생성
            user_friendly_message = _translate_policy_error(e)

            return [
                DomainPolicyViolation(
                    resource_type=DomainResourceType.TOPIC,
                    resource_name="POLICY_CONFIG_ERROR",
                    rule_id="policy.configuration.invalid",
                    message=user_friendly_message,
                    severity=DomainPolicySeverity.ERROR,
                    field=None,
                )
            ]

    async def _get_active_policy(self, policy_type: PolicyType, env: str):
        policies = await self.policy_repository.list_policies(
            policy_type=policy_type,
            status=PolicyStatus.ACTIVE,
        )

        for policy in policies:
            if policy.target_environment == env:
                return policy

        for policy in policies:
            if policy.target_environment == "total":
                return policy

        return None
