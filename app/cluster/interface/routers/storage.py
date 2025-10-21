"""Object Storage Router"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, Query, status

from app.cluster.interface.schemas import (
    ConnectionTestResponse,
    ObjectStorageCreateRequest,
    ObjectStorageResponse,
    ObjectStorageUpdateRequest,
)
from app.container import AppContainer
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter(prefix="/storages", tags=["object-storages"])

# Dependency Injection
CreateStorageUseCase = Depends(
    Provide[AppContainer.cluster_container.create_object_storage_use_case]
)
ListStoragesUseCase = Depends(Provide[AppContainer.cluster_container.list_object_storages_use_case])
GetStorageUseCase = Depends(Provide[AppContainer.cluster_container.get_object_storage_use_case])
UpdateStorageUseCase = Depends(
    Provide[AppContainer.cluster_container.update_object_storage_use_case]
)
DeleteStorageUseCase = Depends(
    Provide[AppContainer.cluster_container.delete_object_storage_use_case]
)
TestStorageConnectionUseCase = Depends(
    Provide[AppContainer.cluster_container.test_object_storage_connection_use_case]
)


@router.post("", response_model=ObjectStorageResponse, status_code=status.HTTP_201_CREATED)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")},
    default_message="Failed to create Object Storage",
)
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


@router.get("", response_model=list[ObjectStorageResponse])
@inject
@endpoint_error_handler(default_message="Failed to list Object Storages")
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


@router.put("/{storage_id}", response_model=ObjectStorageResponse)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")},
    default_message="Failed to update Object Storage",
)
async def update_object_storage(
    request: ObjectStorageUpdateRequest,
    storage_id: str = Path(..., description="스토리지 ID"),
    use_case=UpdateStorageUseCase,
) -> ObjectStorageResponse:
    """Object Storage 수정"""
    storage = await use_case.execute(
        storage_id=storage_id,
        name=request.name,
        endpoint_url=request.endpoint_url,
        access_key=request.access_key,
        secret_key=request.secret_key,
        bucket_name=request.bucket_name,
        description=request.description,
        region=request.region,
        use_ssl=request.use_ssl,
        is_active=request.is_active,
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


@router.patch("/{storage_id}/activate", response_model=ObjectStorageResponse)
@inject
@endpoint_error_handler(default_message="Failed to activate Object Storage")
async def activate_object_storage(
    storage_id: str = Path(..., description="스토리지 ID"),
    get_use_case=GetStorageUseCase,
    update_use_case=UpdateStorageUseCase,
) -> ObjectStorageResponse:
    """Object Storage 활성화 (is_active를 true로 변경)"""
    # 현재 스토리지 조회
    storage = await get_use_case.execute(storage_id)

    # is_active만 변경하여 업데이트
    updated_storage = await update_use_case.execute(
        storage_id=storage_id,
        name=storage.name,
        endpoint_url=storage.endpoint_url,
        description=storage.description,
        access_key=storage.access_key,
        secret_key=storage.secret_key,  # 기존 값 유지 (도메인 엔티티에 저장되어 있음)
        bucket_name=storage.bucket_name,
        region=storage.region,
        use_ssl=storage.use_ssl,
        is_active=True,  # 활성화
    )

    return ObjectStorageResponse(
        storage_id=updated_storage.storage_id,
        name=updated_storage.name,
        endpoint_url=updated_storage.endpoint_url,
        description=updated_storage.description,
        access_key=updated_storage.access_key,
        bucket_name=updated_storage.bucket_name,
        region=updated_storage.region,
        use_ssl=updated_storage.use_ssl,
        is_active=updated_storage.is_active,
        created_at=updated_storage.created_at,
        updated_at=updated_storage.updated_at,
    )


@router.delete("/{storage_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
@endpoint_error_handler(default_message="Failed to delete Object Storage")
async def delete_object_storage(
    storage_id: str = Path(..., description="스토리지 ID"),
    use_case=DeleteStorageUseCase,
) -> None:
    """Object Storage 삭제 (소프트 삭제)"""
    await use_case.execute(storage_id)


@router.post("/{storage_id}/test", response_model=ConnectionTestResponse)
@inject
@endpoint_error_handler(default_message="Object Storage connection test failed")
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
