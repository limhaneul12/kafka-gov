"""Schema Policy Management API Router"""

from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.container import AppContainer
from app.schema.application.use_cases.policy_management import SchemaPolicyUseCase
from app.schema.domain.models.policy_management import SchemaPolicyStatus, SchemaPolicyType

router = APIRouter(prefix="/schemas/policies", tags=["Schema Policies"])


class PolicyCreateRequest(BaseModel):
    name: str
    description: str
    policy_type: SchemaPolicyType
    content: dict[str, Any]
    target_environment: str = "total"
    created_by: str


class PolicyStatusUpdateRequest(BaseModel):
    policy_id: str
    version: int
    status: SchemaPolicyStatus


@router.post("")
@inject
async def create_policy(
    request: PolicyCreateRequest,
    use_case: SchemaPolicyUseCase = Depends(Provide[AppContainer.schema_container.policy_use_case]),
):
    """새로운 스키마 정책 생성"""
    return await use_case.create_policy(
        name=request.name,
        description=request.description,
        policy_type=request.policy_type,
        content=request.content,
        target_environment=request.target_environment,
        created_by=request.created_by,
    )


@router.get("")
@inject
async def list_policies(
    env: str | None = None,
    policy_type: SchemaPolicyType | None = None,
    use_case: SchemaPolicyUseCase = Depends(Provide[AppContainer.schema_container.policy_use_case]),
):
    """정책 목록 조회"""
    return await use_case.list_policies(env=env, policy_type=policy_type)


@router.get("/{policy_id}")
@inject
async def get_policy_detail(
    policy_id: str,
    version: int | None = None,
    use_case: SchemaPolicyUseCase = Depends(Provide[AppContainer.schema_container.policy_use_case]),
):
    """정책 상세 조회"""
    policy = await use_case.get_policy_detail(policy_id, version)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.get("/{policy_id}/history")
@inject
async def get_policy_history(
    policy_id: str,
    use_case: SchemaPolicyUseCase = Depends(Provide[AppContainer.schema_container.policy_use_case]),
):
    """정책 이력 조회"""
    return await use_case.get_history(policy_id)


@router.patch("/status")
@inject
async def update_policy_status(
    request: PolicyStatusUpdateRequest,
    use_case: SchemaPolicyUseCase = Depends(Provide[AppContainer.schema_container.policy_use_case]),
):
    """정책 상태 업데이트 (활성화 등)"""
    if request.status == SchemaPolicyStatus.ACTIVE:
        await use_case.activate_policy(request.policy_id, request.version)
    else:
        await use_case.policy_repository.update_status(
            request.policy_id, request.version, request.status
        )
    return {"message": "Status updated successfully"}
