"""Kafka Connect Use Cases"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from app.cluster.domain.models import ConnectionTestResult, KafkaConnect
from app.cluster.domain.repositories import IKafkaConnectRepository
from app.shared.security import get_encryption_service

logger = logging.getLogger(__name__)


class CreateKafkaConnectUseCase:
    """Kafka Connect 생성 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(
        self,
        connect_id: str,
        cluster_id: str,
        name: str,
        url: str,
        description: str | None = None,
        auth_username: str | None = None,
        auth_password: str | None = None,
    ) -> KafkaConnect:
        """Kafka Connect 생성"""
        encryption_service = get_encryption_service()
        encrypted_password = encryption_service.encrypt(auth_password) if auth_password else None

        connect = KafkaConnect(
            connect_id=connect_id,
            cluster_id=cluster_id,
            name=name,
            url=url,
            description=description,
            auth_username=auth_username,
            auth_password=encrypted_password,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        created = await self.connect_repo.create(connect)
        logger.info(f"Kafka Connect created: {connect_id}")
        return created


class ListKafkaConnectsUseCase:
    """Kafka Connect 목록 조회 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, cluster_id: str | None = None) -> list[KafkaConnect]:
        """Connect 목록 조회 (cluster_id로 필터링 가능)"""
        if cluster_id:
            return await self.connect_repo.list_by_cluster(cluster_id)
        return await self.connect_repo.list_all(active_only=True)


class GetKafkaConnectUseCase:
    """Kafka Connect 단일 조회 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str) -> KafkaConnect:
        """Connect 조회"""
        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")
        return connect


class UpdateKafkaConnectUseCase:
    """Kafka Connect 수정 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(
        self,
        connect_id: str,
        name: str,
        url: str,
        description: str | None = None,
        auth_username: str | None = None,
        auth_password: str | None = None,
        is_active: bool = True,
    ) -> KafkaConnect:
        """Kafka Connect 수정"""
        existing = await self.connect_repo.get_by_id(connect_id)
        if not existing:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        encryption_service = get_encryption_service()
        encrypted_password = encryption_service.encrypt(auth_password) if auth_password else None

        updated_connect = KafkaConnect(
            connect_id=connect_id,
            cluster_id=existing.cluster_id,  # cluster_id는 변경 불가
            name=name,
            url=url,
            description=description,
            auth_username=auth_username,
            auth_password=encrypted_password,
            is_active=is_active,
            created_at=existing.created_at,
            updated_at=datetime.now(UTC),
        )

        result = await self.connect_repo.update(updated_connect)
        logger.info(f"Kafka Connect updated: {connect_id}")
        return result


class DeleteKafkaConnectUseCase:
    """Kafka Connect 삭제 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str) -> bool:
        """Kafka Connect 삭제 (소프트 삭제)"""
        success = await self.connect_repo.delete(connect_id)
        if success:
            logger.info(f"Kafka Connect deleted: {connect_id}")
        return success


class TestKafkaConnectConnectionUseCase:
    """Kafka Connect 연결 테스트 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str) -> ConnectionTestResult:
        """Kafka Connect REST API 연결 테스트"""
        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            return ConnectionTestResult(
                success=False,
                message=f"Kafka Connect not found: {connect_id}",
            )

        try:
            import httpx

            start = time.time()

            async with httpx.AsyncClient(timeout=10.0) as client:
                auth = None
                if connect.auth_username and connect.auth_password:
                    auth = (connect.auth_username, connect.auth_password)

                response = await client.get(
                    f"{connect.url}/connectors",
                    auth=auth,
                )
                response.raise_for_status()

                latency = (time.time() - start) * 1000
                connectors = response.json()

                return ConnectionTestResult(
                    success=True,
                    message="Connected successfully",
                    latency_ms=latency,
                    metadata={"connector_count": len(connectors)},
                )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {e!s}",
            )


# ============================================================================
# Kafka Connect Connector Management Use Cases
# ============================================================================


class ListConnectorsUseCase:
    """커넥터 목록 조회 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str) -> list[dict]:
        """커넥터 목록 조회"""
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")
        if not connect.is_active:
            raise ValueError(f"Kafka Connect is inactive: {connect_id}")

        client = KafkaConnectClient(connect)
        return await client.list_connectors()


class GetConnectorDetailsUseCase:
    """커넥터 상세 조회 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> dict:
        """커넥터 상세 조회"""
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        return await client.get_connector(connector_name)


class GetConnectorStatusUseCase:
    """커넥터 상태 조회 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> dict:
        """커넥터 상태 조회"""
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        return await client.get_connector_status(connector_name)


class CreateConnectorUseCase:
    """커넥터 생성 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, config: dict) -> dict:
        """커넥터 생성"""
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")
        if not connect.is_active:
            raise ValueError(f"Kafka Connect is inactive: {connect_id}")

        client = KafkaConnectClient(connect)
        return await client.create_connector(config)


class DeleteConnectorUseCase:
    """커넥터 삭제 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> None:
        """커넥터 삭제"""
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        await client.delete_connector(connector_name)


class PauseConnectorUseCase:
    """커넥터 일시정지 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> None:
        """커넥터 일시정지"""
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        await client.pause_connector(connector_name)


class ResumeConnectorUseCase:
    """커넥터 재개 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> None:
        """커넥터 재개"""
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        await client.resume_connector(connector_name)


class RestartConnectorUseCase:
    """커넥터 재시작 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> None:
        """커넥터 재시작"""
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        await client.restart_connector(connector_name)
