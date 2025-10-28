"""Consumer Domain Enums

모든 Enum 타입 통합
- GroupState: Consumer Group 상태
- PartitionAssignor: 파티션 할당 알고리즘
- WindowType: 집계 윈도우 타입
- FairnessLevel: 부하 균형 수준
"""

from enum import Enum


class GroupState(str, Enum):
    """Consumer Group 상태

    Kafka Consumer Group의 가능한 상태값
    """

    STABLE = "Stable"
    REBALANCING = "Rebalancing"
    EMPTY = "Empty"
    DEAD = "Dead"


class PartitionAssignor(str, Enum):
    """파티션 할당 알고리즘

    Consumer Group의 파티션 배정 전략
    """

    RANGE = "range"
    ROUNDROBIN = "roundrobin"
    STICKY = "sticky"
    COOPERATIVE_STICKY = "cooperative-sticky"


class WindowType(str, Enum):
    """집계 윈도우 타입"""

    FIVE_MINUTES = "5m"
    ONE_HOUR = "1h"


class FairnessLevel(str, Enum):
    """부하 균형 수준

    Gini 계수 기준 (cal.md 4️⃣):
    - G ≤ 0.2: 균형
    - 0.2 < G ≤ 0.4: 경미한 불균형
    - G > 0.4: 심각한 편중
    """

    BALANCED = "Balanced"
    SLIGHT_SKEW = "Slight Skew"
    HOTSPOT = "Hotspot"
