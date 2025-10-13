"""Topic Management API Router"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, status

from app.connect.domain.types import TopicsResponse
from app.container import AppContainer
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter()

# Use Case Dependencies
TopicOperations = Depends(Provide[AppContainer.connect_container.topic_operations])


@router.get(
    "/{connect_id}/connectors/{connector_name}/topics",
    summary="커넥터 토픽 조회",
    description="커넥터가 사용하는 토픽을 조회합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to get connector topics")
async def get_connector_topics(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=TopicOperations,
) -> TopicsResponse:
    """커넥터 토픽 조회"""
    return await use_case.get_topics(connect_id, connector_name)


@router.put(
    "/{connect_id}/connectors/{connector_name}/topics/reset",
    status_code=status.HTTP_202_ACCEPTED,
    summary="커넥터 토픽 리셋",
    description="커넥터의 토픽을 리셋합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to reset connector topics")
async def reset_connector_topics(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=TopicOperations,
) -> dict[str, str]:
    """커넥터 토픽 리셋"""
    await use_case.reset_topics(connect_id, connector_name)
    return {"message": f"Topics of connector '{connector_name}' reset"}
