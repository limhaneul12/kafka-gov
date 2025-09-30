"""Analysis Query Services"""

from __future__ import annotations

import logging

from ..domain.models import SchemaImpactAnalysis, SubjectName, TopicName, TopicSchemaCorrelation
from ..domain.repositories import ICorrelationRepository, IImpactAnalysisRepository
from ..domain.services import CorrelationAnalyzer

logger = logging.getLogger(__name__)


class CorrelationQueryService:
    """상관관계 조회 서비스"""

    def __init__(self, correlation_repo: ICorrelationRepository) -> None:
        self.correlation_repo = correlation_repo

    async def get_topic_schemas(self, topic_name: TopicName) -> TopicSchemaCorrelation | None:
        """토픽의 스키마 정보 조회"""
        return await self.correlation_repo.find_by_topic(topic_name)

    async def get_schema_topics(self, subject: SubjectName) -> list[TopicSchemaCorrelation]:
        """스키마가 사용되는 토픽 목록 조회"""
        return await self.correlation_repo.find_by_schema(subject)

    async def get_all_correlations(self) -> list[TopicSchemaCorrelation]:
        """모든 상관관계 조회"""
        return await self.correlation_repo.find_all()


class ImpactAnalysisQueryService:
    """영향도 분석 조회 서비스"""

    def __init__(
        self,
        correlation_repo: ICorrelationRepository,
        impact_repo: IImpactAnalysisRepository,
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
