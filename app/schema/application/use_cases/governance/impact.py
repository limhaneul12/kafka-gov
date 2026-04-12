"""Schema subject에서 알려진 토픽명을 추론하는 유스케이스"""

from __future__ import annotations

import logging

from app.schema.domain.models import SubjectName
from app.shared.domain.subject_utils import SubjectStrategy, extract_topics_from_subject


class GetKnownTopicNamesUseCase:
    """Subject naming 규칙으로 알려진 토픽명을 구성합니다."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    async def execute(self, registry_id: str, subject: SubjectName) -> list[str]:
        _ = registry_id

        found_topics = self._derive_known_topic_names(subject)
        self.logger.debug(
            "derived_known_topic_names registry_id=%s subject=%s topics=%s",
            registry_id,
            subject,
            found_topics,
        )

        return found_topics

    def _derive_known_topic_names(self, subject: SubjectName) -> list[str]:
        if subject.endswith(("-key", "-value")):
            return extract_topics_from_subject(subject, SubjectStrategy.TOPIC_NAME)

        if "-" in subject:
            topic_name, suffix = subject.split("-", 1)
            if "." in suffix and suffix.rsplit(".", 1)[-1][:1].isupper():
                return [topic_name]

        if "." in subject and subject.rsplit(".", 1)[-1][:1].isupper():
            return []

        return extract_topics_from_subject(subject, SubjectStrategy.TOPIC_NAME)
