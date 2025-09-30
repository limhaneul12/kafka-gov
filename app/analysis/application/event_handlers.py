"""Analysis Event Handlers - Schema/Topic 이벤트 구독"""

from __future__ import annotations

import logging

from ...shared.domain.events import SchemaRegisteredEvent, TopicCreatedEvent
from ...shared.roles import UserRole
from ..domain.services import TopicSchemaLinker

logger = logging.getLogger(__name__)


class SchemaRegisteredHandler:
    """스키마 등록 이벤트 핸들러"""

    def __init__(self, linker: TopicSchemaLinker) -> None:
        self.linker = linker

    async def handle(self, event: SchemaRegisteredEvent) -> None:
        """스키마 등록 시 자동으로 토픽과 연결"""
        try:
            logger.info(
                f"Handling SchemaRegisteredEvent: {event.subject} "
                f"(actor={event.actor}, role={event.actor_role})"
            )

            # 역할 검증 (자동 연결은 모든 역할 허용)
            actor_role = UserRole(event.actor_role)
            if not actor_role.can_read:
                logger.warning(f"Actor {event.actor} has no permission to trigger auto-linking")
                return

            # Subject naming에서 토픽 추출
            topics = self._extract_topics(event.subject, event.subject_strategy)

            if not topics:
                logger.warning(f"No topics inferred from subject: {event.subject}")
                return

            # 스키마 타입 추론 (key/value)
            schema_type = self._infer_schema_type(event.subject)

            # 각 토픽에 스키마 연결
            for topic_name in topics:
                await self.linker.link_schema_to_topic(
                    topic_name=topic_name,
                    schema_subject=event.subject,
                    schema_type=schema_type,
                    environment=event.environment,
                    link_source="auto",
                )
                logger.info(
                    f"Linked schema {event.subject} to topic {topic_name} "
                    f"(triggered by {event.actor})"
                )

        except Exception as e:
            logger.error(f"Failed to handle SchemaRegisteredEvent: {e}", exc_info=True)
            # 이벤트 핸들러 실패해도 원본 작업은 성공 (베스트 에포트)

    def _extract_topics(self, subject: str, strategy: str) -> list[str]:
        """Subject naming에서 토픽 추출"""
        if strategy == "TopicNameStrategy":
            if subject.endswith(("-key", "-value")):
                topic_name = subject.rsplit("-", 1)[0]
                return [topic_name]

        elif strategy == "TopicRecordNameStrategy":
            parts = subject.split("-", 1)
            if len(parts) >= 2:
                return [parts[0]]

        return []

    def _infer_schema_type(self, subject: str) -> str:
        """Subject 이름에서 key/value 추론"""
        if subject.endswith("-key"):
            return "key"
        if subject.endswith("-value"):
            return "value"
        return "value"  # 기본값


class TopicCreatedHandler:
    """토픽 생성 이벤트 핸들러"""

    def __init__(self, linker: TopicSchemaLinker) -> None:
        self.linker = linker

    async def handle(self, event: TopicCreatedEvent) -> None:
        """토픽 생성 시 처리 (현재는 로깅만)"""
        try:
            logger.info(f"Handling TopicCreatedEvent: {event.topic_name}")
            # 향후 확장: 토픽 생성 시 스키마 추천 등

        except Exception as e:
            logger.error(f"Failed to handle TopicCreatedEvent: {e}", exc_info=True)
