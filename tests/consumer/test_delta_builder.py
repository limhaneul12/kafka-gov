"""Delta Builder 테스트"""

from datetime import datetime, timezone

import pytest

from app.consumer.domain.services.delta_builder import DeltaBuilder
from app.consumer.domain.thresholds import (
    ConsumerThresholds,
    FairnessThresholds,
    LagThresholds,
    StuckThresholds,
)
from tests.consumer.factories import create_consumer_group


@pytest.fixture
def delta_builder():
    """DeltaBuilder 인스턴스"""
    return DeltaBuilder()


@pytest.fixture
def custom_thresholds():
    """커스텀 임계치"""
    return ConsumerThresholds(
        lag=LagThresholds(spike_delta_total_lag=1000, spike_window_s=30),
        stuck=StuckThresholds(delta_committed_le=0, delta_lag_ge=5, duration_s_ge=60),
        fairness=FairnessThresholds(gini_warn=0.3),
    )


@pytest.fixture
def sample_consumer_group():
    """샘플 Consumer Group"""
    return create_consumer_group(
        cluster_id="test-cluster",
        group_id="test-group",
        ts=datetime.now(timezone.utc),
        state="Stable",
        partition_assignor="range",
        member_count=3,
        topic_count=2,
        total_lag=1500,
        p50_lag=450,
        p95_lag=800,
        max_lag=1000,
    )


