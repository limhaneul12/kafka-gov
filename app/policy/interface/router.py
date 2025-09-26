"""Policy REST API 라우터"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ...shared.auth import get_current_user
from ..application.performance_utils import optimize_violation_memory_usage
from ..container import policy_use_case_factory
from ..domain import Environment, PolicySeverity, ResourceType
from .dto import (
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
    PolicyListResponse,
    PolicyRuleResponse,
    PolicySetResponse,
    PolicyViolationResponse,
    ValidationSummaryResponse,
)

router = APIRouter(prefix="/v1/policies", tags=["policies"])


@router.post(
    "/evaluate",
    response_model=PolicyEvaluationResponse,
    summary="정책 평가",
    description="주어진 대상들에 대해 정책을 평가하고 위반 사항을 반환합니다.",
)
async def evaluate_policies(
    request: PolicyEvaluationRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> PolicyEvaluationResponse:
    """정책 평가 API"""
    try:
        service = policy_use_case_factory.get_policy_evaluation_service()

        violations = await service.evaluate_batch(
            environment=request.environment,
            resource_type=request.resource_type,
            targets=request.targets,
            actor=current_user.get("sub", "unknown"),
            metadata=request.metadata,
        )

        # 위반 사항 메모리 최적화 및 DTO로 변환
        optimized_violations = optimize_violation_memory_usage(violations)
        violation_responses = [
            PolicyViolationResponse(
                resource_type=v.resource_type,
                resource_name=v.resource_name,
                rule_id=v.rule_id,
                message=v.message,
                severity=v.severity,
                field=v.field,
                current_value=v.current_value,
                expected_value=v.expected_value,
            )
            for v in optimized_violations
        ]

        # 심각도별 요약
        severity_groups = service.group_violations_by_severity(violations)
        summary = {severity: len(group) for severity, group in severity_groups.items()}

        return PolicyEvaluationResponse(
            environment=request.environment,
            resource_type=request.resource_type,
            total_targets=len(request.targets),
            violations=violation_responses,
            has_blocking_violations=service.has_blocking_violations(violations),
            summary=summary,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy evaluation failed: {e!s}",
        ) from e


@router.get(
    "/validation-summary/{environment}/{resource_type}",
    response_model=ValidationSummaryResponse,
    summary="검증 요약",
    description="특정 환경과 리소스 타입에 대한 정책 검증 요약을 반환합니다.",
)
async def get_validation_summary(
    environment: Environment,
    resource_type: ResourceType,
    targets: list[dict[str, Any]],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> ValidationSummaryResponse:
    """검증 요약 API"""
    try:
        service = policy_use_case_factory.get_policy_evaluation_service()

        violations = await service.evaluate_batch(
            environment=environment,
            resource_type=resource_type,
            targets=targets,
            actor=current_user.get("sub", "unknown"),
        )

        blocking_count = sum(
            1 for v in violations if v.severity in (PolicySeverity.ERROR, PolicySeverity.CRITICAL)
        )
        warning_count = sum(1 for v in violations if v.severity == PolicySeverity.WARNING)

        can_proceed = blocking_count == 0

        if blocking_count > 0:
            status_value = "error"
        elif warning_count > 0:
            status_value = "warning"
        else:
            status_value = "success"

        return ValidationSummaryResponse(
            status=status_value,
            total_violations=len(violations),
            blocking_violations=blocking_count,
            warning_violations=warning_count,
            can_proceed=can_proceed,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation summary failed: {e!s}",
        ) from e


@router.get(
    "/",
    response_model=PolicyListResponse,
    summary="정책 목록 조회",
    description="등록된 모든 정책 집합을 조회합니다.",
)
async def list_policies(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> PolicyListResponse:
    """정책 목록 조회 API"""
    try:
        engine = policy_use_case_factory.get_policy_engine()

        environments = engine.list_environments()
        policy_sets = []

        for env in environments:
            resource_types = engine.list_resource_types(env)
            for rt in resource_types:
                policy_set = engine.get_policy_set(env, rt)
                if policy_set:
                    rules = [
                        PolicyRuleResponse(
                            rule_id=rule.rule_id,
                            description=rule.description,
                            rule_type=rule.__class__.__name__.replace("Rule", "").lower(),
                        )
                        for rule in policy_set.rules
                    ]

                    policy_sets.append(
                        PolicySetResponse(
                            environment=env,
                            resource_type=rt,
                            rules=rules,
                        )
                    )

        return PolicyListResponse(
            environments=environments,
            policy_sets=policy_sets,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list policies: {e!s}",
        ) from e


@router.get(
    "/{environment}/{resource_type}",
    response_model=PolicySetResponse,
    summary="특정 정책 집합 조회",
    description="특정 환경과 리소스 타입의 정책 집합을 조회합니다.",
)
async def get_policy_set(
    environment: Environment,
    resource_type: ResourceType,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> PolicySetResponse:
    """특정 정책 집합 조회 API"""
    try:
        engine = policy_use_case_factory.get_policy_engine()
        policy_set = engine.get_policy_set(environment, resource_type)

        if not policy_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy set not found for {environment.value}/{resource_type.value}",
            )

        rules = [
            PolicyRuleResponse(
                rule_id=rule.rule_id,
                description=rule.description,
                rule_type=rule.__class__.__name__.replace("Rule", "").lower(),
            )
            for rule in policy_set.rules
        ]

        return PolicySetResponse(
            environment=environment,
            resource_type=resource_type,
            rules=rules,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get policy set: {e!s}",
        ) from e


@router.post(
    "/initialize",
    summary="기본 정책 초기화",
    description="시스템 기본 정책을 초기화합니다.",
)
async def initialize_default_policies(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> JSONResponse:
    """기본 정책 초기화 API"""
    try:
        # 관리자 권한 확인 (실제 구현에서는 RBAC 체크)
        user_role = current_user.get("role", "viewer")
        if user_role not in ("admin", "approver"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or approver role required",
            )

        await policy_use_case_factory.initialize_default_policies()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Default policies initialized successfully"},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize policies: {e!s}",
        ) from e
