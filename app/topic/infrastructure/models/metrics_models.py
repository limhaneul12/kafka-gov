"""메트릭 ORM 모델"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ....shared.database import Base


class MetricsSnapshot(Base):
    """메트릭 스냅샷 테이블

    주기적으로 수집된 클러스터 전체 메트릭 스냅샷
    """

    __tablename__ = "metrics_snapshots"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 클러스터 정보
    cluster_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # 수집 시간
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    # 클러스터 지표
    broker_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_partitions: Mapped[int] = mapped_column(Integer, nullable=False)
    partition_to_broker_ratio: Mapped[float] = mapped_column(Float, nullable=False)

    # 로그 디렉토리 (선택)
    log_dir: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    topic_metrics: Mapped[list[TopicPartitionMetrics]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan", lazy="selectin"
    )

    # Indexes
    __table_args__ = (
        Index("idx_cluster_collected", "cluster_id", "collected_at"),
        Index("idx_collected_at_desc", "collected_at", postgresql_ops={"collected_at": "DESC"}),
    )

    def __repr__(self) -> str:
        return (
            f"<MetricsSnapshot(id={self.id}, cluster={self.cluster_id}, "
            f"collected_at={self.collected_at})>"
        )


class TopicPartitionMetrics(Base):
    """토픽 파티션 메트릭 테이블

    각 스냅샷 시점의 토픽별 파티션 메트릭
    """

    __tablename__ = "topic_partition_metrics"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign Key
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("metrics_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 토픽 정보
    topic_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # 파티션 메트릭
    partition_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    avg_partition_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    max_partition_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    min_partition_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Relationships
    snapshot: Mapped[MetricsSnapshot] = relationship(back_populates="topic_metrics")

    # Indexes
    __table_args__ = (
        Index("idx_snapshot_topic", "snapshot_id", "topic_name"),
        Index("idx_topic_name", "topic_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<TopicPartitionMetrics(id={self.id}, snapshot_id={self.snapshot_id}, "
            f"topic={self.topic_name}, partitions={self.partition_count})>"
        )


class LeaderDistribution(Base):
    """리더 분포 메트릭 테이블

    각 스냅샷 시점의 브로커별 리더 파티션 수
    """

    __tablename__ = "leader_distributions"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign Key
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("metrics_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 브로커 정보
    broker_id: Mapped[int] = mapped_column(Integer, nullable=False)
    leader_partition_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Indexes
    __table_args__ = (Index("idx_snapshot_broker", "snapshot_id", "broker_id"),)

    def __repr__(self) -> str:
        return (
            f"<LeaderDistribution(id={self.id}, snapshot_id={self.snapshot_id}, "
            f"broker={self.broker_id}, leaders={self.leader_partition_count})>"
        )
