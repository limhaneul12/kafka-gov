"""Consumer Repository 테스트"""

from datetime import datetime, timedelta, timezone

import pytest

from app.consumer.infrastructure.repository import ConsumerRepository


class TestConsumerRepository:
    """ConsumerRepository 테스트"""

    @pytest.mark.asyncio
    async def test_get_latest_group_snapshot(
        self,
        db_session,
        sample_cluster_id,
        sample_group_id,
        sample_group_snapshot,
    ):
        """최신 그룹 스냅샷 조회"""
        # Given
        repo = ConsumerRepository(db_session)

        # When
        result = await repo.get_latest_group_snapshot(sample_cluster_id, sample_group_id)

        # Then
        assert result is not None
        assert result.group_id == sample_group_id
        assert result.state == "Stable"
        assert result.total_lag == 1500

    @pytest.mark.asyncio
    async def test_get_latest_group_snapshot_not_found(
        self,
        db_session,
        sample_cluster_id,
    ):
        """존재하지 않는 그룹 조회"""
        # Given
        repo = ConsumerRepository(db_session)

        # When
        result = await repo.get_latest_group_snapshot(sample_cluster_id, "non-existent-group")

        # Then
        assert result is None

    @pytest.mark.skip(
        reason="get_latest_members() 메서드는 구현되지 않음. Use Case에서 직접 쿼리 사용"
    )
    @pytest.mark.asyncio
    async def test_get_latest_members(
        self,
        db_session,
        sample_cluster_id,
        sample_group_id,
        sample_group_members,
    ):
        """최신 멤버 목록 조회"""
        # Given
        repo = ConsumerRepository(db_session)

        # When
        result = await repo.get_latest_members(sample_cluster_id, sample_group_id)

        # Then
        assert len(result) == 3
        assert result[0].member_id == "consumer-1"
        assert result[1].member_id == "consumer-2"
        assert result[2].member_id == "consumer-3"

    @pytest.mark.skip(
        reason="get_latest_partitions() 메서드는 구현되지 않음. get_partition_snapshots() 사용"
    )
    @pytest.mark.asyncio
    async def test_get_latest_partitions(
        self,
        db_session,
        sample_cluster_id,
        sample_group_id,
        sample_group_partitions,
    ):
        """최신 파티션 목록 조회"""
        # Given
        repo = ConsumerRepository(db_session)

        # When
        result = await repo.get_latest_partitions(sample_cluster_id, sample_group_id)

        # Then
        assert len(result) == 3
        assert result[0].topic == "orders"
        assert result[0].partition == 0
        assert result[0].lag == 100

    @pytest.mark.skip(
        reason="get_latest_partitions_by_topic() 메서드는 구현되지 않음. Use Case에서 직접 쿼리"
    )
    @pytest.mark.asyncio
    async def test_get_latest_partitions_by_topic(
        self,
        db_session,
        sample_cluster_id,
        sample_group_partitions,
    ):
        """토픽별 파티션 조회"""
        # Given
        repo = ConsumerRepository(db_session)

        # When
        result = await repo.get_latest_partitions_by_topic(sample_cluster_id, "orders")

        # Then
        assert len(result) == 2  # orders 토픽의 파티션 2개
        assert all(p.topic == "orders" for p in result)

    @pytest.mark.skip(
        reason="get_stuck_partitions() 메서드는 구현되지 않음. StuckPartitionDetector 사용"
    )
    @pytest.mark.asyncio
    async def test_get_stuck_partitions(
        self,
        db_session,
        sample_cluster_id,
        sample_group_id,
        sample_group_partitions,
    ):
        """Stuck 파티션 조회 (임계치 기반)"""
        # Given
        repo = ConsumerRepository(db_session)

        # When - lag이 큰 파티션만 조회
        result = await repo.get_stuck_partitions(
            cluster_id=sample_cluster_id,
            group_id=sample_group_id,
            min_lag=500,  # lag >= 500인 파티션만
        )

        # Then
        assert len(result) >= 2  # lag 500, 900인 파티션
        assert all(p.lag >= 500 for p in result)

    @pytest.mark.skip(
        reason="get_group_snapshots_in_range() 메서드는 구현되지 않음. get_group_snapshot_history() 사용"
    )
    @pytest.mark.asyncio
    async def test_get_group_snapshots_in_range(
        self,
        db_session,
        sample_cluster_id,
        sample_group_id,
        sample_timestamp,
    ):
        """시간 범위 내 스냅샷 조회"""
        # Given
        repo = ConsumerRepository(db_session)
        from app.consumer.infrastructure.models import ConsumerGroupSnapshotModel

        # 여러 시점의 스냅샷 생성
        snapshots = [
            ConsumerGroupSnapshotModel(
                cluster_id=sample_cluster_id,
                group_id=sample_group_id,
                ts=sample_timestamp - timedelta(minutes=i),
                state="Stable",
                partition_assignor="range",
                member_count=3,
                topic_count=2,
                total_lag=1000 + i * 100,
                p50_lag=300,
                p95_lag=500,
                max_lag=600,
            )
            for i in range(5)
        ]
        for snapshot in snapshots:
            db_session.add(snapshot)
        await db_session.commit()

        # When
        start_time = sample_timestamp - timedelta(minutes=10)
        end_time = sample_timestamp + timedelta(minutes=10)
        result = await repo.get_group_snapshots_in_range(
            cluster_id=sample_cluster_id,
            group_id=sample_group_id,
            start_time=start_time,
            end_time=end_time,
        )

        # Then
        assert len(result) == 5

    @pytest.mark.skip(
        reason="calculate_lag_percentiles() 메서드는 구현되지 않음. ConsumerMetricsCalculator 사용"
    )
    @pytest.mark.asyncio
    async def test_calculate_lag_percentiles(
        self,
        db_session,
        sample_cluster_id,
        sample_group_id,
        sample_group_partitions,
    ):
        """Lag 백분위수 계산"""
        # Given
        repo = ConsumerRepository(db_session)

        # When
        result = await repo.calculate_lag_percentiles(sample_cluster_id, sample_group_id)

        # Then
        assert "p50" in result
        assert "p95" in result
        assert "max" in result
        assert result["max"] == 900  # 최대 lag
