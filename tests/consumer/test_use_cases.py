"""Consumer Use Cases 테스트"""

import pytest

from app.consumer.application.use_cases.metrics import (
    GetConsumerGroupMetricsUseCase,
    GetGroupAdviceUseCase,
)
from app.consumer.application.use_cases.query import (
    GetConsumerGroupSummaryUseCase,
    GetGroupMembersUseCase,
    GetGroupPartitionsUseCase,
    GetGroupRebalanceUseCase,
    GetTopicConsumersUseCase,
    ListConsumerGroupsUseCase,
)


class TestListConsumerGroupsUseCase:
    """ListConsumerGroupsUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_execute_returns_empty_when_no_groups(
        self,
        session_factory,
        sample_cluster_id,
    ):
        """그룹이 없을 때 빈 리스트 반환"""
        # Given
        use_case = ListConsumerGroupsUseCase(session_factory)

        # When
        result = await use_case.execute(sample_cluster_id)

        # Then
        assert result.total == 0
        assert len(result.groups) == 0

    @pytest.mark.asyncio
    async def test_execute_returns_groups(
        self,
        session_factory,
        sample_cluster_id,
        sample_group_snapshot,
    ):
        """그룹이 있을 때 목록 반환"""
        # Given
        use_case = ListConsumerGroupsUseCase(session_factory)

        # When
        result = await use_case.execute(sample_cluster_id)

        # Then
        assert result.total == 1
        assert len(result.groups) == 1
        assert result.groups[0].group_id == sample_group_snapshot.group_id
        assert result.groups[0].state == "Stable"
        assert result.groups[0].lag_stats.total_lag == 1500


class TestGetConsumerGroupSummaryUseCase:
    """GetConsumerGroupSummaryUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_execute_returns_summary(
        self,
        session_factory,
        sample_cluster_id,
        sample_group_id,
        sample_group_snapshot,
        sample_group_partitions,
    ):
        """그룹 요약 정보 반환"""
        # Given
        use_case = GetConsumerGroupSummaryUseCase(session_factory)

        # When
        result = await use_case.execute(sample_cluster_id, sample_group_id)

        # Then
        assert result.group_id == sample_group_id
        assert result.state == "Stable"
        assert result.lag["total"] == 1500
        assert result.stuck is not None


class TestGetGroupMembersUseCase:
    """GetGroupMembersUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_execute_returns_members_with_partitions(
        self,
        session_factory,
        sample_cluster_id,
        sample_group_id,
        sample_group_snapshot,  # 필수: Use Case가 최신 스냅샷 시각을 참조
        sample_group_members,
        sample_group_partitions,
    ):
        """멤버와 할당된 파티션 반환"""
        # Given
        use_case = GetGroupMembersUseCase(session_factory)

        # When
        result = await use_case.execute(sample_cluster_id, sample_group_id)

        # Then
        assert len(result) == 3
        assert result[0].member_id == "consumer-1"
        assert len(result[0].assigned_partitions) == 1
        assert result[0].assigned_partitions[0]["topic"] == "orders"
        assert result[0].assigned_partitions[0]["partition"] == 0


class TestGetGroupPartitionsUseCase:
    """GetGroupPartitionsUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_execute_returns_partitions(
        self,
        session_factory,
        sample_cluster_id,
        sample_group_id,
        sample_group_snapshot,  # 필수: Use Case가 최신 스냅샷 시각을 참조
        sample_group_partitions,
    ):
        """파티션 목록 반환"""
        # Given
        use_case = GetGroupPartitionsUseCase(session_factory)

        # When
        result = await use_case.execute(sample_cluster_id, sample_group_id)

        # Then
        assert len(result) == 3
        assert result[0].topic == "orders"
        assert result[0].partition == 0
        assert result[0].lag == 100
        assert result[0].assigned_member_id == "consumer-1"


class TestGetGroupRebalanceUseCase:
    """GetGroupRebalanceUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_execute_returns_empty_when_no_events(
        self,
        session_factory,
        sample_cluster_id,
        sample_group_id,
    ):
        """리밸런스 이벤트가 없을 때 빈 리스트 반환"""
        # Given
        use_case = GetGroupRebalanceUseCase(session_factory)

        # When
        result = await use_case.execute(sample_cluster_id, sample_group_id, limit=10)

        # Then
        assert len(result) == 0


class TestGetConsumerGroupMetricsUseCase:
    """GetConsumerGroupMetricsUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_execute_returns_metrics(
        self,
        session_factory,
        sample_cluster_id,
        sample_group_id,
        sample_group_snapshot,
        sample_group_partitions,
    ):
        """메트릭 정보 반환"""
        # Given
        use_case = GetConsumerGroupMetricsUseCase(session_factory)

        # When
        result = await use_case.execute(sample_cluster_id, sample_group_id)

        # Then
        assert result.group_id == sample_group_id
        assert result.fairness is not None
        assert result.advice is not None


class TestGetGroupAdviceUseCase:
    """GetGroupAdviceUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_execute_returns_advice(
        self,
        session_factory,
        sample_cluster_id,
        sample_group_id,
        sample_group_snapshot,
    ):
        """정책 어드바이스 반환"""
        # Given
        use_case = GetGroupAdviceUseCase(session_factory)

        # When
        result = await use_case.execute(sample_cluster_id, sample_group_id)

        # Then - PolicyAdviceResponse는 dict 필드를 가짐
        assert isinstance(result.assignor, dict)
        assert isinstance(result.static_membership, dict)
        assert isinstance(result.scale, dict)
        assert isinstance(result.slo_compliance, float)


class TestGetTopicConsumersUseCase:
    """GetTopicConsumersUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_execute_returns_topic_consumers(
        self,
        session_factory,
        sample_cluster_id,
        sample_group_partitions,
    ):
        """토픽별 컨슈머 매핑 반환"""
        # Given
        use_case = GetTopicConsumersUseCase(session_factory)
        topic = "orders"

        # When
        result = await use_case.execute(sample_cluster_id, topic)

        # Then
        assert result.topic == topic
        assert isinstance(result.consumer_groups, list)
