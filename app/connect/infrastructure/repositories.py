"""Connect Infrastructure Repositories"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connect.domain.models_metadata import ConnectorMetadata
from app.connect.domain.repositories import IConnectorMetadataRepository

from .models import ConnectorMetadataModel

logger = logging.getLogger(__name__)

SessionFactory = Callable[..., AbstractAsyncContextManager[AsyncSession]]


class MySQLConnectorMetadataRepository(IConnectorMetadataRepository):
    """MySQL 기반 커넥터 메타데이터 리포지토리"""

    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    async def get_metadata(self, connect_id: str, connector_name: str) -> ConnectorMetadata | None:
        """단일 커넥터 메타데이터 조회"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ConnectorMetadataModel).where(
                    ConnectorMetadataModel.connect_id == connect_id,
                    ConnectorMetadataModel.connector_name == connector_name,
                )
            )
            model = result.scalar_one_or_none()
            return self._model_to_domain(model) if model else None

    async def get_bulk_metadata(
        self, connect_id: str, connector_names: list[str]
    ) -> dict[str, ConnectorMetadata]:
        """여러 커넥터의 메타데이터를 일괄 조회

        Returns:
            connector_name → ConnectorMetadata 맵
        """
        if not connector_names:
            return {}

        async with self.session_factory() as session:
            result = await session.execute(
                select(ConnectorMetadataModel).where(
                    ConnectorMetadataModel.connect_id == connect_id,
                    ConnectorMetadataModel.connector_name.in_(connector_names),
                )
            )
            models = result.scalars().all()

            return {model.connector_name: self._model_to_domain(model) for model in models}

    async def save_metadata(
        self,
        connect_id: str,
        connector_name: str,
        team: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
        owner: str | None = None,
    ) -> ConnectorMetadata:
        """메타데이터 저장 (생성 또는 업데이트)"""
        async with self.session_factory() as session:
            # 기존 레코드 확인
            result = await session.execute(
                select(ConnectorMetadataModel).where(
                    ConnectorMetadataModel.connect_id == connect_id,
                    ConnectorMetadataModel.connector_name == connector_name,
                )
            )
            model = result.scalar_one_or_none()

            if model:
                # 업데이트
                if team is not None:
                    model.team = team
                if tags is not None:
                    model.tags = {"tags": tags}  # JSON 형식으로 저장
                if description is not None:
                    model.description = description
                if owner is not None:
                    model.owner = owner

                logger.info(f"Connector metadata updated: {connector_name}")
            else:
                # 생성
                model = ConnectorMetadataModel(
                    id=str(uuid4()),
                    connect_id=connect_id,
                    connector_name=connector_name,
                    team=team,
                    tags={"tags": tags or []},
                    description=description,
                    owner=owner,
                )
                session.add(model)
                logger.info(f"Connector metadata created: {connector_name}")

            await session.commit()
            await session.refresh(model)

            return self._model_to_domain(model)

    async def delete_metadata(self, connect_id: str, connector_name: str) -> bool:
        """메타데이터 삭제

        Returns:
            삭제 성공 여부
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(ConnectorMetadataModel).where(
                    ConnectorMetadataModel.connect_id == connect_id,
                    ConnectorMetadataModel.connector_name == connector_name,
                )
            )
            model = result.scalar_one_or_none()

            if not model:
                return False

            await session.delete(model)
            await session.commit()

            logger.info(f"Connector metadata deleted: {connector_name}")
            return True

    async def list_by_team(self, connect_id: str, team: str) -> list[ConnectorMetadata]:
        """특정 팀의 커넥터 메타데이터 목록 조회"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ConnectorMetadataModel).where(
                    ConnectorMetadataModel.connect_id == connect_id,
                    ConnectorMetadataModel.team == team,
                )
            )
            models = result.scalars().all()
            return [self._model_to_domain(model) for model in models]

    @staticmethod
    def _model_to_domain(model: ConnectorMetadataModel) -> ConnectorMetadata:
        """SQLAlchemy 모델 → 도메인 모델 변환"""
        tags = model.tags.get("tags", []) if model.tags else []

        return ConnectorMetadata(
            id=model.id,
            connect_id=model.connect_id,
            connector_name=model.connector_name,
            team=model.team,
            tags=tags,
            description=model.description,
            owner=model.owner,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
