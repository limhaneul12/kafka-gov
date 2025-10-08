"""Cluster Domain Models 테스트"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.cluster.domain.models import (
    KafkaCluster,
    ObjectStorage,
    SaslMechanism,
    SchemaRegistry,
    SecurityProtocol,
)


class TestKafkaCluster:
    """KafkaCluster 도메인 모델 테스트"""

    def test_create_kafka_cluster_plaintext(self):
        """PLAINTEXT 보안 프로토콜로 클러스터 생성"""
        cluster = KafkaCluster(
            cluster_id="test-1",
            name="Test Cluster",
            bootstrap_servers="localhost:9092",
            security_protocol=SecurityProtocol.PLAINTEXT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert cluster.cluster_id == "test-1"
        assert cluster.name == "Test Cluster"
        assert cluster.bootstrap_servers == "localhost:9092"
        assert cluster.security_protocol == SecurityProtocol.PLAINTEXT
        assert cluster.is_active is True

    def test_create_kafka_cluster_with_sasl(self):
        """SASL 인증이 있는 클러스터 생성"""
        cluster = KafkaCluster(
            cluster_id="test-2",
            name="SASL Cluster",
            bootstrap_servers="broker1:9092,broker2:9092",
            security_protocol=SecurityProtocol.SASL_SSL,
            sasl_mechanism=SaslMechanism.SCRAM_SHA_256,
            sasl_username="admin",
            sasl_password="encrypted_password",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert cluster.security_protocol == SecurityProtocol.SASL_SSL
        assert cluster.sasl_mechanism == SaslMechanism.SCRAM_SHA_256
        assert cluster.sasl_username == "admin"
        assert cluster.sasl_password == "encrypted_password"

    def test_to_admin_config_plaintext(self):
        """AdminClient 설정 생성 - PLAINTEXT"""
        cluster = KafkaCluster(
            cluster_id="test-1",
            name="Test",
            bootstrap_servers="localhost:9092",
            security_protocol=SecurityProtocol.PLAINTEXT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        config = cluster.to_admin_config()

        assert config["bootstrap.servers"] == "localhost:9092"
        assert config["security.protocol"] == "PLAINTEXT"
        assert config["request.timeout.ms"] == 60000
        assert "sasl.mechanism" not in config

    def test_to_admin_config_with_sasl(self):
        """AdminClient 설정 생성 - SASL"""
        cluster = KafkaCluster(
            cluster_id="test-2",
            name="SASL Cluster",
            bootstrap_servers="broker:9092",
            security_protocol=SecurityProtocol.SASL_SSL,
            sasl_mechanism=SaslMechanism.PLAIN,
            sasl_username="user",
            sasl_password="pass",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        config = cluster.to_admin_config()

        assert config["security.protocol"] == "SASL_SSL"
        assert config["sasl.mechanism"] == "PLAIN"
        assert config["sasl.username"] == "user"
        assert config["sasl.password"] == "pass"

    def test_kafka_cluster_immutable(self):
        """KafkaCluster는 불변 객체"""
        cluster = KafkaCluster(
            cluster_id="test-1",
            name="Test",
            bootstrap_servers="localhost:9092",
            security_protocol=SecurityProtocol.PLAINTEXT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with pytest.raises(AttributeError):
            cluster.name = "Changed"  # type: ignore


class TestSchemaRegistry:
    """SchemaRegistry 도메인 모델 테스트"""

    def test_create_schema_registry(self):
        """Schema Registry 생성"""
        registry = SchemaRegistry(
            registry_id="reg-1",
            name="Test Registry",
            url="http://localhost:8081",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert registry.registry_id == "reg-1"
        assert registry.name == "Test Registry"
        assert registry.url == "http://localhost:8081"
        assert registry.timeout == 30

    def test_create_schema_registry_with_auth(self):
        """인증이 있는 Schema Registry 생성"""
        registry = SchemaRegistry(
            registry_id="reg-2",
            name="Secure Registry",
            url="https://registry.example.com",
            auth_username="admin",
            auth_password="encrypted_pass",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert registry.auth_username == "admin"
        assert registry.auth_password == "encrypted_pass"

    def test_to_client_config_without_auth(self):
        """Client 설정 생성 - 인증 없음"""
        registry = SchemaRegistry(
            registry_id="reg-1",
            name="Test",
            url="http://localhost:8081",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        config = registry.to_client_config()

        assert config["url"] == "http://localhost:8081"
        assert config["timeout"] == 30
        assert "basic.auth.user.info" not in config

    def test_to_client_config_with_auth(self):
        """Client 설정 생성 - 인증 있음"""
        registry = SchemaRegistry(
            registry_id="reg-2",
            name="Secure",
            url="https://registry.example.com",
            auth_username="user",
            auth_password="pass",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        config = registry.to_client_config()

        assert config["basic.auth.user.info"] == "user:pass"

    def test_schema_registry_immutable(self):
        """SchemaRegistry는 불변 객체"""
        registry = SchemaRegistry(
            registry_id="reg-1",
            name="Test",
            url="http://localhost:8081",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with pytest.raises(AttributeError):
            registry.url = "http://changed:8081"  # type: ignore


class TestObjectStorage:
    """ObjectStorage 도메인 모델 테스트"""

    def test_create_object_storage(self):
        """Object Storage 생성"""
        storage = ObjectStorage(
            storage_id="storage-1",
            name="Test MinIO",
            endpoint_url="localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            bucket_name="test-bucket",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert storage.storage_id == "storage-1"
        assert storage.name == "Test MinIO"
        assert storage.endpoint_url == "localhost:9000"
        assert storage.bucket_name == "test-bucket"
        assert storage.use_ssl is False

    def test_create_object_storage_with_ssl(self):
        """SSL이 활성화된 Object Storage 생성"""
        storage = ObjectStorage(
            storage_id="storage-2",
            name="Secure MinIO",
            endpoint_url="minio.example.com:9000",
            access_key="access",
            secret_key="secret",
            bucket_name="secure-bucket",
            use_ssl=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert storage.use_ssl is True

    def test_to_minio_config(self):
        """MinIO Client 설정 생성"""
        storage = ObjectStorage(
            storage_id="storage-1",
            name="Test",
            endpoint_url="localhost:9000",
            access_key="admin",
            secret_key="password",
            bucket_name="bucket",
            region="us-west-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        config = storage.to_minio_config()

        assert config["endpoint"] == "localhost:9000"
        assert config["access_key"] == "admin"
        assert config["secret_key"] == "password"
        assert config["secure"] is False
        assert config["region"] == "us-west-1"

    def test_to_minio_config_removes_protocol(self):
        """MinIO 설정에서 프로토콜 제거"""
        storage = ObjectStorage(
            storage_id="storage-1",
            name="Test",
            endpoint_url="http://localhost:9000",
            access_key="admin",
            secret_key="password",
            bucket_name="bucket",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        config = storage.to_minio_config()

        # 프로토콜이 제거되어야 함
        assert config["endpoint"] == "localhost:9000"
        assert "http://" not in config["endpoint"]

    def test_base_url_property_http(self):
        """base_url 속성 - HTTP"""
        storage = ObjectStorage(
            storage_id="storage-1",
            name="Test",
            endpoint_url="localhost:9000",
            access_key="admin",
            secret_key="password",
            bucket_name="bucket",
            use_ssl=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert storage.base_url == "http://localhost:9000"

    def test_base_url_property_https(self):
        """base_url 속성 - HTTPS"""
        storage = ObjectStorage(
            storage_id="storage-2",
            name="Secure",
            endpoint_url="minio.example.com:9000",
            access_key="admin",
            secret_key="password",
            bucket_name="bucket",
            use_ssl=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert storage.base_url == "https://minio.example.com:9000"

    def test_object_storage_immutable(self):
        """ObjectStorage는 불변 객체"""
        storage = ObjectStorage(
            storage_id="storage-1",
            name="Test",
            endpoint_url="localhost:9000",
            access_key="admin",
            secret_key="password",
            bucket_name="bucket",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with pytest.raises(AttributeError):
            storage.bucket_name = "changed"  # type: ignore
