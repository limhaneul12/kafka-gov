from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from tests.domain_case_factory import build_domain_case_matrix


def _flatten_domain_cases() -> list[dict[str, Any]]:
    matrix = build_domain_case_matrix()
    flattened: list[dict[str, Any]] = []
    for _, cases in matrix.items():
        flattened.extend(cases)
    return flattened


ALL_DOMAIN_CASES = _flatten_domain_cases()


@pytest.mark.parametrize(
    "case",
    ALL_DOMAIN_CASES,
    ids=lambda case: f"{case['domain']}::{case['name']}",
)
def test_domain_mock_matrix(case: dict[str, Any]) -> None:
    run = case["run"]
    expect_error = case.get("expect_error")

    if expect_error is not None:
        with pytest.raises(expect_error):
            run()
        return

    result = run()
    assertion: Callable[[Any], bool] | None = case.get("assert")
    if assertion is not None:
        assert assertion(result)


def test_domain_case_matrix_contains_all_domains() -> None:
    matrix = build_domain_case_matrix()
    assert set(matrix.keys()) == {"registry_connections", "schema", "shared"}
    assert all(len(cases) >= 2 for cases in matrix.values())
