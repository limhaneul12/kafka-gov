"""Consumer Metrics & Analysis Use Cases - 실시간 Kafka 조회 방식

Consumer Group 메트릭 및 분석 관련 Use Case들을 통합

포함된 Use Cases:
- GetConsumerGroupMetricsUseCase: 그룹 메트릭 조회
- GetGroupAdviceUseCase: 정책 어드바이저
"""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager

from confluent_kafka.admin import AdminClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.consumer.domain.models import RebalanceRollup
from app.consumer.domain.services import ConsumerDataCollector, ConsumerMetricsCalculator
from app.consumer.domain.types_enum import PartitionAssignor, WindowType
from app.consumer.infrastructure.kafka_consumer_adapter import KafkaConsumerAdapter
from app.consumer.infrastructure.repository import ConsumerRepository
from app.consumer.interface.schema import (
    ConsumerGroupAdviceResponse,
    ConsumerGroupMetricsResponse,
    FairnessIndexResponse,
    RebalanceScoreResponse,
)
from app.consumer.interface.schema.detail_schema import PolicyAdviceResponse


class GetConsumerGroupMetricsUseCase:
    """Consumer Group 메트릭 조회 Use Case - 실시간 Kafka 조회"""

    def __init__(
        self,
        admin_client_getter: Callable[[str], Awaitable[AdminClient]],
        session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] | None = None,
    ) -> None:
        """Use case 생성자

        Args:
            admin_client_getter: cluster_id로 AdminClient를 가져오는 함수
            session_factory: Rebalance 점수 조회용 세션 팩토리 (optional)
        """
        self._admin_client_getter = admin_client_getter
        self._session_factory = session_factory
        self._calculator = ConsumerMetricsCalculator()

    async def execute(self, cluster_id: str, group_id: str) -> ConsumerGroupMetricsResponse:
        """Consumer Group 메트릭 조회 - 실시간 Kafka 조회

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID

        Returns:
            ConsumerGroupMetricsResponse

        Raises:
            ValueError: AdminClient를 찾을 수 없거나 그룹이 존재하지 않음
        """
        # 1. AdminClient 및 Adapter 생성
        admin_client = await self._admin_client_getter(cluster_id)

        adapter = KafkaConsumerAdapter(admin_client)
        collector = ConsumerDataCollector(adapter, cluster_id)

        # 2. 실시간 Kafka 조회
        try:
            group = await collector.collect_group(group_id)
            members = await collector.collect_members(group_id)
            partitions = await collector.collect_partitions(group_id)
        except KeyError as e:
            raise ValueError(f"Consumer group not found: {group_id}") from e

        # 3. 메트릭 계산 - 실시간 데이터로
        fairness = self._calculator.calculate_fairness(members, partitions)

        # 4. Rebalance Rollup 조회 (optional)
        rebalance_score_response = None
        rollup_domain = None

        if self._session_factory is not None:
            try:
                async with self._session_factory() as session:
                    repo = ConsumerRepository(session)
                    rollup_model = await repo.get_latest_rollup(
                        cluster_id, group_id, WindowType.ONE_HOUR
                    )

                if rollup_model:
                    rollup_domain = RebalanceRollup(
                        cluster_id=rollup_model.cluster_id,
                        group_id=rollup_model.group_id,
                        window_start=rollup_model.window_start,
                        window=WindowType(rollup_model.window),
                        rebalances=rollup_model.rebalances,
                        avg_moved_partitions=rollup_model.avg_moved_partitions,
                        max_moved_partitions=rollup_model.max_moved_partitions,
                        stable_ratio=rollup_model.stable_ratio,
                    )

                    rebalance_score_response = RebalanceScoreResponse(
                        score=rollup_domain.rebalance_score(),
                        rebalances_per_hour=rollup_domain.rebalances_per_hour(),
                        stable_ratio=rollup_domain.stable_ratio,
                        window=rollup_domain.window.value,
                    )
            except Exception:
                # Rollup 조회 실패 시 무시 (optional 기능)
                pass

        # 5. Policy Advice 생성 - 실시간 데이터 사용
        current_assignor = (
            PartitionAssignor(group.partition_assignor.value) if group.partition_assignor else None
        )

        advice_domain = self._calculator.generate_advice(
            current_assignor=current_assignor,
            rebalance_rollup=rollup_domain,
            fairness=fairness,
            total_partitions=len(partitions),
            member_count=len(members),
            p95_lag=group.lag_stats.p95_lag,
            target_p95_ms=10000,
        )

        # 6. Response 조립
        return ConsumerGroupMetricsResponse(
            cluster_id=cluster_id,
            group_id=group_id,
            fairness=FairnessIndexResponse(
                gini_coefficient=fairness.gini_coefficient,
                level=fairness.level().value,
                member_count=fairness.member_count,
                avg_tp_per_member=fairness.avg_tp_per_member,
                max_tp_per_member=fairness.max_tp_per_member,
                min_tp_per_member=fairness.min_tp_per_member,
            ),
            rebalance_score=rebalance_score_response,
            advice=ConsumerGroupAdviceResponse(
                assignor_recommendation=advice_domain.assignor_recommendation,
                assignor_reason=advice_domain.assignor_reason,
                static_membership_recommended=advice_domain.static_membership_recommended,
                static_membership_reason=advice_domain.static_membership_reason,
                scale_recommendation=advice_domain.scale_recommendation,
                scale_reason=advice_domain.scale_reason,
                slo_compliance_rate=advice_domain.slo_compliance_rate,
                risk_eta=advice_domain.risk_eta,
            ),
        )


