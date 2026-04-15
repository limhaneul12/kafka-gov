"""Schema Registry router."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, Query, status

from app.container import AppContainer
from app.registry_connections.interface.schemas import (
    ConnectionTestResponse,
    SchemaRegistryCreateRequest,
    SchemaRegistryResponse,
    SchemaRegistryUpdateRequest,
)
from app.shared.error_handlers import endpoint_error_handler

router = APIRouter(prefix="/schema-registries", tags=["schema-registries"])

CreateRegistryUseCase = Depends(
    Provide[AppContainer.registry_container.create_schema_registry_use_case]
)
ListRegistriesUseCase = Depends(
    Provide[AppContainer.registry_container.list_schema_registries_use_case]
)
GetRegistryUseCase = Depends(Provide[AppContainer.registry_container.get_schema_registry_use_case])
UpdateRegistryUseCase = Depends(
    Provide[AppContainer.registry_container.update_schema_registry_use_case]
)
DeleteRegistryUseCase = Depends(
    Provide[AppContainer.registry_container.delete_schema_registry_use_case]
)
TestRegistryConnectionUseCase = Depends(
    Provide[AppContainer.registry_container.test_schema_registry_connection_use_case]
)


@router.post("", response_model=SchemaRegistryResponse, status_code=status.HTTP_201_CREATED)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")},
    default_message="Failed to create Schema Registry",
)
async def create_schema_registry(
    request: SchemaRegistryCreateRequest,
    use_case=CreateRegistryUseCase,
) -> SchemaRegistryResponse:
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


@router.get("", response_model=list[SchemaRegistryResponse])
@inject
@endpoint_error_handler(default_message="Failed to list Schema Registries")
async def list_schema_registries(
    active_only: bool = Query(default=True, description="활성화된 레지스트리만 조회"),
    use_case=ListRegistriesUseCase,
) -> list[SchemaRegistryResponse]:
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


@router.get("/{registry_id}", response_model=SchemaRegistryResponse)
@inject
@endpoint_error_handler(default_message="Failed to get Schema Registry")
async def get_schema_registry(
    registry_id: str = Path(..., description="레지스트리 ID"),
    use_case=GetRegistryUseCase,
) -> SchemaRegistryResponse:
    registry = await use_case.execute(registry_id)
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


@router.put("/{registry_id}", response_model=SchemaRegistryResponse)
@inject
@endpoint_error_handler(
    error_mappings={ValueError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation error")},
    default_message="Failed to update Schema Registry",
)
async def update_schema_registry(
    request: SchemaRegistryUpdateRequest,
    registry_id: str = Path(..., description="레지스트리 ID"),
    use_case=UpdateRegistryUseCase,
) -> SchemaRegistryResponse:
    registry = await use_case.execute(
        registry_id=registry_id,
        name=request.name,
        url=request.url,
        description=request.description,
        auth_username=request.auth_username,
        auth_password=request.auth_password,
        ssl_ca_location=request.ssl_ca_location,
        ssl_cert_location=request.ssl_cert_location,
        ssl_key_location=request.ssl_key_location,
        timeout=request.timeout,
        is_active=request.is_active,
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


@router.patch("/{registry_id}/activate", response_model=SchemaRegistryResponse)
@inject
@endpoint_error_handler(default_message="Failed to activate Schema Registry")
async def activate_schema_registry(
    registry_id: str = Path(..., description="레지스트리 ID"),
    get_use_case=GetRegistryUseCase,
    update_use_case=UpdateRegistryUseCase,
) -> SchemaRegistryResponse:
    registry = await get_use_case.execute(registry_id)
    updated_registry = await update_use_case.execute(
        registry_id=registry_id,
        name=registry.name,
        url=registry.url,
        description=registry.description,
        auth_username=registry.auth_username,
        auth_password=None,
        ssl_ca_location=registry.ssl_ca_location,
        ssl_cert_location=registry.ssl_cert_location,
        ssl_key_location=registry.ssl_key_location,
        timeout=registry.timeout,
        is_active=True,
    )

    return SchemaRegistryResponse(
        registry_id=updated_registry.registry_id,
        name=updated_registry.name,
        url=updated_registry.url,
        description=updated_registry.description,
        auth_username=updated_registry.auth_username,
        ssl_ca_location=updated_registry.ssl_ca_location,
        ssl_cert_location=updated_registry.ssl_cert_location,
        ssl_key_location=updated_registry.ssl_key_location,
        timeout=updated_registry.timeout,
        is_active=updated_registry.is_active,
        created_at=updated_registry.created_at,
        updated_at=updated_registry.updated_at,
    )


@router.delete("/{registry_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
@endpoint_error_handler(default_message="Failed to delete Schema Registry")
async def delete_schema_registry(
    registry_id: str = Path(..., description="레지스트리 ID"),
    use_case=DeleteRegistryUseCase,
) -> None:
    await use_case.execute(registry_id)


@router.post("/{registry_id}/test", response_model=ConnectionTestResponse)
@inject
@endpoint_error_handler(default_message="Schema Registry connection test failed")
async def test_schema_registry_connection(
    registry_id: str = Path(..., description="레지스트리 ID"),
    use_case=TestRegistryConnectionUseCase,
) -> ConnectionTestResponse:
    result = await use_case.execute(registry_id)
    return ConnectionTestResponse(
        success=result.success,
        message=result.message,
        latency_ms=result.latency_ms,
        metadata=result.metadata,
    )
