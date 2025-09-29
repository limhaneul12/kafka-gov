"""Topic 모듈 성능 최적화 유틸리티"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from ..domain.models import DomainTopicSpec, TopicName

T = TypeVar("T")
R = TypeVar("R")


class BatchProcessor:
    """배치 처리 성능 최적화 유틸리티"""

    def __init__(self, max_concurrency: int = 10) -> None:
        """
        Args:
            max_concurrency: 최대 동시 실행 수
        """
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def process_batch_parallel(
        self, items: list[T], processor: Callable[[T], Awaitable[R]], *, chunk_size: int = 5
    ) -> list[R]:
        """배치를 병렬로 처리

        Args:
            items: 처리할 아이템 목록
            processor: 각 아이템을 처리할 함수
            chunk_size: 청크 크기

        Returns:
            처리 결과 목록
        """

        async def _process_with_semaphore(item: T) -> R:
            async with self._semaphore:
                return await processor(item)

        # 청크 단위로 분할하여 처리
        results: list[R] = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i : i + chunk_size]
            chunk_tasks = [_process_with_semaphore(item) for item in chunk]
            chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
            for r in chunk_results:
                if isinstance(r, Exception):
                    continue
                # 타입 가드: Exception이 아닌 경우만 추가
                results.append(r)  # type: ignore[arg-type]

        return results

    async def process_topic_specs_parallel(
        self,
        specs: list[DomainTopicSpec],
        processor: Callable[[DomainTopicSpec], Awaitable[Any]],
    ) -> dict[TopicName, Any]:
        """토픽 스펙들을 병렬로 처리

                Args:
                    specs: 처리할 토픽 스펙 목록
        {{ ... }}

                Returns:
                    토픽 이름별 처리 결과
        """
        results = await self.process_batch_parallel(specs, processor)
        return {spec.name: result for spec, result in zip(specs, results, strict=False)}


class MemoryOptimizer:
    """메모리 사용 최적화 유틸리티"""

    @staticmethod
    def optimize_tuple_creation(items: list[Any]) -> tuple[Any, ...]:
        """리스트를 메모리 효율적인 튜플로 변환

        Args:
            items: 변환할 리스트

        Returns:
            최적화된 튜플
        """
        # 빈 리스트는 빈 튜플로
        if not items:
            return ()

        # 단일 아이템은 직접 튜플 생성
        if len(items) == 1:
            return (items[0],)

        # 큰 리스트는 청크 단위로 처리하여 메모리 사용량 최적화
        if len(items) > 1000:
            return tuple(items[i : i + 100] for i in range(0, len(items), 100))

        return tuple(items)

    @staticmethod
    def batch_dict_operations(operations: list[dict[str, Any]]) -> dict[str, Any]:
        """딕셔너리 연산들을 배치로 처리하여 메모리 효율성 향상

        Args:
            operations: 처리할 딕셔너리 연산 목록

        Returns:
            병합된 결과 딕셔너리
        """
        if not operations:
            return {}

        # 단일 딕셔너리는 그대로 반환
        if len(operations) == 1:
            return operations[0]

        # 여러 딕셔너리를 효율적으로 병합
        result = {}
        for op_dict in operations:
            result.update(op_dict)

        return result


# 전역 인스턴스 (재사용을 위한 싱글톤 패턴)
batch_processor = BatchProcessor()
memory_optimizer = MemoryOptimizer()


async def optimize_topic_batch_processing(
    specs: list[DomainTopicSpec],
    processor: Callable[[DomainTopicSpec], Any],
) -> dict[TopicName, Any]:
    """토픽 배치 처리 최적화 함수

    Args:
        specs: 처리할 토픽 스펙 목록
        processor: 각 스펙을 처리할 함수

    Returns:
        최적화된 처리 결과
    """
    return await batch_processor.process_topic_specs_parallel(specs, processor)


def optimize_memory_usage(items: list[Any]) -> tuple[Any, ...]:
    """메모리 사용량 최적화 함수

    Args:
        items: 최적화할 아이템 목록

    Returns:
        메모리 최적화된 튜플
    """
    return memory_optimizer.optimize_tuple_creation(items)
