"""Connector CRUD API Router"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.connect.domain.types import (
    ConnectorConfig,
    ConnectorConfigResponse,
    ConnectorListResponse,
    ConnectorResponse,
    ConnectorStatusResponse,
)
from app.container import AppContainer
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter()

# Use Case Dependencies
ListConnectorsUseCase = Depends(Provide[AppContainer.connect_container.list_connectors_use_case])
ConnectorOperations = Depends(Provide[AppContainer.connect_container.connector_operations])


@router.get(
    "/{connect_id}/connectors",
    summary="커넥터 목록 조회",
    description="Kafka Connect의 등록된 커넥터 목록을 조회합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to list connectors")
async def list_connectors(
    connect_id: str = Path(..., description="Connect ID"),
    expand: list[str] | None = Query(None, description="확장 정보 (status, info)"),
    use_case=ListConnectorsUseCase,
) -> ConnectorListResponse:
    """커넥터 목록 조회

    Query Parameters:
        - expand: status, info 등을 포함하여 상세 정보 조회

    Example:
        GET /v1/connect/{connect_id}/connectors
        GET /v1/connect/{connect_id}/connectors?expand=status&expand=info
    """
    return await use_case.execute(connect_id, expand=expand)


@router.get(
    "/{connect_id}/connectors/{connector_name}",
    summary="커넥터 상세 조회",
    description="특정 커넥터의 상세 정보를 조회합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to get connector")
async def get_connector(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=ConnectorOperations,
) -> ConnectorResponse:
    """커넥터 상세 조회"""
    return await use_case.get(connect_id, connector_name)


@router.get(
    "/{connect_id}/connectors/{connector_name}/config",
    summary="커넥터 설정 조회",
    description="커넥터의 현재 설정을 조회합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to get connector config")
async def get_connector_config(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=ConnectorOperations,
) -> ConnectorConfigResponse:
    """커넥터 설정 조회"""
    return await use_case.get_config(connect_id, connector_name)


@router.get(
    "/{connect_id}/connectors/{connector_name}/status",
    summary="커넥터 상태 조회",
    description="커넥터와 태스크의 현재 상태를 조회합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to get connector status")
async def get_connector_status(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=ConnectorOperations,
) -> ConnectorStatusResponse:
    """커넥터 상태 조회"""
    return await use_case.get_status(connect_id, connector_name)


@router.post(
    "/{connect_id}/connectors",
    status_code=status.HTTP_201_CREATED,
    summary="커넥터 생성",
    description="새로운 커넥터를 생성합니다.",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")},
    default_message="Failed to create connector",
)
async def create_connector(
    connect_id: str = Path(..., description="Connect ID"),
    config: ConnectorConfig = Body(..., description="커넥터 설정 (name, config 포함)"),
    use_case=ConnectorOperations,
) -> ConnectorResponse:
    """커넥터 생성

    Request Body:
    ```json
    {
        "name": "my-connector",
        "config": {
            "connector.class": "io.debezium.connector.mysql.MySqlConnector",
            "tasks.max": "1",
            "database.hostname": "localhost",
            "database.port": "3306"
        }
    }
    ```
    """
    return await use_case.create(connect_id, config)


@router.put(
    "/{connect_id}/connectors/{connector_name}/config",
    summary="커넥터 설정 수정",
    description="커넥터의 설정을 수정합니다.",
)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")},
    default_message="Failed to update connector config",
)
async def update_connector_config(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    config: ConnectorConfig = Body(..., description="새로운 설정"),
    use_case=ConnectorOperations,
) -> ConnectorResponse:
    """커넥터 설정 수정"""
    return await use_case.update_config(connect_id, connector_name, config)


@router.delete(
    "/{connect_id}/connectors/{connector_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="커넥터 삭제",
    description="커넥터를 삭제합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to delete connector")
async def delete_connector(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=ConnectorOperations,
) -> None:
    """커넥터 삭제"""
    await use_case.delete(connect_id, connector_name)
