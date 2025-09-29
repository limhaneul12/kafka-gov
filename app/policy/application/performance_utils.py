"""Policy 모듈 성능 최적화 유틸리티"""

from __future__ import annotations

import asyncio
import hashlib
from typing import TYPE_CHECKING, Any, TypeVar

import orjson

if TYPE_CHECKING:
    from ..domain.models import DomainPolicyViolation, PolicyRule, PolicyTarget

T = TypeVar("T")
R = TypeVar("R")


class PolicyEvaluationOptimizer:
    """정책 평가 성능 최적화 유틸리티"""

    def __init__(self, max_concurrency: int = 5) -> None:
        """
        Args:
            max_concurrency: 최대 동시 실행 수 (정책 평가는 CPU 집약적이므로 보수적)
        """
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def evaluate_rules_parallel(
        self,
        rules: list[PolicyRule],
        targets: list[PolicyTarget],
        context: Any,  # PolicyContext
    ) -> list[DomainPolicyViolation]:
        """규칙들을 병렬로 평가

        Args:
            rules: 평가할 정책 규칙 목록
            targets: 평가 대상 목록
            context: 정책 평가 컨텍스트

        Returns:
            모든 위반 사항 목록
        """

        async def _evaluate_rule_batch(rule: PolicyRule) -> list[DomainPolicyViolation]:
            async with self._semaphore:
                violations = []
                for target in targets:
                    violations.extend(rule.validate(target, context))
                return violations

        # 규칙별로 병렬 평가
        tasks = [_evaluate_rule_batch(rule) for rule in rules]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 병합
        all_violations = []
        for result in results:
            if isinstance(result, Exception):
                # 예외 발생한 규칙은 건너뛰고 로깅
                continue
            if isinstance(result, list):
                all_violations.extend(result)

        return all_violations

    async def evaluate_targets_parallel(
        self,
        rule: PolicyRule,
        targets: list[PolicyTarget],
        context: Any,  # PolicyContext
        chunk_size: int = 10,
    ) -> list[DomainPolicyViolation]:
        """대상들을 청크 단위로 병렬 평가

        Args:
            rule: 평가할 정책 규칙
            targets: 평가 대상 목록
            context: 정책 평가 컨텍스트
            chunk_size: 청크 크기

        Returns:
            위반 사항 목록
        """

        async def _evaluate_chunk(chunk: list[PolicyTarget]) -> list[DomainPolicyViolation]:
            async with self._semaphore:
                violations = []
                for target in chunk:
                    violations.extend(rule.validate(target, context))
                return violations

        # 청크 단위로 분할
        chunks: list[list[PolicyTarget]] = [
            targets[i : i + chunk_size] for i in range(0, len(targets), chunk_size)
        ]

        # 병렬 처리
        tasks = [_evaluate_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 병합
        all_violations = []
        for result in results:
            if isinstance(result, Exception):
                continue
            if isinstance(result, list):
                all_violations.extend(result)

        return all_violations


class PolicyCacheOptimizer:
    """정책 캐시 최적화 유틸리티"""

    def __init__(self, max_cache_size: int = 1000) -> None:
        """
        Args:
            max_cache_size: 최대 캐시 크기
        """
        self.max_cache_size = max_cache_size
        self._rule_cache: dict[str, Any] = {}  # 규칙 캐시
        self._violation_cache: dict[str, list[DomainPolicyViolation]] = {}  # 위반 캐시

    def cache_rule_result(
        self,
        rule_id: str,
        target_hash: str,
        violations: list[DomainPolicyViolation],
    ) -> None:
        """규칙 평가 결과 캐시"""
        cache_key = f"{rule_id}:{target_hash}"

        # 캐시 크기 제한
        if len(self._violation_cache) >= self.max_cache_size:
            # LRU 방식으로 오래된 항목 제거
            oldest_key = next(iter(self._violation_cache))
            del self._violation_cache[oldest_key]

        self._violation_cache[cache_key] = violations

    def get_cached_result(
        self,
        rule_id: str,
        target_hash: str,
    ) -> list[DomainPolicyViolation] | None:
        """캐시된 평가 결과 조회"""
        cache_key = f"{rule_id}:{target_hash}"
        return self._violation_cache.get(cache_key)

    def generate_target_hash(self, target: PolicyTarget) -> str:
        """대상 객체의 해시 생성"""

        # 정렬된 JSON 문자열로 변환하여 일관된 해시 생성
        target_str = orjson.dumps(target)
        return hashlib.sha256(target_str).hexdigest()[:16]

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._rule_cache.clear()
        self._violation_cache.clear()


class PolicyMemoryOptimizer:
    """정책 메모리 사용 최적화 유틸리티"""

    @staticmethod
    def optimize_violation_storage(
        violations: list[DomainPolicyViolation],
    ) -> tuple[DomainPolicyViolation, ...]:
        """위반 사항 저장 최적화

        Args:
            violations: 최적화할 위반 사항 목록

        Returns:
            메모리 최적화된 위반 사항 튜플
        """
        if not violations:
            return ()

        # 중복 제거 (동일한 리소스, 규칙, 메시지)
        unique_violations = []
        seen = set()

        for violation in violations:
            key = (
                violation.resource_name,
                violation.rule_id,
                violation.message,
                violation.severity.value,
            )
            if key not in seen:
                seen.add(key)
                unique_violations.append(violation)

        # 심각도별 정렬 (CRITICAL > ERROR > WARNING)
        severity_order = {"critical": 0, "error": 1, "warning": 2}
        unique_violations.sort(
            key=lambda v: (
                severity_order.get(v.severity.value, 3),
                v.resource_name,
                v.rule_id,
            )
        )

        return tuple(unique_violations)

    @staticmethod
    def batch_violation_operations(
        violation_groups: list[list[DomainPolicyViolation]],
    ) -> list[DomainPolicyViolation]:
        """위반 사항 연산들을 배치로 처리

        Args:
            violation_groups: 처리할 위반 사항 그룹 목록

        Returns:
            병합된 위반 사항 목록
        """
        if not violation_groups:
            return []

        # 단일 그룹은 그대로 반환
        if len(violation_groups) == 1:
            return violation_groups[0]

        # 여러 그룹을 효율적으로 병합
        all_violations = []
        for group in violation_groups:
            all_violations.extend(group)

        return all_violations

    @staticmethod
    def optimize_rule_storage(rules: list[PolicyRule]) -> tuple[PolicyRule, ...]:
        """규칙 저장 최적화

        Args:
            rules: 최적화할 규칙 목록

        Returns:
            메모리 최적화된 규칙 튜플
        """
        if not rules:
            return ()

        # 규칙 ID로 중복 제거
        unique_rules = []
        seen_ids = set()

        for rule in rules:
            if rule.rule_id not in seen_ids:
                seen_ids.add(rule.rule_id)
                unique_rules.append(rule)

        # 규칙 ID로 정렬하여 캐시 효율성 향상
        unique_rules.sort(key=lambda r: r.rule_id)

        return tuple(unique_rules)


# 전역 인스턴스 (재사용을 위한 싱글톤 패턴)
policy_evaluation_optimizer = PolicyEvaluationOptimizer()
policy_cache_optimizer = PolicyCacheOptimizer()
policy_memory_optimizer = PolicyMemoryOptimizer()


async def optimize_policy_evaluation(
    rules: list[PolicyRule],
    targets: list[PolicyTarget],
    context: Any,  # PolicyContext
) -> list[DomainPolicyViolation]:
    """정책 평가 최적화 함수

    Args:
        rules: 평가할 정책 규칙 목록
        targets: 평가 대상 목록
        context: 정책 평가 컨텍스트

    Returns:
        최적화된 평가 결과
    """
    return await policy_evaluation_optimizer.evaluate_rules_parallel(rules, targets, context)


def optimize_violation_memory_usage(
    violations: list[DomainPolicyViolation],
) -> tuple[DomainPolicyViolation, ...]:
    """위반 사항 메모리 사용량 최적화 함수

    Args:
        violations: 최적화할 위반 사항 목록

    Returns:
        메모리 최적화된 위반 사항 튜플
    """
    return policy_memory_optimizer.optimize_violation_storage(violations)


def cache_policy_result(
    rule_id: str,
    target: PolicyTarget,
    violations: list[DomainPolicyViolation],
) -> None:
    """정책 평가 결과 캐시 함수

    Args:
        rule_id: 규칙 ID
        target: 평가 대상
        violations: 위반 사항 목록
    """
    target_hash = policy_cache_optimizer.generate_target_hash(target)
    policy_cache_optimizer.cache_rule_result(rule_id, target_hash, violations)
