"""Connector State Control API Router"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, status

from app.container import AppContainer
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter()

# Use Case Dependencies
ConnectorStateControl = Depends(Provide[AppContainer.connect_container.connector_state_control])


@router.post(
    "/{connect_id}/connectors/{connector_name}/restart",
    status_code=status.HTTP_202_ACCEPTED,
    summary="커넥터 재시작",
    description="커넥터를 재시작합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to restart connector")
async def restart_connector(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=ConnectorStateControl,
) -> dict[str, str]:
    """커넥터 재시작"""
    await use_case.restart(connect_id, connector_name)
    return {"message": f"Connector '{connector_name}' restart initiated"}


@router.put(
    "/{connect_id}/connectors/{connector_name}/pause",
    status_code=status.HTTP_202_ACCEPTED,
    summary="커넥터 일시정지",
    description="커넥터를 일시정지합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to pause connector")
async def pause_connector(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=ConnectorStateControl,
) -> dict[str, str]:
    """커넥터 일시정지"""
    await use_case.pause(connect_id, connector_name)
    return {"message": f"Connector '{connector_name}' paused"}


@router.put(
    "/{connect_id}/connectors/{connector_name}/resume",
    status_code=status.HTTP_202_ACCEPTED,
    summary="커넥터 재개",
    description="일시정지된 커넥터를 재개합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to resume connector")
async def resume_connector(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=ConnectorStateControl,
) -> dict[str, str]:
    """커넥터 재개"""
    await use_case.resume(connect_id, connector_name)
    return {"message": f"Connector '{connector_name}' resumed"}
