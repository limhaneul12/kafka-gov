"""Topic Detail with Consumer Health Use Case

토픽 상세 + Consumer Health 통합 조회 (거버넌스 지표)
"""

import logging
from collections.abc import Awaitable, Callable

from confluent_kafka.admin import AdminClient, ConfigResource, ResourceType

from app.consumer.application.use_cases.query import (
    GetConsumerGroupSummaryUseCase,
    GetTopicConsumersUseCase,
)
from app.consumer.interface.schema.detail_schema import TopicConsumerMappingResponse
from app.consumer.interface.schema.topic_detail_schema import (
    ConsumerHealthSummary,
    GovernanceAlert,
    TopicConsumerInsight,
    TopicDetailWithConsumerHealthResponse,
)
from app.shared.i18n.translator import t


class GetTopicDetailWithConsumerHealthUseCase:
    """토픽 상세 + Consumer Health 조회 Use Case

    토픽 정보와 해당 토픽을 소비하는 Consumer Group들의 Health를 통합 조회
    """

    # SLO 임계값 (추후 Policy에서 가져오도록 개선 가능)
    SLO_THRESHOLD_P95_LAG = 1000
    SLO_COMPLIANCE_MIN = 0.95
    REBALANCE_SCORE_MIN = 70
    FAIRNESS_GINI_MAX = 0.40

    def __init__(
        self,
        admin_client_getter: Callable[[str], Awaitable[AdminClient]],
        get_topic_consumers_use_case: GetTopicConsumersUseCase,
        get_summary_use_case: GetConsumerGroupSummaryUseCase,
    ) -> None:
        """Use case 생성자

        Args:
            admin_client_getter: AdminClient를 가져오는 함수
            get_topic_consumers_use_case: 토픽별 Consumer 조회 Use Case
            get_summary_use_case: Consumer Group Summary 조회 Use Case
        """
        self._admin_client_getter = admin_client_getter
        self._get_topic_consumers_use_case = get_topic_consumers_use_case
        self._get_summary_use_case = get_summary_use_case

    async def execute(self, cluster_id: str, topic: str) -> TopicDetailWithConsumerHealthResponse:
        """토픽 상세 + Consumer Health 조회

        Args:
            cluster_id: 클러스터 ID
            topic: 토픽 이름

        Returns:
            TopicDetailWithConsumerHealthResponse

        Raises:
            ValueError: AdminClient를 찾을 수 없거나 토픽이 존재하지 않음
        """
        # 1. Topic 메타데이터 조회
        admin_client = await self._admin_client_getter(cluster_id)
        topic_metadata = await self._get_topic_metadata(admin_client, topic)

        # 2. 해당 토픽을 소비하는 Consumer Group 목록 조회
        topic_consumers = await self._get_topic_consumers_use_case.execute(cluster_id, topic)

        # 3. 각 Consumer Group의 Health 조회
        consumer_health_list: list[ConsumerHealthSummary] = []
        governance_alerts: list[GovernanceAlert] = []

        logging.warning(
            f"🔍 [Consumer Groups] Found {len(topic_consumers.consumer_groups)} consumer groups for topic '{topic}'"
        )

        for consumer_group_info in topic_consumers.consumer_groups:
            group_id = consumer_group_info["group_id"]
            logging.warning(f"📊 [Processing] Consumer group: {group_id}")

            try:
                # Consumer Group Summary 조회
                summary = await self._get_summary_use_case.execute(cluster_id, group_id)
                logging.warning(
                    f"✅ [Summary] Got summary for {group_id}: state={summary.state}, members={summary.member_count}"
                )

                # SLO Compliance 계산
                slo_compliance = self._calculate_slo_compliance(summary.lag["p95"])

                # Consumer Health 요약 생성
                health = ConsumerHealthSummary(
                    group_id=group_id,
                    state=summary.state,
                    slo_compliance=slo_compliance,
                    lag_p50=summary.lag["p50"],
                    lag_p95=summary.lag["p95"],
                    lag_max=summary.lag["max"],
                    stuck_count=len(summary.stuck),
                    rebalance_score=summary.rebalance_score,
                    fairness_gini=summary.fairness_gini,
                    member_count=summary.member_count,
                    recommendation=self._get_recommendation(
                        slo_compliance, summary.rebalance_score, summary.fairness_gini
                    ),
                )
                consumer_health_list.append(health)
                logging.warning(f"✅ [Health] Added health for {group_id}")

                # 거버넌스 경고 생성
                alerts = self._generate_governance_alerts(group_id, health)
                governance_alerts.extend(alerts)

            except Exception as e:
                # 개별 Consumer Group 조회 실패 시 로깅하고 건너뜀
                logging.error(
                    f"❌ [Error] Failed to get health for group {group_id}: {e}", exc_info=True
                )
                continue

        # 4. Consumer 전체 인사이트 생성
        logging.warning(f"📊 [Total] Consumer health list size: {len(consumer_health_list)}")
        insight = self._generate_insight(
            consumer_health_list, topic_metadata["partitions"], topic_consumers
        )

        # 5. 응답 조립
        return TopicDetailWithConsumerHealthResponse(
            topic=topic,
            cluster_id=cluster_id,
            partitions=topic_metadata["partitions"],
            replication_factor=topic_metadata["replication_factor"],
            retention_ms=topic_metadata["retention_ms"],
            insight=insight,
            consumer_groups=consumer_health_list,
            governance_alerts=governance_alerts,
        )

    async def _get_topic_metadata(self, admin_client: AdminClient, topic: str) -> dict[str, int]:
        """토픽 메타데이터 조회

        Args:
            admin_client: Kafka AdminClient
            topic: 토픽 이름

        Returns:
            토픽 메타데이터 (partitions, replication_factor, retention_ms)

        Raises:
            ValueError: 토픽이 존재하지 않음
        """
        # Metadata 조회
        metadata = admin_client.list_topics(topic=topic, timeout=10)

        if topic not in metadata.topics:
            raise ValueError(f"Topic '{topic}' not found")

        topic_metadata = metadata.topics[topic]
        partitions = len(topic_metadata.partitions)

        # Replication factor (첫 번째 파티션 기준)
        replication_factor = len(topic_metadata.partitions[0].replicas) if partitions > 0 else 1

        # Config 조회 (retention.ms)
        resource = ConfigResource(ResourceType.TOPIC, topic)
        configs = admin_client.describe_configs([resource])

        retention_ms = 604800000  # 기본값 7일
        for future in configs.values():
            config_dict = future.result()
            if "retention.ms" in config_dict:
                retention_ms = int(config_dict["retention.ms"].value)

        return {
            "partitions": partitions,
            "replication_factor": replication_factor,
            "retention_ms": retention_ms,
        }

    def _calculate_slo_compliance(self, lag_p95: int) -> float:
        """SLO Compliance 계산

        Args:
            lag_p95: P95 Lag

        Returns:
            SLO 준수율 (0.0-1.0)
        """
        if lag_p95 <= self.SLO_THRESHOLD_P95_LAG:
            return 1.0

        # 초과하면 비율로 계산 (최소 0.0)
        return max(0.0, 1.0 - (lag_p95 - self.SLO_THRESHOLD_P95_LAG) / self.SLO_THRESHOLD_P95_LAG)

    def _get_recommendation(
        self, slo_compliance: float, rebalance_score: float | None, fairness_gini: float
    ) -> str | None:
        """권장사항 생성

        Args:
            slo_compliance: SLO 준수율
            rebalance_score: Rebalance 점수 (None이면 이력 데이터 없음)
            fairness_gini: Fairness Gini 계수

        Returns:
            권장사항 문자열 또는 None
        """
        recommendations = []

        if slo_compliance < self.SLO_COMPLIANCE_MIN:
            recommendations.append("Scale-out 필요")

        # Rebalance 점수는 이력 데이터가 있을 때만 판단
        if rebalance_score is not None and rebalance_score < self.REBALANCE_SCORE_MIN:
            recommendations.append("Rebalance 안정성 개선 필요")

        if fairness_gini > self.FAIRNESS_GINI_MAX:
            recommendations.append("파티션 재분배 고려")

        return ", ".join(recommendations) if recommendations else None

    def _generate_governance_alerts(
        self, group_id: str, health: ConsumerHealthSummary
    ) -> list[GovernanceAlert]:
        """거버넌스 경고 생성

        Args:
            group_id: Consumer Group ID
            health: Consumer Health 요약

        Returns:
            거버넌스 경고 목록
        """
        alerts: list[GovernanceAlert] = []

        # SLO 미달
        if health.slo_compliance < self.SLO_COMPLIANCE_MIN:
            alerts.append(
                GovernanceAlert(
                    severity="warning",
                    consumer_group=group_id,
                    message=t(
                        "consumer.governance.slo_violation",
                        current=f"{health.slo_compliance * 100:.1f}",
                        threshold=f"{self.SLO_COMPLIANCE_MIN * 100:.0f}",
                    ),
                    metric="slo",
                )
            )

        # Stuck Partition 감지
        if health.stuck_count > 0:
            alerts.append(
                GovernanceAlert(
                    severity="error",
                    consumer_group=group_id,
                    message=t("consumer.governance.stuck_partitions", count=health.stuck_count),
                    metric="stuck",
                )
            )

        # Rebalance 불안정 (이력 데이터가 있을 때만 판단)
        if health.rebalance_score is not None and health.rebalance_score < self.REBALANCE_SCORE_MIN:
            alerts.append(
                GovernanceAlert(
                    severity="warning",
                    consumer_group=group_id,
                    message=t(
                        "consumer.governance.rebalance_instability",
                        score=f"{health.rebalance_score:.1f}",
                    ),
                    metric="rebalance",
                )
            )

        # Fairness 불균형
        if health.fairness_gini > self.FAIRNESS_GINI_MAX:
            alerts.append(
                GovernanceAlert(
                    severity="info",
                    consumer_group=group_id,
                    message=t(
                        "consumer.governance.unfair_distribution",
                        gini=f"{health.fairness_gini:.2f}",
                    ),
                    metric="fairness",
                )
            )

        return alerts

    def _generate_insight(
        self,
        consumer_health_list: list[ConsumerHealthSummary],
        total_partitions: int,
        topic_consumers: TopicConsumerMappingResponse,
    ) -> TopicConsumerInsight:
        """Consumer 전체 인사이트 생성

        Args:
            consumer_health_list: Consumer Health 목록
            total_partitions: 전체 파티션 수
            topic_consumers: 토픽 Consumer 매핑 응답

        Returns:
            TopicConsumerInsight
        """
        if not consumer_health_list:
            return TopicConsumerInsight(
                total_consumers=0,
                healthy_consumers=0,
                unhealthy_consumers=0,
                avg_slo_compliance=0.0,
                avg_rebalance_score=0.0,
                total_stuck_partitions=0,
                partitions_with_consumers=0,
                total_partitions=total_partitions,
                summary="No Consumer Group is consuming this topic",
            )

        # 통계 계산
        total_consumers = len(consumer_health_list)
        healthy_consumers = sum(
            1
            for h in consumer_health_list
            if h.slo_compliance >= self.SLO_COMPLIANCE_MIN and h.stuck_count == 0
        )
        unhealthy_consumers = total_consumers - healthy_consumers

        avg_slo_compliance = sum(h.slo_compliance for h in consumer_health_list) / total_consumers

        # Rebalance 점수는 None이 아닌 것만 평균 계산
        rebalance_scores = [
            h.rebalance_score for h in consumer_health_list if h.rebalance_score is not None
        ]
        avg_rebalance_score = (
            sum(rebalance_scores) / len(rebalance_scores) if rebalance_scores else 0.0
        )

        total_stuck_partitions = sum(h.stuck_count for h in consumer_health_list)

        # 소비되고 있는 파티션 수 계산
        consumed_partitions = set()
        for consumer_group_info in topic_consumers.consumer_groups:
            for partition_info in consumer_group_info.get("partitions", []):
                consumed_partitions.add(partition_info["partition"])
        partitions_with_consumers = len(consumed_partitions)

        # 한 줄 요약 생성
        summary = self._generate_summary(
            total_consumers,
            healthy_consumers,
            unhealthy_consumers,
            avg_slo_compliance,
            total_stuck_partitions,
            partitions_with_consumers,
            total_partitions,
        )

        return TopicConsumerInsight(
            total_consumers=total_consumers,
            healthy_consumers=healthy_consumers,
            unhealthy_consumers=unhealthy_consumers,
            avg_slo_compliance=avg_slo_compliance,
            avg_rebalance_score=avg_rebalance_score,
            total_stuck_partitions=total_stuck_partitions,
            partitions_with_consumers=partitions_with_consumers,
            total_partitions=total_partitions,
            summary=summary,
        )

    def _generate_summary(
        self,
        total: int,
        healthy: int,
        unhealthy: int,
        avg_slo: float,
        stuck: int,
        consumed_partitions: int,
        total_partitions: int,
    ) -> str:
        """한 줄 요약 생성"""
        if unhealthy == 0 and stuck == 0:
            return f"✅ {t('consumer.governance.summary_all_healthy')}"

        issues = []
        if unhealthy > 0:
            issues.append(t("consumer.governance.summary_slo_violation", count=unhealthy))
        if stuck > 0:
            issues.append(t("consumer.governance.summary_stuck_partitions", count=stuck))
        if consumed_partitions < total_partitions:
            issues.append(
                t(
                    "consumer.governance.summary_unconsumed_partitions",
                    count=total_partitions - consumed_partitions,
                )
            )

        return f"⚠️ {', '.join(issues)}"
