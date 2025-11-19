"""Cluster Domain Repositories - 연결 정보 저장소 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import KafkaCluster, SchemaRegistry


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
