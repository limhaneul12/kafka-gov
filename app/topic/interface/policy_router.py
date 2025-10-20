"""Policy Router - 정책 CRUD API"""

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, Query, status

from app.container import AppContainer
from app.shared.error_handlers import handle_api_errors, handle_server_errors
from app.topic.application.use_cases.policy_crud import (
    ActivatePolicyUseCase,
    ArchivePolicyUseCase,
    CreatePolicyUseCase,
    DeletePolicyUseCase,
    GetActivePolicyUseCase,
    GetPolicyUseCase,
    ListPoliciesUseCase,
    ListPolicyVersionsUseCase,
    RollbackPolicyUseCase,
    UpdatePolicyUseCase,
)
from app.topic.domain.policies.management import PolicyStatus, PolicyType
from app.topic.interface.schemas.policy import (
    ActivatePolicyRequest,
    CreatePolicyRequest,
    PolicyDeleteResponse,
    PolicyListResponse,
    PolicyResponse,
    PolicyVersionListResponse,
    RollbackPolicyRequest,
    UpdatePolicyRequest,
    to_policy_dto,
)

router = APIRouter(prefix="/v1/policies", tags=["policies"])

# Dependency Injection Shortcuts
CreatePolicyDep = Depends(Provide[AppContainer.topic_container.create_policy_use_case])
GetPolicyDep = Depends(Provide[AppContainer.topic_container.get_policy_use_case])
GetActivePolicyDep = Depends(Provide[AppContainer.topic_container.get_active_policy_use_case])
ListPoliciesDep = Depends(Provide[AppContainer.topic_container.list_policies_use_case])
ListVersionsDep = Depends(Provide[AppContainer.topic_container.list_policy_versions_use_case])
UpdatePolicyDep = Depends(Provide[AppContainer.topic_container.update_policy_use_case])
ActivatePolicyDep = Depends(Provide[AppContainer.topic_container.activate_policy_use_case])
ArchivePolicyDep = Depends(Provide[AppContainer.topic_container.archive_policy_use_case])
DeletePolicyDep = Depends(Provide[AppContainer.topic_container.delete_policy_use_case])
RollbackPolicyDep = Depends(Provide[AppContainer.topic_container.rollback_policy_use_case])


# ============================================================================
# 정책 생성
# ============================================================================


@router.post(
    "",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="정책 생성",
    description="새 정책을 생성합니다 (version=1, status=DRAFT)",
)
@inject
@handle_api_errors(validation_error_message="Policy creation validation error")
async def create_policy(
    request: CreatePolicyRequest,
    use_case: CreatePolicyUseCase = CreatePolicyDep,
) -> PolicyResponse:
    """정책 생성"""
    policy, message = await use_case.execute(
        policy_type=request.policy_type,
        name=request.name,
        description=request.description,
        content=request.content,
        created_by=request.created_by,
        target_environment=request.target_environment,
    )
    return PolicyResponse(policy=to_policy_dto(policy), message=message)


# ============================================================================
# 정책 조회
# ============================================================================


@router.get(
    "",
    response_model=PolicyListResponse,
    status_code=status.HTTP_200_OK,
    summary="정책 목록 조회",
    description="정책 목록을 조회합니다 (최신 버전만)",
)
@inject
@handle_server_errors(error_message="Failed to list policies")
async def list_policies(
    policy_type: PolicyType | None = Query(None, description="정책 타입 필터 (naming/guardrail)"),
    status_filter: PolicyStatus | None = Query(
        None, alias="status", description="상태 필터 (draft/active/archived)"
    ),
    use_case: ListPoliciesUseCase = ListPoliciesDep,
) -> PolicyListResponse:
    """정책 목록 조회"""
    policies, total = await use_case.execute(policy_type=policy_type, status=status_filter)
    return PolicyListResponse(policies=[to_policy_dto(p) for p in policies], total=total)


