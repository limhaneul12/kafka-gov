"""Shared Application Use Cases"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.cluster.domain.services import IConnectionManager
from app.shared.domain.models import ApprovalRequest, AuditActivity, ClusterStatus
from app.shared.domain.repositories import IApprovalRequestRepository, IAuditActivityRepository


class GetRecentActivitiesUseCase:
    """최근 활동 조회 Use Case"""

    def __init__(self, audit_repository: IAuditActivityRepository) -> None:
        self.audit_repository = audit_repository

    async def execute(self, limit: int = 20) -> list[AuditActivity]:
        """
        최근 활동 조회

        Args:
            limit: 조회할 최대 개수 (1-100)

        Returns:
            최근 활동 목록
        """
        # 입력 검증
        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        # Repository를 통해 조회
        activities = await self.audit_repository.get_recent_activities(limit)

        return activities


class GetActivityHistoryUseCase:
    """활동 히스토리 조회 Use Case"""

    def __init__(self, audit_repository: IAuditActivityRepository) -> None:
        self.audit_repository = audit_repository

    async def execute(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        activity_type: str | None = None,
        action: str | None = None,
        actor: str | None = None,
        limit: int = 100,
    ) -> list[AuditActivity]:
        """
        활동 히스토리 조회 (필터링 지원)

        Args:
            from_date: 시작 날짜/시간
            to_date: 종료 날짜/시간
            activity_type: 활동 타입 ("topic" or "schema")
            action: 액션 타입
            actor: 수행자
            limit: 최대 조회 개수 (기본 100개, 최대 500개)

        Returns:
            필터링된 활동 목록 (시간 역순)
        """
        # 입력 검증
        if limit < 1:
            limit = 1
        elif limit > 500:
            limit = 500

        # Repository를 통해 조회
        activities = await self.audit_repository.get_activity_history(
            from_date=from_date,
            to_date=to_date,
            activity_type=activity_type,
            action=action,
            actor=actor,
            limit=limit,
        )

        return activities


class GetClusterStatusUseCase:
    """Kafka 클러스터 상태 조회 Use Case"""

    def __init__(self, connection_manager: IConnectionManager) -> None:
        self.connection_manager = connection_manager

    async def execute(self, cluster_id: str) -> ClusterStatus:
        """
        Kafka 클러스터 상태 조회

        Args:
            cluster_id: 클러스터 ID

        Returns:
            클러스터 상태 정보 (브로커 목록, 토픽/파티션 수)
        """
        # ConnectionManager를 통해 AdminClient 획득
        admin_client = await self.connection_manager.get_kafka_admin_client(cluster_id)

        # 클러스터 메타데이터 조회 (동기 방식이지만 빠름)
        metadata = admin_client.list_topics(timeout=10)

        # 컨트롤러 ID 조회
        controller_id = metadata.controller_id

        # 브로커 정보 수집
        from app.shared.domain.models import BrokerInfo

        brokers_dict = {}
        for broker in metadata.brokers.values():
            brokers_dict[broker.id] = BrokerInfo(
                broker_id=broker.id,
                host=broker.host,
                port=broker.port,
                is_controller=(broker.id == controller_id),
                leader_partition_count=0,  # 기본값
            )

        # 파티션별 리더 카운트 계산
        total_partitions = 0
        for topic in metadata.topics.values():
            if not topic.error:  # 에러가 없는 토픽만
                for partition in topic.partitions.values():
                    total_partitions += 1
                    leader_id = partition.leader
                    if leader_id in brokers_dict:
                        # 리더 파티션 카운트 증가 (불변 객체이므로 새로 생성)
                        old_broker = brokers_dict[leader_id]
                        brokers_dict[leader_id] = BrokerInfo(
                            broker_id=old_broker.broker_id,
                            host=old_broker.host,
                            port=old_broker.port,
                            is_controller=old_broker.is_controller,
                            leader_partition_count=old_broker.leader_partition_count + 1,
                        )

        # ClusterStatus 생성
        from app.shared.domain.models import ClusterStatus

        return ClusterStatus(
            cluster_id=cluster_id,
            controller_id=controller_id,
            brokers=tuple(brokers_dict.values()),
            total_topics=len([t for t in metadata.topics.values() if not t.error]),
            total_partitions=total_partitions,
        )


class CreateApprovalRequestUseCase:
    def __init__(self, approval_repository: IApprovalRequestRepository) -> None:
        self.approval_repository = approval_repository

    async def execute(
        self,
        *,
        resource_type: str,
        resource_name: str,
        change_type: str,
        summary: str,
        justification: str,
        requested_by: str,
        change_ref: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            request_id=str(uuid4()),
            resource_type=resource_type,
            resource_name=resource_name,
            change_type=change_type,
            change_ref=change_ref,
            summary=summary,
            justification=justification,
            requested_by=requested_by,
            status="pending",
            metadata=metadata,
            requested_at=datetime.now(UTC),
        )
        return await self.approval_repository.create(request)


class ListApprovalRequestsUseCase:
    def __init__(self, approval_repository: IApprovalRequestRepository) -> None:
        self.approval_repository = approval_repository

    async def execute(
        self,
        *,
        status: str | None = None,
        resource_type: str | None = None,
        requested_by: str | None = None,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        return await self.approval_repository.list(
            status=status,
            resource_type=resource_type,
            requested_by=requested_by,
            limit=limit,
        )


class GetApprovalRequestUseCase:
    def __init__(self, approval_repository: IApprovalRequestRepository) -> None:
        self.approval_repository = approval_repository

    async def execute(self, request_id: str) -> ApprovalRequest:
        request = await self.approval_repository.get(request_id)
        if request is None:
            raise ValueError(f"approval request not found: {request_id}")
        return request


class ApproveApprovalRequestUseCase:
    def __init__(self, approval_repository: IApprovalRequestRepository) -> None:
        self.approval_repository = approval_repository

    async def execute(
        self, *, request_id: str, approver: str, decision_reason: str | None = None
    ) -> ApprovalRequest:
        return await self.approval_repository.update_status(
            request_id=request_id,
            status="approved",
            approver=approver,
            decision_reason=decision_reason,
        )


class RejectApprovalRequestUseCase:
    def __init__(self, approval_repository: IApprovalRequestRepository) -> None:
        self.approval_repository = approval_repository

    async def execute(
        self, *, request_id: str, approver: str, decision_reason: str | None = None
    ) -> ApprovalRequest:
        return await self.approval_repository.update_status(
            request_id=request_id,
            status="rejected",
            approver=approver,
            decision_reason=decision_reason,
        )
