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
    GetSchemaRegistryUseCase,
    ListSchemaRegistriesUseCase,
    TestSchemaRegistryConnectionUseCase,
    UpdateSchemaRegistryUseCase,
)

__all__ = [
    "CreateConnectorUseCase",
    # Kafka Cluster
    "CreateKafkaClusterUseCase",
    # Kafka Connect
    "CreateKafkaConnectUseCase",
    # Schema Registry
    "CreateSchemaRegistryUseCase",
    "DeleteConnectorUseCase",
    "DeleteKafkaClusterUseCase",
    "DeleteKafkaConnectUseCase",
    "DeleteSchemaRegistryUseCase",
    "GetConnectorDetailsUseCase",
    "GetConnectorStatusUseCase",
    "GetKafkaClusterUseCase",
    "GetKafkaConnectUseCase",
    "GetSchemaRegistryUseCase",
    # Connectors
    "ListConnectorsUseCase",
    "ListKafkaClustersUseCase",
    "ListKafkaConnectsUseCase",
    "ListSchemaRegistriesUseCase",
    "PauseConnectorUseCase",
    "RestartConnectorUseCase",
    "ResumeConnectorUseCase",
    "TestKafkaConnectConnectionUseCase",
    "TestKafkaConnectionUseCase",
    "TestSchemaRegistryConnectionUseCase",
    "UpdateKafkaClusterUseCase",
    "UpdateKafkaConnectUseCase",
    "UpdateSchemaRegistryUseCase",
]