class GetGroupAdviceUseCase:
    """Consumer Group 정책 어드바이저 Use Case - 실시간 Kafka 조회"""

    def __init__(
        self,
        admin_client_getter: Callable[[str], Awaitable[AdminClient]],
        session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]] | None = None,
    ) -> None:
        """Use case 생성자

        Args:
            admin_client_getter: cluster_id로 AdminClient를 가져오는 함수
            session_factory: Rollup 조회용 세션 팩토리 (optional)
        """
        self._admin_client_getter = admin_client_getter
        self._session_factory = session_factory
        self._calculator = ConsumerMetricsCalculator()

    async def execute(self, cluster_id: str, group_id: str) -> PolicyAdviceResponse:
        """정책 어드바이스 생성 - 실시간 Kafka 조회

        Args:
            cluster_id: 클러스터 ID
            group_id: Consumer Group ID

        Returns:
            PolicyAdviceResponse

        Raises:
            ValueError: AdminClient를 찾을 수 없거나 그룹이 존재하지 않음
        """
        # 1. AdminClient 및 Adapter 생성
        admin_client = await self._admin_client_getter(cluster_id)

        adapter = KafkaConsumerAdapter(admin_client)
        collector = ConsumerDataCollector(adapter, cluster_id)

        # 2. 실시간 Kafka 조회
        try:
            group = await collector.collect_group(group_id)
            members = await collector.collect_members(group_id)
            partitions = await collector.collect_partitions(group_id)
        except KeyError as e:
            raise ValueError(f"Consumer group not found: {group_id}") from e

        # 3. Fairness 계산
        fairness = self._calculator.calculate_fairness(members, partitions)

        # 4. Rollup (optional)
        rollup_domain = None
        if self._session_factory is not None:
            try:
                async with self._session_factory() as session:
                    repo = ConsumerRepository(session)
                    rollup_model = await repo.get_latest_rollup(
                        cluster_id, group_id, WindowType.ONE_HOUR
                    )

                if rollup_model:
                    rollup_domain = RebalanceRollup(
                        cluster_id=rollup_model.cluster_id,
                        group_id=rollup_model.group_id,
                        window_start=rollup_model.window_start,
                        window=WindowType(rollup_model.window),
                        rebalances=rollup_model.rebalances,
                        avg_moved_partitions=rollup_model.avg_moved_partitions,
                        max_moved_partitions=rollup_model.max_moved_partitions,
                        stable_ratio=rollup_model.stable_ratio,
                    )
            except Exception:
                # Rollup 조회 실패 시 무시
                pass

        # 5. Advice 생성
        current_assignor = (
            PartitionAssignor(group.partition_assignor.value) if group.partition_assignor else None
        )

        advice_domain = self._calculator.generate_advice(
            current_assignor=current_assignor,
            rebalance_rollup=rollup_domain,
            fairness=fairness,
            total_partitions=len(partitions),
            member_count=len(members),
            p95_lag=group.lag_stats.p95_lag,
            target_p95_ms=10000,
        )

        # 6. Response 조립
        return PolicyAdviceResponse(
            assignor={
                "recommendation": advice_domain.assignor_recommendation,
                "reason": advice_domain.assignor_reason,
            },
            static_membership={
                "recommended": advice_domain.static_membership_recommended,
                "reason": advice_domain.static_membership_reason,
            },
            scale={
                "recommendation": advice_domain.scale_recommendation,
                "reason": advice_domain.scale_reason,
            },
            slo_compliance=advice_domain.slo_compliance_rate,
            risk_eta=advice_domain.risk_eta,
        )
