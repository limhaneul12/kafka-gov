"""ConnectionManager 테스트"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cluster.domain.models import (
    KafkaCluster,
    SchemaRegistry,
    SecurityProtocol,
)
from app.cluster.domain.services import ConnectionManager


class TestConnectionManagerKafka:
    """ConnectionManager - Kafka AdminClient 관련 테스트"""

    @pytest.mark.asyncio
    async def test_get_kafka_admin_client_creates_new_client(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
        sample_kafka_cluster,
    ):
        """Kafka AdminClient 최초 생성"""
        # Given
        mock_kafka_cluster_repo.get_by_id.return_value = sample_kafka_cluster

        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
        )

        # When
        with patch("app.cluster.domain.services.AdminClient") as mock_admin_client_class:
            mock_client = MagicMock()
            mock_admin_client_class.return_value = mock_client

            client = await manager.get_kafka_admin_client("test-cluster-1")

        # Then
        assert client == mock_client
        mock_kafka_cluster_repo.get_by_id.assert_called_once_with("test-cluster-1")
        mock_admin_client_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_kafka_admin_client_uses_cache(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
        sample_kafka_cluster,
    ):
        """Kafka AdminClient 캐싱 확인"""
        # Given
        mock_kafka_cluster_repo.get_by_id.return_value = sample_kafka_cluster

        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
        )

        # When
        with patch("app.cluster.domain.services.AdminClient") as mock_admin_client_class:
            mock_client = MagicMock()
            mock_admin_client_class.return_value = mock_client

            client1 = await manager.get_kafka_admin_client("test-cluster-1")
            client2 = await manager.get_kafka_admin_client("test-cluster-1")

        # Then
        assert client1 == client2
        # Repository는 한 번만 호출되어야 함 (캐시 사용)
        mock_kafka_cluster_repo.get_by_id.assert_called_once()
        # AdminClient도 한 번만 생성되어야 함
        mock_admin_client_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_kafka_admin_client_cluster_not_found(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
    ):
        """존재하지 않는 클러스터 조회 시 에러"""
        # Given
        mock_kafka_cluster_repo.get_by_id.return_value = None

        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
        )

        # When & Then
        with pytest.raises(ValueError, match="Kafka cluster not found"):
            await manager.get_kafka_admin_client("non-existent")

    @pytest.mark.asyncio
    async def test_get_kafka_admin_client_inactive_cluster(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
    ):
        """비활성 클러스터 조회 시 에러"""
        # Given
        inactive_cluster = KafkaCluster(
            cluster_id="inactive-cluster",
            name="Inactive",
            bootstrap_servers="localhost:9092",
            security_protocol=SecurityProtocol.PLAINTEXT,
            is_active=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_kafka_cluster_repo.get_by_id.return_value = inactive_cluster

        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
        )

        # When & Then
        with pytest.raises(ValueError, match="Kafka cluster is inactive"):
            await manager.get_kafka_admin_client("inactive-cluster")


class TestConnectionManagerSchemaRegistry:
    """ConnectionManager - Schema Registry Client 관련 테스트"""

    @pytest.mark.asyncio
    async def test_get_schema_registry_client_creates_new_client(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
        sample_schema_registry,
    ):
        """Schema Registry Client 최초 생성"""
        # Given
        mock_schema_registry_repo.get_by_id.return_value = sample_schema_registry

        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
            storage_repo=mock_object_storage_repo,
        )

        # When
        with patch("app.cluster.domain.services.AsyncSchemaRegistryClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            client = await manager.get_schema_registry_client("test-registry-1")

        # Then
        assert client == mock_client
        mock_schema_registry_repo.get_by_id.assert_called_once_with("test-registry-1")
        mock_client_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_schema_registry_client_uses_cache(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
        sample_schema_registry,
    ):
        """Schema Registry Client 캐싱 확인"""
        # Given
        mock_schema_registry_repo.get_by_id.return_value = sample_schema_registry

        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
            storage_repo=mock_object_storage_repo,
        )

        # When
        with patch("app.cluster.domain.services.AsyncSchemaRegistryClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            client1 = await manager.get_schema_registry_client("test-registry-1")
            client2 = await manager.get_schema_registry_client("test-registry-1")

        # Then
        assert client1 == client2
        mock_schema_registry_repo.get_by_id.assert_called_once()
        mock_client_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_schema_registry_client_not_found(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
    ):
        """존재하지 않는 레지스트리 조회 시 에러"""
        # Given
        mock_schema_registry_repo.get_by_id.return_value = None

        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
            storage_repo=mock_object_storage_repo,
        )

        # When & Then
        with pytest.raises(ValueError, match="Schema Registry not found"):
            await manager.get_schema_registry_client("non-existent")

    @pytest.mark.asyncio
    async def test_get_schema_registry_client_inactive(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
    ):
        """비활성 레지스트리 조회 시 에러"""
        # Given
        inactive_registry = SchemaRegistry(
            registry_id="inactive-registry",
            name="Inactive",
            url="http://localhost:8081",
            is_active=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_schema_registry_repo.get_by_id.return_value = inactive_registry

        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
        )

        # When & Then
        with pytest.raises(ValueError, match="Schema Registry is inactive"):
            await manager.get_schema_registry_client("inactive-registry")


class TestConnectionManagerCacheInvalidation:
    """ConnectionManager - 캐시 무효화 테스트"""

    @pytest.mark.asyncio
    async def test_invalidate_kafka_cache(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
        sample_kafka_cluster,
    ):
        """Kafka 캐시 무효화"""
        # Given
        mock_kafka_cluster_repo.get_by_id.return_value = sample_kafka_cluster

        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
            storage_repo=mock_object_storage_repo,
        )

        with patch("app.cluster.domain.services.AdminClient") as mock_admin_client_class:
            mock_client = MagicMock()
            mock_admin_client_class.return_value = mock_client

            # 첫 번째 호출로 캐시 생성
            await manager.get_kafka_admin_client("test-cluster-1")

            # When: 캐시 무효화
            manager.invalidate_cache("kafka", "test-cluster-1")

            # Then: 다시 호출하면 새로 생성되어야 함
            await manager.get_kafka_admin_client("test-cluster-1")

            # Repository가 2번 호출되어야 함 (캐시 무효화 후 재생성)
            assert mock_kafka_cluster_repo.get_by_id.call_count == 2

    @pytest.mark.asyncio
    async def test_invalidate_schema_registry_cache(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
        sample_schema_registry,
    ):
        """Schema Registry 캐시 무효화"""
        # Given
        mock_schema_registry_repo.get_by_id.return_value = sample_schema_registry

        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
        )

        with patch("app.cluster.domain.services.AsyncSchemaRegistryClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            await manager.get_schema_registry_client("test-registry-1")

            # When
            manager.invalidate_cache("schema_registry", "test-registry-1")

            # Then
            await manager.get_schema_registry_client("test-registry-1")
            assert mock_schema_registry_repo.get_by_id.call_count == 2

    def test_clear_all_caches(
        self,
        mock_kafka_cluster_repo,
        mock_schema_registry_repo,
    ):
        """전체 캐시 초기화"""
        # Given
        manager = ConnectionManager(
            kafka_cluster_repo=mock_kafka_cluster_repo,
            schema_registry_repo=mock_schema_registry_repo,
        )

        # 캐시에 데이터 추가 (직접 접근)
        manager._kafka_clients["test-1"] = MagicMock()
        manager._schema_registry_clients["test-2"] = MagicMock()

        # When
        manager.clear_all_caches()

        # Then
        assert len(manager._kafka_clients) == 0
        assert len(manager._schema_registry_clients) == 0
        assert len(manager._locks) == 0
