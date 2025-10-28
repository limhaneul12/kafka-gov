"""Consumer 모듈 통합 테스트

Use Case → Repository → Database 전체 흐름 테스트
"""

from datetime import datetime, timezone

import pytest

from app.consumer.application.use_cases.query import (
    GetConsumerGroupSummaryUseCase,
    GetGroupMembersUseCase,
    ListConsumerGroupsUseCase,
)
from app.consumer.domain.services.delta_builder import DeltaBuilder
from app.consumer.infrastructure.models import (
    ConsumerGroupSnapshotModel,
    ConsumerMemberSnapshotModel,
    ConsumerPartitionSnapshotModel,
)


class TestConsumerIntegration:
    """Consumer 모듈 통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_flow_list_groups(
        self,
        db_session,
        session_factory,
        sample_cluster_id,
    ):
        """전체 플로우: 데이터 저장 → Use Case 실행 → 응답 검증"""
        # Given - DB에 여러 그룹 저장
        groups = [
            ConsumerGroupSnapshotModel(
                cluster_id=sample_cluster_id,
                group_id=f"group-{i}",
                ts=datetime.now(timezone.utc),
                state="Stable",
                partition_assignor="range",
                member_count=3,
                topic_count=2,
                total_lag=1000 * i,
                p50_lag=300,
                p95_lag=500,
                max_lag=600,
            )
            for i in range(1, 4)
        ]
        for group in groups:
            db_session.add(group)
        await db_session.commit()

        # When - Use Case 실행
        use_case = ListConsumerGroupsUseCase(session_factory)
        result = await use_case.execute(sample_cluster_id)

        # Then
        assert result.total == 3
        assert len(result.groups) == 3
        assert result.groups[0].group_id in ["group-1", "group-2", "group-3"]

    @pytest.mark.asyncio
    async def test_full_flow_group_summary_with_members(
        self,
        db_session,
        session_factory,
        sample_cluster_id,
    ):
        """전체 플로우: 그룹 요약 + 멤버 조회"""
        # Given - 그룹 스냅샷
        group_id = "integration-test-group"
        ts = datetime.now(timezone.utc)

        snapshot = ConsumerGroupSnapshotModel(
            cluster_id=sample_cluster_id,
            group_id=group_id,
            ts=ts,
            state="Stable",
            partition_assignor="cooperative-sticky",
            member_count=2,
            topic_count=1,
            total_lag=500,
            p50_lag=200,
            p95_lag=400,
            max_lag=500,
        )
        db_session.add(snapshot)

        # Given - 멤버 데이터
        members = [
            ConsumerMemberSnapshotModel(
                cluster_id=sample_cluster_id,
                group_id=group_id,
                ts=ts,
                member_id=f"consumer-{i}",
                client_id=f"client-{i}",
                client_host=f"192.168.1.{10 + i}",
                assigned_tp_count=1,
            )
            for i in range(1, 3)
        ]
        for member in members:
            db_session.add(member)

        # Given - 파티션 데이터
        partitions = [
            ConsumerPartitionSnapshotModel(
                cluster_id=sample_cluster_id,
                group_id=group_id,
                ts=ts,
                topic="orders",
                partition=i,
                committed_offset=1000 * i,
                latest_offset=1000 * i + 100,
                lag=100,
                assigned_member_id=f"consumer-{i + 1}",
            )
            for i in range(2)
        ]
        for partition in partitions:
            db_session.add(partition)

        await db_session.commit()

        # When - 그룹 요약 조회
        summary_use_case = GetConsumerGroupSummaryUseCase(session_factory)
        summary = await summary_use_case.execute(sample_cluster_id, group_id)

        # Then
        assert summary.group_id == group_id
        assert summary.state == "Stable"
        assert isinstance(summary.lag, dict)

        # When - 멤버 목록 조회
        members_use_case = GetGroupMembersUseCase(session_factory)
        member_list = await members_use_case.execute(sample_cluster_id, group_id)

        # Then
        assert len(member_list) == 2
        assert member_list[0].member_id == "consumer-1"
        assert len(member_list[0].assigned_partitions) == 1

    @pytest.mark.asyncio
    async def test_delta_builder_with_real_data(
        self,
        db_session,
        session_factory,
        sample_cluster_id,
    ):
        """Delta Builder를 실제 데이터로 테스트"""
        # Given
        from tests.consumer.factories import create_consumer_group

        group_id = "delta-test-group"
        ts = datetime.now(timezone.utc)

        # 첫 번째 상태
        first_group = create_consumer_group(
            cluster_id=sample_cluster_id,
            group_id=group_id,
            ts=ts,
            state="Stable",
            partition_assignor="range",
            member_count=3,
            topic_count=2,
            total_lag=1000,
            p50_lag=300,
            p95_lag=500,
            max_lag=600,
        )

        # When - Delta Builder로 첫 상태 저장
        delta_builder = DeltaBuilder()
        events = delta_builder.calculate_delta(first_group)

        # Then - 첫 상태는 이벤트 없음
        assert len(events) == 0

        # When - 두 번째 상태 (Lag 급증)
        second_group = create_consumer_group(
            cluster_id=sample_cluster_id,
            group_id=group_id,
            ts=ts,
            state="Stable",
            partition_assignor="range",
            member_count=3,
            topic_count=2,
            total_lag=5000,  # 1000 → 5000 (+4000)
            p50_lag=1200,
            p95_lag=2000,
            max_lag=2500,
        )
        events = delta_builder.calculate_delta(second_group)

        # Then - Lag Spike 이벤트 발생
        assert len(events) >= 1
        lag_event = next(e for e in events if e["type"] == "lag_spike")
        assert lag_event["delta_total_lag"] == 4000
        assert lag_event["current"]["total_lag"] == 5000

    @pytest.mark.asyncio
    async def test_websocket_event_publishing_flow(self, sample_cluster_id):
        """WebSocket 이벤트 발행 플로우 테스트"""
        # Given
        from unittest.mock import AsyncMock, patch
        from uuid import uuid4

        from app.consumer.interface.routes.consumer_websocket import publish_event

        event = {
            "type": "group_state_changed",
            "version": "v1",
            "ts": datetime.utcnow().isoformat(),
            "trace_id": str(uuid4()),
            "group_id": "test-group",
            "old_state": "Stable",
            "new_state": "Rebalancing",
            "reason": "member_join",
        }

        # When
        from app.consumer.interface.routes.consumer_websocket import manager

        with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
            await publish_event(sample_cluster_id, event, group_id="test-group")

            # Then - 전체 스트림 + 그룹별 스트림 2번 호출
            assert mock_broadcast.call_count == 2


class TestEndToEndScenario:
    """End-to-End 시나리오 테스트"""

    @pytest.mark.asyncio
    async def test_consumer_monitoring_scenario(
        self,
        db_session,
        session_factory,
        sample_cluster_id,
    ):
        """실제 모니터링 시나리오: 수집 → 저장 → 조회 → 델타 계산 → 이벤트"""
        # Scenario: Consumer 그룹이 정상 → 리밸런싱 → 정상으로 전환

        group_id = "e2e-test-group"
        ts = datetime.now(timezone.utc)

        # 1단계: 정상 상태 저장
        stable_snapshot = ConsumerGroupSnapshotModel(
            cluster_id=sample_cluster_id,
            group_id=group_id,
            ts=ts,
            state="Stable",
            partition_assignor="range",
            member_count=3,
            topic_count=2,
            total_lag=1000,
            p50_lag=300,
            p95_lag=500,
            max_lag=600,
        )
        db_session.add(stable_snapshot)
        await db_session.commit()

        # 2단계: 조회
        use_case = ListConsumerGroupsUseCase(session_factory)
        result = await use_case.execute(sample_cluster_id)
        assert result.total == 1
        assert result.groups[0].state == "Stable"

        # 3단계: Delta Builder로 상태 변경 감지
        from tests.consumer.factories import create_consumer_group

        first_state = create_consumer_group(
            cluster_id=sample_cluster_id,
            group_id=group_id,
            ts=ts,
            state="Stable",
            partition_assignor="range",
            member_count=3,
            topic_count=2,
            total_lag=1000,
            p50_lag=300,
            p95_lag=500,
            max_lag=600,
        )

        delta_builder = DeltaBuilder()
        delta_builder.calculate_delta(first_state)

        # 4단계: 리밸런싱 상태로 전환
        rebalancing_state = create_consumer_group(
            cluster_id=sample_cluster_id,
            group_id=group_id,
            ts=ts,
            state="Rebalancing",  # 상태 변경
            partition_assignor="range",
            member_count=4,  # 멤버 증가
            topic_count=2,
            total_lag=1000,
            p50_lag=300,
            p95_lag=500,
            max_lag=600,
        )

        events = delta_builder.calculate_delta(rebalancing_state)

        # 5단계: 상태 변경 이벤트 확인
        assert len(events) >= 1
        state_event = next(e for e in events if e["type"] == "group_state_changed")
        assert state_event["old_state"] == "Stable"
        assert state_event["new_state"] == "Rebalancing"
        assert state_event["reason"] == "member_join"
