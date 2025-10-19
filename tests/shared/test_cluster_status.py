"""Shared Cluster Status 테스트"""

from __future__ import annotations

from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.shared.domain.models import BrokerInfo, ClusterStatus
from app.shared.infrastructure.cluster_repository import KafkaClusterRepository


class TestBrokerInfo:
    """BrokerInfo 도메인 모델 테스트"""

    def test_create_broker_info(self):
        """브로커 정보 생성"""
        broker = BrokerInfo(
            broker_id=1,
            host="kafka-1",
            port=9092,
            is_controller=True,
            leader_partition_count=45,
        )

        assert broker.broker_id == 1
        assert broker.host == "kafka-1"
        assert broker.port == 9092
        assert broker.is_controller is True
        assert broker.leader_partition_count == 45

    def test_immutable(self):
        """불변성 검증"""
        broker = BrokerInfo(
            broker_id=1,
            host="kafka-1",
            port=9092,
            is_controller=True,
            leader_partition_count=45,
        )

        with pytest.raises(AttributeError):
            broker.broker_id = 2  # type: ignore[misc]

    def test_disk_usage_optional(self):
        """디스크 사용량은 옵션"""
        broker_without_disk = BrokerInfo(
            broker_id=1,
            host="kafka-1",
            port=9092,
            is_controller=True,
            leader_partition_count=45,
        )
        assert broker_without_disk.disk_usage_bytes is None

        broker_with_disk = BrokerInfo(
            broker_id=1,
            host="kafka-1",
            port=9092,
            is_controller=True,
            leader_partition_count=45,
            disk_usage_bytes=1024 * 1024 * 1024,  # 1GB
        )
        assert broker_with_disk.disk_usage_bytes == 1024 * 1024 * 1024


class TestClusterStatus:
    """ClusterStatus 도메인 모델 테스트"""

    def test_create_cluster_status(self):
        """클러스터 상태 생성"""
        broker1 = BrokerInfo(
            broker_id=1,
            host="kafka-1",
            port=9092,
            is_controller=True,
            leader_partition_count=45,
        )
        broker2 = BrokerInfo(
            broker_id=2,
            host="kafka-2",
            port=9092,
            is_controller=False,
            leader_partition_count=40,
        )

        cluster = ClusterStatus(
            cluster_id="test-cluster",
            controller_id=1,
            brokers=(broker1, broker2),
            total_topics=25,
            total_partitions=120,
        )

        assert cluster.cluster_id == "test-cluster"
        assert cluster.controller_id == 1
        assert len(cluster.brokers) == 2
        assert cluster.total_topics == 25
        assert cluster.total_partitions == 120

    def test_dataclass_serialization(self):
        """dataclass 직렬화 테스트 (asdict 사용)"""
        broker = BrokerInfo(
            broker_id=1,
            host="kafka-1",
            port=9092,
            is_controller=True,
            leader_partition_count=45,
        )

        cluster = ClusterStatus(
            cluster_id="test-cluster",
            controller_id=1,
            brokers=(broker,),
            total_topics=10,
            total_partitions=30,
        )

        # dataclasses.asdict()를 통한 직렬화 테스트
        cluster_dict = asdict(cluster)

        assert cluster_dict["cluster_id"] == "test-cluster"
        assert cluster_dict["controller_id"] == 1
        assert len(cluster_dict["brokers"]) == 1
        # asdict는 중첩된 dataclass도 dict로 변환
        first_broker = cluster_dict["brokers"][0]
        assert first_broker["broker_id"] == 1
        assert first_broker["host"] == "kafka-1"


class TestKafkaClusterRepository:
    """KafkaClusterRepository 테스트"""

    @pytest.mark.asyncio
    async def test_get_cluster_status(self):
        """클러스터 상태 조회"""
        # Mock AdminClient
        mock_admin = MagicMock()

        # Mock metadata
        mock_broker = MagicMock()
        mock_broker.id = 1
        mock_broker.host = "kafka-1"
        mock_broker.port = 9092

        mock_partition = MagicMock()
        mock_partition.leader = 1

        mock_topic = MagicMock()
        mock_topic.partitions = {0: mock_partition}

        mock_metadata = MagicMock()
        mock_metadata.controller_id = 1
        mock_metadata.cluster_id = "test-cluster"
        mock_metadata.brokers = {1: mock_broker}
        mock_metadata.topics = {"test-topic": mock_topic}

        mock_admin.list_topics.return_value = mock_metadata

        # Repository 생성
        repository = KafkaClusterRepository(admin_client=mock_admin)

        # 실행
        result = await repository.get_cluster_status()

        # 검증
        assert result.cluster_id == "test-cluster"
        assert result.controller_id == 1
        assert len(result.brokers) == 1
        assert result.brokers[0].broker_id == 1
        assert result.brokers[0].host == "kafka-1"
        assert result.brokers[0].port == 9092
        assert result.brokers[0].is_controller is True
        assert result.brokers[0].leader_partition_count == 1
        assert result.total_topics == 1
        assert result.total_partitions == 1
