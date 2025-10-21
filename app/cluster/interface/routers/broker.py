"""Kafka Cluster (Broker) Router"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, Query, status

from app.cluster.interface.schemas import (
    ConnectionTestResponse,
    KafkaClusterCreateRequest,
    KafkaClusterResponse,
    KafkaClusterUpdateRequest,
)
from app.container import AppContainer
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter(prefix="/brokers", tags=["kafka-brokers"])

# Dependency Injection
CreateClusterUseCase = Depends(
    Provide[AppContainer.cluster_container.create_kafka_cluster_use_case]
)
ListClustersUseCase = Depends(Provide[AppContainer.cluster_container.list_kafka_clusters_use_case])
GetClusterUseCase = Depends(Provide[AppContainer.cluster_container.get_kafka_cluster_use_case])
UpdateClusterUseCase = Depends(
    Provide[AppContainer.cluster_container.update_kafka_cluster_use_case]
)
DeleteClusterUseCase = Depends(
    Provide[AppContainer.cluster_container.delete_kafka_cluster_use_case]
)
TestClusterConnectionUseCase = Depends(
    Provide[AppContainer.cluster_container.test_kafka_connection_use_case]
)


@router.post("", response_model=KafkaClusterResponse, status_code=status.HTTP_201_CREATED)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")},
    default_message="Failed to create Kafka cluster",
)
async def create_kafka_cluster(
    request: KafkaClusterCreateRequest,
    use_case=CreateClusterUseCase,
) -> KafkaClusterResponse:
    """Kafka 클러스터 생성"""
    cluster = await use_case.execute(
        cluster_id=request.cluster_id,
        name=request.name,
        bootstrap_servers=request.bootstrap_servers,
        description=request.description,
        security_protocol=request.security_protocol,
        sasl_mechanism=request.sasl_mechanism,
        sasl_username=request.sasl_username,
        sasl_password=request.sasl_password,
        ssl_ca_location=request.ssl_ca_location,
        ssl_cert_location=request.ssl_cert_location,
        ssl_key_location=request.ssl_key_location,
        request_timeout_ms=request.request_timeout_ms,
        socket_timeout_ms=request.socket_timeout_ms,
    )

    return KafkaClusterResponse(
        cluster_id=cluster.cluster_id,
        name=cluster.name,
        bootstrap_servers=cluster.bootstrap_servers,
        description=cluster.description,
        security_protocol=cluster.security_protocol.value,
        sasl_mechanism=cluster.sasl_mechanism.value if cluster.sasl_mechanism else None,
        sasl_username=cluster.sasl_username,
        ssl_ca_location=cluster.ssl_ca_location,
        ssl_cert_location=cluster.ssl_cert_location,
        ssl_key_location=cluster.ssl_key_location,
        request_timeout_ms=cluster.request_timeout_ms,
        socket_timeout_ms=cluster.socket_timeout_ms,
        is_active=cluster.is_active,
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
    )


@router.get("", response_model=list[KafkaClusterResponse])
@inject
@endpoint_error_handler(default_message="Failed to list Kafka clusters")
async def list_kafka_clusters(
    active_only: bool = Query(default=True, description="활성화된 클러스터만 조회"),
    use_case=ListClustersUseCase,
) -> list[KafkaClusterResponse]:
    """Kafka 클러스터 목록 조회"""
    clusters = await use_case.execute(active_only=active_only)

    return [
        KafkaClusterResponse(
            cluster_id=c.cluster_id,
            name=c.name,
            bootstrap_servers=c.bootstrap_servers,
            description=c.description,
            security_protocol=c.security_protocol.value,
            sasl_mechanism=c.sasl_mechanism.value if c.sasl_mechanism else None,
            sasl_username=c.sasl_username,
            ssl_ca_location=c.ssl_ca_location,
            ssl_cert_location=c.ssl_cert_location,
            ssl_key_location=c.ssl_key_location,
            request_timeout_ms=c.request_timeout_ms,
            socket_timeout_ms=c.socket_timeout_ms,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in clusters
    ]


@router.get("/{cluster_id}", response_model=KafkaClusterResponse)
@inject
@endpoint_error_handler(default_message="Failed to get Kafka cluster")
async def get_kafka_cluster(
    cluster_id: str = Path(..., description="클러스터 ID"),
    use_case=GetClusterUseCase,
) -> KafkaClusterResponse:
    """Kafka 클러스터 단일 조회"""
    cluster = await use_case.execute(cluster_id)

    return KafkaClusterResponse(
        cluster_id=cluster.cluster_id,
        name=cluster.name,
        bootstrap_servers=cluster.bootstrap_servers,
        description=cluster.description,
        security_protocol=cluster.security_protocol.value,
        sasl_mechanism=cluster.sasl_mechanism.value if cluster.sasl_mechanism else None,
        sasl_username=cluster.sasl_username,
        ssl_ca_location=cluster.ssl_ca_location,
        ssl_cert_location=cluster.ssl_cert_location,
        ssl_key_location=cluster.ssl_key_location,
        request_timeout_ms=cluster.request_timeout_ms,
        socket_timeout_ms=cluster.socket_timeout_ms,
        is_active=cluster.is_active,
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
    )


@router.put("/{cluster_id}", response_model=KafkaClusterResponse)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")},
    default_message="Failed to update Kafka cluster",
)
async def update_kafka_cluster(
    request: KafkaClusterUpdateRequest,
    cluster_id: str = Path(..., description="클러스터 ID"),
    use_case=UpdateClusterUseCase,
) -> KafkaClusterResponse:
    """Kafka 클러스터 수정"""
    cluster = await use_case.execute(
        cluster_id=cluster_id,
        name=request.name,
        bootstrap_servers=request.bootstrap_servers,
        description=request.description,
        security_protocol=request.security_protocol,
        sasl_mechanism=request.sasl_mechanism,
        sasl_username=request.sasl_username,
        sasl_password=request.sasl_password,
        ssl_ca_location=request.ssl_ca_location,
        ssl_cert_location=request.ssl_cert_location,
        ssl_key_location=request.ssl_key_location,
        request_timeout_ms=request.request_timeout_ms,
        socket_timeout_ms=request.socket_timeout_ms,
        is_active=request.is_active,
    )

    return KafkaClusterResponse(
        cluster_id=cluster.cluster_id,
        name=cluster.name,
        bootstrap_servers=cluster.bootstrap_servers,
        description=cluster.description,
        security_protocol=cluster.security_protocol.value,
        sasl_mechanism=cluster.sasl_mechanism.value if cluster.sasl_mechanism else None,
        sasl_username=cluster.sasl_username,
        ssl_ca_location=cluster.ssl_ca_location,
        ssl_cert_location=cluster.ssl_cert_location,
        ssl_key_location=cluster.ssl_key_location,
        request_timeout_ms=cluster.request_timeout_ms,
        socket_timeout_ms=cluster.socket_timeout_ms,
        is_active=cluster.is_active,
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
    )


@router.patch("/{cluster_id}/activate", response_model=KafkaClusterResponse)
@inject
@endpoint_error_handler(default_message="Failed to activate Kafka cluster")
async def activate_kafka_cluster(
    cluster_id: str = Path(..., description="클러스터 ID"),
    get_use_case=GetClusterUseCase,
    update_use_case=UpdateClusterUseCase,
) -> KafkaClusterResponse:
    """Kafka 클러스터 활성화 (is_active를 true로 변경)"""
    # 현재 클러스터 조회
    cluster = await get_use_case.execute(cluster_id)

    # is_active만 변경하여 업데이트
    updated_cluster = await update_use_case.execute(
        cluster_id=cluster_id,
        name=cluster.name,
        bootstrap_servers=cluster.bootstrap_servers,
        description=cluster.description,
        security_protocol=cluster.security_protocol,
        sasl_mechanism=cluster.sasl_mechanism,
        sasl_username=cluster.sasl_username,
        sasl_password=None,  # 기존 값 유지
        ssl_ca_location=cluster.ssl_ca_location,
        ssl_cert_location=cluster.ssl_cert_location,
        ssl_key_location=cluster.ssl_key_location,
        request_timeout_ms=cluster.request_timeout_ms,
        socket_timeout_ms=cluster.socket_timeout_ms,
        is_active=True,  # 활성화
    )

    return KafkaClusterResponse(
        cluster_id=updated_cluster.cluster_id,
        name=updated_cluster.name,
        bootstrap_servers=updated_cluster.bootstrap_servers,
        description=updated_cluster.description,
        security_protocol=updated_cluster.security_protocol.value,
        sasl_mechanism=updated_cluster.sasl_mechanism.value
        if updated_cluster.sasl_mechanism
        else None,
        sasl_username=updated_cluster.sasl_username,
        ssl_ca_location=updated_cluster.ssl_ca_location,
        ssl_cert_location=updated_cluster.ssl_cert_location,
        ssl_key_location=updated_cluster.ssl_key_location,
        request_timeout_ms=updated_cluster.request_timeout_ms,
        socket_timeout_ms=updated_cluster.socket_timeout_ms,
        is_active=updated_cluster.is_active,
        created_at=updated_cluster.created_at,
        updated_at=updated_cluster.updated_at,
    )


@router.delete("/{cluster_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
@endpoint_error_handler(default_message="Failed to delete Kafka cluster")
async def delete_kafka_cluster(
    cluster_id: str = Path(..., description="클러스터 ID"),
    use_case=DeleteClusterUseCase,
) -> None:
    """Kafka 클러스터 삭제 (소프트 삭제)"""
    await use_case.execute(cluster_id)


@router.post("/{cluster_id}/test", response_model=ConnectionTestResponse)
@inject
@endpoint_error_handler(default_message="Kafka connection test failed")
async def test_kafka_connection(
    cluster_id: str = Path(..., description="클러스터 ID"),
    use_case=TestClusterConnectionUseCase,
) -> ConnectionTestResponse:
    """Kafka 연결 테스트"""
    result = await use_case.execute(cluster_id)

    return ConnectionTestResponse(
        success=result.success,
        message=result.message,
        latency_ms=result.latency_ms,
        metadata=result.metadata,
    )
