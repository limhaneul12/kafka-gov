"""Consumer Infrastructure Models - SQLAlchemy ORM

Consumer Group Governance 테이블 정의
- 스냅샷 테이블 3개 (Group, Member, Partition)
- 리밸런스 테이블 2개 (Delta, Rollup)

"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base

# ============================================================================
# 스냅샷 테이블 (시계열 데이터)
# ============================================================================


class ConsumerGroupSnapshotModel(Base):
    """Consumer Group 스냅샷 테이블

    30-60초 주기로 수집되는 Consumer Group 상태

    저장 데이터:
    - Group 기본 정보 (state, assignor, member_count)
    - Lag 통계 (total_lag, p50_lag, p95_lag, max_lag)

    계산 공식 (cal.md):
    - total_lag = Σ(lag_i)
    - p50_lag = median({ lag_i })
    - p95_lag = percentile({ lag_i }, 95)
    - max_lag = max({ lag_i })
    """

    __tablename__ = "consumer_group_snapshot"

    # 기본 키
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="스냅샷 ID"
    )

    # 클러스터 & 그룹 식별자
    cluster_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="클러스터 ID"
    )
    group_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Consumer Group ID"
    )

    # 타임스탬프
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="수집 시각",
    )

    # Group 상태 정보
    state: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="그룹 상태 (Stable/Rebalancing/Empty/Dead)"
    )
    partition_assignor: Mapped[str | None] = mapped_column(
        String(100), comment="파티션 할당 알고리즘 (range/roundrobin/cooperative-sticky)"
    )

    # 카운트 정보
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="멤버 수")
    topic_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="구독 토픽 수")

    # Lag 통계 (cal.md 1️⃣)
    total_lag: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="전체 lag 합")
    p50_lag: Mapped[int | None] = mapped_column(BigInteger, comment="P50 lag (중간값)")
    p95_lag: Mapped[int | None] = mapped_column(BigInteger, comment="P95 lag")
    max_lag: Mapped[int | None] = mapped_column(BigInteger, comment="최대 lag")

    # 인덱스
    __table_args__ = (
        Index("idx_consumer_group_snapshot_cluster_group_ts", "cluster_id", "group_id", "ts"),
        Index("idx_consumer_group_snapshot_ts", "ts"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConsumerGroupSnapshot("
            f"group_id={self.group_id}, "
            f"state={self.state}, "
            f"total_lag={self.total_lag}"
            f")>"
        )


class ConsumerMemberSnapshotModel(Base):
    """Consumer Member 스냅샷 테이블

    Consumer Group 내 개별 멤버(consumer) 정보

    저장 데이터:
    - 멤버 식별자 (member_id, client_id)
    - 호스트 정보 (client_host)
    - 할당 파티션 수 (assigned_tp_count)

    용도:
    - Fairness Index 계산 (cal.md 4️⃣)
    - Hotspot 감지
    """

    __tablename__ = "consumer_member_snapshot"

    # 기본 키
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="스냅샷 ID"
    )

    # 클러스터 & 그룹 식별자
    cluster_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="클러스터 ID"
    )
    group_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Consumer Group ID"
    )

    # 타임스탬프
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="수집 시각",
    )

    # 멤버 식별 정보
    member_id: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="GroupCoordinator 부여 멤버 ID"
    )
    client_id: Mapped[str | None] = mapped_column(String(255), comment="Consumer client 식별자")
    client_host: Mapped[str | None] = mapped_column(String(255), comment="실행 호스트 IP")

    # 할당 정보
    assigned_tp_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="담당 파티션 수"
    )

    # 인덱스
    __table_args__ = (
        Index("idx_consumer_member_snapshot_cluster_group_ts", "cluster_id", "group_id", "ts"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConsumerMemberSnapshot("
            f"group_id={self.group_id}, "
            f"member_id={self.member_id}, "
            f"assigned_tp_count={self.assigned_tp_count}"
            f")>"
        )


class ConsumerPartitionSnapshotModel(Base):
    """Consumer Partition 스냅샷 테이블

    파티션별 오프셋 및 lag 정보

    저장 데이터:
    - 오프셋 (committed_offset, latest_offset)
    - Lag (latest - committed)
    - 담당 멤버 (assigned_member_id)

    용도:
    - Lag 통계 계산 (cal.md 1️⃣)
    - Stuck Partition 감지 (cal.md 2️⃣)
    """

    __tablename__ = "consumer_partition_snapshot"

    # 기본 키
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="스냅샷 ID"
    )

    # 클러스터 & 그룹 식별자
    cluster_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="클러스터 ID"
    )
    group_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Consumer Group ID"
    )

    # 타임스탬프
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="수집 시각",
    )

    # 파티션 식별자
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="토픽 이름")
    partition: Mapped[int] = mapped_column(Integer, nullable=False, comment="파티션 번호")

    # 오프셋 정보
    committed_offset: Mapped[int | None] = mapped_column(
        BigInteger, comment="그룹의 커밋 오프셋 (list_consumer_group_offsets)"
    )
    latest_offset: Mapped[int | None] = mapped_column(
        BigInteger, comment="브로커 최신 오프셋 (list_offsets)"
    )
    lag: Mapped[int | None] = mapped_column(
        BigInteger, comment="Lag (latest_offset - committed_offset)"
    )

    # 할당 정보
    assigned_member_id: Mapped[str | None] = mapped_column(
        String(255), comment="담당 consumer 멤버 ID"
    )

    # 인덱스
    __table_args__ = (
        Index(
            "idx_consumer_partition_snapshot_cluster_group_ts",
            "cluster_id",
            "group_id",
            "ts",
        ),
        Index("idx_consumer_partition_snapshot_cluster_topic_ts", "cluster_id", "topic", "ts"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConsumerPartitionSnapshot("
            f"group_id={self.group_id}, "
            f"topic={self.topic}, "
            f"partition={self.partition}, "
            f"lag={self.lag}"
            f")>"
        )


# ============================================================================
# 리밸런스 테이블 (변경 감지 + 집계)
# ============================================================================


class ConsumerGroupRebalanceDeltaModel(Base):
    """Consumer Group 리밸런스 델타 테이블

    리밸런스 발생 시 변경 내역 기록 (해시 기반 변경 감지)

    저장 데이터:
    - 파티션 이동 (moved_partitions)
    - 멤버 증감 (join_count, leave_count)
    - 경과 시간 (elapsed_since_prev_s)
    - 할당 해시 (assignment_hash: SHA-1)

    용도:
    - Rebalance Churn Score 계산 (cal.md 3️⃣)
    - Movement Rate 계산
    - Stable Ratio 계산
    """

    __tablename__ = "consumer_group_rebalance_delta"

    # 기본 키
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="델타 ID"
    )

    # 클러스터 & 그룹 식별자
    cluster_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="클러스터 ID"
    )
    group_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Consumer Group ID"
    )

    # 타임스탬프
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="리밸런스 발생 시각",
    )

    # 리밸런스 델타 정보
    moved_partitions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="이전 대비 이동한 파티션 수"
    )
    join_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="새로 참여한 멤버 수"
    )
    leave_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="떠난 멤버 수"
    )

    # 경과 시간
    elapsed_since_prev_s: Mapped[int | None] = mapped_column(
        Integer, comment="직전 리밸런스 이후 경과 시간 (초)"
    )

    # 상태
    state: Mapped[str] = mapped_column(String(50), nullable=False, comment="리밸런스 후 그룹 상태")

    # 할당 해시 (변경 감지용)
    assignment_hash: Mapped[str] = mapped_column(
        String(40), nullable=False, comment="TP→Member 매핑의 SHA-1 해시"
    )

    # 인덱스
    __table_args__ = (
        Index("idx_consumer_rebalance_delta_cluster_group_ts", "cluster_id", "group_id", "ts"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConsumerGroupRebalanceDelta("
            f"group_id={self.group_id}, "
            f"moved_partitions={self.moved_partitions}, "
            f"join={self.join_count}, "
            f"leave={self.leave_count}"
            f")>"
        )


class ConsumerGroupRebalanceRollupModel(Base):
    """Consumer Group 리밸런스 롤업 테이블

    시간 윈도우별 리밸런스 통계 집계 (5분/1시간)

    저장 데이터:
    - 리밸런스 횟수 (rebalances)
    - 파티션 이동 통계 (avg_moved_partitions, max_moved_partitions)
    - 안정 유지 비율 (stable_ratio)

    용도:
    - Rebalance Score 계산 (cal.md)
    - 장기 트렌드 분석

    계산 공식 (cal.md 3):
    - rebalance_score = 100 - alpha * rebalances_per_hour (alpha=10)
    - stable_ratio = stable_time / (stable_time + rebalancing_time)
    """

    __tablename__ = "consumer_group_rebalance_rollup"

    # 기본 키
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="롤업 ID"
    )

    # 클러스터 & 그룹 식별자
    cluster_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="클러스터 ID"
    )
    group_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Consumer Group ID"
    )

    # 윈도우 정보
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="윈도우 시작 시각"
    )
    window: Mapped[str] = mapped_column(
        Enum("5m", "1h", name="rollup_window_enum"),
        nullable=False,
        comment="집계 단위 (5분/1시간)",
    )

    # 리밸런스 통계
    rebalances: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="윈도우 내 리밸런스 횟수"
    )
    avg_moved_partitions: Mapped[float | None] = mapped_column(Float, comment="평균 이동 파티션 수")
    max_moved_partitions: Mapped[int | None] = mapped_column(Integer, comment="최대 이동 파티션 수")

    # 안정성 지표 (cal.md 3️⃣)
    stable_ratio: Mapped[float | None] = mapped_column(
        Float, comment="안정 유지 비율 (stable_time / total_time)"
    )

    # 유니크 제약 (중복 방지)
    __table_args__ = (
        UniqueConstraint(
            "cluster_id",
            "group_id",
            "window",
            "window_start",
            name="uk_consumer_rebalance_rollup",
        ),
        Index(
            "idx_consumer_rebalance_rollup_cluster_group_window",
            "cluster_id",
            "group_id",
            "window",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ConsumerGroupRebalanceRollup("
            f"group_id={self.group_id}, "
            f"window={self.window}, "
            f"rebalances={self.rebalances}, "
            f"stable_ratio={self.stable_ratio}"
            f")>"
        )
