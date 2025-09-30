"""Subject Naming Strategy 유틸리티"""

from __future__ import annotations

from enum import Enum


class SubjectStrategy(str, Enum):
    """Subject Naming Strategy"""

    TOPIC_NAME = "TopicNameStrategy"
    RECORD_NAME = "RecordNameStrategy"
    TOPIC_RECORD_NAME = "TopicRecordNameStrategy"


def extract_topics_from_subject(subject: str, strategy: SubjectStrategy | str) -> list[str]:
    """Subject naming strategy에 따라 토픽명 추출

    Args:
        subject: Schema subject 이름
        strategy: Subject naming strategy

    Returns:
        추출된 토픽명 리스트 (추출 불가 시 빈 리스트)

    Examples:
        >>> extract_topics_from_subject("orders-value", SubjectStrategy.TOPIC_NAME)
        ['orders']

        >>> extract_topics_from_subject("orders-com.example.Order", SubjectStrategy.TOPIC_RECORD_NAME)
        ['orders']

        >>> extract_topics_from_subject("com.example.Order", SubjectStrategy.RECORD_NAME)
        []
    """
    # str로 전달된 경우 변환
    if isinstance(strategy, str):
        try:
            strategy = SubjectStrategy(strategy)
        except ValueError:
            return []

    if strategy == SubjectStrategy.TOPIC_NAME:
        # 예: "orders-value" -> ["orders"]
        if subject.endswith(("-key", "-value")):
            topic_name = subject.rsplit("-", 1)[0]
            return [topic_name]

    elif strategy == SubjectStrategy.TOPIC_RECORD_NAME:
        # 예: "orders-com.example.Order" -> ["orders"]
        parts = subject.split("-", 1)
        if len(parts) >= 2:
            return [parts[0]]

    elif strategy == SubjectStrategy.RECORD_NAME:
        # 예: "com.example.Order" -> 토픽명 추론 불가
        return []

    return []
