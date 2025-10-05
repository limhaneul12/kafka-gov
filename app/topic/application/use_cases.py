"""Topic Application 유스케이스 - 비즈니스 로직 조합"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Any

from app.shared.constants import AuditAction, AuditStatus, AuditTarget, MethodType

from ..domain.models import (
    ChangeId,
    DomainTopicApplyResult,
    DomainTopicBatch,
    DomainTopicPlan,
    DomainTopicSpec,
    TopicName,
)
from ..domain.repositories.interfaces import (
    IAuditRepository,
    ITopicMetadataRepository,
    ITopicRepository,
)
from ..domain.services import TopicPlannerService

KafkaMetaDescription = dict[TopicName, dict[str, Any]]
TopicDescription = list[dict[str, Any]]


class TopicBatchDryRunUseCase:
    """토픽 배치 Dry-Run 유스케이스"""

    def __init__(
        self,
        topic_repository: ITopicRepository,
        metadata_repository: ITopicMetadataRepository,
        audit_repository: IAuditRepository,
    ) -> None:
        self.topic_repository = topic_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.planner_service = TopicPlannerService(topic_repository)

    async def execute(self, batch: DomainTopicBatch, actor: str) -> DomainTopicPlan:
        """Dry-Run 실행"""
        # 감사 로그 기록
        await self.audit_repository.log_topic_operation(
            change_id=batch.change_id,
            action=AuditAction.DRY_RUN,
            target=AuditTarget.BATCH,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Dry-run started for {len(batch.specs)} topics",
        )

        try:
            # 실행 계획 생성
            plan = await self.planner_service.create_plan(batch, actor)

            # 계획 저장
            await self.metadata_repository.save_plan(plan, actor)

            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action=AuditAction.DRY_RUN,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message=f"Dry-run completed: {len(plan.items)} items, {len(plan.violations)} violations",
                snapshot={"plan_summary": plan.summary()},
            )

            return plan

        except Exception as e:
            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action=AuditAction.DRY_RUN,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Dry-run failed: {e!s}",
            )
            raise


class TopicBatchApplyUseCase:
    """토픽 배치 Apply 유스케이스"""

    def __init__(
        self,
        topic_repository: ITopicRepository,
        metadata_repository: ITopicMetadataRepository,
        audit_repository: IAuditRepository,
    ) -> None:
        self.topic_repository = topic_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.planner_service = TopicPlannerService(topic_repository)

    async def execute(self, batch: DomainTopicBatch, actor: str) -> DomainTopicApplyResult:
        """배치 적용 실행"""
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
            # 실행 계획 재생성 및 검증
            plan = await self.planner_service.create_plan(batch, actor)

            # 에러 위반이 있으면 적용 중단
            if not plan.can_apply:
                error_violations = [v.message for v in plan.error_violations]
                raise ValueError(f"Cannot apply due to policy violations: {error_violations}")

            # 토픽 적용 실행
            applied, skipped, failed = await self._apply_topics(batch.specs, actor, batch.change_id)

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
                message = f"배치 작업 완료: {action_summary}"
                target = AuditTarget.BATCH

            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=target,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message=message,
                snapshot={
                    "method": method,
                    "total_count": len(applied),
                    "actions": dict(actions_map),  # defaultdict를 dict로 변환
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

    async def _apply_topics(
        self, specs: tuple[DomainTopicSpec, ...], actor: str, change_id: ChangeId
    ) -> tuple[list[TopicName], list[TopicName], list[dict[str, str]]]:
        """토픽 적용 실행"""
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

        # 토픽 생성
        if create_specs:
            create_results = await self.topic_repository.create_topics(create_specs)
            for spec in create_specs:
                name = spec.name
                error = create_results.get(name)
                if error is None:
                    applied.append(name)
                    await self._log_topic_operation(name, "CREATE", actor, change_id, "SUCCESS")
                    # 메타데이터 저장
                    await self._save_topic_metadata(spec, actor)
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
            delete_results = await self.topic_repository.delete_topics(delete_names)
            for name, error in delete_results.items():
                if error is None:
                    applied.append(name)
                    await self._log_topic_operation(name, "DELETE", actor, change_id, "SUCCESS")
                    # 메타데이터도 삭제
                    await self._delete_topic_metadata(name)
                else:
                    failed.append({"name": name, "error": str(error), "action": "DELETE"})
                    await self._log_topic_operation(
                        name, AuditAction.DELETE, actor, change_id, AuditStatus.FAILED, str(error)
                    )

        # 토픽 설정 변경
        if update_specs:
            # 파티션 수 변경
            partition_changes = {}
            config_changes = {}

            for spec in update_specs:
                if spec.config:
                    # 현재 토픽 정보 조회
                    current_topics = await self.topic_repository.describe_topics([spec.name])
                    current_topic = current_topics.get(spec.name)

                    if current_topic:
                        current_partitions = current_topic.get("partition_count", 0)
                        if spec.config.partitions > current_partitions:
                            partition_changes[spec.name] = spec.config.partitions

                        # 설정 변경
                        config_changes[spec.name] = spec.config.to_kafka_config()

            # 파티션 수 변경 실행
            if partition_changes:
                partition_results = await self.topic_repository.create_partitions(partition_changes)
                for name, error in partition_results.items():
                    if error is not None:
                        failed.append(
                            {"name": name, "error": str(error), "action": "ALTER_PARTITIONS"}
                        )
                        await self._log_topic_operation(
                            name, "ALTER_PARTITIONS", actor, change_id, "FAILED", str(error)
                        )

            # 설정 변경 실행
            if config_changes:
                config_results = await self.topic_repository.alter_topic_configs(config_changes)
                for name, error in config_results.items():
                    if error is None:
                        if name not in [
                            f["name"] for f in failed
                        ]:  # 파티션 변경이 실패하지 않은 경우만
                            applied.append(name)
                            await self._log_topic_operation(
                                name, "ALTER_CONFIG", actor, change_id, "SUCCESS"
                            )
                    else:
                        failed.append({"name": name, "error": str(error), "action": "ALTER_CONFIG"})
                        await self._log_topic_operation(
                            name, "ALTER_CONFIG", actor, change_id, "FAILED", str(error)
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
    ) -> None:
        """토픽 작업 로그 기록"""
        await self.audit_repository.log_topic_operation(
            change_id=change_id,
            action=action,
            target=name,
            actor=actor,
            status=status,
            message=message,
        )

    async def _save_topic_metadata(self, spec: DomainTopicSpec, actor: str) -> None:
        """토픽 메타데이터 저장"""
        try:
            # 메타데이터 딕셔너리 생성
            metadata_dict = {
                "topic_name": spec.name,
                "owner": spec.metadata.owner if spec.metadata else None,
                "doc": spec.metadata.doc if spec.metadata else None,
                "tags": list(spec.metadata.tags) if spec.metadata and spec.metadata.tags else [],
                "config": spec.config.to_dict() if spec.config else None,
                "created_by": actor,
                "updated_by": actor,
            }

            logger = logging.getLogger(__name__)
            logger.info(
                f"Saving topic metadata for {spec.name}: "
                f"owner={metadata_dict['owner']}, tags={metadata_dict['tags']}"
            )

            await self.metadata_repository.save_topic_metadata(spec.name, metadata_dict)

            logger.info(f"Successfully saved topic metadata for {spec.name}")

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save topic metadata for {spec.name}: {e}", exc_info=True)

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


class TopicListUseCase:
    """토픽 목록 조회 유스케이스"""

    def __init__(
        self,
        topic_repository: ITopicRepository,
        metadata_repository: ITopicMetadataRepository,
    ) -> None:
        self.topic_repository = topic_repository
        self.metadata_repository = metadata_repository

    async def execute(self) -> TopicDescription:
        """토픽 목록 조회"""
        # 1. Kafka에서 모든 토픽 이름 조회
        all_topics: list[TopicName] = await self.topic_repository.list_topics()

        # 2. Kafka에서 모든 토픽 상세 정보 배치 조회 (파티션수, 복제개수)
        topic_details: KafkaMetaDescription = await self.topic_repository.describe_topics(
            all_topics
        )

        # 3. DB 메타데이터와 Kafka 정보를 병합
        topics_with_metadata: TopicDescription = []
        for topic_name in all_topics:
            metadata = await self.metadata_repository.get_topic_metadata(topic_name)
            kafka_info = topic_details.get(topic_name, {})

            topics_with_metadata.append(
                {
                    "name": topic_name,
                    "owner": metadata.get("owner") if metadata else None,
                    "tags": metadata.get("tags", []) if metadata else [],
                    "partition_count": kafka_info.get("partition_count"),
                    "replication_factor": kafka_info.get("replication_factor"),
                    "environment": self._infer_environment(topic_name),
                }
            )

        return topics_with_metadata

    @staticmethod
    def _infer_environment(topic_name: str) -> str:
        """토픽 이름에서 환경 추론"""
        if topic_name.startswith("dev."):
            return "dev"
        if topic_name.startswith("stg."):
            return "stg"
        if topic_name.startswith("prod."):
            return "prod"
        return "unknown"
