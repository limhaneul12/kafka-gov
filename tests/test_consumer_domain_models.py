from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.consumer.domain.models.group import ConsumerGroup, LagStats
from app.consumer.domain.models.member import ConsumerMember, MemberStats
from app.consumer.domain.models.metrics import ConsumerGroupAdvice, FairnessIndex
from app.consumer.domain.models.partition import ConsumerPartition, StuckPartition
from app.consumer.domain.models.rebalance import RebalanceDelta, RebalanceRollup
from app.consumer.domain.types_enum import FairnessLevel, GroupState, PartitionAssignor, WindowType


def _ts() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def test_lag_stats_and_consumer_group_behaviors() -> None:
    lag = LagStats(
        total_lag=1200, mean_lag=300.0, p50_lag=200, p95_lag=900, max_lag=1200, partition_count=4
    )
    assert lag.is_healthy(1000) is True
    assert lag.is_healthy(800) is False
    assert lag.slo_compliance_rate(1000) == 1.0
    assert 0.0 < lag.slo_compliance_rate(500) < 1.0

    group = ConsumerGroup(
        cluster_id="c1",
        group_id="g1",
        ts=_ts(),
        state=GroupState.STABLE,
        partition_assignor=PartitionAssignor.COOPERATIVE_STICKY,
        member_count=3,
        topic_count=2,
        lag_stats=lag,
    )
    assert group.is_stable() is True
    assert group.is_rebalancing() is False
    assert group.is_empty() is False
    assert group.has_high_lag(1000) is True
    assert group.needs_attention(800) is True
    assert "group_id=g1" in repr(group)


def test_consumer_member_and_member_stats() -> None:
    member = ConsumerMember(
        cluster_id="c1",
        group_id="g1",
        member_id="m1",
        ts=_ts(),
        client_id="client-a",
        client_host="10.0.0.1",
        assigned_tp_count=2,
    )
    assert member.has_partitions() is True
    assert member.is_idle() is False
    assert "member_id=m1" in repr(member)

    idle_member = ConsumerMember(
        cluster_id="c1",
        group_id="g1",
        member_id="m2",
        ts=_ts(),
        client_id=None,
        client_host=None,
        assigned_tp_count=0,
    )
    assert idle_member.has_partitions() is False
    assert idle_member.is_idle() is True

    stats = MemberStats(member_id="m1", assigned_tp_count=6, total_lag=300, avg_lag=50.0)
    assert stats.workload_ratio(12) == 0.5
    assert stats.workload_ratio(0) == 0.0
    assert stats.is_overloaded(avg_tp_count=2.0, threshold=1.5) is True
    assert stats.is_overloaded(avg_tp_count=0.0) is False
    assert "tp_count=6" in repr(stats)


def test_fairness_and_advice() -> None:
    balanced = FairnessIndex(
        gini_coefficient=0.1,
        member_count=4,
        avg_tp_per_member=3.0,
        max_tp_per_member=4,
        min_tp_per_member=2,
    )
    slight = FairnessIndex(
        gini_coefficient=0.3,
        member_count=4,
        avg_tp_per_member=3.0,
        max_tp_per_member=6,
        min_tp_per_member=1,
    )
    hotspot = FairnessIndex(
        gini_coefficient=0.7,
        member_count=4,
        avg_tp_per_member=3.0,
        max_tp_per_member=10,
        min_tp_per_member=0,
    )
    assert balanced.level() == FairnessLevel.BALANCED
    assert slight.level() == FairnessLevel.SLIGHT_SKEW
    assert hotspot.level() == FairnessLevel.HOTSPOT
    assert balanced.is_balanced() is True
    assert hotspot.has_hotspot() is True

    no_action = ConsumerGroupAdvice(
        assignor_recommendation=None,
        assignor_reason=None,
        static_membership_recommended=False,
        static_membership_reason=None,
        scale_recommendation=None,
        scale_reason=None,
        slo_compliance_rate=1.0,
        risk_eta=None,
    )
    action = ConsumerGroupAdvice(
        assignor_recommendation="cooperative-sticky",
        assignor_reason="less movement",
        static_membership_recommended=True,
        static_membership_reason="restart stability",
        scale_recommendation="increase_consumers",
        scale_reason="high lag",
        slo_compliance_rate=0.6,
        risk_eta=_ts(),
    )
    assert no_action.needs_action() is False
    assert action.needs_action() is True


def test_consumer_partition_and_stuck_partition() -> None:
    part = ConsumerPartition(
        cluster_id="c1",
        group_id="g1",
        topic="orders",
        partition=0,
        ts=_ts(),
        committed_offset=100,
        latest_offset=500,
        lag=400,
        assigned_member_id="m1",
    )
    assert part.is_assigned() is True
    assert part.is_lagging(300) is True
    assert part.has_high_lag(300) is True
    assert part.is_caught_up(10) is False
    assert "topic=orders" in repr(part)

    part_none = ConsumerPartition(
        cluster_id="c1",
        group_id="g1",
        topic="orders",
        partition=1,
        ts=_ts(),
        committed_offset=None,
        latest_offset=None,
        lag=None,
        assigned_member_id=None,
    )
    assert part_none.is_assigned() is False
    assert part_none.is_lagging() is False
    assert part_none.has_high_lag() is False
    assert part_none.is_caught_up() is False

    stuck = StuckPartition(
        cluster_id="c1",
        group_id="g1",
        topic="orders",
        partition=2,
        assigned_member_id="m2",
        since_ts=_ts(),
        detected_ts=_ts() + timedelta(minutes=3),
        current_lag=60000,
        delta_committed=0,
        delta_lag=25,
    )
    assert stuck.stuck_duration_seconds(_ts() + timedelta(seconds=30)) == 30.0
    assert stuck.is_critical(50000) is True
    assert stuck.meets_detection_criteria() is True
    assert "stuck_since=" in repr(stuck)


def test_rebalance_models() -> None:
    delta = RebalanceDelta(
        cluster_id="c1",
        group_id="g1",
        ts=_ts(),
        moved_partitions=3,
        join_count=2,
        leave_count=1,
        elapsed_since_prev_s=60,
        state="Stable",
        assignment_hash="abc",
    )
    assert delta.movement_rate(0) == 0.0
    assert delta.movement_rate(10) == 0.3
    assert delta.movement_rate(2) == 1.0
    assert delta.is_significant_movement() is True
    assert delta.has_membership_changes() is True
    assert delta.net_member_change() == 1
    assert "moved=3" in repr(delta)

    roll_5m = RebalanceRollup(
        cluster_id="c1",
        group_id="g1",
        window_start=_ts(),
        window=WindowType.FIVE_MINUTES,
        rebalances=2,
        avg_moved_partitions=10.0,
        max_moved_partitions=20,
        stable_ratio=0.8,
    )
    roll_1h = RebalanceRollup(
        cluster_id="c1",
        group_id="g1",
        window_start=_ts(),
        window=WindowType.ONE_HOUR,
        rebalances=2,
        avg_moved_partitions=None,
        max_moved_partitions=None,
        stable_ratio=None,
    )
    assert roll_5m.rebalances_per_hour() == 24
    assert roll_1h.rebalances_per_hour() == 2.0

    assert 0.0 <= roll_5m.rebalance_score() <= 100.0
    assert roll_5m.is_stable(0.0) is True
    assert roll_5m.is_churning(100.0) is True
    assert roll_1h.stickiness_score() == 1.0
    assert 0.0 <= roll_5m.stickiness_score() <= 1.0
    assert "window=5m" in repr(roll_5m)
