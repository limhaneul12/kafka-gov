"""Analysis Application Queries"""

from __future__ import annotations

import logging

from sqlalchemy import func, select

from ...schema.infrastructure.models import SchemaMetadataModel
from ...topic.infrastructure.models import TopicMetadataModel
from ..domain.models import SchemaImpactAnalysis, SubjectName, TopicName, TopicSchemaCorrelation
from ..domain.repositories import ICorrelationRepository, IImpactAnalysisRepository
from ..domain.services import CorrelationAnalyzer
from ..infrastructure.models import TopicSchemaCorrelationModel

logger = logging.getLogger(__name__)


class CorrelationQueryService:
    """상관관계 조회 서비스"""

    def __init__(self, correlation_repo: ICorrelationRepository, session_factory) -> None:
        self.correlation_repo = correlation_repo
        self.session_factory = session_factory

    async def get_topic_schemas(self, topic_name: TopicName) -> TopicSchemaCorrelation | None:
        """토픽의 스키마 정보 조회"""
        return await self.correlation_repo.find_by_topic(topic_name)

    async def get_schema_topics(self, subject: SubjectName) -> list[TopicSchemaCorrelation]:
        """스키마가 사용되는 토픽 목록 조회"""
        return await self.correlation_repo.find_by_schema(subject)

    async def get_all_correlations(self) -> list[TopicSchemaCorrelation]:
        """모든 상관관계 조회"""
        return await self.correlation_repo.find_all()

    async def get_topic_count(self) -> int:
        """토픽 개수 조회"""
        async with self.session_factory() as session:
            stmt = select(func.count()).select_from(TopicMetadataModel)
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def get_schema_count(self) -> int:
        """스키마 개수 조회"""
        async with self.session_factory() as session:
            stmt = select(func.count()).select_from(SchemaMetadataModel)
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def get_correlation_count(self) -> int:
        """상관관계 개수 조회"""
        async with self.session_factory() as session:
            stmt = select(func.count()).select_from(TopicSchemaCorrelationModel)
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def get_statistics(self) -> dict[str, int]:
        """통계 조회 - 1급 함수 사용"""
        async with self.session_factory() as session:

            async def count_table(model: type) -> int:
                """테이블 카운트 헬퍼 함수"""
                stmt = select(func.count()).select_from(model)
                result = await session.execute(stmt)
                return result.scalar() or 0

            topic_count = await count_table(TopicMetadataModel)
            schema_count = await count_table(SchemaMetadataModel)
            correlation_count = await count_table(TopicSchemaCorrelationModel)

            return {
                "topic_count": topic_count,
                "schema_count": schema_count,
                "correlation_count": correlation_count,
            }


class ImpactAnalysisQueryService:
    """영향도 분석 조회 서비스"""

    def __init__(
        self, correlation_repo: ICorrelationRepository, impact_repo: IImpactAnalysisRepository
    ) -> None:
        self.correlation_repo = correlation_repo
        self.impact_repo = impact_repo
        self.analyzer = CorrelationAnalyzer(correlation_repo)

    async def analyze_schema_impact(
        self, subject: SubjectName, subject_strategy: str
    ) -> SchemaImpactAnalysis:
        """스키마 영향도 분석 (실시간)"""
        analysis = await self.analyzer.analyze_schema_impact(subject, subject_strategy)

        # 분석 결과 저장
        await self.impact_repo.save_analysis(analysis)

        return analysis

    async def get_latest_analysis(self, subject: SubjectName) -> SchemaImpactAnalysis | None:
        """최신 분석 결과 조회 (캐시)"""
        return await self.impact_repo.get_latest_analysis(subject)
