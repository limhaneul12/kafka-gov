"""Subject Utils 테스트"""

from __future__ import annotations

from app.shared.domain.subject_utils import SubjectStrategy, extract_topics_from_subject


class TestSubjectStrategy:
    """SubjectStrategy Enum 테스트"""

    def test_enum_values(self):
        """Enum 값 확인"""
        assert SubjectStrategy.TOPIC_NAME.value == "TopicNameStrategy"
        assert SubjectStrategy.RECORD_NAME.value == "RecordNameStrategy"
        assert SubjectStrategy.TOPIC_RECORD_NAME.value == "TopicRecordNameStrategy"


class TestExtractTopicsFromSubject:
    """extract_topics_from_subject 함수 테스트"""

    def test_topic_name_strategy_with_value_suffix(self):
        """TopicNameStrategy: -value 접미사"""
        topics = extract_topics_from_subject("orders-value", SubjectStrategy.TOPIC_NAME)
        assert topics == ["orders"]

    def test_topic_name_strategy_with_key_suffix(self):
        """TopicNameStrategy: -key 접미사"""
        topics = extract_topics_from_subject("users-key", SubjectStrategy.TOPIC_NAME)
        assert topics == ["users"]

    def test_topic_name_strategy_without_suffix(self):
        """TopicNameStrategy: 접미사 없음"""
        topics = extract_topics_from_subject("orders", SubjectStrategy.TOPIC_NAME)
        assert topics == []

    def test_topic_name_strategy_with_dots(self):
        """TopicNameStrategy: 점이 포함된 토픽명"""
        topics = extract_topics_from_subject("dev.orders.events-value", SubjectStrategy.TOPIC_NAME)
        assert topics == ["dev.orders.events"]

    def test_topic_record_name_strategy(self):
        """TopicRecordNameStrategy"""
        topics = extract_topics_from_subject(
            "orders-com.example.Order", SubjectStrategy.TOPIC_RECORD_NAME
        )
        assert topics == ["orders"]

    def test_topic_record_name_strategy_no_separator(self):
        """TopicRecordNameStrategy: 구분자 없음"""
        topics = extract_topics_from_subject("com.example.Order", SubjectStrategy.TOPIC_RECORD_NAME)
        assert topics == []

    def test_record_name_strategy(self):
        """RecordNameStrategy: 토픽명 추론 불가"""
        topics = extract_topics_from_subject("com.example.Order", SubjectStrategy.RECORD_NAME)
        assert topics == []

    def test_strategy_as_string(self):
        """Strategy를 문자열로 전달"""
        topics = extract_topics_from_subject("orders-value", "TopicNameStrategy")
        assert topics == ["orders"]

    def test_invalid_strategy_string(self):
        """잘못된 strategy 문자열"""
        topics = extract_topics_from_subject("orders-value", "InvalidStrategy")
        assert topics == []

    def test_empty_subject(self):
        """빈 subject"""
        topics = extract_topics_from_subject("", SubjectStrategy.TOPIC_NAME)
        assert topics == []

    def test_complex_topic_name(self):
        """복잡한 토픽명"""
        topics = extract_topics_from_subject(
            "prod.events.user.created-value", SubjectStrategy.TOPIC_NAME
        )
        assert topics == ["prod.events.user.created"]
