"""Consumer 모듈 테스트용 Fixtures"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.consumer.infrastructure.models import (
    ConsumerGroupSnapshotModel,
    ConsumerMemberSnapshotModel,
    ConsumerPartitionSnapshotModel,
)


@pytest.fixture
def sample_cluster_id() -> str:
    """샘플 클러스터 ID"""
    return "test-cluster"


@pytest.fixture
def sample_group_id() -> str:
    """샘플 Consumer Group ID"""
    return "test-group"


@pytest.fixture
def sample_timestamp() -> datetime:
    """샘플 타임스탬프"""
    return datetime(2025, 10, 28, 7, 10, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def session_factory(test_engine):
    """AsyncSession 팩토리 (Use Cases에서 사용)"""
    factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    @asynccontextmanager
    async def get_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    return get_session


@pytest_asyncio.fixture
async def sample_group_snapshot(
    db_session: AsyncSession,
    sample_cluster_id: str,
    sample_group_id: str,
    sample_timestamp: datetime,
) -> ConsumerGroupSnapshotModel:
    """샘플 Consumer Group 스냅샷"""
    snapshot = ConsumerGroupSnapshotModel(
        cluster_id=sample_cluster_id,
        group_id=sample_group_id,
        ts=sample_timestamp,
        state="Stable",
        partition_assignor="range",
        member_count=3,
        topic_count=2,
        total_lag=1500,
        p50_lag=450,
        p95_lag=800,
        max_lag=1000,
    )
    db_session.add(snapshot)
    await db_session.commit()
    await db_session.refresh(snapshot)
    return snapshot


@pytest_asyncio.fixture
async def sample_group_members(
    db_session: AsyncSession,
    sample_cluster_id: str,
    sample_group_id: str,
    sample_timestamp: datetime,
) -> list[ConsumerMemberSnapshotModel]:
    """샘플 Consumer Group 멤버 목록"""
    members = [
        ConsumerMemberSnapshotModel(
            cluster_id=sample_cluster_id,
            group_id=sample_group_id,
            ts=sample_timestamp,
            member_id="consumer-1",
            client_id="client-1",
            client_host="192.168.1.10",
            assigned_tp_count=1,
        ),
        ConsumerMemberSnapshotModel(
            cluster_id=sample_cluster_id,
            group_id=sample_group_id,
            ts=sample_timestamp,
            member_id="consumer-2",
            client_id="client-2",
            client_host="192.168.1.11",
            assigned_tp_count=1,
        ),
        ConsumerMemberSnapshotModel(
            cluster_id=sample_cluster_id,
            group_id=sample_group_id,
            ts=sample_timestamp,
            member_id="consumer-3",
            client_id="client-3",
            client_host="192.168.1.12",
            assigned_tp_count=1,
        ),
    ]
    for member in members:
        db_session.add(member)
    await db_session.commit()
    for member in members:
        await db_session.refresh(member)
    return members


@pytest_asyncio.fixture
async def sample_group_partitions(
    db_session: AsyncSession,
    sample_cluster_id: str,
    sample_group_id: str,
    sample_timestamp: datetime,
) -> list[ConsumerPartitionSnapshotModel]:
    """샘플 Consumer Group 파티션 목록"""
    partitions = [
        ConsumerPartitionSnapshotModel(
            cluster_id=sample_cluster_id,
            group_id=sample_group_id,
            ts=sample_timestamp,
            topic="orders",
            partition=0,
            committed_offset=1000,
            latest_offset=1100,
            lag=100,
            assigned_member_id="consumer-1",
        ),
        ConsumerPartitionSnapshotModel(
            cluster_id=sample_cluster_id,
            group_id=sample_group_id,
            ts=sample_timestamp,
            topic="orders",
            partition=1,
            committed_offset=2000,
            latest_offset=2500,
            lag=500,
            assigned_member_id="consumer-2",
        ),
        ConsumerPartitionSnapshotModel(
            cluster_id=sample_cluster_id,
            group_id=sample_group_id,
            ts=sample_timestamp,
            topic="payments",
            partition=0,
            committed_offset=5000,
            latest_offset=5900,
            lag=900,
            assigned_member_id="consumer-3",
        ),
    ]
    for partition in partitions:
        db_session.add(partition)
    await db_session.commit()
    for partition in partitions:
        await db_session.refresh(partition)
    return partitions
