"""토픽 배치 Apply 유스케이스"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict

import msgspec

from app.cluster.domain.services import IConnectionManager
from app.shared.constants import AuditAction, AuditStatus, AuditTarget, MethodType
from app.topic.infrastructure.kafka_adapter import KafkaTopicAdapter

from ...domain.models import (
    ChangeId,
    DomainTopicApplyResult,
    DomainTopicBatch,
    DomainTopicPlan,
    DomainTopicSpec,
    TopicName,
)
from ...domain.repositories.interfaces import IAuditRepository, ITopicMetadataRepository
from ...domain.services import TopicPlannerService


class TopicBatchApplyUseCase:
    """토픽 배치 Apply 유스케이스 (멀티 클러스터 지원)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ITopicMetadataRepository,
        audit_repository: IAuditRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository

    async def execute(
        self, cluster_id: str, batch: DomainTopicBatch, actor: str
    ) -> DomainTopicApplyResult:
        """배치 적용 실행 (트랜잭션 보장 개선)"""
        audit_id = str(uuid.uuid4())

        # 감사 로그 기록
        await self.audit_repository.log_topic_operation(
            change_id=batch.change_id,
            action=AuditAction.APPLY,
            target=AuditTarget.BATCH,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Apply started for {len(batch.specs)} topics",
        )

        try:
            # 1. ConnectionManager로 AdminClient 획득
            admin_client = await self.connection_manager.get_kafka_admin_client(cluster_id)

            # 2. Adapter 생성
            topic_repository = KafkaTopicAdapter(admin_client)

            # 3. Planner Service 생성 및 계획 재생성
            planner_service = TopicPlannerService(topic_repository)
            plan = await planner_service.create_plan(batch, actor)

            # 에러 위반이 있으면 적용 중단
            if not plan.can_apply:
                error_violations = [v.message for v in plan.error_violations]
                raise ValueError(f"Cannot apply due to policy violations: {error_violations}")

            # Plan과 현재 상태 일치 검증 (경쟁 조건 방지)
            await self._validate_plan_consistency(topic_repository, plan, batch.specs)

            # 토픽 적용 실행
            applied, skipped, failed = await self._apply_topics(
                topic_repository, batch.specs, actor, batch.change_id
            )

            # 결과 생성
            result = DomainTopicApplyResult(
                change_id=batch.change_id,
                env=batch.env,
                applied=tuple(applied),
                skipped=tuple(skipped),
                failed=tuple(failed),
                audit_id=audit_id,
            )

            # 결과 저장
            await self.metadata_repository.save_apply_result(result, actor)

            # 단일 vs 배치 판단
            is_single = len(batch.specs) == 1
            method = MethodType.SINGLE if is_single else MethodType.BATCH

            # 액션별로 그룹화 (스냅샷용)
            actions_map: defaultdict[str, list[str]] = defaultdict(list)
            for spec in batch.specs:
                if spec.name in applied:
                    actions_map[spec.action.value.upper()].append(spec.name)

            # 상태 결정: 실패가 있으면 PARTIALLY_COMPLETED
            if len(failed) > 0 and len(applied) > 0:
                final_status = AuditStatus.PARTIALLY_COMPLETED
            elif len(applied) == 0:
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
                snapshot={
                    "method": method,
                    "total_count": len(applied),
                    "failed_count": len(failed),
                    "actions": dict(actions_map),
                    "failed_details": failed,  # 실패 상세 정보
                    "apply_summary": result.summary(),
                },
            )

            # 부분 실패 허용 - 결과 반환 (failed 포함)
            return result

        except Exception as e:
            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Apply failed: {e!s}",
            )
            raise

    async def _validate_plan_consistency(
        self,
        topic_repository: KafkaTopicAdapter,
        plan: DomainTopicPlan,
        specs: tuple[DomainTopicSpec, ...],
    ) -> None:
        """계획 일관성 검증 (경쟁 조건 방지)

        Plan 생성 시점과 Apply 시점 사이에 토픽 상태 변경 검증
        """
        topic_names = [spec.name for spec in specs]
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
        specs: tuple[DomainTopicSpec, ...],
        actor: str,
        change_id: ChangeId,
    ) -> tuple[list[TopicName], list[TopicName], list[dict[str, str]]]:
        """토픽 적용 실행 (트랜잭션 개선)"""
        created_topics: list[TopicName] = []  # 롤백용
        applied: list[TopicName] = []
        skipped: list[TopicName] = []
        failed: list[dict[str, str]] = []

        # 액션별로 그룹화
        create_specs: list[DomainTopicSpec] = [
            s for s in specs if s.action.value in ("create", "upsert")
        ]
        delete_specs: list[DomainTopicSpec] = [s for s in specs if s.action.value == "delete"]
        update_specs: list[DomainTopicSpec] = [
            s for s in specs if s.action.value in ("update", "upsert")
        ]

        # 토픽 생성 (트랜잭션 보장)
        if create_specs:
            create_results = await topic_repository.create_topics(create_specs)
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
                        team = spec.metadata.owner if spec.metadata else None
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
                team = spec.metadata.owner if spec.metadata else None
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
                        name,
                        AuditAction.DELETE,
                        actor,
                        change_id,
                        AuditStatus.FAILED,
                        str(error),
                        team=team,
                    )

        # 토픽 설정 변경
        if update_specs:
            # 파티션 수 변경
            partition_changes = {}
            config_changes = {}

            for spec in update_specs:
                if spec.config:
                    # 현재 토픽 정보 조회
                    current_topics = await topic_repository.describe_topics([spec.name])
                    current_topic = current_topics.get(spec.name)

                    if current_topic:
                        current_partitions = current_topic.get("partition_count", 0)
                        if spec.config.partitions > current_partitions:
                            partition_changes[spec.name] = spec.config.partitions

                        # 설정 변경
                        config_changes[spec.name] = spec.config.to_kafka_config()

            # 파티션 수 변경 실행
            if partition_changes:
                partition_results = await topic_repository.create_partitions(partition_changes)
                for spec in update_specs:
                    if spec.name in partition_results:
                        error = partition_results[spec.name]
                        team = spec.metadata.owner if spec.metadata else None
                        if error is not None:
                            failed.append(
                                {
                                    "name": spec.name,
                                    "error": str(error),
                                    "action": "ALTER_PARTITIONS",
                                }
                            )
                            await self._log_topic_operation(
                                spec.name,
                                "ALTER_PARTITIONS",
                                actor,
                                change_id,
                                "FAILED",
                                str(error),
                                team=team,
                            )

            # 설정 변경 실행
            if config_changes:
                config_results = await topic_repository.alter_topic_configs(config_changes)

                for spec in update_specs:
                    if spec.name in config_results:
                        error = config_results[spec.name]
                        team = spec.metadata.owner if spec.metadata else None
                        if error is None:
                            # 설정 변경 성공 시 무조건 applied에 추가 (파티션 실패 여부와 무관)
                            if spec.name not in applied:  # 중복 방지
                                applied.append(spec.name)
                            await self._log_topic_operation(
                                spec.name,
                                "ALTER_CONFIG",
                                actor,
                                change_id,
                                AuditStatus.COMPLETED,
                                team=team,
                            )
                        else:
                            failed.append(
                                {"name": spec.name, "error": str(error), "action": "ALTER_CONFIG"}
                            )
                            await self._log_topic_operation(
                                spec.name,
                                "ALTER_CONFIG",
                                actor,
                                change_id,
                                AuditStatus.FAILED,
                                str(error),
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
        # msgspec.structs.asdict()를 사용하여 딕셔너리로 변환
        config_dict = msgspec.structs.asdict(spec.config) if spec.config else None

        metadata_dict = {
            "topic_name": spec.name,
            "owner": spec.metadata.owner if spec.metadata else None,
            "doc": spec.metadata.doc if spec.metadata else None,
            "tags": list(spec.metadata.tags) if spec.metadata and spec.metadata.tags else [],
            "config": config_dict,
            "created_by": actor,
            "updated_by": actor,
        }

        logger = logging.getLogger(__name__)
        logger.info(
            f"Saving topic metadata for {spec.name}: "
            f"owner={metadata_dict['owner']}, tags={metadata_dict['tags']}"
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
