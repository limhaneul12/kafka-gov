"""Analysis REST API Router"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from app.analysis.domain.authorization import validate_action
from app.analysis.interface.schema import (
    SchemaImpactAnalysisResponse,
    StatisticsResponse,
    TopicSchemaCorrelationResponse,
)
from app.container import AppContainer
from app.shared.roles import DEFAULT_ROLE, UserRole

router = APIRouter(prefix="/v1/analysis", tags=["analysis"])

# =============================================================================
# Dependency Injection
# =============================================================================
CorrelationServiceDep = Depends(Provide[AppContainer.analysis_container.correlation_query_service])
ImpactServiceDep = Depends(Provide[AppContainer.analysis_container.impact_analysis_query_service])


@router.get(
    "/correlations",
    response_model=list[TopicSchemaCorrelationResponse],
    status_code=status.HTTP_200_OK,
    summary="모든 토픽-스키마 상관관계 조회",
    description="모든 토픽-스키마 상관관계를 조회합니다. (읽기 권한 필요)",
)
@inject
async def get_all_correlations(
    service=CorrelationServiceDep, role: UserRole = DEFAULT_ROLE
) -> list[TopicSchemaCorrelationResponse]:
    """모든 토픽-스키마 상관관계 조회"""
    try:
        # 권한 검증
        validate_action(role, "view")

        correlations = await service.get_all_correlations()

        return [
            TopicSchemaCorrelationResponse(
                correlation_id=corr.correlation_id,
                topic_name=corr.topic_name,
                key_schema_subject=corr.key_schema_subject,
                value_schema_subject=corr.value_schema_subject,
                environment=corr.environment,
                link_source=corr.link_source,
                confidence_score=corr.confidence_score,
            )
            for corr in correlations
        ]

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.get(
    "/correlations/topic/{topic_name}",
    response_model=TopicSchemaCorrelationResponse,
    status_code=status.HTTP_200_OK,
    summary="토픽의 스키마 정보 조회",
)
@inject
async def get_topic_schemas(
    topic_name: str, service=CorrelationServiceDep
) -> TopicSchemaCorrelationResponse:
    """특정 토픽의 스키마 정보 조회"""
    try:
        correlation = await service.get_topic_schemas(topic_name)

        if not correlation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic '{topic_name}' not found",
            )

        return TopicSchemaCorrelationResponse(
            correlation_id=correlation.correlation_id,
            topic_name=correlation.topic_name,
            key_schema_subject=correlation.key_schema_subject,
            value_schema_subject=correlation.value_schema_subject,
            environment=correlation.environment,
            link_source=correlation.link_source,
            confidence_score=correlation.confidence_score,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.get(
    "/correlations/schema/{subject}",
    response_model=list[TopicSchemaCorrelationResponse],
    status_code=status.HTTP_200_OK,
    summary="스키마가 사용되는 토픽 목록 조회",
)
@inject
async def get_schema_topics(
    subject: str, service=CorrelationServiceDep
) -> list[TopicSchemaCorrelationResponse]:
    """스키마가 사용되는 토픽 목록 조회"""
    try:
        correlations = await service.get_schema_topics(subject)

        return [
            TopicSchemaCorrelationResponse(
                correlation_id=corr.correlation_id,
                topic_name=corr.topic_name,
                key_schema_subject=corr.key_schema_subject,
                value_schema_subject=corr.value_schema_subject,
                environment=corr.environment,
                link_source=corr.link_source,
                confidence_score=corr.confidence_score,
            )
            for corr in correlations
        ]

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.get(
    "/impact/schema/{subject}",
    response_model=SchemaImpactAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="스키마 영향도 분석",
    description="스키마 변경/삭제 시 영향도를 분석합니다. (읽기 권한 필요)",
)
@inject
async def analyze_schema_impact(
    subject: str,
    service=ImpactServiceDep,
    strategy: str = "TopicNameStrategy",
    role: UserRole = DEFAULT_ROLE,
) -> SchemaImpactAnalysisResponse:
    """스키마 영향도 분석"""
    try:
        # 권한 검증
        validate_action(role, "view")
        analysis = await service.analyze_schema_impact(subject, strategy)

        return SchemaImpactAnalysisResponse(
            subject=analysis.subject,
            affected_topics=list(analysis.affected_topics),
            total_impact_count=analysis.total_impact_count,
            risk_level=analysis.risk_level,
            warnings=list(analysis.warnings),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.get(
    "/statistics/topics",
    status_code=status.HTTP_200_OK,
    summary="토픽 개수 조회",
    description="등록된 토픽 개수를 조회합니다.",
)
@inject
async def get_topic_count(
    service=CorrelationServiceDep,
) -> dict[str, int]:
    """토픽 개수 조회"""
    try:
        count = await service.get_topic_count()
        return {"count": count}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.get(
    "/statistics/schemas",
    status_code=status.HTTP_200_OK,
    summary="스키마 개수 조회",
    description="등록된 스키마 개수를 조회합니다.",
)
@inject
async def get_schema_count(
    service=CorrelationServiceDep,
) -> dict[str, int]:
    """스키마 개수 조회"""
    try:
        count = await service.get_schema_count()
        return {"count": count}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    status_code=status.HTTP_200_OK,
    summary="전체 통계 조회",
    description="토픽, 스키마, 상관관계 개수를 한번에 조회합니다.",
)
@inject
async def get_statistics(
    service=CorrelationServiceDep,
) -> StatisticsResponse:
    """전체 통계 조회"""
    try:
        stats = await service.get_statistics()

        return StatisticsResponse(
            topic_count=stats["topic_count"],
            schema_count=stats["schema_count"],
            correlation_count=stats["correlation_count"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc!s}",
        ) from exc
