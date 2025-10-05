"""Topic Adapters 최적화 테스트"""

import pytest

from app.topic.interface.adapters import _to_int


class TestToIntOptimization:
    """_to_int() 함수 최적화 테스트"""

    def test_none_returns_none(self):
        """None 입력 시 None 반환"""
        assert _to_int(None) is None

    def test_int_returns_same(self):
        """int 입력 시 그대로 반환"""
        assert _to_int(42) == 42
        assert _to_int(0) == 0
        assert _to_int(-10) == -10

    def test_valid_string_converts_to_int(self):
        """유효한 문자열은 int로 변환"""
        assert _to_int("42") == 42
        assert _to_int("0") == 0
        assert _to_int("-10") == -10
        assert _to_int("  100  ") == 100  # 공백 포함

    def test_invalid_string_returns_none(self):
        """무효한 문자열은 None 반환"""
        assert _to_int("abc") is None
        assert _to_int("12.5") is None
        assert _to_int("") is None
        assert _to_int("  ") is None

    def test_float_converts_to_int(self):
        """float은 int로 변환 (소수점 버림)"""
        assert _to_int(42.7) == 42
        assert _to_int(42.3) == 42
        assert _to_int(-10.9) == -10

    def test_bool_converts_to_int(self):
        """bool은 int로 변환"""
        assert _to_int(True) == 1
        assert _to_int(False) == 0

    def test_list_returns_none(self):
        """list는 None 반환"""
        assert _to_int([1, 2, 3]) is None
        assert _to_int([]) is None

    def test_dict_returns_none(self):
        """dict는 None 반환"""
        assert _to_int({"key": "value"}) is None
        assert _to_int({}) is None

    def test_object_returns_none(self):
        """일반 object는 None 반환"""

        class CustomObject:
            pass

        assert _to_int(CustomObject()) is None

    def test_performance_improvement(self):
        """성능 개선 확인 - early return 검증"""
        # None과 int는 즉시 반환되어야 함
        import time

        # int 케이스 (빠름)
        start = time.perf_counter()
        for _ in range(10000):
            _to_int(42)
        int_time = time.perf_counter() - start

        # 문자열 변환 케이스 (느림)
        start = time.perf_counter()
        for _ in range(10000):
            _to_int("42")
        str_time = time.perf_counter() - start

        # int가 문자열보다 빨라야 함
        assert int_time < str_time

    def test_edge_cases(self):
        """경계값 테스트"""
        assert _to_int(2**31 - 1) == 2**31 - 1  # 최대값
        assert _to_int(-(2**31)) == -(2**31)  # 최소값
        assert _to_int("9999999999999999999") == 9999999999999999999  # 큰 수
