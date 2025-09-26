"""Schema 모듈 성능 최적화 유틸리티"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

from ..domain.models import SchemaSpec, SubjectName

T = TypeVar("T")
R = TypeVar("R")


class SchemaBatchProcessor:
    """스키마 배치 처리 성능 최적화 유틸리티"""
    
    def __init__(self, max_concurrency: int = 8) -> None:
        """
        Args:
            max_concurrency: 최대 동시 실행 수 (스키마 처리는 I/O 집약적)
        """
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
    
    async def process_schema_specs_parallel(
        self,
        specs: list[SchemaSpec],
        processor: Callable[[SchemaSpec], Any],
        *,
        chunk_size: int = 3,  # 스키마 처리는 더 작은 청크 사용
    ) -> dict[SubjectName, Any]:
        """스키마 스펙들을 병렬로 처리
        
        Args:
            specs: 처리할 스키마 스펙 목록
            processor: 각 스펙을 처리할 함수
            chunk_size: 청크 크기 (스키마 처리는 더 보수적)
            
        Returns:
            Subject 이름별 처리 결과
        """
        async def _process_with_semaphore(spec: SchemaSpec) -> tuple[SubjectName, Any]:
            async with self._semaphore:
                result = await processor(spec)
                return spec.subject, result
        
        # 청크 단위로 분할하여 처리
        results = {}
        for i in range(0, len(specs), chunk_size):
            chunk = specs[i:i + chunk_size]
            chunk_tasks = [_process_with_semaphore(spec) for spec in chunk]
            chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
            
            for result in chunk_results:
                if isinstance(result, Exception):
                    # 예외 처리 - 로깅하고 계속 진행
                    continue
                subject, value = result
                results[subject] = value
        
        return results
    
    async def validate_schemas_parallel(
        self,
        specs: list[SchemaSpec],
        validator: Callable[[SchemaSpec], Any],
    ) -> dict[SubjectName, bool]:
        """스키마들을 병렬로 검증
        
        Args:
            specs: 검증할 스키마 스펙 목록
            validator: 검증 함수
            
        Returns:
            Subject별 검증 결과
        """
        return await self.process_schema_specs_parallel(specs, validator, chunk_size=5)


class SchemaMemoryOptimizer:
    """스키마 메모리 사용 최적화 유틸리티"""
    
    @staticmethod
    def optimize_schema_content(content: str) -> str:
        """스키마 콘텐츠 메모리 최적화
        
        Args:
            content: 원본 스키마 콘텐츠
            
        Returns:
            최적화된 스키마 콘텐츠
        """
        if not content:
            return content
        
        # JSON 스키마의 경우 불필요한 공백 제거
        if content.strip().startswith('{'):
            try:
                import json
                parsed = json.loads(content)
                return json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        
        # 기본적인 공백 정리
        lines = content.split('\n')
        cleaned_lines = [line.rstrip() for line in lines if line.strip()]
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    def batch_schema_operations(
        operations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """스키마 연산들을 배치로 처리하여 메모리 효율성 향상
        
        Args:
            operations: 처리할 스키마 연산 목록
            
        Returns:
            병합된 결과 딕셔너리
        """
        if not operations:
            return {}
        
        # 단일 연산은 그대로 반환
        if len(operations) == 1:
            return operations[0]
        
        # 여러 연산을 효율적으로 병합
        result = {}
        for op_dict in operations:
            # 중복 키 처리 - 최신 값 우선
            result.update(op_dict)
        
        return result
    
    @staticmethod
    def optimize_artifact_storage(
        artifacts: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], ...]:
        """아티팩트 저장 최적화
        
        Args:
            artifacts: 최적화할 아티팩트 목록
            
        Returns:
            메모리 최적화된 아티팩트 튜플
        """
        if not artifacts:
            return ()
        
        # 중복 제거 및 정렬
        unique_artifacts = []
        seen_keys = set()
        
        for artifact in artifacts:
            key = f"{artifact.get('subject', '')}:{artifact.get('version', 0)}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_artifacts.append(artifact)
        
        # Subject 이름으로 정렬하여 캐시 효율성 향상
        unique_artifacts.sort(key=lambda x: x.get('subject', ''))
        
        return tuple(unique_artifacts)


class SchemaFileProcessor:
    """스키마 파일 처리 최적화"""
    
    def __init__(self, max_file_size: int = 10 * 1024 * 1024) -> None:
        """
        Args:
            max_file_size: 최대 파일 크기 (기본 10MB)
        """
        self.max_file_size = max_file_size
        self.supported_extensions = {".avsc", ".json", ".proto", ".zip"}
    
    async def process_files_parallel(
        self,
        files: list[Any],
        processor: Callable[[Any], Any],
        max_workers: int = 4,
    ) -> list[Any]:
        """파일들을 병렬로 처리
        
        Args:
            files: 처리할 파일 목록
            processor: 파일 처리 함수
            max_workers: 최대 워커 수
            
        Returns:
            처리 결과 목록
        """
        semaphore = asyncio.Semaphore(max_workers)
        
        async def _process_with_semaphore(file: Any) -> Any:
            async with semaphore:
                return await processor(file)
        
        tasks = [_process_with_semaphore(file) for file in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외가 아닌 결과만 반환
        return [result for result in results if not isinstance(result, Exception)]
    
    def validate_file_efficiently(self, file_info: dict[str, Any]) -> bool:
        """파일을 효율적으로 검증
        
        Args:
            file_info: 파일 정보
            
        Returns:
            검증 결과
        """
        # 파일 크기 검증
        if file_info.get("size", 0) > self.max_file_size:
            return False
        
        # 확장자 검증
        extension = file_info.get("extension", "").lower()
        if extension not in self.supported_extensions:
            return False
        
        # 빈 파일 검증
        return file_info.get("size", 0) != 0


# 전역 인스턴스 (재사용을 위한 싱글톤 패턴)
schema_batch_processor = SchemaBatchProcessor()
schema_memory_optimizer = SchemaMemoryOptimizer()
schema_file_processor = SchemaFileProcessor()


async def optimize_schema_batch_processing(
    specs: list[SchemaSpec],
    processor: Callable[[SchemaSpec], Any],
) -> dict[SubjectName, Any]:
    """스키마 배치 처리 최적화 함수
    
    Args:
        specs: 처리할 스키마 스펙 목록
        processor: 각 스펙을 처리할 함수
        
    Returns:
        최적화된 처리 결과
    """
    return await schema_batch_processor.process_schema_specs_parallel(specs, processor)


def optimize_schema_memory_usage(content: str) -> str:
    """스키마 메모리 사용량 최적화 함수
    
    Args:
        content: 최적화할 스키마 콘텐츠
        
    Returns:
        메모리 최적화된 콘텐츠
    """
    return schema_memory_optimizer.optimize_schema_content(content)


async def optimize_file_processing(
    files: list[Any],
    processor: Callable[[Any], Any],
) -> list[Any]:
    """파일 처리 최적화 함수
    
    Args:
        files: 처리할 파일 목록
        processor: 파일 처리 함수
        
    Returns:
        최적화된 처리 결과
    """
    return await schema_file_processor.process_files_parallel(files, processor)
