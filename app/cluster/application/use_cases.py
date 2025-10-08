"""Cluster Application Use Cases - 연결 관리 Use Cases"""

from __future__ import annotations

import logging
from datetime import datetime

from app.cluster.domain.models import (
    ConnectionTestResult,
    KafkaCluster,
    KafkaConnect,
    ObjectStorage,
    SaslMechanism,
    SchemaRegistry,
    SecurityProtocol,
)
from app.cluster.domain.repositories import (
    IKafkaClusterRepository,
    IKafkaConnectRepository,
    IObjectStorageRepository,
    ISchemaRegistryRepository,
)
from app.cluster.domain.services import IConnectionManager
from app.shared.security import get_encryption_service

logger = logging.getLogger(__name__)


# ============================================================================
# Kafka Cluster Use Cases
# ============================================================================


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
        """클러스터 생성

        Args:
            cluster_id: 클러스터 ID (고유)
            name: 클러스터 이름
            bootstrap_servers: 브로커 주소 (예: "broker1:9092,broker2:9092")
            description: 설명 (선택)
            security_protocol: 보안 프로토콜 (PLAINTEXT/SSL/SASL_PLAINTEXT/SASL_SSL)
            sasl_mechanism: SASL 메커니즘 (선택)
            sasl_username: SASL 사용자명 (선택)
            sasl_password: SASL 비밀번호 (선택, 암호화 권장)
            ssl_ca_location: SSL CA 인증서 경로 (선택)
            ssl_cert_location: SSL 인증서 경로 (선택)
            ssl_key_location: SSL 키 경로 (선택)
            socket_timeout_ms: 소켓 타임아웃 (ms)

        Returns:
            생성된 KafkaCluster
        """
        # 비밀번호 암호화
        encryption_service = get_encryption_service()
        encrypted_password = encryption_service.encrypt(sasl_password) if sasl_password else None

        # 새 클러스터 생성
        new_cluster = KafkaCluster(
            cluster_id=cluster_id,
            name=name,
            bootstrap_servers=bootstrap_servers,
            description=description,
            security_protocol=SecurityProtocol(security_protocol),
            sasl_mechanism=SaslMechanism(sasl_mechanism) if sasl_mechanism else None,
            sasl_username=sasl_username,
            sasl_password=encrypted_password,  # 암호화된 비밀번호 저장
            ssl_ca_location=ssl_ca_location,
            ssl_cert_location=ssl_cert_location,
            ssl_key_location=ssl_key_location,
            socket_timeout_ms=socket_timeout_ms,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        # Repository를 통해 저장
        created_cluster = await self.cluster_repo.create(new_cluster)

        logger.info(f"Kafka cluster created: {cluster_id}")
        return created_cluster


class ListKafkaClustersUseCase:
    """Kafka 클러스터 목록 조회 Use Case"""

    def __init__(self, cluster_repo: IKafkaClusterRepository) -> None:
        self.cluster_repo = cluster_repo

    async def execute(self, active_only: bool = True) -> list[KafkaCluster]:
        """클러스터 목록 조회

        Args:
            active_only: 활성화된 클러스터만 조회 여부

        Returns:
            클러스터 목록
        """
        clusters = await self.cluster_repo.list_all(active_only=active_only)
        return clusters


class GetKafkaClusterUseCase:
    """Kafka 클러스터 단일 조회 Use Case"""

    def __init__(self, cluster_repo: IKafkaClusterRepository) -> None:
        self.cluster_repo = cluster_repo

    async def execute(self, cluster_id: str) -> KafkaCluster:
        """클러스터 조회

        Args:
            cluster_id: 클러스터 ID

        Returns:
            KafkaCluster

        Raises:
            ValueError: 클러스터가 존재하지 않을 때
        """
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
        """클러스터 수정

        Args:
            cluster_id: 클러스터 ID
            (나머지 파라미터는 CreateKafkaClusterUseCase와 동일)

        Returns:
            수정된 KafkaCluster
        """
        # 기존 클러스터 조회
        existing = await self.cluster_repo.get_by_id(cluster_id)
        if not existing:
            raise ValueError(f"Kafka cluster not found: {cluster_id}")

        # 비밀번호 암호화
        encryption_service = get_encryption_service()
        encrypted_password = encryption_service.encrypt(sasl_password) if sasl_password else None

        # Domain 모델 생성 (업데이트된 값)
        updated_cluster = KafkaCluster(
            cluster_id=cluster_id,
            name=name,
            bootstrap_servers=bootstrap_servers,
            description=description,
            security_protocol=SecurityProtocol(security_protocol),
            sasl_mechanism=SaslMechanism(sasl_mechanism) if sasl_mechanism else None,
            sasl_username=sasl_username,
            sasl_password=encrypted_password,  # 암호화된 비밀번호 저장
            ssl_ca_location=ssl_ca_location,
            ssl_cert_location=ssl_cert_location,
            ssl_key_location=ssl_key_location,
            request_timeout_ms=request_timeout_ms,
            socket_timeout_ms=socket_timeout_ms,
            is_active=is_active,
            created_at=existing.created_at,
            updated_at=datetime.now(),
        )

        # Repository를 통해 수정
        result = await self.cluster_repo.update(updated_cluster)

        # ConnectionManager 캐시 무효화 (설정 변경 반영)
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
        """클러스터 삭제 (소프트 삭제)

        Args:
            cluster_id: 클러스터 ID

        Returns:
            삭제 성공 여부
        """
        success = await self.cluster_repo.delete(cluster_id)

        if success:
            # ConnectionManager 캐시 무효화
            self.connection_manager.invalidate_cache("kafka", cluster_id)
            logger.info(f"Kafka cluster deleted: {cluster_id}")

        return success


class TestKafkaConnectionUseCase:
    """Kafka 연결 테스트 Use Case"""

    def __init__(self, connection_manager: IConnectionManager) -> None:
        self.connection_manager = connection_manager

    async def execute(self, cluster_id: str) -> ConnectionTestResult:
        """Kafka 연결 테스트

        Args:
            cluster_id: 클러스터 ID

        Returns:
            연결 테스트 결과
        """
        return await self.connection_manager.test_kafka_connection(cluster_id)


# ============================================================================
# Schema Registry Use Cases (패턴 동일 - 간략히 작성)
# ============================================================================


class CreateSchemaRegistryUseCase:
    """Schema Registry 생성 Use Case"""

    def __init__(
        self,
        registry_repo: ISchemaRegistryRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.registry_repo = registry_repo
        self.connection_manager = connection_manager

    async def execute(
        self,
        registry_id: str,
        name: str,
        url: str,
        description: str | None = None,
        auth_username: str | None = None,
        auth_password: str | None = None,
        ssl_ca_location: str | None = None,
        ssl_cert_location: str | None = None,
        ssl_key_location: str | None = None,
        timeout: int = 30,
    ) -> SchemaRegistry:
        """레지스트리 생성"""
        # 비밀번호 암호화
        encryption_service = get_encryption_service()
        encrypted_password = encryption_service.encrypt(auth_password) if auth_password else None

        registry = SchemaRegistry(
            registry_id=registry_id,
            name=name,
            url=url,
            description=description,
            auth_username=auth_username,
            auth_password=encrypted_password,  # 암호화된 비밀번호 저장
            ssl_ca_location=ssl_ca_location,
            ssl_cert_location=ssl_cert_location,
            ssl_key_location=ssl_key_location,
            timeout=timeout,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        created_registry = await self.registry_repo.create(registry)
        logger.info(f"Schema Registry created: {registry_id}")
        return created_registry


class ListSchemaRegistriesUseCase:
    """Schema Registry 목록 조회 Use Case"""

    def __init__(self, registry_repo: ISchemaRegistryRepository) -> None:
        self.registry_repo = registry_repo

    async def execute(self, active_only: bool = True) -> list[SchemaRegistry]:
        """레지스트리 목록 조회"""
        return await self.registry_repo.list_all(active_only=active_only)


class DeleteSchemaRegistryUseCase:
    """Schema Registry 삭제 Use Case"""

    def __init__(
        self,
        registry_repo: ISchemaRegistryRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.registry_repo = registry_repo
        self.connection_manager = connection_manager

    async def execute(self, registry_id: str) -> bool:
        """레지스트리 삭제 (소프트 삭제)"""
        success = await self.registry_repo.delete(registry_id)
        if success:
            self.connection_manager.invalidate_cache("schema_registry", registry_id)
        return success


class TestSchemaRegistryConnectionUseCase:
    """Schema Registry 연결 테스트 Use Case"""

    def __init__(self, connection_manager: IConnectionManager) -> None:
        self.connection_manager = connection_manager

    async def execute(self, registry_id: str) -> ConnectionTestResult:
        """Schema Registry 연결 테스트"""
        return await self.connection_manager.test_schema_registry_connection(registry_id)


# ============================================================================
# Object Storage Use Cases (패턴 동일 - 간략히 작성)
# ============================================================================


class CreateObjectStorageUseCase:
    """Object Storage 생성 Use Case"""

    def __init__(
        self,
        storage_repo: IObjectStorageRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.storage_repo = storage_repo
        self.connection_manager = connection_manager

    async def execute(
        self,
        storage_id: str,
        name: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        description: str | None = None,
        region: str = "us-east-1",
        use_ssl: bool = False,
    ) -> ObjectStorage:
        """스토리지 생성"""
        # Secret Key 암호화
        encryption_service = get_encryption_service()
        encrypted_secret = encryption_service.encrypt(secret_key) if secret_key else None

        storage = ObjectStorage(
            storage_id=storage_id,
            name=name,
            endpoint_url=endpoint_url,
            description=description,
            access_key=access_key,
            secret_key=encrypted_secret,  # 암호화된 Secret Key 저장
            bucket_name=bucket_name,
            region=region,
            use_ssl=use_ssl,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        created_storage = await self.storage_repo.create(storage)
        logger.info(f"Object Storage created: {storage_id}")
        return created_storage


class ListObjectStoragesUseCase:
    """Object Storage 목록 조회 Use Case"""

    def __init__(self, storage_repo: IObjectStorageRepository) -> None:
        self.storage_repo = storage_repo

    async def execute(self, active_only: bool = True) -> list[ObjectStorage]:
        """스토리지 목록 조회"""
        return await self.storage_repo.list_all(active_only=active_only)


class DeleteObjectStorageUseCase:
    """Object Storage 삭제 Use Case"""

    def __init__(
        self,
        storage_repo: IObjectStorageRepository,
        connection_manager: IConnectionManager,
    ) -> None:
        self.storage_repo = storage_repo
        self.connection_manager = connection_manager

    async def execute(self, storage_id: str) -> bool:
        """스토리지 삭제 (소프트 삭제)"""
        success = await self.storage_repo.delete(storage_id)
        if success:
            self.connection_manager.invalidate_cache("storage", storage_id)
        return success


class TestObjectStorageConnectionUseCase:
    """Object Storage 연결 테스트 Use Case"""

    def __init__(self, connection_manager: IConnectionManager) -> None:
        self.connection_manager = connection_manager

    async def execute(self, storage_id: str) -> ConnectionTestResult:
        """Object Storage 연결 테스트"""
        return await self.connection_manager.test_storage_connection(storage_id)


# ============================================================================
# Kafka Connect Use Cases
# ============================================================================


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
        from datetime import UTC, datetime

        connect = KafkaConnect(
            connect_id=connect_id,
            cluster_id=cluster_id,
            name=name,
            url=url,
            description=description,
            auth_username=auth_username,
            auth_password=auth_password,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        return await self.connect_repo.create(connect)


class ListKafkaConnectsUseCase:
    """Kafka Connect 목록 조회 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, cluster_id: str | None = None) -> list[KafkaConnect]:
        """Connect 목록 조회 (cluster_id로 필터링 가능)"""
        if cluster_id:
            return await self.connect_repo.list_by_cluster(cluster_id)

        # 전체 목록 조회
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


class DeleteKafkaConnectUseCase:
    """Kafka Connect 삭제 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str) -> bool:
        """Kafka Connect 삭제 (소프트 삭제)"""
        return await self.connect_repo.delete(connect_id)


class TestKafkaConnectConnectionUseCase:
    """Kafka Connect 연결 테스트 Use Case"""

    def __init__(self, connect_repo: IKafkaConnectRepository) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str) -> ConnectionTestResult:
        """Kafka Connect REST API 연결 테스트"""
        import time

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            return ConnectionTestResult(
                success=False,
                message=f"Kafka Connect not found: {connect_id}",
            )

        try:
            import httpx

            start = time.time()

            # Kafka Connect REST API의 기본 엔드포인트 테스트
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

    def __init__(
        self,
        connect_repo: IKafkaConnectRepository,
    ) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str) -> list[dict]:
        """커넥터 목록 조회

        Args:
            connect_id: Connect ID

        Returns:
            커넥터 목록
        """
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        # Connect 정보 조회
        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")
        if not connect.is_active:
            raise ValueError(f"Kafka Connect is inactive: {connect_id}")

        # REST API 호출
        client = KafkaConnectClient(connect)
        return await client.list_connectors()


class GetConnectorDetailsUseCase:
    """커넥터 상세 조회 Use Case"""

    def __init__(
        self,
        connect_repo: IKafkaConnectRepository,
    ) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> dict:
        """커넥터 상세 조회

        Args:
            connect_id: Connect ID
            connector_name: 커넥터 이름

        Returns:
            커넥터 상세 정보
        """
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        return await client.get_connector(connector_name)


class GetConnectorStatusUseCase:
    """커넥터 상태 조회 Use Case"""

    def __init__(
        self,
        connect_repo: IKafkaConnectRepository,
    ) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> dict:
        """커넥터 상태 조회

        Args:
            connect_id: Connect ID
            connector_name: 커넥터 이름

        Returns:
            커넥터 상태
        """
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        return await client.get_connector_status(connector_name)


class CreateConnectorUseCase:
    """커넥터 생성 Use Case"""

    def __init__(
        self,
        connect_repo: IKafkaConnectRepository,
    ) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, config: dict) -> dict:
        """커넥터 생성

        Args:
            connect_id: Connect ID
            config: 커넥터 설정

        Returns:
            생성된 커넥터 정보
        """
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

    def __init__(
        self,
        connect_repo: IKafkaConnectRepository,
    ) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> None:
        """커넥터 삭제

        Args:
            connect_id: Connect ID
            connector_name: 커넥터 이름
        """
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        await client.delete_connector(connector_name)


class PauseConnectorUseCase:
    """커넥터 일시정지 Use Case"""

    def __init__(
        self,
        connect_repo: IKafkaConnectRepository,
    ) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> None:
        """커넥터 일시정지

        Args:
            connect_id: Connect ID
            connector_name: 커넥터 이름
        """
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        await client.pause_connector(connector_name)


class ResumeConnectorUseCase:
    """커넥터 재개 Use Case"""

    def __init__(
        self,
        connect_repo: IKafkaConnectRepository,
    ) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> None:
        """커넥터 재개

        Args:
            connect_id: Connect ID
            connector_name: 커넥터 이름
        """
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        await client.resume_connector(connector_name)


class RestartConnectorUseCase:
    """커넥터 재시작 Use Case"""

    def __init__(
        self,
        connect_repo: IKafkaConnectRepository,
    ) -> None:
        self.connect_repo = connect_repo

    async def execute(self, connect_id: str, connector_name: str) -> None:
        """커넥터 재시작

        Args:
            connect_id: Connect ID
            connector_name: 커넥터 이름
        """
        from app.cluster.infrastructure.connectors import KafkaConnectClient

        connect = await self.connect_repo.get_by_id(connect_id)
        if not connect:
            raise ValueError(f"Kafka Connect not found: {connect_id}")

        client = KafkaConnectClient(connect)
        await client.restart_connector(connector_name)
