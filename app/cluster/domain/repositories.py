"""Cluster Domain Repositories - 연결 정보 저장소 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import KafkaCluster, KafkaConnect, ObjectStorage, SchemaRegistry


class IKafkaClusterRepository(ABC):
    """Kafka 클러스터 리포지토리 인터페이스"""

    @abstractmethod
    async def create(self, cluster: KafkaCluster) -> KafkaCluster:
        """클러스터 생성"""
        ...

    @abstractmethod
    async def get_by_id(self, cluster_id: str) -> KafkaCluster | None:
        """ID로 클러스터 조회"""
        ...

    @abstractmethod
    async def list_all(self, active_only: bool = True) -> list[KafkaCluster]:
        """전체 클러스터 목록 조회"""
        ...

    @abstractmethod
    async def update(self, cluster: KafkaCluster) -> KafkaCluster:
        """클러스터 정보 수정"""
        ...

    @abstractmethod
    async def delete(self, cluster_id: str) -> bool:
        """클러스터 삭제 (소프트 삭제: is_active=False)"""
        ...


class ISchemaRegistryRepository(ABC):
    """Schema Registry 리포지토리 인터페이스"""

    @abstractmethod
    async def create(self, registry: SchemaRegistry) -> SchemaRegistry:
        """레지스트리 생성"""
        ...

    @abstractmethod
    async def get_by_id(self, registry_id: str) -> SchemaRegistry | None:
        """ID로 레지스트리 조회"""
        ...

    @abstractmethod
    async def list_all(self, active_only: bool = True) -> list[SchemaRegistry]:
        """전체 레지스트리 목록 조회"""
        ...

    @abstractmethod
    async def update(self, registry: SchemaRegistry) -> SchemaRegistry:
        """레지스트리 정보 수정"""
        ...

    @abstractmethod
    async def delete(self, registry_id: str) -> bool:
        """레지스트리 삭제 (소프트 삭제: is_active=False)"""
        ...


class IObjectStorageRepository(ABC):
    """Object Storage 리포지토리 인터페이스"""

    @abstractmethod
    async def create(self, storage: ObjectStorage) -> ObjectStorage:
        """스토리지 생성"""
        ...

    @abstractmethod
    async def get_by_id(self, storage_id: str) -> ObjectStorage | None:
        """ID로 스토리지 조회"""
        ...

    @abstractmethod
    async def list_all(self, active_only: bool = True) -> list[ObjectStorage]:
        """전체 스토리지 목록 조회"""
        ...

    @abstractmethod
    async def update(self, storage: ObjectStorage) -> ObjectStorage:
        """스토리지 정보 수정"""
        ...

    @abstractmethod
    async def delete(self, storage_id: str) -> bool:
        """스토리지 삭제 (소프트 삭제: is_active=False)"""
        ...


class IKafkaConnectRepository(ABC):
    """Kafka Connect 리포지토리 인터페이스"""

    @abstractmethod
    async def create(self, connect: KafkaConnect) -> KafkaConnect:
        """Connect 생성"""
        ...

    @abstractmethod
    async def get_by_id(self, connect_id: str) -> KafkaConnect | None:
        """ID로 Connect 조회"""
        ...

    @abstractmethod
    async def list_by_cluster(self, cluster_id: str) -> list[KafkaConnect]:
        """클러스터별 Connect 목록 조회"""
        ...

    @abstractmethod
    async def list_all(self, active_only: bool = True) -> list[KafkaConnect]:
        """전체 Connect 목록 조회"""
        ...

    @abstractmethod
    async def update(self, connect: KafkaConnect) -> KafkaConnect:
        """Connect 정보 수정"""
        ...

    @abstractmethod
    async def delete(self, connect_id: str) -> bool:
        """Connect 삭제 (소프트 삭제: is_active=False)"""
        ...
