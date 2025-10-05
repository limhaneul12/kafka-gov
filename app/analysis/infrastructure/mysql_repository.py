"""Analysis MySQL Repository Implementation (Session Factory 패턴)"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import SchemaImpactAnalysis, SubjectName, TopicName, TopicSchemaCorrelation
from ..domain.repositories import ICorrelationRepository, IImpactAnalysisRepository
from .models import SchemaImpactAnalysisModel, TopicSchemaCorrelationModel

logger = logging.getLogger(__name__)


class MySQLCorrelationRepository(ICorrelationRepository):
    """MySQL 기반 상관관계 Repository (Session Factory 패턴)"""

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    async def save(self, correlation: TopicSchemaCorrelation) -> None:
        """상관관계 저장"""
        async with self.session_factory() as session:
            try:
                # 기존 레코드 조회
                stmt = select(TopicSchemaCorrelationModel).where(
                    TopicSchemaCorrelationModel.correlation_id == correlation.correlation_id
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # 업데이트
                    existing.topic_name = correlation.topic_name
                    existing.key_schema_subject = correlation.key_schema_subject
                    existing.value_schema_subject = correlation.value_schema_subject
                    existing.environment = correlation.environment
                    existing.link_source = correlation.link_source
                    existing.confidence_score = correlation.confidence_score
                else:
                    # 새로 생성
                    model = TopicSchemaCorrelationModel(
                        correlation_id=correlation.correlation_id,
                        topic_name=correlation.topic_name,
                        key_schema_subject=correlation.key_schema_subject,
                        value_schema_subject=correlation.value_schema_subject,
                        environment=correlation.environment,
                        link_source=correlation.link_source,
                        confidence_score=correlation.confidence_score,
                    )
                    session.add(model)

                await session.flush()
                logger.info(f"Correlation saved: {correlation.topic_name}")

            except Exception as e:
                logger.error(f"Failed to save correlation: {e}")
                raise

    async def find_by_topic(self, topic_name: TopicName) -> TopicSchemaCorrelation | None:
        """토픽으로 상관관계 조회"""
        async with self.session_factory() as session:
            try:
                stmt = select(TopicSchemaCorrelationModel).where(
                    TopicSchemaCorrelationModel.topic_name == topic_name
                )
                result = await session.execute(stmt)
                model = result.scalar_one_or_none()

                if not model:
                    return None

                return TopicSchemaCorrelation(
                    correlation_id=model.correlation_id,
                    topic_name=model.topic_name,
                    key_schema_subject=model.key_schema_subject,
                    value_schema_subject=model.value_schema_subject,
                    environment=model.environment,
                    link_source=model.link_source,
                    confidence_score=model.confidence_score,
                )

            except Exception as e:
                logger.error(f"Failed to find correlation by topic {topic_name}: {e}")
                raise

    async def find_by_schema(self, subject: SubjectName) -> list[TopicSchemaCorrelation]:
        """스키마로 상관관계 조회"""
        async with self.session_factory() as session:
            try:
                stmt = select(TopicSchemaCorrelationModel).where(
                    (TopicSchemaCorrelationModel.key_schema_subject == subject)
                    | (TopicSchemaCorrelationModel.value_schema_subject == subject)
                )
                result = await session.execute(stmt)
                models = result.scalars().all()

                return [
                    TopicSchemaCorrelation(
                        correlation_id=model.correlation_id,
                        topic_name=model.topic_name,
                        key_schema_subject=model.key_schema_subject,
                        value_schema_subject=model.value_schema_subject,
                        environment=model.environment,
                        link_source=model.link_source,
                        confidence_score=model.confidence_score,
                    )
                    for model in models
                ]

            except Exception as e:
                logger.error(f"Failed to find correlations by schema {subject}: {e}")
                raise

    async def find_all(self) -> list[TopicSchemaCorrelation]:
        """모든 상관관계 조회"""
        async with self.session_factory() as session:
            try:
                stmt = select(TopicSchemaCorrelationModel)
                result = await session.execute(stmt)
                models = result.scalars().all()

                return [
                    TopicSchemaCorrelation(
                        correlation_id=model.correlation_id,
                        topic_name=model.topic_name,
                        key_schema_subject=model.key_schema_subject,
                        value_schema_subject=model.value_schema_subject,
                        environment=model.environment,
                        link_source=model.link_source,
                        confidence_score=model.confidence_score,
                    )
                    for model in models
                ]

            except Exception as e:
                logger.error(f"Failed to find all correlations: {e}")
                raise

    async def remove_schema_reference(self, subject: str) -> int:
        """스키마 참조 제거 (스키마 삭제 시 호출)"""
        async with self.session_factory() as session:
            try:
                from sqlalchemy import update

                # key_schema_subject가 해당 subject인 경우 NULL로 업데이트
                stmt_key = (
                    update(TopicSchemaCorrelationModel)
                    .where(TopicSchemaCorrelationModel.key_schema_subject == subject)
                    .values(key_schema_subject=None)
                )
                result_key = await session.execute(stmt_key)

                # value_schema_subject가 해당 subject인 경우 NULL로 업데이트
                stmt_value = (
                    update(TopicSchemaCorrelationModel)
                    .where(TopicSchemaCorrelationModel.value_schema_subject == subject)
                    .values(value_schema_subject=None)
                )
                result_value = await session.execute(stmt_value)

                await session.commit()

                total_updated = result_key.rowcount + result_value.rowcount
                logger.info(
                    f"Removed schema reference '{subject}' from {total_updated} correlations"
                )
                return total_updated

            except Exception as e:
                logger.error(f"Failed to remove schema reference: {e}")
                await session.rollback()
                raise


class MySQLImpactAnalysisRepository(IImpactAnalysisRepository):
    """MySQL 기반 영향도 분석 Repository (Session Factory 패턴)"""

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    async def save_analysis(self, analysis: SchemaImpactAnalysis) -> None:
        """분석 결과 저장"""
        async with self.session_factory() as session:
            try:
                model = SchemaImpactAnalysisModel(
                    subject=analysis.subject,
                    affected_topics={"topics": list(analysis.affected_topics)},
                    total_impact_count=analysis.total_impact_count,
                    risk_level=analysis.risk_level,
                    warnings={"warnings": list(analysis.warnings)},
                )
                session.add(model)
                await session.flush()

                logger.info(f"Impact analysis saved: {analysis.subject}")

            except Exception as e:
                logger.error(f"Failed to save impact analysis: {e}")
                raise

    async def get_latest_analysis(self, subject: SubjectName) -> SchemaImpactAnalysis | None:
        """최신 분석 결과 조회"""
        async with self.session_factory() as session:
            try:
                stmt = (
                    select(SchemaImpactAnalysisModel)
                    .where(SchemaImpactAnalysisModel.subject == subject)
                    .order_by(SchemaImpactAnalysisModel.analyzed_at.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                model = result.scalar_one_or_none()

                if not model:
                    return None

                return SchemaImpactAnalysis(
                    subject=model.subject,
                    affected_topics=tuple(model.affected_topics.get("topics", [])),
                    total_impact_count=model.total_impact_count,
                    risk_level=model.risk_level,
                    warnings=tuple(model.warnings.get("warnings", [])),
                )

            except Exception as e:
                logger.error(f"Failed to get latest analysis for {subject}: {e}")
                raise
