"""Metadata Management API Router (거버넌스)"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from typing_extensions import TypedDict

from app.container import AppContainer
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter()

# Use Case Dependencies
GetConnectorMetadataUseCase = Depends(
    Provide[AppContainer.connect_container.get_connector_metadata_use_case]
)
UpdateConnectorMetadataUseCase = Depends(
    Provide[AppContainer.connect_container.update_connector_metadata_use_case]
)
DeleteConnectorMetadataUseCase = Depends(
    Provide[AppContainer.connect_container.delete_connector_metadata_use_case]
)
ListConnectorsByTeamUseCase = Depends(
    Provide[AppContainer.connect_container.list_connectors_by_team_use_case]
)


class MetadataResponse(TypedDict, total=False):
    """메타데이터 API 응답 타입"""

    id: str
    connector_name: str
    team: str | None
    tags: list[str]
    description: str | None
    owner: str | None
    created_at: str | None
    updated_at: str | None


@router.get(
    "/{connect_id}/connectors/{connector_name}/metadata",
    summary="커넥터 메타데이터 조회",
    description="커넥터의 거버넌스 메타데이터(팀, 태그, 설명 등)를 조회합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to get connector metadata")
async def get_connector_metadata(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=GetConnectorMetadataUseCase,
) -> MetadataResponse | None:
    """커넥터 메타데이터 조회"""
    metadata = await use_case.execute(connect_id, connector_name)
    if not metadata:
        return None

    return {
        "id": metadata.id,
        "connector_name": metadata.connector_name,
        "team": metadata.team,
        "tags": list(metadata.tags) if metadata.tags else [],
        "description": metadata.description,
        "owner": metadata.owner,
        "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
        "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else None,
    }


@router.patch(
    "/{connect_id}/connectors/{connector_name}/metadata",
    summary="커넥터 메타데이터 업데이트",
    description="커넥터의 거버넌스 메타데이터를 업데이트합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to update connector metadata")
async def update_connector_metadata(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    team: str | None = Body(None, description="소유 팀"),
    tags: list[str] | None = Body(None, description="태그 목록"),
    description: str | None = Body(None, description="커넥터 설명"),
    owner: str | None = Body(None, description="담당자"),
    use_case=UpdateConnectorMetadataUseCase,
) -> MetadataResponse:
    """커넥터 메타데이터 업데이트

    Request Body:
    ```json
    {
        "team": "data-platform",
        "tags": ["production", "critical", "pii"],
        "description": "User synchronization connector",
        "owner": "admin@example.com"
    }
    ```
    """
    metadata = await use_case.execute(
        connect_id=connect_id,
        connector_name=connector_name,
        team=team,
        tags=tags,
        description=description,
        owner=owner,
    )

    return {
        "id": metadata.id,
        "connector_name": metadata.connector_name,
        "team": metadata.team,
        "tags": list(metadata.tags) if metadata.tags else [],
        "description": metadata.description,
        "owner": metadata.owner,
        "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
        "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else None,
    }


@router.delete(
    "/{connect_id}/connectors/{connector_name}/metadata",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="커넥터 메타데이터 삭제",
    description="커넥터의 메타데이터를 삭제합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to delete connector metadata")
async def delete_connector_metadata(
    connect_id: str = Path(..., description="Connect ID"),
    connector_name: str = Path(..., description="커넥터 이름"),
    use_case=DeleteConnectorMetadataUseCase,
) -> None:
    """커넥터 메타데이터 삭제"""
    deleted = await use_case.execute(connect_id, connector_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Metadata not found")


@router.get(
    "/{connect_id}/metadata/by-team/{team}",
    summary="팀별 커넥터 목록 조회",
    description="특정 팀이 소유한 커넥터 메타데이터 목록을 조회합니다.",
)
@inject
@endpoint_error_handler(default_message="Failed to list connectors by team")
async def list_connectors_by_team(
    connect_id: str = Path(..., description="Connect ID"),
    team: str = Path(..., description="팀 이름"),
    use_case=ListConnectorsByTeamUseCase,
) -> list[MetadataResponse]:
    """팀별 커넥터 목록 조회"""
    metadata_list = await use_case.execute(connect_id, team)

    return [
        {
            "id": meta.id,
            "connector_name": meta.connector_name,
            "team": meta.team,
            "tags": list(meta.tags) if meta.tags else [],
            "description": meta.description,
            "owner": meta.owner,
            "created_at": meta.created_at.isoformat() if meta.created_at else None,
            "updated_at": meta.updated_at.isoformat() if meta.updated_at else None,
        }
        for meta in metadata_list
    ]
