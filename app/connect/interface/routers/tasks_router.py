"""Task Management API Router"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, status

from app.connect.domain.types import TaskListResponse, TaskStatusResponse
from app.container import AppContainer
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter()

# Use Case Dependencies
TaskOperations = Depends(Provide[AppContainer.connect_container.task_operations])


@router.get(
    "/{connect_id}/connectors/{connector_name}/tasks",
    summary="태스크 목록 조회",
    description="커넥터의 태스크 목록을 조회합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to get connector tasks")
async def get_connector_tasks(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=TaskOperations,
) -> TaskListResponse:
    """태스크 목록 조회"""
    return await use_case.get_tasks(connect_id, connector_name)


@router.get(
    "/{connect_id}/connectors/{connector_name}/tasks/{task_id}/status",
    summary="태스크 상태 조회",
    description="특정 태스크의 상태를 조회합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to get task status")
async def get_task_status(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    task_id: int = Path(..., description="태스크 ID"),
    use_case=TaskOperations,
) -> TaskStatusResponse:
    """태스크 상태 조회"""
    return await use_case.get_status(connect_id, connector_name, task_id)


@router.post(
    "/{connect_id}/connectors/{connector_name}/tasks/{task_id}/restart",
    status_code=status.HTTP_202_ACCEPTED,
    summary="태스크 재시작",
    description="특정 태스크를 재시작합니다 (Connector RUNNING + Task FAILED 시 사용).",
)
@inject
@endpoint_error_handler(default_message="Failed to restart task")
async def restart_task(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    task_id: int = Path(..., description="태스크 ID"),
    use_case=TaskOperations,
) -> dict[str, str]:
    """태스크 재시작"""
    await use_case.restart(connect_id, connector_name, task_id)
    return {"message": f"Task {task_id} of connector '{connector_name}' restarted"}
