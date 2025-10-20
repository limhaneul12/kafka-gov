"""Dry-Run 리포트 Domain 모델"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types_enum import TopicName


@dataclass(frozen=True, slots=True)
class ViolationDetail:
    """정책 위반 상세 정보"""

    target: str
    policy_type: str
    message: str
    level: str  # "error" | "warning"


@dataclass(frozen=True, slots=True)
class DryRunItemReport:
    """개별 토픽 Dry-Run 결과"""

    name: TopicName
    action: str
    diff: dict[str, Any]
    violations: tuple[ViolationDetail, ...]


@dataclass(frozen=True, slots=True)
class DryRunSummary:
    """Dry-Run 요약 정보"""

    total_items: int
    total_violations: int
    error_violations: int
    can_apply: bool


@dataclass(frozen=True, slots=True)
class DryRunReport:
    """Dry-Run 전체 리포트 (Domain)"""

    change_id: str
    env: str
    summary: DryRunSummary
    items: tuple[DryRunItemReport, ...]
    violations: tuple[ViolationDetail, ...]

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환 (orjson serialization용)"""
        return {
            "change_id": self.change_id,
            "env": self.env,
            "summary": {
                "total_items": self.summary.total_items,
                "total_violations": self.summary.total_violations,
                "error_violations": self.summary.error_violations,
                "can_apply": self.summary.can_apply,
            },
            "items": [
                {
                    "name": str(item.name),
                    "action": item.action,
                    "diff": item.diff,
                    "violations": [
                        {
                            "target": v.target,
                            "policy_type": v.policy_type,
                            "message": v.message,
                            "level": v.level,
                        }
                        for v in item.violations
                    ],
                }
                for item in self.items
            ],
            "violations": [
                {
                    "target": v.target,
                    "policy_type": v.policy_type,
                    "message": v.message,
                    "level": v.level,
                }
                for v in self.violations
            ],
        }
