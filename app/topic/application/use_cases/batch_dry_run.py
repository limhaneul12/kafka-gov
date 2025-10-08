"""토픽 배치 Dry-Run 유스케이스"""

from __future__ import annotations

from app.cluster.domain.services import IConnectionManager
from app.shared.constants import AuditAction, AuditStatus, AuditTarget
from app.topic.infrastructure.kafka_adapter import KafkaTopicAdapter

from ...domain.models import DomainTopicBatch, DomainTopicPlan
from ...domain.repositories.interfaces import IAuditRepository, ITopicMetadataRepository
from ...domain.services import TopicPlannerService


class TopicBatchDryRunUseCase:
    """토픽 배치 Dry-Run 유스케이스 (멀티 클러스터 지원)"""

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
    ) -> DomainTopicPlan:
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
            # 1. ConnectionManager로 AdminClient 획득
            admin_client = await self.connection_manager.get_kafka_admin_client(cluster_id)

            # 2. Adapter 생성
            topic_repository = KafkaTopicAdapter(admin_client)

            # 3. Planner Service 생성 및 계획 수립
            planner_service = TopicPlannerService(topic_repository)
            plan = await planner_service.create_plan(batch, actor)

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
