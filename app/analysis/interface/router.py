"""Analysis REST API Router"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.container import get_correlation_query_service, get_impact_analysis_service
from app.analysis.domain.authorization import validate_action
from app.analysis.interface.schema import (
    SchemaImpactAnalysisResponse,
    TopicSchemaCorrelationResponse,
)
from app.shared.database import get_db_session
from app.shared.roles import DEFAULT_ROLE, UserRole

router = APIRouter(prefix="/v1/analysis", tags=["analysis"])


@router.get(
    "/correlations",
    response_model=list[TopicSchemaCorrelationResponse],
    status_code=status.HTTP_200_OK,
    summary="모든 토픽-스키마 상관관계 조회",
    description="모든 토픽-스키마 상관관계를 조회합니다. (읽기 권한 필요)",
)
async def get_all_correlations(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    role: UserRole = DEFAULT_ROLE,
) -> list[TopicSchemaCorrelationResponse]:
    """모든 토픽-스키마 상관관계 조회"""
    try:
        # 권한 검증
        validate_action(role, "view")

        service = get_correlation_query_service(session)
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
async def get_topic_schemas(
    topic_name: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TopicSchemaCorrelationResponse:
    """특정 토픽의 스키마 정보 조회"""
    try:
        service = get_correlation_query_service(session)
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
async def get_schema_topics(
    subject: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[TopicSchemaCorrelationResponse]:
    """특정 스키마가 사용되는 토픽 목록 조회"""
    try:
        service = get_correlation_query_service(session)
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
async def analyze_schema_impact(
    subject: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    strategy: str = "TopicNameStrategy",
    role: UserRole = DEFAULT_ROLE,
) -> SchemaImpactAnalysisResponse:
    """스키마 변경/삭제 시 영향도 분석"""
    try:
        # 권한 검증
        validate_action(role, "analyze")

        service = get_impact_analysis_service(session)
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
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Analysis 모듈 헬스체크",
)
async def health_check() -> ORJSONResponse:
    """헬스체크"""
    return ORJSONResponse(
        content={
            "status": "healthy",
            "module": "analysis",
            "version": "1.0.0",
        }
    )
