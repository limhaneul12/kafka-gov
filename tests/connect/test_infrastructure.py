"""Connect Infrastructure 테스트"""

import pytest


class TestKafkaConnectRestClient:
    """Kafka Connect REST Client 테스트"""

    def test_client_import(self):
        """클라이언트 import 가능"""
        from app.connect.infrastructure.client import KafkaConnectRestClient

        assert KafkaConnectRestClient is not None

    def test_client_has_required_methods(self):
        """필수 메서드 존재 확인"""
        from app.connect.infrastructure.client import KafkaConnectRestClient

        assert hasattr(KafkaConnectRestClient, "list_connectors")
        assert hasattr(KafkaConnectRestClient, "get_connector")
        assert hasattr(KafkaConnectRestClient, "create_connector")
        assert hasattr(KafkaConnectRestClient, "delete_connector")


class TestConnectorMetadataRepository:
    """Connector Metadata Repository 테스트"""

    def test_repository_import(self):
        """Repository import 가능"""
        from app.connect.infrastructure.repositories import MySQLConnectorMetadataRepository

        assert MySQLConnectorMetadataRepository is not None

    def test_repository_implements_interface(self):
        """Repository가 인터페이스 구현"""
        from app.connect.domain.repositories import IConnectorMetadataRepository
        from app.connect.infrastructure.repositories import MySQLConnectorMetadataRepository

        # 인터페이스의 메서드들이 구현체에 존재하는지 확인
        assert hasattr(MySQLConnectorMetadataRepository, "get_metadata")
        assert hasattr(MySQLConnectorMetadataRepository, "save_metadata")
        assert hasattr(MySQLConnectorMetadataRepository, "delete_metadata")


class TestConnectorMetadataModel:
    """Connector Metadata SQLAlchemy Model 테스트"""

    def test_model_import(self):
        """Model import 가능"""
        from app.connect.infrastructure.models import ConnectorMetadataModel

        assert ConnectorMetadataModel is not None

    def test_model_has_required_fields(self):
        """필수 필드 존재"""
        from app.connect.infrastructure.models import ConnectorMetadataModel

        assert hasattr(ConnectorMetadataModel, "id")
        assert hasattr(ConnectorMetadataModel, "connect_id")
        assert hasattr(ConnectorMetadataModel, "connector_name")
        assert hasattr(ConnectorMetadataModel, "team")
        assert hasattr(ConnectorMetadataModel, "tags")
