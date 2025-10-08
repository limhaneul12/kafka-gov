"""Connector Metadata Use Cases"""

from __future__ import annotations

from app.connect.domain.models_metadata import ConnectorMetadata
from app.connect.domain.repositories import IConnectorMetadataRepository


class GetConnectorMetadataUseCase:
    """커넥터 메타데이터 조회 Use Case"""

    def __init__(self, metadata_repo: IConnectorMetadataRepository) -> None:
        self.metadata_repo = metadata_repo

    async def execute(self, connect_id: str, connector_name: str) -> ConnectorMetadata | None:
        """커넥터 메타데이터 조회"""
        return await self.metadata_repo.get_metadata(connect_id, connector_name)


class UpdateConnectorMetadataUseCase:
    """커넥터 메타데이터 업데이트 Use Case"""

    def __init__(self, metadata_repo: IConnectorMetadataRepository) -> None:
        self.metadata_repo = metadata_repo

    async def execute(
        self,
        connect_id: str,
        connector_name: str,
        team: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
        owner: str | None = None,
    ) -> ConnectorMetadata:
        """커넥터 메타데이터 업데이트 (생성 또는 수정)"""
        return await self.metadata_repo.save_metadata(
            connect_id=connect_id,
            connector_name=connector_name,
            team=team,
            tags=tags,
            description=description,
            owner=owner,
        )


class DeleteConnectorMetadataUseCase:
    """커넥터 메타데이터 삭제 Use Case"""

    def __init__(self, metadata_repo: IConnectorMetadataRepository) -> None:
        self.metadata_repo = metadata_repo

    async def execute(self, connect_id: str, connector_name: str) -> bool:
        """커넥터 메타데이터 삭제"""
        return await self.metadata_repo.delete_metadata(connect_id, connector_name)


class ListConnectorsByTeamUseCase:
    """팀별 커넥터 메타데이터 목록 조회 Use Case"""

    def __init__(self, metadata_repo: IConnectorMetadataRepository) -> None:
        self.metadata_repo = metadata_repo

    async def execute(self, connect_id: str, team: str) -> list[ConnectorMetadata]:
        """특정 팀의 커넥터 메타데이터 목록 조회"""
        return await self.metadata_repo.list_by_team(connect_id, team)
