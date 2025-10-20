"""Cluster Use Cases - 모듈화된 Use Case 집합"""

from .broker import (
    CreateKafkaClusterUseCase,
    DeleteKafkaClusterUseCase,
    GetKafkaClusterUseCase,
    ListKafkaClustersUseCase,
    TestKafkaConnectionUseCase,
    UpdateKafkaClusterUseCase,
)
from .connect import (
    CreateConnectorUseCase,
    CreateKafkaConnectUseCase,
    DeleteConnectorUseCase,
    DeleteKafkaConnectUseCase,
    GetConnectorDetailsUseCase,
    GetConnectorStatusUseCase,
    GetKafkaConnectUseCase,
    ListConnectorsUseCase,
    ListKafkaConnectsUseCase,
    PauseConnectorUseCase,
    RestartConnectorUseCase,
    ResumeConnectorUseCase,
    TestKafkaConnectConnectionUseCase,
    UpdateKafkaConnectUseCase,
)
from .registry import (
    CreateSchemaRegistryUseCase,
    DeleteSchemaRegistryUseCase,
    ListSchemaRegistriesUseCase,
    TestSchemaRegistryConnectionUseCase,
    UpdateSchemaRegistryUseCase,
)
from .storage import (
    CreateObjectStorageUseCase,
    DeleteObjectStorageUseCase,
    ListObjectStoragesUseCase,
    TestObjectStorageConnectionUseCase,
    UpdateObjectStorageUseCase,
)

__all__ = [
    "CreateConnectorUseCase",
    # Kafka Cluster
    "CreateKafkaClusterUseCase",
    # Kafka Connect
    "CreateKafkaConnectUseCase",
    # Object Storage
    "CreateObjectStorageUseCase",
    # Schema Registry
    "CreateSchemaRegistryUseCase",
    "DeleteConnectorUseCase",
    "DeleteKafkaClusterUseCase",
    "DeleteKafkaConnectUseCase",
    "DeleteObjectStorageUseCase",
    "DeleteSchemaRegistryUseCase",
    "GetConnectorDetailsUseCase",
    "GetConnectorStatusUseCase",
    "GetKafkaClusterUseCase",
    "GetKafkaConnectUseCase",
    # Connectors
    "ListConnectorsUseCase",
    "ListKafkaClustersUseCase",
    "ListKafkaConnectsUseCase",
    "ListObjectStoragesUseCase",
    "ListSchemaRegistriesUseCase",
    "PauseConnectorUseCase",
    "RestartConnectorUseCase",
    "ResumeConnectorUseCase",
    "TestKafkaConnectConnectionUseCase",
    "TestKafkaConnectionUseCase",
    "TestObjectStorageConnectionUseCase",
    "TestSchemaRegistryConnectionUseCase",
    "UpdateKafkaClusterUseCase",
    "UpdateKafkaConnectUseCase",
    "UpdateObjectStorageUseCase",
    "UpdateSchemaRegistryUseCase",
]
