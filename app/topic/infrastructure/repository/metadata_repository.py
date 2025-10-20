"""Topic Metadata Repository - 토픽 메타데이터 저장/조회/삭제"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.topic.domain.models import TopicName
from app.topic.infrastructure.models import TopicMetadataModel

logger = logging.getLogger(__name__)


class MetadataRepository:
    """Topic Metadata 저장/조회/삭제 리포지토리 (Session Factory 패턴)"""

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        """테스트에서 AsyncMock이 반환한 awaitable을 안전하게 처리"""
        return await value if inspect.isawaitable(value) else value

    async def get_topic_metadata(self, name: TopicName) -> dict[str, Any] | None:
        """토픽 메타데이터 조회"""
        async with self.session_factory() as session:
            try:
                stmt = select(TopicMetadataModel).where(TopicMetadataModel.topic_name == name)
                result = await session.execute(stmt)
                metadata_model = await self._maybe_await(result.scalar_one_or_none())

                if metadata_model is None:
                    logger.debug(f"No metadata found for topic: {name}")
                    return None

                metadata_dict = {
                    "owners": metadata_model.owners or [],
                    "doc": metadata_model.doc,
                    "tags": metadata_model.tags or [],
                    "environment": metadata_model.environment,
                    "slo": metadata_model.slo,
                    "sla": metadata_model.sla,
                    "config": metadata_model.config or {},
                    "created_by": metadata_model.created_by,
                    "updated_by": metadata_model.updated_by,
                }

                logger.debug(
                    f"Retrieved metadata for {name}: owners={metadata_dict['owners']}, "
                    f"doc={metadata_dict['doc']}, env={metadata_dict['environment']}"
                )

                return metadata_dict

            except Exception as e:
                logger.error(f"Failed to get topic metadata {name}: {e}", exc_info=True)
                raise

    async def save_topic_metadata(self, name: TopicName, metadata: dict[str, Any]) -> None:
        """토픽 메타데이터 저장"""
        async with self.session_factory() as session:
            try:
                # 기존 메타데이터 조회
                stmt = select(TopicMetadataModel).where(TopicMetadataModel.topic_name == name)
                result = await session.execute(stmt)
                existing = await self._maybe_await(result.scalar_one_or_none())

                logger.info(
                    f"Saving metadata for {name}: owners={metadata.get('owners')}, "
                    f"doc={metadata.get('doc')}, tags={metadata.get('tags')}, env={metadata.get('environment')}"
                )

                if existing:
                    # 업데이트 후 merge 적용
                    existing.owners = metadata.get("owners", [])
                    existing.doc = metadata.get("doc")
                    existing.tags = metadata.get("tags", [])
                    existing.environment = metadata.get("environment")
                    existing.slo = metadata.get("slo")
                    existing.sla = metadata.get("sla")
                    existing.config = metadata.get("config", {})
                    existing.updated_by = metadata.get("updated_by", "system")
                    session.add(existing)
                    logger.info(f"Updating existing metadata for {name}")
                else:
                    # 새로 생성
                    metadata_model = TopicMetadataModel(
                        topic_name=name,
                        owners=metadata.get("owners", []),
                        doc=metadata.get("doc"),
                        tags=metadata.get("tags", []),
                        environment=metadata.get("environment"),
                        slo=metadata.get("slo"),
                        sla=metadata.get("sla"),
                        config=metadata.get("config", {}),
                        created_by=metadata.get("created_by", "system"),
                        updated_by=metadata.get("updated_by", "system"),
                    )
                    session.add(metadata_model)
                    logger.info(f"Creating new metadata for {name}")

                await session.flush()
                logger.info(f"Topic metadata saved and flushed: {name}")

            except Exception as e:
                logger.error(f"Failed to save topic metadata {name}: {e}", exc_info=True)
                raise

    async def delete_topic_metadata(self, name: TopicName) -> None:
        """토픽 메타데이터 삭제"""
        async with self.session_factory() as session:
            try:
                stmt = select(TopicMetadataModel).where(TopicMetadataModel.topic_name == name)
                result = await session.execute(stmt)
                metadata_model = await self._maybe_await(result.scalar_one_or_none())

                if metadata_model:
                    await session.delete(metadata_model)
                    await session.flush()
                    logger.info(f"Topic metadata deleted: {name}")
                else:
                    logger.info(f"No metadata found to delete for topic: {name}")

            except Exception as e:
                logger.error(f"Failed to delete topic metadata {name}: {e}")
                raise
