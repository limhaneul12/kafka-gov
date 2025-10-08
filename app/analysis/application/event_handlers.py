"""Analysis Event Handlers - Schema/Topic 이벤트 구독"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...schema.infrastructure.models import SchemaMetadataModel
from ...shared.domain.events import SchemaRegisteredEvent, TopicCreatedEvent
from ...shared.roles import UserRole
from ..domain.services import TopicSchemaLinker

logger = logging.getLogger(__name__)


class SchemaRegisteredHandler:
    """스키마 등록 이벤트 핸들러 (Session Factory 패턴)"""

    def __init__(
        self,
        linker: TopicSchemaLinker,
        session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]],
    ) -> None:
        self.linker = linker
        self.session_factory = session_factory

    async def handle(self, event: SchemaRegisteredEvent) -> None:
        """스키마 등록 시 자동으로 토픽과 연결 및 메타데이터 저장"""
        try:
            logger.info(
                f"Handling SchemaRegisteredEvent: {event.subject} "
                f"(actor={event.actor}, role={event.actor_role})"
            )

            # 1. schema_metadata에 저장
            await self._save_schema_metadata(event)

            # 2. 토픽과 연결

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

    async def _save_schema_metadata(self, event: SchemaRegisteredEvent) -> None:
        """스키마 메타데이터 저장 (Session Factory 패턴)"""
        async with self.session_factory() as session:
            try:
                stmt = select(SchemaMetadataModel).where(
                    SchemaMetadataModel.subject == event.subject
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # 이미 존재하면 업데이트
                    existing.updated_by = event.actor
                    existing.description = f"Schema ID: {event.schema_id}, Version: {event.version}, Type: {event.schema_type}"
                    logger.info(f"Updated schema metadata: {event.subject}")
                else:
                    # 새로 생성
                    metadata = SchemaMetadataModel(
                        subject=event.subject,
                        description=f"Schema ID: {event.schema_id}, Version: {event.version}, Type: {event.schema_type}, Compatibility: {event.compatibility_mode}",
                        created_by=event.actor,
                        updated_by=event.actor,
                    )
                    session.add(metadata)
                    logger.info(f"Created schema metadata: {event.subject}")

                await session.flush()

            except Exception as e:
                logger.error(
                    f"Failed to save schema metadata for {event.subject}: {e}", exc_info=True
                )
                # 메타데이터 저장 실패해도 계속 진행

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
