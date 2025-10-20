"""Kafka Cluster Use Cases"""

from __future__ import annotations

import logging
from datetime import datetime

from app.cluster.domain.models import (
    ConnectionTestResult,
    KafkaCluster,
    SaslMechanism,
    SecurityProtocol,
)
from app.cluster.domain.repositories import IKafkaClusterRepository
from app.cluster.domain.services import IConnectionManager
from app.shared.security import get_encryption_service

logger = logging.getLogger(__name__)


class CreateKafkaClusterUseCase:
    """Kafka 클러스터 생성 Use Case"""

    def __init__(
        self,
        cluster_repo: IKafkaClusterRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.cluster_repo = cluster_repo
        self.connection_manager = connection_manager

    async def execute(
        self,
        cluster_id: str,
        name: str,
        bootstrap_servers: str,
        description: str | None = None,
        security_protocol: str = "PLAINTEXT",
        sasl_mechanism: str | None = None,
        sasl_username: str | None = None,
        sasl_password: str | None = None,
        ssl_ca_location: str | None = None,
        ssl_cert_location: str | None = None,
        ssl_key_location: str | None = None,
        request_timeout_ms: int = 60000,
        socket_timeout_ms: int = 60000,
    ) -> KafkaCluster:
        """클러스터 생성"""
        encryption_service = get_encryption_service()
        encrypted_password = encryption_service.encrypt(sasl_password) if sasl_password else None

        new_cluster = KafkaCluster(
            cluster_id=cluster_id,
            name=name,
            bootstrap_servers=bootstrap_servers,
            description=description,
            security_protocol=SecurityProtocol(security_protocol),
            sasl_mechanism=SaslMechanism(sasl_mechanism) if sasl_mechanism else None,
            sasl_username=sasl_username,
            sasl_password=encrypted_password,
            ssl_ca_location=ssl_ca_location,
            ssl_cert_location=ssl_cert_location,
            ssl_key_location=ssl_key_location,
            socket_timeout_ms=socket_timeout_ms,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        created_cluster = await self.cluster_repo.create(new_cluster)
        logger.info(f"Kafka cluster created: {cluster_id}")
        return created_cluster


class ListKafkaClustersUseCase:
    """Kafka 클러스터 목록 조회 Use Case"""

    def __init__(self, cluster_repo: IKafkaClusterRepository) -> None:
        self.cluster_repo = cluster_repo

    async def execute(self, active_only: bool = True) -> list[KafkaCluster]:
        """클러스터 목록 조회"""
        return await self.cluster_repo.list_all(active_only=active_only)


class GetKafkaClusterUseCase:
    """Kafka 클러스터 단일 조회 Use Case"""

    def __init__(self, cluster_repo: IKafkaClusterRepository) -> None:
        self.cluster_repo = cluster_repo

    async def execute(self, cluster_id: str) -> KafkaCluster:
        """클러스터 조회"""
        cluster = await self.cluster_repo.get_by_id(cluster_id)
        if not cluster:
            raise ValueError(f"Kafka cluster not found: {cluster_id}")
        return cluster


class UpdateKafkaClusterUseCase:
    """Kafka 클러스터 수정 Use Case"""

    def __init__(
        self,
        cluster_repo: IKafkaClusterRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.cluster_repo = cluster_repo
        self.connection_manager = connection_manager

    async def execute(
        self,
        cluster_id: str,
        name: str,
        bootstrap_servers: str,
        description: str | None = None,
        security_protocol: str = "PLAINTEXT",
        sasl_mechanism: str | None = None,
        sasl_username: str | None = None,
        sasl_password: str | None = None,
        ssl_ca_location: str | None = None,
        ssl_cert_location: str | None = None,
        ssl_key_location: str | None = None,
        request_timeout_ms: int = 60000,
        socket_timeout_ms: int = 60000,
        is_active: bool = True,
    ) -> KafkaCluster:
        """클러스터 수정"""
        existing = await self.cluster_repo.get_by_id(cluster_id)
        if not existing:
            raise ValueError(f"Kafka cluster not found: {cluster_id}")

        encryption_service = get_encryption_service()
        encrypted_password = encryption_service.encrypt(sasl_password) if sasl_password else None

        updated_cluster = KafkaCluster(
            cluster_id=cluster_id,
            name=name,
            bootstrap_servers=bootstrap_servers,
            description=description,
            security_protocol=SecurityProtocol(security_protocol),
            sasl_mechanism=SaslMechanism(sasl_mechanism) if sasl_mechanism else None,
            sasl_username=sasl_username,
            sasl_password=encrypted_password,
            ssl_ca_location=ssl_ca_location,
            ssl_cert_location=ssl_cert_location,
            ssl_key_location=ssl_key_location,
            request_timeout_ms=request_timeout_ms,
            socket_timeout_ms=socket_timeout_ms,
            is_active=is_active,
            created_at=existing.created_at,
            updated_at=datetime.now(),
        )

        result = await self.cluster_repo.update(updated_cluster)
        self.connection_manager.invalidate_cache("kafka", cluster_id)
        logger.info(f"Kafka cluster updated: {cluster_id}")
        return result


class DeleteKafkaClusterUseCase:
    """Kafka 클러스터 삭제 Use Case"""

    def __init__(
        self,
        cluster_repo: IKafkaClusterRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.cluster_repo = cluster_repo
        self.connection_manager = connection_manager

    async def execute(self, cluster_id: str) -> bool:
        """클러스터 삭제 (소프트 삭제)"""
        success = await self.cluster_repo.delete(cluster_id)
        if success:
            self.connection_manager.invalidate_cache("kafka", cluster_id)
            logger.info(f"Kafka cluster deleted: {cluster_id}")
        return success


class TestKafkaConnectionUseCase:
    """Kafka 연결 테스트 Use Case"""

    def __init__(self, connection_manager: IConnectionManager) -> None:
        self.connection_manager = connection_manager

    async def execute(self, cluster_id: str) -> ConnectionTestResult:
        """Kafka 연결 테스트"""
        return await self.connection_manager.test_kafka_connection(cluster_id)
