"""Cluster Interface Router - 연결 관리 API 엔드포인트"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, Query, status

from app.container import AppContainer

from .schemas import (
    ConnectionTestResponse,
    KafkaClusterCreateRequest,
    KafkaClusterResponse,
    KafkaClusterUpdateRequest,
    KafkaConnectCreateRequest,
    KafkaConnectResponse,
    ObjectStorageCreateRequest,
    ObjectStorageResponse,
    SchemaRegistryCreateRequest,
    SchemaRegistryResponse,
)

router = APIRouter(prefix="/v1/clusters", tags=["clusters"])

# =============================================================================
# Dependency Injection - Use Case 의존성을 변수로 선언하여 재사용
# =============================================================================

# Kafka Cluster Dependencies
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

# Schema Registry Dependencies
CreateRegistryUseCase = Depends(
    Provide[AppContainer.cluster_container.create_schema_registry_use_case]
)
ListRegistriesUseCase = Depends(
    Provide[AppContainer.cluster_container.list_schema_registries_use_case]
)
DeleteRegistryUseCase = Depends(
    Provide[AppContainer.cluster_container.delete_schema_registry_use_case]
)
TestRegistryConnectionUseCase = Depends(
    Provide[AppContainer.cluster_container.test_schema_registry_connection_use_case]
)

# Object Storage Dependencies
CreateStorageUseCase = Depends(
    Provide[AppContainer.cluster_container.create_object_storage_use_case]
)
ListStoragesUseCase = Depends(Provide[AppContainer.cluster_container.list_object_storages_use_case])
DeleteStorageUseCase = Depends(
    Provide[AppContainer.cluster_container.delete_object_storage_use_case]
)
TestStorageConnectionUseCase = Depends(
    Provide[AppContainer.cluster_container.test_object_storage_connection_use_case]
)

# Kafka Connect Dependencies
CreateConnectUseCase = Depends(
    Provide[AppContainer.cluster_container.create_kafka_connect_use_case]
)
ListConnectsUseCase = Depends(Provide[AppContainer.cluster_container.list_kafka_connects_use_case])
GetConnectUseCase = Depends(Provide[AppContainer.cluster_container.get_kafka_connect_use_case])
DeleteConnectUseCase = Depends(
    Provide[AppContainer.cluster_container.delete_kafka_connect_use_case]
)
TestConnectConnectionUseCase = Depends(
    Provide[AppContainer.cluster_container.test_kafka_connect_connection_use_case]
)


# ============================================================================
# Kafka Cluster API
# ============================================================================


@router.post("/kafka", response_model=KafkaClusterResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_kafka_cluster(
    request: KafkaClusterCreateRequest,
    use_case=CreateClusterUseCase,
) -> KafkaClusterResponse:
    """
    Kafka 클러스터 생성

    Request Body:
        - cluster_id: 클러스터 ID (고유)
        - name: 클러스터 이름
        - bootstrap_servers: 브로커 주소
        - security_protocol: 보안 프로토콜 (기본: PLAINTEXT)
        - (기타 보안 설정)
    """
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


@router.get("/kafka", response_model=list[KafkaClusterResponse])
@inject
async def list_kafka_clusters(
    active_only: bool = Query(default=True, description="활성화된 클러스터만 조회"),
    use_case=ListClustersUseCase,
) -> list[KafkaClusterResponse]:
    """
    Kafka 클러스터 목록 조회

    Query Parameters:
        - active_only: 활성화된 클러스터만 조회 (기본: true)
    """
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


@router.get("/kafka/{cluster_id}", response_model=KafkaClusterResponse)
@inject
async def get_kafka_cluster(
    cluster_id: str = Path(..., description="클러스터 ID"),
    use_case=GetClusterUseCase,
) -> KafkaClusterResponse:
    """
    Kafka 클러스터 단일 조회

    Path Parameters:
        - cluster_id: 클러스터 ID
    """
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


@router.put("/kafka/{cluster_id}", response_model=KafkaClusterResponse)
@inject
async def update_kafka_cluster(
    request: KafkaClusterUpdateRequest,
    cluster_id: str = Path(..., description="클러스터 ID"),
    use_case=UpdateClusterUseCase,
) -> KafkaClusterResponse:
    """
    Kafka 클러스터 수정

    Path Parameters:
        - cluster_id: 클러스터 ID

    Note:
        설정 변경 시 ConnectionManager 캐시가 자동으로 무효화됨
    """
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


@router.delete("/kafka/{cluster_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_kafka_cluster(
    cluster_id: str = Path(..., description="클러스터 ID"),
    use_case=DeleteClusterUseCase,
) -> None:
    """
    Kafka 클러스터 삭제 (소프트 삭제: is_active=False)

    Path Parameters:
        - cluster_id: 클러스터 ID
    """
    await use_case.execute(cluster_id)


@router.post("/kafka/{cluster_id}/test", response_model=ConnectionTestResponse)
@inject
async def test_kafka_connection(
    cluster_id: str = Path(..., description="클러스터 ID"),
    use_case=TestClusterConnectionUseCase,
) -> ConnectionTestResponse:
    """
    Kafka 연결 테스트

    Path Parameters:
        - cluster_id: 클러스터 ID

    Returns:
        연결 성공 여부, 지연시간, 브로커 수 등
    """
    result = await use_case.execute(cluster_id)

    return ConnectionTestResponse(
        success=result.success,
        message=result.message,
        latency_ms=result.latency_ms,
        metadata=result.metadata,
    )


# ============================================================================
# Schema Registry API (간략히)
# ============================================================================


@router.post(
    "/schema-registries", response_model=SchemaRegistryResponse, status_code=status.HTTP_201_CREATED
)
@inject
async def create_schema_registry(
    request: SchemaRegistryCreateRequest,
    use_case=CreateRegistryUseCase,
) -> SchemaRegistryResponse:
    """Schema Registry 생성"""
    registry = await use_case.execute(
        registry_id=request.registry_id,
        name=request.name,
        url=request.url,
        description=request.description,
        auth_username=request.auth_username,
        auth_password=request.auth_password,
        ssl_ca_location=request.ssl_ca_location,
        ssl_cert_location=request.ssl_cert_location,
        ssl_key_location=request.ssl_key_location,
        timeout=request.timeout,
    )

    return SchemaRegistryResponse(
        registry_id=registry.registry_id,
        name=registry.name,
        url=registry.url,
        description=registry.description,
        auth_username=registry.auth_username,
        ssl_ca_location=registry.ssl_ca_location,
        ssl_cert_location=registry.ssl_cert_location,
        ssl_key_location=registry.ssl_key_location,
        timeout=registry.timeout,
        is_active=registry.is_active,
        created_at=registry.created_at,
        updated_at=registry.updated_at,
    )


@router.get("/schema-registries", response_model=list[SchemaRegistryResponse])
@inject
async def list_schema_registries(
    active_only: bool = Query(default=True, description="활성화된 레지스트리만 조회"),
    use_case=ListRegistriesUseCase,
) -> list[SchemaRegistryResponse]:
    """Schema Registry 목록 조회"""
    registries = await use_case.execute(active_only=active_only)

    return [
        SchemaRegistryResponse(
            registry_id=r.registry_id,
            name=r.name,
            url=r.url,
            description=r.description,
            auth_username=r.auth_username,
            ssl_ca_location=r.ssl_ca_location,
            ssl_cert_location=r.ssl_cert_location,
            ssl_key_location=r.ssl_key_location,
            timeout=r.timeout,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in registries
    ]


@router.delete("/schema-registries/{registry_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_schema_registry(
    registry_id: str = Path(..., description="레지스트리 ID"),
    use_case=DeleteRegistryUseCase,
) -> None:
    """Schema Registry 삭제 (소프트 삭제)"""
    await use_case.execute(registry_id)


@router.post("/schema-registries/{registry_id}/test", response_model=ConnectionTestResponse)
@inject
async def test_schema_registry_connection(
    registry_id: str = Path(..., description="레지스트리 ID"),
    use_case=TestRegistryConnectionUseCase,
) -> ConnectionTestResponse:
    """Schema Registry 연결 테스트"""
    result = await use_case.execute(registry_id)

    return ConnectionTestResponse(
        success=result.success,
        message=result.message,
        latency_ms=result.latency_ms,
        metadata=result.metadata,
    )


# ============================================================================
# Object Storage API (간략히)
# ============================================================================


@router.post("/storages", response_model=ObjectStorageResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_object_storage(
    request: ObjectStorageCreateRequest,
    use_case=CreateStorageUseCase,
) -> ObjectStorageResponse:
    """Object Storage 생성"""
    storage = await use_case.execute(
        storage_id=request.storage_id,
        name=request.name,
        endpoint_url=request.endpoint_url,
        access_key=request.access_key,
        secret_key=request.secret_key,
        bucket_name=request.bucket_name,
        description=request.description,
        region=request.region,
        use_ssl=request.use_ssl,
    )

    return ObjectStorageResponse(
        storage_id=storage.storage_id,
        name=storage.name,
        endpoint_url=storage.endpoint_url,
        description=storage.description,
        access_key=storage.access_key,
        bucket_name=storage.bucket_name,
        region=storage.region,
        use_ssl=storage.use_ssl,
        is_active=storage.is_active,
        created_at=storage.created_at,
        updated_at=storage.updated_at,
    )


@router.get("/storages", response_model=list[ObjectStorageResponse])
@inject
async def list_object_storages(
    active_only: bool = Query(default=True, description="활성화된 스토리지만 조회"),
    use_case=ListStoragesUseCase,
) -> list[ObjectStorageResponse]:
    """Object Storage 목록 조회"""
    storages = await use_case.execute(active_only=active_only)

    return [
        ObjectStorageResponse(
            storage_id=s.storage_id,
            name=s.name,
            endpoint_url=s.endpoint_url,
            description=s.description,
            access_key=s.access_key,
            bucket_name=s.bucket_name,
            region=s.region,
            use_ssl=s.use_ssl,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in storages
    ]


@router.delete("/storages/{storage_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_object_storage(
    storage_id: str = Path(..., description="스토리지 ID"),
    use_case=DeleteStorageUseCase,
) -> None:
    """Object Storage 삭제 (소프트 삭제)"""
    await use_case.execute(storage_id)


@router.post("/storages/{storage_id}/test", response_model=ConnectionTestResponse)
@inject
async def test_object_storage_connection(
    storage_id: str = Path(..., description="스토리지 ID"),
    use_case=TestStorageConnectionUseCase,
) -> ConnectionTestResponse:
    """Object Storage 연결 테스트"""
    result = await use_case.execute(storage_id)

    return ConnectionTestResponse(
        success=result.success,
        message=result.message,
        latency_ms=result.latency_ms,
        metadata=result.metadata,
    )


# ============================================================================
# Kafka Connect API
# ============================================================================


@router.post(
    "/connects",
    status_code=status.HTTP_201_CREATED,
    response_model=KafkaConnectResponse,
    summary="Kafka Connect 생성",
    description="새로운 Kafka Connect를 등록합니다. Connect는 특정 Kafka 클러스터에 연결됩니다.",
    response_description="생성된 Kafka Connect 정보",
)
@inject
async def create_kafka_connect(
    request: KafkaConnectCreateRequest,
    use_case=CreateConnectUseCase,
) -> KafkaConnectResponse:
    """
    Kafka Connect 생성

    Request Body:
        - connect_id: Connect ID (고유)
        - cluster_id: 연관된 Kafka Cluster ID
        - name: Connect 이름
        - url: Connect REST API URL (예: http://localhost:8083)
        - description: 설명 (선택)
        - auth_username: 인증 사용자명 (선택)
        - auth_password: 인증 비밀번호 (선택)
    """
    connect = await use_case.execute(
        connect_id=request.connect_id,
        cluster_id=request.cluster_id,
        name=request.name,
        url=request.url,
        description=request.description,
        auth_username=request.auth_username,
        auth_password=request.auth_password,
    )

    return KafkaConnectResponse(
        connect_id=connect.connect_id,
        cluster_id=connect.cluster_id,
        name=connect.name,
        url=connect.url,
        description=connect.description,
        auth_username=connect.auth_username,
        is_active=connect.is_active,
        created_at=connect.created_at,
        updated_at=connect.updated_at,
    )


@router.get(
    "/connects",
    response_model=list[KafkaConnectResponse],
    summary="Kafka Connect 목록 조회",
    description="등록된 Kafka Connect 목록을 조회합니다. 특정 클러스터로 필터링할 수 있습니다.",
    response_description="Kafka Connect 목록",
)
@inject
async def list_kafka_connects(
    cluster_id: str | None = Query(default=None, description="필터: 클러스터 ID"),
    use_case=ListConnectsUseCase,
) -> list[KafkaConnectResponse]:
    """
    Kafka Connect 목록 조회

    Query Parameters:
        - cluster_id: 특정 Kafka 클러스터의 Connect만 조회 (선택)

    Returns:
        Kafka Connect 목록 (활성화된 것만)
    """
    connects = await use_case.execute(cluster_id=cluster_id)

    return [
        KafkaConnectResponse(
            connect_id=c.connect_id,
            cluster_id=c.cluster_id,
            name=c.name,
            url=c.url,
            description=c.description,
            auth_username=c.auth_username,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in connects
    ]


@router.get(
    "/connects/{connect_id}",
    response_model=KafkaConnectResponse,
    summary="Kafka Connect 단일 조회",
    description="ID로 특정 Kafka Connect의 상세 정보를 조회합니다.",
    response_description="Kafka Connect 상세 정보",
)
@inject
async def get_kafka_connect(
    connect_id: str = Path(..., description="Connect ID"),
    use_case=GetConnectUseCase,
) -> KafkaConnectResponse:
    """
    Kafka Connect 단일 조회

    Path Parameters:
        - connect_id: Connect ID

    Returns:
        Kafka Connect 상세 정보
    """
    connect = await use_case.execute(connect_id)

    return KafkaConnectResponse(
        connect_id=connect.connect_id,
        cluster_id=connect.cluster_id,
        name=connect.name,
        url=connect.url,
        description=connect.description,
        auth_username=connect.auth_username,
        is_active=connect.is_active,
        created_at=connect.created_at,
        updated_at=connect.updated_at,
    )


@router.delete(
    "/connects/{connect_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Kafka Connect 삭제",
    description="등록된 Kafka Connect를 삭제합니다 (소프트 삭제).",
)
@inject
async def delete_kafka_connect(
    connect_id: str = Path(..., description="Connect ID"),
    use_case=DeleteConnectUseCase,
) -> None:
    """
    Kafka Connect 삭제

    Path Parameters:
        - connect_id: Connect ID
    """
    await use_case.execute(connect_id)


@router.post(
    "/connects/{connect_id}/test",
    response_model=ConnectionTestResponse,
    summary="Kafka Connect 연결 테스트",
    description="Kafka Connect REST API에 연결하여 상태를 확인합니다. 커넥터 개수 등의 정보를 반환합니다.",
    response_description="연결 테스트 결과 (성공 여부, 지연시간, 커넥터 개수)",
)
@inject
async def test_kafka_connect_connection(
    connect_id: str = Path(..., description="Connect ID"),
    use_case=TestConnectConnectionUseCase,
) -> ConnectionTestResponse:
    """
    Kafka Connect 연결 테스트

    Path Parameters:
        - connect_id: Connect ID

    Returns:
        연결 성공 여부, 지연시간(ms), 커넥터 개수 등의 메타데이터
    """
    result = await use_case.execute(connect_id)

    return ConnectionTestResponse(
        success=result.success,
        message=result.message,
        latency_ms=result.latency_ms,
        metadata=result.metadata,
    )
