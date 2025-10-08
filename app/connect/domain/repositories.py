"""Connect Domain Repositories - Interfaces"""

from abc import ABC, abstractmethod

from .models_metadata import ConnectorMetadata


class IConnectorMetadataRepository(ABC):
    """커넥터 메타데이터 리포지토리 인터페이스"""

    @abstractmethod
    async def get_metadata(self, connect_id: str, connector_name: str) -> ConnectorMetadata | None:
        """단일 커넥터 메타데이터 조회"""
        ...

    @abstractmethod
    async def get_bulk_metadata(
        self, connect_id: str, connector_names: list[str]
    ) -> dict[str, ConnectorMetadata]:
        """여러 커넥터의 메타데이터를 일괄 조회"""
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def delete_metadata(self, connect_id: str, connector_name: str) -> bool:
        """메타데이터 삭제"""
        ...

    @abstractmethod
    async def list_by_team(self, connect_id: str, team: str) -> list[ConnectorMetadata]:
        """특정 팀의 커넥터 메타데이터 목록 조회"""
        ...
