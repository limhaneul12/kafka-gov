"""Cluster Domain Services - 동적 연결 관리자"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from confluent_kafka.admin import AdminClient
from confluent_kafka.schema_registry import AsyncSchemaRegistryClient
from kafka import KafkaAdminClient
from minio import Minio

from .models import (
    ConnectionTestResult,
    ObjectStorage,
)
from .repositories import (
    IKafkaClusterRepository,
    IObjectStorageRepository,
    ISchemaRegistryRepository,
)

logger = logging.getLogger(__name__)


class IConnectionManager(ABC):
    """연결 관리자 인터페이스 (다른 모듈에서 주입받아 사용)"""

    @abstractmethod
    async def get_kafka_admin_client(self, cluster_id: str) -> AdminClient:
        """Kafka AdminClient 획득 (동적 생성/캐싱)"""

    @abstractmethod
    async def get_kafka_py_admin_client(self, cluster_id: str) -> KafkaAdminClient:
        """kafka-python KafkaAdminClient 획득 (동적 생성/캐싱)"""

    @abstractmethod
    async def get_schema_registry_client(self, registry_id: str) -> AsyncSchemaRegistryClient:
        """Schema Registry Client 획득 (동적 생성/캐싱)"""

    @abstractmethod
    async def get_minio_client(self, storage_id: str) -> tuple[Minio, str]:
        """MinIO Client 획득 (동적 생성/캐싱)

        Returns:
            (Minio 클라이언트, bucket_name) 튜플
        """
        ...

    @abstractmethod
    async def get_storage_info(self, storage_id: str) -> ObjectStorage:
        """Object Storage 정보 조회

        Returns:
            ObjectStorage 도메인 모델
        """
        ...

    @abstractmethod
    async def test_kafka_connection(self, cluster_id: str) -> ConnectionTestResult:
        """Kafka 연결 테스트"""
        ...

    @abstractmethod
    async def test_schema_registry_connection(self, registry_id: str) -> ConnectionTestResult:
        """Schema Registry 연결 테스트"""
        ...

    @abstractmethod
    async def test_storage_connection(self, storage_id: str) -> ConnectionTestResult:
        """Object Storage 연결 테스트"""
        ...

    @abstractmethod
    def invalidate_cache(self, resource_type: str, resource_id: str) -> None:
        """캐시 무효화 (설정 변경 시 호출)"""
        ...


class ConnectionManager(IConnectionManager):
    """동적 연결 관리자 (핵심 Domain Service)

    책임:
        1. cluster_id/registry_id/storage_id 기반으로 클라이언트 동적 생성
        2. 클라이언트 캐싱 (메모리 효율성)
        3. 연결 상태 확인 및 헬스체크

    사용 방법 (다른 모듈에서):
        ```python
        # Topic Use Case 예시
        class TopicListUseCase:
            def __init__(self, connection_manager: IConnectionManager):
                self.connection_manager = connection_manager

            async def execute(self, cluster_id: str):
                # cluster_id로 AdminClient 동적 획득
                admin_client = await self.connection_manager.get_kafka_admin_client(cluster_id)

                # KafkaTopicAdapter에 전달하여 작업 수행
                adapter = KafkaTopicAdapter(admin_client)
                return await adapter.list_topics()
        ```
    """

    def __init__(
        self,
        kafka_cluster_repo: IKafkaClusterRepository,
        schema_registry_repo: ISchemaRegistryRepository,
        storage_repo: IObjectStorageRepository,
    ) -> None:
        self.kafka_cluster_repo = kafka_cluster_repo
        self.schema_registry_repo = schema_registry_repo
        self.storage_repo = storage_repo

        # 클라이언트 캐시 (resource_id -> client)
        self._kafka_clients: dict[str, AdminClient] = {}
        self._kafka_py_clients: dict[str, KafkaAdminClient] = {}
        self._schema_registry_clients: dict[str, AsyncSchemaRegistryClient] = {}
        self._minio_clients: dict[str, tuple[Minio, str]] = {}  # (client, bucket_name)

        # 캐시 락 (동시 생성 방지) - 이벤트 루프별로 관리
        self._locks: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Lock]] = {}

    async def get_kafka_admin_client(self, cluster_id: str) -> AdminClient:
        """Kafka AdminClient 획득 (동적 생성/캐싱)

        Args:
            cluster_id: 클러스터 ID

        Returns:
            AdminClient 인스턴스

        Raises:
            ValueError: 클러스터가 존재하지 않거나 비활성 상태
        """
        # 캐시 확인
        if cluster_id in self._kafka_clients:
            logger.debug(f"Kafka AdminClient cache hit: {cluster_id}")
            return self._kafka_clients[cluster_id]

        # Lock 획득 (동시 생성 방지)
        lock_key = f"kafka_{cluster_id}"
        lock = self._get_loop_scoped_lock(lock_key)

        async with lock:
            # Double-check (Lock 대기 중에 다른 코루틴이 생성했을 수 있음)
            if cluster_id in self._kafka_clients:
                return self._kafka_clients[cluster_id]

            # DB에서 클러스터 정보 조회
            cluster = await self.kafka_cluster_repo.get_by_id(cluster_id)
            if not cluster:
                raise ValueError(f"Kafka cluster not found: {cluster_id}")
            if not cluster.is_active:
                raise ValueError(f"Kafka cluster is inactive: {cluster_id}")

            # AdminClient 생성
            logger.info(f"Creating new Kafka AdminClient: {cluster_id}")
            config = cluster.to_admin_config()
            admin_client = AdminClient(config)

            # 캐시 저장
            self._kafka_clients[cluster_id] = admin_client

            return admin_client

    async def get_kafka_py_admin_client(self, cluster_id: str) -> KafkaAdminClient:
        """kafka-python KafkaAdminClient 획득 (동적 생성/캐싱)

        Args:
            cluster_id: 클러스터 ID

        Returns:
            KafkaAdminClient 인스턴스 (kafka-python)

        Raises:
            ValueError: 클러스터가 존재하지 않거나 비활성 상태
        """
        # 캐시 확인
        if cluster_id in self._kafka_py_clients:
            logger.debug(f"Kafka (py) AdminClient cache hit: {cluster_id}")
            return self._kafka_py_clients[cluster_id]

        # Lock 획득 (동시 생성 방지)
        lock_key = f"kafka_py_{cluster_id}"
        lock = self._get_loop_scoped_lock(lock_key)

        async with lock:
            # Double-check
            if cluster_id in self._kafka_py_clients:
                return self._kafka_py_clients[cluster_id]

            # DB에서 클러스터 정보 조회
            cluster = await self.kafka_cluster_repo.get_by_id(cluster_id)
            if not cluster:
                raise ValueError(f"Kafka cluster not found: {cluster_id}")
            if not cluster.is_active:
                raise ValueError(f"Kafka cluster is inactive: {cluster_id}")

            # kafka-python AdminClient 설정 매핑
            config: dict[str, str | int | bool] = {
                "bootstrap_servers": cluster.bootstrap_servers,
                "security_protocol": cluster.security_protocol.value,
                "request_timeout_ms": cluster.request_timeout_ms,
            }

            # SASL 설정 (kafka-python 필드명과 매핑)
            if cluster.sasl_mechanism:
                config["sasl_mechanism"] = cluster.sasl_mechanism.value
            if cluster.sasl_username:
                config["sasl_plain_username"] = cluster.sasl_username
            if cluster.sasl_password:
                config["sasl_plain_password"] = cluster.sasl_password

            # SSL 설정
            if cluster.ssl_ca_location:
                config["ssl_cafile"] = cluster.ssl_ca_location
            if cluster.ssl_cert_location:
                config["ssl_certfile"] = cluster.ssl_cert_location
            if cluster.ssl_key_location:
                config["ssl_keyfile"] = cluster.ssl_key_location

            logger.info(f"Creating new Kafka (py) AdminClient: {cluster_id}")
            client = KafkaAdminClient(**config)

            # 캐시 저장
            self._kafka_py_clients[cluster_id] = client

            return client

    async def get_schema_registry_client(self, registry_id: str) -> AsyncSchemaRegistryClient:
        """Schema Registry Client 획득 (동적 생성/캐싱)

        Args:
            registry_id: 레지스트리 ID

        Returns:
            AsyncSchemaRegistryClient 인스턴스

        Raises:
            ValueError: 레지스트리가 존재하지 않거나 비활성 상태
        """
        # 캐시 확인
        if registry_id in self._schema_registry_clients:
            logger.debug(f"Schema Registry Client cache hit: {registry_id}")
            return self._schema_registry_clients[registry_id]

        # Lock 획득
        lock_key = f"schema_{registry_id}"
        lock = self._get_loop_scoped_lock(lock_key)

        async with lock:
            # Double-check
            if registry_id in self._schema_registry_clients:
                return self._schema_registry_clients[registry_id]

            # DB에서 레지스트리 정보 조회
            registry = await self.schema_registry_repo.get_by_id(registry_id)
            if not registry:
                raise ValueError(f"Schema Registry not found: {registry_id}")
            if not registry.is_active:
                raise ValueError(f"Schema Registry is inactive: {registry_id}")

            # Client 생성
            logger.info(f"Creating new Schema Registry Client: {registry_id}")
            config = registry.to_client_config()
            client = AsyncSchemaRegistryClient(config)

            # 캐시 저장
            self._schema_registry_clients[registry_id] = client

            return client

    async def get_minio_client(self, storage_id: str) -> tuple[Minio, str]:
        """MinIO Client 획득 (동적 생성/캐싱)

        Args:
            storage_id: 스토리지 ID

        Returns:
            (Minio 클라이언트, bucket_name) 튜플

        Raises:
            ValueError: 스토리지가 존재하지 않거나 비활성 상태
        """
        # 캐시 확인
        if storage_id in self._minio_clients:
            logger.debug(f"MinIO Client cache hit: {storage_id}")
            return self._minio_clients[storage_id]

        # Lock 획득
        lock_key = f"storage_{storage_id}"
        lock = self._get_loop_scoped_lock(lock_key)

        async with lock:
            # Double-check
            if storage_id in self._minio_clients:
                return self._minio_clients[storage_id]

            # DB에서 스토리지 정보 조회
            storage = await self.storage_repo.get_by_id(storage_id)
            if not storage:
                raise ValueError(f"Object Storage not found: {storage_id}")
            if not storage.is_active:
                raise ValueError(f"Object Storage is inactive: {storage_id}")

            # Client 생성
            logger.info(f"Creating new MinIO Client: {storage_id}")
            config = storage.to_minio_config()

            # 타입 안전성을 위한 명시적 변환
            endpoint: str = str(config["endpoint"])
            access_key: str | None = str(config["access_key"]) if config["access_key"] else None
            secret_key: str | None = str(config["secret_key"]) if config["secret_key"] else None
            secure: bool = bool(config["secure"])

            client = Minio(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
            )

            # 캐시 저장 (bucket_name과 함께)
            result = (client, storage.bucket_name)
            self._minio_clients[storage_id] = result

            return result

    async def get_storage_info(self, storage_id: str) -> ObjectStorage:
        """Object Storage 정보 조회

        Args:
            storage_id: 스토리지 ID

        Returns:
            ObjectStorage 도메인 모델
        """
        storage = await self.storage_repo.get_by_id(storage_id)
        if not storage:
            raise ValueError(f"Object Storage not found: {storage_id}")
        if not storage.is_active:
            raise ValueError(f"Object Storage is inactive: {storage_id}")

        return storage

    async def test_kafka_connection(self, cluster_id: str) -> ConnectionTestResult:
        """Kafka 연결 테스트

        Args:
            cluster_id: 클러스터 ID

        Returns:
            연결 테스트 결과
        """
        import time

        try:
            start_time = time.time()

            # AdminClient 획득
            admin_client = await self.get_kafka_admin_client(cluster_id)

            # 메타데이터 조회 (타임아웃 10초)
            metadata = admin_client.list_topics(timeout=10)

            latency_ms = (time.time() - start_time) * 1000

            return ConnectionTestResult(
                success=True,
                message=f"Connected to Kafka cluster: {len(metadata.brokers)} brokers",
                latency_ms=latency_ms,
                metadata={
                    "broker_count": len(metadata.brokers),
                    "topic_count": len(metadata.topics),
                    "cluster_id": metadata.cluster_id or "unknown",
                },
            )

        except Exception as e:
            logger.error(f"Kafka connection test failed for {cluster_id}: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {e!s}",
            )

    async def test_schema_registry_connection(self, registry_id: str) -> ConnectionTestResult:
        """Schema Registry 연결 테스트

        Args:
            registry_id: 레지스트리 ID

        Returns:
            연결 테스트 결과
        """
        import time

        try:
            start_time = time.time()

            # Client 획득
            client = await self.get_schema_registry_client(registry_id)

            # 스키마 목록 조회 (연결 확인)
            subjects = await client.get_subjects()

            latency_ms = (time.time() - start_time) * 1000

            return ConnectionTestResult(
                success=True,
                message=f"Connected to Schema Registry: {len(subjects)} subjects",
                latency_ms=latency_ms,
                metadata={
                    "subject_count": len(subjects),
                },
            )

        except Exception as e:
            logger.error(f"Schema Registry connection test failed for {registry_id}: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {e!s}",
            )

    async def test_storage_connection(self, storage_id: str) -> ConnectionTestResult:
        """Object Storage 연결 테스트

        Args:
            storage_id: 스토리지 ID

        Returns:
            연결 테스트 결과
        """
        import time

        try:
            start_time = time.time()

            # Client 획득
            client, bucket_name = await self.get_minio_client(storage_id)

            # 버킷 존재 확인
            def _check():
                return client.bucket_exists(bucket_name)

            bucket_exists = await asyncio.to_thread(_check)

            latency_ms = (time.time() - start_time) * 1000

            return ConnectionTestResult(
                success=True,
                message=f"Connected to Object Storage: bucket '{bucket_name}' {'exists' if bucket_exists else 'not found'}",
                latency_ms=latency_ms,
                metadata={
                    "bucket_name": bucket_name,
                    "bucket_exists": bucket_exists,
                },
            )

        except Exception as e:
            logger.error(f"Object Storage connection test failed for {storage_id}: {e}")
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {e!s}",
            )

    def invalidate_cache(self, resource_type: str, resource_id: str) -> None:
        """캐시 무효화 (설정 변경 시 호출)

        Args:
            resource_type: "kafka" | "schema_registry" | "storage"
            resource_id: 리소스 ID
        """
        if resource_type == "kafka":
            if resource_id in self._kafka_clients:
                del self._kafka_clients[resource_id]
                logger.info(f"Kafka AdminClient cache invalidated: {resource_id}")
            if resource_id in self._kafka_py_clients:
                del self._kafka_py_clients[resource_id]
                logger.info(f"Kafka (py) AdminClient cache invalidated: {resource_id}")

        elif resource_type == "schema_registry" and resource_id in self._schema_registry_clients:
            del self._schema_registry_clients[resource_id]
            logger.info(f"Schema Registry Client cache invalidated: {resource_id}")

        elif resource_type == "storage" and resource_id in self._minio_clients:
            del self._minio_clients[resource_id]
            logger.info(f"MinIO Client cache invalidated: {resource_id}")

        # Lock도 제거
        lock_key = f"{resource_type}_{resource_id}"
        if lock_key in self._locks:
            del self._locks[lock_key]

    def clear_all_caches(self) -> None:
        """전체 캐시 초기화"""
        self._kafka_clients.clear()
        self._kafka_py_clients.clear()
        self._schema_registry_clients.clear()
        self._minio_clients.clear()
        self._locks.clear()
        logger.info("All connection locks cleared")

    def _get_loop_scoped_lock(self, key: str) -> asyncio.Lock:
        """현재 이벤트 루프에 안전한 Lock 획득"""
        loop = asyncio.get_running_loop()
        entry = self._locks.get(key)
        if entry is not None:
            stored_loop, lock = entry
            if stored_loop is loop:
                return lock

        lock = asyncio.Lock()
        self._locks[key] = (loop, lock)
        return lock
