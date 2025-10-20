"""Plugin Management API Router"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends, Path

from app.connect.domain.types import PluginConfig, ValidationResponse
from app.container import AppContainer
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter()

# Use Case Dependencies
PluginOperations = Depends(Provide[AppContainer.connect_container.plugin_operations])


@router.get(
    "/{connect_id}/connector-plugins",
    summary="플러그인 목록 조회",
    description="Kafka Connect에 설치된 커넥터 플러그인 목록을 조회합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to list connector plugins")
async def list_connector_plugins(
    connect_id: str = Path(..., description="Connect ID"),
    use_case=PluginOperations,
) -> dict:
    """플러그인 목록 조회"""
    plugins = await use_case.list_plugins(connect_id)
    return {"plugins": plugins}


@router.put(
    "/{connect_id}/connector-plugins/{plugin_class}/config/validate",
    summary="커넥터 설정 검증",
    description="커넥터 설정이 유효한지 검증합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to validate connector config")
async def validate_connector_config(
    connect_id: str = Path(..., description="Connect ID"),
    plugin_class: str = Path(..., description="플러그인 클래스 이름"),
    config: PluginConfig = Body(..., description="검증할 설정"),
    use_case=PluginOperations,
) -> ValidationResponse:
    """커넥터 설정 검증

    Example:
    ```json
    {
        "connector.class": "org.apache.kafka.connect.file.FileStreamSinkConnector",
        "tasks.max": "1",
        "topics": "test-topic"
    }
    ```
    """
    return await use_case.validate_config(connect_id, plugin_class, config)
