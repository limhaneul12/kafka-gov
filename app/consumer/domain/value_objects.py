"""Consumer Domain Value Objects

Infrastructure에서 Domain으로 옮긴 Value Objects
- TopicPartition: 토픽 파티션 식별자
- BrokerInfo: 브로커 정보
- MemberInfo: Consumer 멤버 정보
- ConsumerGroupInfo: 그룹 기본 정보
- ConsumerGroupDescription: 그룹 상세 정보
- PartitionOffset: 파티션 오프셋 정보
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TopicPartition:
    """토픽 파티션 식별자"""

    topic: str
    partition: int


@dataclass(frozen=True, slots=True)
class BrokerInfo:
    """브로커 정보"""

    broker_id: int
    host: str
    port: int


@dataclass(slots=True)
class MemberInfo:
    """Consumer Member 정보"""

    member_id: str
    client_id: str
    client_host: str
    assignments: list[TopicPartition]


@dataclass(slots=True)
class ConsumerGroupInfo:
    """Consumer Group 기본 정보

    list_consumer_groups() 결과 (Confluent Kafka Python v2.12.0)

    참고:
    - ConsumerGroupListing 객체에서 추출
    - partition_assignor는 describe_consumer_groups()에서만 조회 가능
    """

    group_id: str
    state: str  # Stable, Rebalancing, Empty, Dead
    is_simple_consumer_group: bool  # Simple vs Classic/New protocol
    group_type: str  # ConsumerGroupType (Classic, Consumer)


@dataclass(slots=True)
class ConsumerGroupDescription:
    """Consumer Group 상세 정보

    describe_consumer_groups() 결과
    """

    group_id: str
    state: str
    partition_assignor: str
    members: list[MemberInfo]
    coordinator: BrokerInfo


@dataclass(frozen=True, slots=True)
class PartitionOffset:
    """파티션 오프셋 정보"""

    topic: str
    partition: int
    offset: int | None  # None이면 아직 커밋 안 됨
