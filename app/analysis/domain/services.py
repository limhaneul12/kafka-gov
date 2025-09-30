"""Analysis Domain Services"""

from __future__ import annotations

import uuid

from .models import SchemaImpactAnalysis, SubjectName, TopicName, TopicSchemaCorrelation
from .repositories import ICorrelationRepository


class CorrelationAnalyzer:
    """상관관계 분석 서비스"""

    def __init__(self, correlation_repo: ICorrelationRepository) -> None:
        self.correlation_repo = correlation_repo

    async def analyze_schema_impact(
        self, subject: SubjectName, subject_strategy: str
    ) -> SchemaImpactAnalysis:
        """스키마 삭제/변경 시 영향도 분석"""
        # 1. DB에서 실제 연결된 토픽 조회
        correlations = await self.correlation_repo.find_by_schema(subject)
        affected_topics = tuple(corr.topic_name for corr in correlations)

        # 2. Subject naming에서 추론
        inferred_topics = self._extract_topics_from_subject(subject, subject_strategy)

        # 3. 병합 (중복 제거)
        all_topics = tuple(set(affected_topics) | set(inferred_topics))

        # 4. 위험도 계산
        risk_level = self._calculate_risk_level(len(all_topics), subject)

        # 5. 경고 메시지 생성
        warnings = self._generate_warnings(subject, all_topics, risk_level)

        return SchemaImpactAnalysis(
            subject=subject,
            affected_topics=all_topics,
            total_impact_count=len(all_topics),
            risk_level=risk_level,
            warnings=warnings,
        )

    def _extract_topics_from_subject(self, subject: SubjectName, strategy: str) -> list[TopicName]:
        """Subject naming에서 토픽 추출"""
        if strategy == "TopicNameStrategy":
            if subject.endswith(("-key", "-value")):
                topic_name = subject.rsplit("-", 1)[0]
                return [topic_name]

        elif strategy == "TopicRecordNameStrategy":
            parts = subject.split("-", 1)
            if len(parts) >= 2:
                return [parts[0]]

        return []

    def _calculate_risk_level(self, topic_count: int, subject: str) -> str:
        """위험도 계산"""
        if topic_count == 0:
            return "low"
        if topic_count >= 5 or "prod" in subject.lower():
            return "high"
        return "medium"

    def _generate_warnings(
        self, subject: str, topics: tuple[TopicName, ...], risk_level: str
    ) -> tuple[str, ...]:
        """경고 메시지 생성"""
        warnings = []

        if topics:
            topic_list = ", ".join(topics[:5])  # 최대 5개만 표시
            if len(topics) > 5:
                topic_list += f" 외 {len(topics) - 5}개"
            warnings.append(f"영향받는 토픽: {topic_list}")

        if risk_level == "high":
            warnings.append("⚠️ 높은 위험도: 프로덕션 환경 또는 다수의 토픽에 영향")

        if "prod" in subject.lower():
            warnings.append("🚨 프로덕션 스키마: 변경 전 반드시 검토 필요")

        return tuple(warnings)


class TopicSchemaLinker:
    """토픽-스키마 자동 연결 서비스"""

    def __init__(self, correlation_repo: ICorrelationRepository) -> None:
        self.correlation_repo = correlation_repo

    async def link_schema_to_topic(
        self,
        topic_name: TopicName,
        schema_subject: SubjectName,
        schema_type: str,
        environment: str,
        link_source: str = "auto",
    ) -> TopicSchemaCorrelation:
        """스키마를 토픽에 연결"""
        # 1. 기존 상관관계 조회
        existing = await self.correlation_repo.find_by_topic(topic_name)

        # 2. 업데이트 또는 생성
        if existing:
            # 기존 연결 업데이트
            if schema_type == "key":
                correlation = TopicSchemaCorrelation(
                    correlation_id=existing.correlation_id,
                    topic_name=topic_name,
                    key_schema_subject=schema_subject,
                    value_schema_subject=existing.value_schema_subject,
                    environment=environment,
                    link_source=link_source,
                    confidence_score=1.0 if link_source == "manual" else 0.9,
                )
            else:  # value
                correlation = TopicSchemaCorrelation(
                    correlation_id=existing.correlation_id,
                    topic_name=topic_name,
                    key_schema_subject=existing.key_schema_subject,
                    value_schema_subject=schema_subject,
                    environment=environment,
                    link_source=link_source,
                    confidence_score=1.0 if link_source == "manual" else 0.9,
                )
        else:
            # 새로운 연결 생성
            correlation = TopicSchemaCorrelation(
                correlation_id=f"corr_{uuid.uuid4().hex[:12]}",
                topic_name=topic_name,
                key_schema_subject=schema_subject if schema_type == "key" else None,
                value_schema_subject=schema_subject if schema_type == "value" else None,
                environment=environment,
                link_source=link_source,
                confidence_score=1.0 if link_source == "manual" else 0.9,
            )

        # 3. 저장
        await self.correlation_repo.save(correlation)

        return correlation
