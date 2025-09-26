"""Policy API DTO 모델"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..domain import Environment, PolicySeverity, ResourceType


class PolicyViolationResponse(BaseModel):
    """정책 위반 응답 모델"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        str_min_length=1,
    )

    resource_type: ResourceType
    resource_name: str = Field(..., min_length=1)
    rule_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    severity: PolicySeverity
    field: str | None = None
    current_value: Any = None
    expected_value: Any = None


class PolicyEvaluationRequest(BaseModel):
    """정책 평가 요청 모델"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    environment: Environment
    resource_type: ResourceType
    targets: list[dict[str, Any]] = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    metadata: dict[str, Any] | None = None


class PolicyEvaluationResponse(BaseModel):
    """정책 평가 응답 모델"""

    model_config = ConfigDict(extra="forbid")

    environment: Environment
    resource_type: ResourceType
    total_targets: int = Field(..., ge=0)
    violations: list[PolicyViolationResponse]
    has_blocking_violations: bool
    summary: dict[str, int]  # severity별 위반 개수


class PolicyRuleResponse(BaseModel):
    """정책 규칙 응답 모델"""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    description: str
    rule_type: str  # "naming", "configuration", etc.


class PolicySetResponse(BaseModel):
    """정책 집합 응답 모델"""

    model_config = ConfigDict(extra="forbid")

    environment: Environment
    resource_type: ResourceType
    rules: list[PolicyRuleResponse]
    created_at: str | None = None
    updated_at: str | None = None


class PolicyListResponse(BaseModel):
    """정책 목록 응답 모델"""

    model_config = ConfigDict(extra="forbid")

    environments: list[Environment]
    policy_sets: list[PolicySetResponse]


class ValidationSummaryResponse(BaseModel):
    """검증 요약 응답 모델"""

    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "warning", "error"]
    total_violations: int = Field(..., ge=0)
    blocking_violations: int = Field(..., ge=0)
    warning_violations: int = Field(..., ge=0)
    can_proceed: bool  # 차단 위반이 없으면 True
