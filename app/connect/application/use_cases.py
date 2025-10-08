"""Kafka Connect Use Cases"""

from __future__ import annotations

from app.cluster.domain.repositories import IKafkaConnectRepository
from app.connect.domain.repositories import IConnectorMetadataRepository
from app.connect.domain.types import ConnectorConfig, ConnectorListResponse, PluginConfig
from app.connect.infrastructure.client import KafkaConnectRestClient

# ============================================================================
# Base Use Case (공통 로직 추상화)
# ============================================================================


class BaseConnectorUseCase:
    """Base Use Case - 공통 로직 추출

    모든 Use Case에서 반복되는 패턴:
    1. connect_id로 Connect 조회
    2. 활성화 상태 확인
    3. Client 생성
    """

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def _get_client(self, connect_id: str) -> KafkaConnectRestClient:
        """공통: Connect 조회 및 Client 생성

        모든 Use Case에서 재사용되는 로직을 한 곳에 집중
        """
        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")
        if not connect.is_active:
            raise ValueError(f"Kafka Connect is inactive: {connect_id}")

        return KafkaConnectRestClient(connect)


# ============================================================================
# Connector Management Use Cases
# ============================================================================


class ListConnectorsUseCase(BaseConnectorUseCase):
    """커넥터 목록 조회 Use Case (메타데이터 포함)"""

    def __init__(
        self,
        connect_repo: IKafkaConnectRepository,
        metadata_repo: IConnectorMetadataRepository,
    ) -> None:
        super().__init__(connect_repo)
        self.metadata_repo = metadata_repo

    async def execute(
        self, connect_id: str, expand: list[str] | None = None
    ) -> ConnectorListResponse:
        """커넥터 목록 조회 (메타데이터 포함)"""
        # 1. Client 생성 (Base의 _get_client 재사용)
        client = await self._get_client(connect_id)

        # 2. 커넥터 목록 조회
        connectors = await client.list_connectors(expand=expand)

        # 3. expand가 있으면 메타데이터 병합
        if isinstance(connectors, dict):
            connector_names = list(connectors.keys())
            metadata_map = await self.metadata_repo.get_bulk_metadata(connect_id, connector_names)

            for name, connector_info in connectors.items():
                meta = metadata_map.get(name)
                if meta:
                    connector_info["team"] = meta.team
                    connector_info["tags"] = list(meta.tags) if meta.tags else []
                    connector_info["description"] = meta.description
                    connector_info["owner"] = meta.owner
                else:
                    connector_info["tags"] = []
                    connector_info["owner"] = None

        return connectors


class ConnectorOperations(BaseConnectorUseCase):
    """커넥터 기본 CRUD 작업을 통합한 Use Case

    하나의 클래스로 여러 작업을 제공하여 중복 제거
    """

    async def get(self, connect_id: str, connector_name: str) -> dict:
        """커넥터 조회"""
        client = await self._get_client(connect_id)
        return await client.get_connector(connector_name)  # type: ignore

    async def get_config(self, connect_id: str, connector_name: str) -> dict:
        """커넥터 설정 조회"""
        client = await self._get_client(connect_id)
        return await client.get_connector_config(connector_name)  # type: ignore

    async def get_status(self, connect_id: str, connector_name: str) -> dict:
        """커넥터 상태 조회"""
        client = await self._get_client(connect_id)
        return await client.get_connector_status(connector_name)  # type: ignore

    async def create(self, connect_id: str, config: ConnectorConfig) -> dict:
        """커넥터 생성"""
        client = await self._get_client(connect_id)
        return await client.create_connector(config)  # type: ignore

    async def update_config(
        self, connect_id: str, connector_name: str, config: ConnectorConfig
    ) -> dict:
        """커넥터 설정 업데이트"""
        client = await self._get_client(connect_id)
        return await client.update_connector_config(connector_name, config)  # type: ignore

    async def delete(self, connect_id: str, connector_name: str) -> None:
        """커넥터 삭제"""
        client = await self._get_client(connect_id)
        await client.delete_connector(connector_name)


# ============================================================================
# Connector State Control Use Cases
# ============================================================================


class ConnectorStateControl(BaseConnectorUseCase):
    """커넥터 상태 제어 Use Case (재시작, 일시정지, 재개)"""

    async def restart(self, connect_id: str, connector_name: str) -> None:
        """커넥터 재시작 (태스크는 재시작 안 됨)"""
        client = await self._get_client(connect_id)
        await client.restart_connector(connector_name)

    async def pause(self, connect_id: str, connector_name: str) -> None:
        """커넥터 일시정지"""
        client = await self._get_client(connect_id)
        await client.pause_connector(connector_name)

    async def resume(self, connect_id: str, connector_name: str) -> None:
        """커넥터 재개"""
        client = await self._get_client(connect_id)
        await client.resume_connector(connector_name)


# ============================================================================
# Task Operations Use Cases


class TaskOperations(BaseConnectorUseCase):
    """태스크 관련 작업을 통합한 Use Case"""

    async def get_tasks(self, connect_id: str, connector_name: str) -> list[dict]:
        """태스크 목록 조회"""
        client = await self._get_client(connect_id)
        return await client.get_connector_tasks(connector_name)  # type: ignore

    async def get_status(self, connect_id: str, connector_name: str, task_id: int) -> dict:
        """태스크 상태 조회"""
        client = await self._get_client(connect_id)
        return await client.get_task_status(connector_name, task_id)  # type: ignore

    async def restart(self, connect_id: str, connector_name: str, task_id: int) -> None:
        """태스크 재시작 (Connector RUNNING + Task FAILED 시 사용)"""
        client = await self._get_client(connect_id)
        await client.restart_task(connector_name, task_id)


class TopicOperations(BaseConnectorUseCase):
    """커넥터 토픽 관련 작업을 통합한 Use Case"""

    async def get_topics(self, connect_id: str, connector_name: str) -> dict:
        """커넥터가 사용하는 토픽 조회"""
        client = await self._get_client(connect_id)
        return await client.get_connector_topics(connector_name)  # type: ignore

    async def reset_topics(self, connect_id: str, connector_name: str) -> None:
        """커넥터 토픽 리셋"""
        client = await self._get_client(connect_id)
        await client.reset_connector_topics(connector_name)


# ============================================================================
# Plugin Operations Use Cases
# ============================================================================


class PluginOperations(BaseConnectorUseCase):
    """플러그인 관련 작업을 통합한 Use Case"""

    async def list_plugins(self, connect_id: str) -> list[dict]:
        """플러그인 목록 조회"""
        client = await self._get_client(connect_id)
        return await client.list_connector_plugins()  # type: ignore

    async def validate_config(
        self, connect_id: str, plugin_class: str, config: PluginConfig
    ) -> dict:
        """커넥터 설정 검증"""
        client = await self._get_client(connect_id)
        return await client.validate_connector_config(plugin_class, config)  # type: ignore
