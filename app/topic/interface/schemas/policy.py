"""Policy API Schemas - Pydantic DTOs for Interface Layer"""

from pydantic import BaseModel, ConfigDict, Field

from app.topic.domain.policies.management import PolicyStatus, PolicyType, StoredPolicy

# ============================================================================
# Request DTOs
# ============================================================================


class CreatePolicyRequest(BaseModel):
    """정책 생성 요청"""

    model_config = ConfigDict(extra="forbid")

    policy_type: PolicyType
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", description="정책 설명 (선택사항)")
    content: dict = Field(..., description="CustomNamingRules 또는 CustomGuardrailPreset의 dict")
    created_by: str = Field(..., min_length=1, max_length=255)
    target_environment: str = Field(default="total", description="적용 환경 (dev/stg/prod/total)")


class UpdatePolicyRequest(BaseModel):
    """정책 수정 요청 (새 버전 생성)"""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, description="정책 설명 (선택사항)")
    content: dict | None = None
    target_environment: str | None = Field(None, description="적용 환경 (dev/stg/prod/total)")


class ActivatePolicyRequest(BaseModel):
    """정책 활성화 요청"""

    model_config = ConfigDict(extra="forbid")

    version: int | None = Field(None, description="활성화할 버전 (미지정 시 최신 DRAFT)")


class RollbackPolicyRequest(BaseModel):
    """정책 롤백 요청"""

    model_config = ConfigDict(extra="forbid")

    target_version: int = Field(..., gt=0, description="롤백할 대상 버전")
    created_by: str = Field(
        default="system", min_length=1, max_length=255, description="롤백 실행자"
    )


# ============================================================================
# Response DTOs
# ============================================================================


class PolicyDTO(BaseModel):
    """정책 DTO - IO 경계용 Pydantic 모델"""

    model_config = ConfigDict(extra="forbid")

    policy_id: str
    policy_type: PolicyType
    name: str
    description: str
    version: int
    status: PolicyStatus
    content: dict[str, str | int | bool | list[str]]
    created_by: str
    created_at: str
    target_environment: str = "total"
    updated_at: str | None = None
    activated_at: str | None = None


class PolicyResponse(BaseModel):
    """정책 응답"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "policy": {
                    "policy_id": "550e8400-e29b-41d4-a716-446655440000",
                    "version": 1,
                    "policy_type": "naming",
                    "name": "Production Naming",
                    "description": "Strict naming for production",
                    "status": "active",
                    "content": {"pattern": "^prod\\..*"},
                    "created_by": "admin@example.com",
                    "created_at": "2024-01-01T00:00:00",
                },
                "message": "Policy retrieved successfully",
            }
        },
    )

    policy: PolicyDTO
    message: str


class PolicyListResponse(BaseModel):
    """정책 목록 응답"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "policies": [
                    {
                        "policy_id": "550e8400-e29b-41d4-a716-446655440000",
                        "version": 2,
                        "policy_type": "naming",
                        "name": "Production Naming",
                        "status": "active",
                    }
                ],
                "total": 1,
            }
        },
    )

    policies: list[PolicyDTO]
    total: int


class PolicyVersionListResponse(BaseModel):
    """정책 버전 히스토리 응답"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "policy_id": "550e8400-e29b-41d4-a716-446655440000",
                "versions": [
                    {"version": 2, "status": "active"},
                    {"version": 1, "status": "archived"},
                ],
                "total": 2,
            }
        },
    )

    policy_id: str
    versions: list[PolicyDTO]
    total: int


class PolicyDeleteResponse(BaseModel):
    """정책 삭제 응답"""

    model_config = ConfigDict(extra="forbid")

    message: str


# ============================================================================
# Mappers - Domain to DTO
# ============================================================================


def to_policy_dto(policy: StoredPolicy) -> PolicyDTO:
    """도메인 모델(StoredPolicy)을 DTO(PolicyDTO)로 변환

    Args:
        policy: 도메인 정책 모델 (dataclass)

    Returns:
        PolicyDTO: IO 경계용 Pydantic 모델

    Note:
        dataclass는 Pydantic과 자연스럽게 호환되므로 직접 변환
    """
    return PolicyDTO(
        policy_id=policy.policy_id,
        policy_type=policy.policy_type,
        name=policy.name,
        description=policy.description,
        version=policy.version,
        status=policy.status,
        content=policy.content,
        created_by=policy.created_by,
        created_at=policy.created_at,
        target_environment=policy.target_environment,
        updated_at=policy.updated_at,
        activated_at=policy.activated_at,
    )
