"""Topic Domain 유틸리티 함수"""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


def calculate_dict_diff(
    current: dict[str, T], target: dict[str, T]
) -> dict[str, tuple[T | None, T | None]]:
    """두 딕셔너리의 차이를 계산하는 유틸리티 함수

    Args:
        current: 현재 상태 딕셔너리
        target: 목표 상태 딕셔너리

    Returns:
        변경된 키와 (현재값, 목표값) 튜플의 딕셔너리

    Example:
        >>> current = {"a": 1, "b": 2, "c": 3}
        >>> target = {"a": 1, "b": 5, "d": 4}
        >>> calculate_dict_diff(current, target)
        {'b': (2, 5), 'c': (3, None), 'd': (None, 4)}
    """
    diff: dict[str, tuple[T | None, T | None]] = {}
    all_keys = set(current.keys()) | set(target.keys())

    for key in all_keys:
        current_value = current.get(key)
        target_value = target.get(key)

        if current_value != target_value:
            diff[key] = (current_value, target_value)

    return diff


def format_diff_string(current_value: Any, target_value: Any) -> str:
    """차이를 사람이 읽기 쉬운 문자열로 포맷팅

    Args:
        current_value: 현재 값
        target_value: 목표 값

    Returns:
        "현재값→목표값" 형태의 문자열

    Example:
        >>> format_diff_string(None, "value")
        'none→value'
        >>> format_diff_string("old", "new")
        'old→new'
    """
    current_str = "none" if current_value is None else str(current_value)
    target_str = "none" if target_value is None else str(target_value)
    return f"{current_str}→{target_str}"


def merge_configs(base: dict[str, T], override: dict[str, T]) -> dict[str, T]:
    """설정 병합 유틸리티

    base 설정에 override 설정을 병합합니다.
    override에 있는 값이 우선순위가 높습니다.

    Args:
        base: 기본 설정 딕셔너리
        override: 덮어쓸 설정 딕셔너리

    Returns:
        병합된 설정 딕셔너리

    Example:
        >>> base = {"partitions": 3, "retention_ms": 86400000}
        >>> override = {"partitions": 5}
        >>> merge_configs(base, override)
        {'partitions': 5, 'retention_ms': 86400000}

    Note:
        - override의 None 값은 base 값을 유지함 (명시적 제거 아님)
        - 깊은 병합(nested dict)은 지원하지 않음 (단순 병합)
    """
    result = base.copy()

    for key, value in override.items():
        # None이 아닌 값만 병합 (None은 "미설정"으로 간주)
        if value is not None:
            result[key] = value

    return result


def validate_partition_change(current: int, target: int) -> bool:
    """파티션 변경 검증 (감소 불가)

    Kafka는 파티션 수를 줄일 수 없으므로 target >= current 여야 합니다.

    Args:
        current: 현재 파티션 수
        target: 목표 파티션 수

    Returns:
        변경이 유효하면 True, 그렇지 않으면 False

    Example:
        >>> validate_partition_change(3, 5)
        True
        >>> validate_partition_change(5, 3)
        False
        >>> validate_partition_change(3, 3)
        True

    Note:
        파티션 수가 같은 경우(변경 없음)도 유효한 것으로 간주합니다.
    """
    return target >= current


def validate_replication_factor_change(current: int, target: int) -> tuple[bool, str | None]:
    """복제 팩터 변경 검증

    복제 팩터(replication factor) 변경은 일반적으로 수동 개입이 필요합니다.
    Kafka는 자동으로 복제 팩터를 변경하지 않습니다.

    Args:
        current: 현재 복제 팩터
        target: 목표 복제 팩터

    Returns:
        (유효성, 에러 메시지) 튜플
        - 변경이 없으면: (True, None)
        - 변경이 있으면: (False, "에러 메시지")

    Example:
        >>> validate_replication_factor_change(3, 3)
        (True, None)
        >>> validate_replication_factor_change(2, 3)
        (False, 'Cannot change replication factor from 2 to 3 (requires manual intervention)')

    Note:
        복제 팩터 변경이 필요한 경우 kafka-reassign-partitions 도구를 사용해야 합니다.
    """
    if current == target:
        return True, None

    error_msg = (
        f"Cannot change replication factor from {current} to {target} "
        f"(requires manual intervention using kafka-reassign-partitions)"
    )
    return False, error_msg
