"""Consumer Member Domain Models

Consumer Group 내 개별 멤버(Consumer) 모델
- ConsumerMember: 멤버 정보
- MemberStats: 멤버별 통계

참고: cal.md - Fairness Index 계산
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, kw_only=True)
class ConsumerMember:
    """Consumer Member 도메인 엔티티

    Consumer Group 내 개별 consumer 정보

    책임:
    - 멤버 식별 (member_id, client_id)
    - 호스트 정보 (client_host)
    - 할당 파티션 수 (assigned_tp_count)

    용도:
    - Fairness Index 계산 (cal.md)
    - Hotspot 감지
    """

    # 식별자
    cluster_id: str
    group_id: str
    member_id: str

    # 스냅샷 시각
    ts: datetime

    # 멤버 정보
    client_id: str | None
    client_host: str | None

    # 할당 정보
    assigned_tp_count: int  # 담당 파티션 수

    def has_partitions(self) -> bool:
        """파티션 할당 여부"""
        return self.assigned_tp_count > 0

    def is_idle(self) -> bool:
        """유휴 상태 여부 (파티션 없음)"""
        return self.assigned_tp_count == 0

    def __repr__(self) -> str:
        return (
            f"<ConsumerMember("
            f"member_id={self.member_id}, "
            f"client_id={self.client_id}, "
            f"assigned_tp={self.assigned_tp_count}"
            f")>"
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class MemberStats:
    """멤버별 통계 Value Object

    Fairness Index 계산을 위한 멤버 통계

    계산 공식 (cal.md 4️⃣):
    - 멤버별 담당 파티션 부하 분포
    - Gini Coefficient로 불균형 측정
    """

    member_id: str
    assigned_tp_count: int
    total_lag: int  # 해당 멤버 담당 파티션의 총 lag
    avg_lag: float  # 해당 멤버 담당 파티션의 평균 lag

    def workload_ratio(self, total_partitions: int) -> float:
        """작업 부하 비율

        Args:
            total_partitions: 전체 파티션 수

        Returns:
            할당 비율 (0.0 ~ 1.0)
        """
        if total_partitions == 0:
            return 0.0
        return self.assigned_tp_count / total_partitions

    def is_overloaded(self, avg_tp_count: float, threshold: float = 1.5) -> bool:
        """과부하 여부

        Args:
            avg_tp_count: 평균 파티션 수
            threshold: 과부하 임계값 (기본 1.5배)

        Returns:
            True if 평균 대비 threshold배 이상
        """
        if avg_tp_count == 0:
            return False
        return self.assigned_tp_count > avg_tp_count * threshold

    def __repr__(self) -> str:
        return (
            f"<MemberStats("
            f"member_id={self.member_id}, "
            f"tp_count={self.assigned_tp_count}, "
            f"total_lag={self.total_lag}"
            f")>"
        )
