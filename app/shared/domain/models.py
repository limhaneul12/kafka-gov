"""Shared Domain Models"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True, kw_only=True)
class AuditActivity:
    """감사 활동 도메인 모델 - Value Object"""

    activity_type: str  # "topic" | "schema"
    action: str  # CREATE, UPDATE, DELETE,ADD, etc.
    target: str  # 대상 이름
    message: str  # 포맷된 메시지
    actor: str  # 작업자
    team: str | None = None  # 팀 (토픽 소유자)
    timestamp: datetime
    metadata: dict[str, Any] | None = None  # 추가 메타데이터
