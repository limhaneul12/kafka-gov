"""Analysis Repository Interfaces"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import SchemaImpactAnalysis, SubjectName, TopicName, TopicSchemaCorrelation


class ICorrelationRepository(ABC):
    """토픽-스키마 상관관계 Repository"""

    @abstractmethod
    async def save(self, correlation: TopicSchemaCorrelation) -> None:
        """상관관계 저장"""

    @abstractmethod
    async def find_by_topic(self, topic_name: TopicName) -> TopicSchemaCorrelation | None:
        """토픽으로 상관관계 조회"""

    @abstractmethod
    async def find_by_schema(self, subject: SubjectName) -> list[TopicSchemaCorrelation]:
        """스키마로 상관관계 조회 (여러 토픽 가능)"""

    @abstractmethod
    async def find_all(self) -> list[TopicSchemaCorrelation]:
        """모든 상관관계 조회"""

    @abstractmethod
    async def remove_schema_reference(self, subject: SubjectName) -> int:
        """
        스키마 참조 제거 (스키마 삭제 시 호출)

        해당 스키마를 참조하는 correlation의 스키마 필드를 NULL로 업데이트합니다.

        Returns:
            업데이트된 레코드 수
        """


class IImpactAnalysisRepository(ABC):
    """영향도 분석 Repository"""

    @abstractmethod
    async def save_analysis(self, analysis: SchemaImpactAnalysis) -> None:
        """분석 결과 저장"""

    @abstractmethod
    async def get_latest_analysis(self, subject: SubjectName) -> SchemaImpactAnalysis | None:
        """최신 분석 결과 조회"""
