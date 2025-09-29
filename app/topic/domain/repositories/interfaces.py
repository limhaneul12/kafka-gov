"""Topic Domain Repository 인터페이스"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict

from ..models import ChangeId, DomainTopicApplyResult, DomainTopicPlan, DomainTopicSpec, TopicName


class ITopicRepository(ABC):
    """토픽 리포지토리 인터페이스"""

    @abstractmethod
    async def get_topic_metadata(self, name: TopicName) -> dict[str, Any] | None:
        """토픽 메타데이터 조회"""
        ...

    @abstractmethod
    async def create_topics(
        self, specs: list[DomainTopicSpec]
    ) -> dict[TopicName, Exception | None]:
        """토픽 생성"""
        ...

    @abstractmethod
    async def delete_topics(self, names: list[TopicName]) -> dict[TopicName, Exception | None]:
        """토픽 삭제"""
        ...

    @abstractmethod
    async def alter_topic_configs(
        self, configs: dict[TopicName, dict[str, str]]
    ) -> dict[TopicName, Exception | None]:
        """토픽 설정 변경"""
        ...

    @abstractmethod
    async def create_partitions(
        self, partitions: dict[TopicName, int]
    ) -> dict[TopicName, Exception | None]:
        """파티션 수 증가"""
        ...

    @abstractmethod
    async def describe_topics(self, names: list[TopicName]) -> dict[TopicName, dict[str, Any]]:
        """토픽 상세 정보 조회"""
        ...


class PlanMeta(TypedDict):
    """토픽 계획 메타 정보 타입

    - status: 계획 상태 (pending/applied/failed)
    - created_at: 계획 생성 시각 (ISO8601 문자열)
    - applied_at: 계획 적용 시각 (ISO8601 문자열) 또는 없음
    """

    status: str
    created_at: str
    applied_at: str | None


class ITopicMetadataRepository(ABC):
    """토픽 메타데이터 리포지토리 인터페이스"""

    @abstractmethod
    async def save_plan(self, plan: DomainTopicPlan, created_by: str) -> None:
        """계획 저장"""
        ...

    @abstractmethod
    async def get_plan(self, change_id: ChangeId) -> DomainTopicPlan | None:
        """계획 조회"""
        ...

    @abstractmethod
    async def get_plan_meta(self, change_id: ChangeId) -> PlanMeta | None:
        """계획 메타 정보 조회 (상태/타임스탬프)

        Returns:
            PlanMeta dict 또는 None
        """
        ...

    @abstractmethod
    async def save_apply_result(self, result: DomainTopicApplyResult, applied_by: str) -> None:
        """적용 결과 저장"""
        ...

    @abstractmethod
    async def get_topic_metadata(self, name: TopicName) -> dict[str, Any] | None:
        """토픽 메타데이터 조회"""
        ...

    @abstractmethod
    async def save_topic_metadata(self, name: TopicName, metadata: dict[str, Any]) -> None:
        """토픽 메타데이터 저장"""
        ...


class IAuditRepository(ABC):
    """감사 로그 리포지토리 인터페이스"""

    @abstractmethod
    async def log_topic_operation(
        self,
        change_id: ChangeId,
        action: str,
        target: TopicName,
        actor: str,
        status: str,
        message: str | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> str:
        """토픽 작업 감사 로그 기록"""
        ...