class TestDeltaBuilder:
    """DeltaBuilder 테스트"""

    def test_calculate_delta_no_previous_state(self, delta_builder, sample_consumer_group):
        """이전 상태가 없을 때 이벤트 생성 안함"""
        # When
        events = delta_builder.calculate_delta(sample_consumer_group)

        # Then
        assert len(events) == 0

    def test_calculate_delta_state_changed(self, delta_builder, sample_consumer_group):
        """상태 변경 감지"""
        # Given - 첫 번째 상태 저장
        delta_builder.calculate_delta(sample_consumer_group)

        # When - 상태 변경
        new_group = create_consumer_group(
            cluster_id=sample_consumer_group.cluster_id,
            group_id=sample_consumer_group.group_id,
            ts=datetime.now(timezone.utc),
            state="Rebalancing",  # 상태 변경
            partition_assignor=sample_consumer_group.partition_assignor.value,
            member_count=sample_consumer_group.member_count,
            topic_count=sample_consumer_group.topic_count,
            total_lag=sample_consumer_group.lag_stats.total_lag,
            p50_lag=sample_consumer_group.lag_stats.p50_lag,
            p95_lag=sample_consumer_group.lag_stats.p95_lag,
            max_lag=sample_consumer_group.lag_stats.max_lag,
        )
        events = delta_builder.calculate_delta(new_group)

        # Then
        assert len(events) >= 1
        state_event = next(e for e in events if e["type"] == "group_state_changed")
        assert state_event["old_state"] == "Stable"
        assert state_event["new_state"] == "Rebalancing"
        assert state_event["group_id"] == sample_consumer_group.group_id

    def test_calculate_delta_lag_spike(self, delta_builder, sample_consumer_group):
        """Lag Spike 감지"""
        # Given
        delta_builder.calculate_delta(sample_consumer_group)

        # When - Lag 급증
        new_group = create_consumer_group(
            cluster_id=sample_consumer_group.cluster_id,
            group_id=sample_consumer_group.group_id,
            ts=datetime.now(timezone.utc),
            state=sample_consumer_group.state.value,
            partition_assignor=sample_consumer_group.partition_assignor.value,
            member_count=sample_consumer_group.member_count,
            topic_count=sample_consumer_group.topic_count,
            total_lag=4500,  # 1500 → 4500 (+3000, 임계치 2000 초과)
            p50_lag=1000,
            p95_lag=1500,
            max_lag=2000,
        )
        events = delta_builder.calculate_delta(new_group)

        # Then
        assert len(events) >= 1
        lag_event = next(e for e in events if e["type"] == "lag_spike")
        assert lag_event["delta_total_lag"] == 3000
        assert lag_event["current"]["total_lag"] == 4500
        assert lag_event["group_id"] == sample_consumer_group.group_id

    def test_build_stuck_detected_event(self, delta_builder, sample_consumer_group):
        """Stuck Partition 이벤트 생성"""
        # When
        event = delta_builder.build_stuck_detected_event(
            group_id=sample_consumer_group.group_id,
            topic="orders",
            partition=7,
            member_id="consumer-3",
            since=datetime.now(timezone.utc),
            lag=4520,
        )

        # Then
        assert event["type"] == "stuck_detected"
        assert event["group_id"] == sample_consumer_group.group_id
        assert event["topic"] == "orders"
        assert event["partition"] == 7
        assert event["lag"] == 4520
        assert "rule" in event

    def test_build_assignment_changed_event(self, delta_builder):
        """Assignment Changed 이벤트 생성"""
        # When
        event = delta_builder.build_assignment_changed_event(
            group_id="test-group",
            moved_partitions=6,
            join_count=1,
            leave_count=0,
            total_partitions=128,
            stable_elapsed_s=380,
            assignment_partitions=[("orders", 0), ("orders", 1), ("payments", 0)],
        )

        # Then
        assert event["type"] == "assignment_changed"
        assert event["group_id"] == "test-group"
        assert event["moved_partitions"] == 6
        assert event["join_count"] == 1
        assert event["leave_count"] == 0
        assert event["movement_rate"] == pytest.approx(0.0469, abs=0.001)
        assert "assignment_hash" in event

    def test_build_fairness_warn_event(self, delta_builder):
        """Fairness Warning 이벤트 생성"""
        # When
        event = delta_builder.build_fairness_warn_event(
            group_id="test-group",
            gini=0.46,
            hint="Add 1 consumer or rebalance keys",
        )

        # Then
        assert event["type"] == "fairness_warn"
        assert event["group_id"] == "test-group"
        assert event["gini"] == 0.46
        assert event["hint"] == "Add 1 consumer or rebalance keys"
        assert "thresholds" in event

    def test_build_advisor_event(self, delta_builder):
        """Advisor 이벤트 생성"""
        # When
        advice_list = [
            {"kind": "assignor", "level": "recommend", "message": "Use cooperative-sticky"},
            {"kind": "static-membership", "level": "must", "message": "Enable group.instance.id"},
        ]
        event = delta_builder.build_advisor_event(
            group_id="test-group",
            advice_list=advice_list,
        )

        # Then
        assert event["type"] == "advisor"
        assert event["group_id"] == "test-group"
        assert len(event["advice"]) == 2
        assert event["advice"][0]["kind"] == "assignor"

    def test_build_system_health_event(self, delta_builder):
        """System Health 이벤트 생성"""
        # When
        event = delta_builder.build_system_health_event(
            collector_ok=True,
            broker_ok=True,
        )

        # Then
        assert event["type"] == "system_health"
        assert event["collector_ok"] is True
        assert event["broker_ok"] is True

    def test_custom_thresholds(self, custom_thresholds):
        """커스텀 임계치 적용"""
        # Given
        builder = DeltaBuilder(thresholds=custom_thresholds)

        # Then
        assert builder._thresholds.lag.spike_delta_total_lag == 1000
        assert builder._thresholds.stuck.duration_s_ge == 60
        assert builder._thresholds.fairness.gini_warn == 0.3

    def test_event_common_header(self, delta_builder):
        """모든 이벤트의 공통 헤더 검증"""
        # When
        event = delta_builder.build_system_health_event(
            collector_ok=True,
            broker_ok=True,
        )

        # Then - 공통 헤더 필드
        assert "type" in event
        assert "version" in event
        assert event["version"] == "v1"
        assert "ts" in event
        assert "trace_id" in event