@router.get(
    "/active/environment",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="환경별 활성 정책 조회",
    description="특정 환경(dev/stg/prod)의 ACTIVE 정책을 조회합니다 (우선순위: env-specific > total)",
)
@inject
@handle_server_errors(error_message="Failed to get active policies by environment")
async def get_active_policies_by_environment(
    environment: str = Query(..., regex="^(dev|stg|prod)$", description="환경 (dev/stg/prod)"),
    list_use_case: ListPoliciesUseCase = ListPoliciesDep,
) -> dict:
    """환경별 ACTIVE 정책 조회

    Returns:
        {
            "environment": "prod",
            "naming_policy": {...} or null,
            "guardrail_policy": {...} or null
        }
    """

    async def get_policy_for_env(policy_type: PolicyType):
        """환경별 정책 조회 헬퍼"""
        policies, _ = await list_use_case.execute(
            policy_type=policy_type,
            status=PolicyStatus.ACTIVE,
        )

        # env-specific 우선
        for policy in policies:
            if policy.target_environment == environment:
                return to_policy_dto(policy)

        # total fallback
        for policy in policies:
            if policy.target_environment == "total":
                return to_policy_dto(policy)

        return None

    naming_policy = await get_policy_for_env(PolicyType.NAMING)
    guardrail_policy = await get_policy_for_env(PolicyType.GUARDRAIL)

    return {
        "environment": environment,
        "naming_policy": naming_policy,
        "guardrail_policy": guardrail_policy,
    }


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="정책 조회",
    description="특정 정책을 조회합니다 (version 지정 가능)",
)
@inject
@handle_server_errors(error_message="Failed to get policy")
async def get_policy(
    policy_id: Annotated[str, Path(description="정책 ID (UUID)")],
    version: int | None = Query(None, description="버전 번호 (미지정 시 최신)"),
    use_case: GetPolicyUseCase = GetPolicyDep,
) -> PolicyResponse:
    """정책 조회"""
    policy, message = await use_case.execute(policy_id=policy_id, version=version)
    return PolicyResponse(policy=to_policy_dto(policy), message=message)


@router.get(
    "/{policy_id}/active",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="활성 정책 조회",
    description="활성화된 정책을 조회합니다 (status=ACTIVE)",
)
@inject
@handle_server_errors(error_message="Failed to get active policy")
async def get_active_policy(
    policy_id: Annotated[str, Path(description="정책 ID (UUID)")],
    use_case: GetActivePolicyUseCase = GetActivePolicyDep,
) -> PolicyResponse:
    """활성 정책 조회"""
    policy, message = await use_case.execute(policy_id=policy_id)
    return PolicyResponse(policy=to_policy_dto(policy), message=message)


@router.get(
    "/{policy_id}/versions",
    response_model=PolicyVersionListResponse,
    status_code=status.HTTP_200_OK,
    summary="정책 버전 히스토리 조회",
    description="정책의 모든 버전을 조회합니다",
)
@inject
@handle_server_errors(error_message="Failed to list policy versions")
async def list_policy_versions(
    policy_id: Annotated[str, Path(description="정책 ID (UUID)")],
    use_case: ListPolicyVersionsUseCase = ListVersionsDep,
) -> PolicyVersionListResponse:
    """정책 버전 히스토리 조회"""
    policy_id_result, versions, total = await use_case.execute(policy_id=policy_id)
    return PolicyVersionListResponse(
        policy_id=policy_id_result, versions=[to_policy_dto(v) for v in versions], total=total
    )


# ============================================================================
# 정책 수정
# ============================================================================


@router.put(
    "/{policy_id}",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="정책 수정",
    description="정책을 수정합니다 (새 버전 생성, status=DRAFT)",
)
@inject
@handle_api_errors(validation_error_message="Policy update validation error")
async def update_policy(
    policy_id: Annotated[str, Path(description="정책 ID (UUID)")],
    request: UpdatePolicyRequest,
    use_case: UpdatePolicyUseCase = UpdatePolicyDep,
) -> PolicyResponse:
    """정책 수정"""
    policy, message = await use_case.execute(
        policy_id=policy_id,
        name=request.name,
        description=request.description,
        content=request.content,
        target_environment=request.target_environment,
    )
    return PolicyResponse(policy=to_policy_dto(policy), message=message)


