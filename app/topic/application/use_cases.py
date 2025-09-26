"""Topic Application 유스케이스 - 비즈니스 로직 조합"""

from __future__ import annotations

import uuid
from typing import Any

from ..domain.models import (
    ChangeId,
    TopicApplyResult,
    TopicBatch,
    TopicName,
    TopicPlan,
    TopicSpec,
)
from ..domain.repositories.interfaces import (
    IAuditRepository,
    ITopicMetadataRepository,
    ITopicRepository,
)
from ..domain.services import TopicPlannerService
from .policy_integration import TopicPolicyAdapter


class TopicBatchDryRunUseCase:
    """토픽 배치 Dry-Run 유스케이스"""

    def __init__(
        self,
        topic_repository: ITopicRepository,
        metadata_repository: ITopicMetadataRepository,
        audit_repository: IAuditRepository,
        policy_adapter: TopicPolicyAdapter,
    ) -> None:
        self.topic_repository = topic_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.policy_adapter = policy_adapter
        self.planner_service = TopicPlannerService(topic_repository, policy_adapter)

    async def execute(self, batch: TopicBatch, actor: str) -> TopicPlan:
        """Dry-Run 실행"""
        # 감사 로그 기록
        await self.audit_repository.log_topic_operation(
            change_id=batch.change_id,
            action="DRY_RUN",
            target="BATCH",
            actor=actor,
            status="STARTED",
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
                action="DRY_RUN",
                target="BATCH",
                actor=actor,
                status="COMPLETED",
                message=f"Dry-run completed: {len(plan.items)} items, {len(plan.violations)} violations",
                snapshot={"plan_summary": plan.summary()},
            )

            return plan

        except Exception as e:
            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action="DRY_RUN",
                target="BATCH",
                actor=actor,
                status="FAILED",
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
        policy_adapter: TopicPolicyAdapter,
    ) -> None:
        self.topic_repository = topic_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.policy_adapter = policy_adapter
        self.planner_service = TopicPlannerService(topic_repository, policy_adapter)

    async def execute(self, batch: TopicBatch, actor: str) -> TopicApplyResult:
        """배치 적용 실행"""
        audit_id = str(uuid.uuid4())

        # 감사 로그 기록
        await self.audit_repository.log_topic_operation(
            change_id=batch.change_id,
            action="APPLY",
            target="BATCH",
            actor=actor,
            status="STARTED",
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
            result = TopicApplyResult(
                change_id=batch.change_id,
                env=batch.env,
                applied=tuple(applied),
                skipped=tuple(skipped),
                failed=tuple(failed),
                audit_id=audit_id,
            )

            # 결과 저장
            await self.metadata_repository.save_apply_result(result, actor)

            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action="APPLY",
                target="BATCH",
                actor=actor,
                status="COMPLETED",
                message=f"Apply completed: {len(applied)} applied, {len(failed)} failed",
                snapshot={"apply_summary": result.summary()},
            )

            return result

        except Exception as e:
            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action="APPLY",
                target="BATCH",
                actor=actor,
                status="FAILED",
                message=f"Apply failed: {e!s}",
            )
            raise

    async def _apply_topics(
        self, specs: tuple[TopicSpec, ...], actor: str, change_id: ChangeId
    ) -> tuple[list[TopicName], list[TopicName], list[dict[str, str]]]:
        """토픽 적용 실행"""
        applied = []
        skipped = []
        failed = []

        # 액션별로 그룹화
        create_specs = [s for s in specs if s.action.value in ("create", "upsert")]
        delete_specs = [s for s in specs if s.action.value == "delete"]
        update_specs = [s for s in specs if s.action.value in ("update", "upsert")]

        # 토픽 생성
        if create_specs:
            create_results = await self.topic_repository.create_topics(create_specs)
            for name, error in create_results.items():
                if error is None:
                    applied.append(name)
                    await self._log_topic_operation(name, "CREATE", actor, change_id, "SUCCESS")
                else:
                    failed.append({"name": name, "error": str(error), "action": "CREATE"})
                    await self._log_topic_operation(
                        name, "CREATE", actor, change_id, "FAILED", str(error)
                    )

        # 토픽 삭제
        if delete_specs:
            delete_names = [s.name for s in delete_specs]
            delete_results = await self.topic_repository.delete_topics(delete_names)
            for name, error in delete_results.items():
                if error is None:
                    applied.append(name)
                    await self._log_topic_operation(name, "DELETE", actor, change_id, "SUCCESS")
                else:
                    failed.append({"name": name, "error": str(error), "action": "DELETE"})
                    await self._log_topic_operation(
                        name, "DELETE", actor, change_id, "FAILED", str(error)
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
        """개별 토픽 작업 감사 로그"""
        await self.audit_repository.log_topic_operation(
            change_id=change_id,
            action=action,
            target=name,
            actor=actor,
            status=status,
            message=message,
        )


class TopicDetailUseCase:
    """토픽 상세 조회 유스케이스"""

    def __init__(
        self,
        topic_repository: ITopicRepository,
        metadata_repository: ITopicMetadataRepository,
    ) -> None:
        self.topic_repository = topic_repository
        self.metadata_repository = metadata_repository

    async def execute(self, name: TopicName) -> dict[str, Any] | None:
        """토픽 상세 정보 조회"""
        # Kafka에서 토픽 정보 조회
        kafka_topics = await self.topic_repository.describe_topics([name])
        kafka_topic = kafka_topics.get(name)

        if kafka_topic is None:
            return None

        # 메타데이터 조회
        metadata = await self.metadata_repository.get_topic_metadata(name)

        return {
            "name": name,
            "kafka_metadata": kafka_topic,
            "metadata": metadata or {},
        }


class TopicPlanUseCase:
    """토픽 계획 조회 유스케이스"""

    def __init__(self, metadata_repository: ITopicMetadataRepository) -> None:
        self.metadata_repository = metadata_repository

    async def execute(self, change_id: ChangeId) -> TopicPlan | None:
        """계획 조회"""
        return await self.metadata_repository.get_plan(change_id)
