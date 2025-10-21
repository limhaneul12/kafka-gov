"""Kafka Connect Router"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, Query, status

from app.cluster.interface.schemas import (
    ConnectionTestResponse,
    KafkaConnectCreateRequest,
    KafkaConnectResponse,
    KafkaConnectUpdateRequest,
)
from app.container import AppContainer
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter(prefix="/connects", tags=["kafka-connect"])

# Dependency Injection - Kafka Connect
CreateConnectUseCase = Depends(
    Provide[AppContainer.cluster_container.create_kafka_connect_use_case]
)
ListConnectsUseCase = Depends(Provide[AppContainer.cluster_container.list_kafka_connects_use_case])
GetConnectUseCase = Depends(Provide[AppContainer.cluster_container.get_kafka_connect_use_case])
UpdateConnectUseCase = Depends(
    Provide[AppContainer.cluster_container.update_kafka_connect_use_case]
)
DeleteConnectUseCase = Depends(
    Provide[AppContainer.cluster_container.delete_kafka_connect_use_case]
)
TestConnectConnectionUseCase = Depends(
    Provide[AppContainer.cluster_container.test_kafka_connect_connection_use_case]
)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=KafkaConnectResponse)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")},
    default_message="Failed to create Kafka Connect",
)
async def create_kafka_connect(
    request: KafkaConnectCreateRequest,
    use_case=CreateConnectUseCase,
) -> KafkaConnectResponse:
    """Kafka Connect 생성"""
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


@router.get("", response_model=list[KafkaConnectResponse])
@inject
@endpoint_error_handler(default_message="Failed to list Kafka Connects")
async def list_kafka_connects(
    cluster_id: str | None = Query(default=None, description="필터: 클러스터 ID"),
    use_case=ListConnectsUseCase,
) -> list[KafkaConnectResponse]:
    """Kafka Connect 목록 조회"""
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


@router.get("/{connect_id}", response_model=KafkaConnectResponse)
@inject
@endpoint_error_handler(default_message="Failed to get Kafka Connect")
async def get_kafka_connect(
    connect_id: str = Path(..., description="Connect ID"),
    use_case=GetConnectUseCase,
) -> KafkaConnectResponse:
    """Kafka Connect 단일 조회"""
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


@router.put("/{connect_id}", response_model=KafkaConnectResponse)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")},
    default_message="Failed to update Kafka Connect",
)
async def update_kafka_connect(
    request: KafkaConnectUpdateRequest,
    connect_id: str = Path(..., description="Connect ID"),
    use_case=UpdateConnectUseCase,
) -> KafkaConnectResponse:
    """Kafka Connect 수정"""
    connect = await use_case.execute(
        connect_id=connect_id,
        name=request.name,
        url=request.url,
        description=request.description,
        auth_username=request.auth_username,
        auth_password=request.auth_password,
        is_active=request.is_active,
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


@router.patch("/{connect_id}/activate", response_model=KafkaConnectResponse)
@inject
@endpoint_error_handler(default_message="Failed to activate Kafka Connect")
async def activate_kafka_connect(
    connect_id: str = Path(..., description="Connect ID"),
    get_use_case=GetConnectUseCase,
    update_use_case=UpdateConnectUseCase,
) -> KafkaConnectResponse:
    """Kafka Connect 활성화 (is_active를 true로 변경)"""
    # 현재 Connect 조회
    connect = await get_use_case.execute(connect_id)

    # is_active만 변경하여 업데이트
    updated_connect = await update_use_case.execute(
        connect_id=connect_id,
        name=connect.name,
        url=connect.url,
        description=connect.description,
        cluster_id=connect.cluster_id,
        is_active=True,  # 활성화
    )

    return KafkaConnectResponse(
        connect_id=updated_connect.connect_id,
        cluster_id=updated_connect.cluster_id,
        name=updated_connect.name,
        url=updated_connect.url,
        description=updated_connect.description,
        auth_username=updated_connect.auth_username,
        is_active=updated_connect.is_active,
        created_at=updated_connect.created_at,
        updated_at=updated_connect.updated_at,
    )


@router.delete("/{connect_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
@endpoint_error_handler(default_message="Failed to delete Kafka Connect")
async def delete_kafka_connect(
    connect_id: str = Path(..., description="Connect ID"),
    use_case=DeleteConnectUseCase,
) -> None:
    """Kafka Connect 삭제 (소프트 삭제)"""
    await use_case.execute(connect_id)


@router.post("/{connect_id}/test", response_model=ConnectionTestResponse)
@inject
@endpoint_error_handler(default_message="Kafka Connect connection test failed")
async def test_kafka_connect_connection(
    connect_id: str = Path(..., description="Connect ID"),
    use_case=TestConnectConnectionUseCase,
) -> ConnectionTestResponse:
    """Kafka Connect 연결 테스트"""
    result = await use_case.execute(connect_id)

    return ConnectionTestResponse(
        success=result.success,
        message=result.message,
        latency_ms=result.latency_ms,
        metadata=result.metadata,
    )
