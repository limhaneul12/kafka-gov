"""타입 검증 테스트"""

from pydantic import ValidationError

from app.topic.interface.schema import TopicConfig, TopicMetadata


def test_topic_metadata():
    """TopicMetadata 검증 테스트"""
    print("=== TopicMetadata 검증 테스트 ===")

    # 정상 케이스
    try:
        metadata = TopicMetadata(
            owner="team-commerce",
            sla="P99<200ms",
            doc="https://wiki.company.com/streams/orders",
            tags=["pii", "critical"],
        )
        print("✅ 정상 케이스 통과:", metadata)
    except Exception as e:
        print("❌ 정상 케이스 실패:", e)

    # 잘못된 owner (패턴 위반)
    try:
        metadata = TopicMetadata(owner="Team-Commerce")  # 대문자 사용
        print("❌ 패턴 검증 실패 - 통과하면 안됨")
    except ValidationError as e:
        print("✅ 패턴 검증 성공:", e.errors()[0]["msg"])

    # 잘못된 태그
    try:
        metadata = TopicMetadata(
            owner="team-commerce",
            tags=["PII"],  # 대문자 사용
        )
        print("❌ 태그 검증 실패 - 통과하면 안됨")
    except ValidationError as e:
        print("✅ 태그 검증 성공:", e.errors()[0]["msg"])


def test_topic_config():
    """TopicConfig 검증 테스트"""
    print("\n=== TopicConfig 검증 테스트 ===")

    # 정상 케이스
    try:
        config = TopicConfig(
            partitions=12,
            replication_factor=3,
            retention_ms=604800000,
            min_insync_replicas=2,
            max_message_bytes=1048576,
        )
        print("✅ 정상 케이스 통과:", config)
    except Exception as e:
        print("❌ 정상 케이스 실패:", e)

    # 범위 초과 (파티션)
    try:
        config = TopicConfig(
            partitions=2000,  # 1000 초과
            replication_factor=3,
        )
        print("❌ 파티션 범위 검증 실패 - 통과하면 안됨")
    except ValidationError as e:
        print("✅ 파티션 범위 검증 성공:", e.errors()[0]["msg"])

    # 일관성 검증 (min_insync_replicas > replication_factor)
    try:
        config = TopicConfig(
            partitions=12,
            replication_factor=3,
            min_insync_replicas=5,  # replication_factor보다 큼
        )
        print("❌ 일관성 검증 실패 - 통과하면 안됨")
    except ValidationError as e:
        print("✅ 일관성 검증 성공:", e.errors()[0]["msg"])


if __name__ == "__main__":
    test_topic_metadata()
    test_topic_config()