# ============================================================================
# 정책 활성화/보관
# ============================================================================


@router.post(
    "/{policy_id}/activate",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="정책 활성화",
    description="정책을 활성화합니다 (DRAFT → ACTIVE, 기존 ACTIVE → ARCHIVED)",
)
@inject
@handle_api_errors(validation_error_message="Policy activation error")
async def activate_policy(
    policy_id: Annotated[str, Path(description="정책 ID (UUID)")],
    request: ActivatePolicyRequest,
    use_case: ActivatePolicyUseCase = ActivatePolicyDep,
) -> PolicyResponse:
    """정책 활성화"""
    policy, message = await use_case.execute(policy_id=policy_id, version=request.version)
    return PolicyResponse(policy=to_policy_dto(policy), message=message)


@router.post(
    "/{policy_id}/archive",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="정책 보관",
    description="정책을 보관합니다 (ACTIVE → ARCHIVED)",
)
@inject
@handle_server_errors(error_message="Failed to archive policy")
async def archive_policy(
    policy_id: Annotated[str, Path(description="정책 ID (UUID)")],
    use_case: ArchivePolicyUseCase = ArchivePolicyDep,
) -> PolicyResponse:
    """정책 보관"""
    policy, message = await use_case.execute(policy_id=policy_id)
    return PolicyResponse(policy=to_policy_dto(policy), message=message)


# ============================================================================
# 정책 삭제
# ============================================================================


@router.delete(
    "/{policy_id}",
    response_model=PolicyDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="정책 삭제",
    description="정책을 삭제합니다 (ACTIVE 제외, DRAFT/ARCHIVED 가능)",
)
@inject
@handle_server_errors(error_message="Failed to delete policy")
async def delete_policy(
    policy_id: Annotated[str, Path(description="정책 ID (UUID)")],
    version: int | None = Query(None, description="삭제할 버전 (미지정 시 모든 DRAFT)"),
    use_case: DeletePolicyUseCase = DeletePolicyDep,
) -> PolicyDeleteResponse:
    """정책 삭제 (ACTIVE 제외)"""
    message = await use_case.execute(policy_id=policy_id, version=version)
    return PolicyDeleteResponse(message=message)


@router.delete(
    "/{policy_id}/all",
    response_model=PolicyDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="정책 전체 삭제",
    description="정책의 모든 버전을 삭제합니다 (ACTIVE/ARCHIVED 포함)",
)
@inject
@handle_server_errors(error_message="Failed to delete all policy versions")
async def delete_all_policy_versions(
    policy_id: Annotated[str, Path(description="정책 ID (UUID)")],
    use_case: DeletePolicyUseCase = DeletePolicyDep,
) -> PolicyDeleteResponse:
    """정책 전체 삭제 (모든 버전)"""
    message = await use_case.execute_delete_all(policy_id=policy_id)
    return PolicyDeleteResponse(message=message)


# ============================================================================
# 정책 롤백
# ============================================================================


@router.post(
    "/{policy_id}/rollback",
    response_model=PolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="정책 롤백",
    description="이전 버전으로 롤백합니다 (대상 버전을 ACTIVE로 변경)",
)
@inject
@handle_api_errors(validation_error_message="Policy rollback error")
async def rollback_policy(
    policy_id: Annotated[str, Path(description="정책 ID (UUID)")],
    request: RollbackPolicyRequest,
    use_case: RollbackPolicyUseCase = RollbackPolicyDep,
) -> PolicyResponse:
    """정책 롤백"""
    policy, message = await use_case.execute(
        policy_id=policy_id,
        target_version=request.target_version,
        created_by=request.created_by,
    )
    return PolicyResponse(policy=to_policy_dto(policy), message=message)
