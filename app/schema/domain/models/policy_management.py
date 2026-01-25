"""Schema Policy Management Domain Models"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SchemaPolicyType(str, Enum):
    """스키마 정책 타입"""

    LINT = "lint"  # 내용 검사 (doc, nullable, naming 등)
    GUARDRAIL = "guardrail"  # 운영 환경 제약 (compatibility 등)


class SchemaPolicyStatus(str, Enum):
    """스키마 정책 상태"""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class DomainSchemaPolicy:
    """사용자 정의 스키마 정책 - Entity"""

    policy_id: str
    policy_type: SchemaPolicyType
    name: str
    description: str
    version: int
    status: SchemaPolicyStatus

    # 정책 내용 (JSON 직렬화 가능 구조)
    # LINT: 각 룰 활성화 여부 및 파라미터
    # GUARDRAIL: 환경별 호환성 제약 등
    content: dict[str, Any]

    # 적용 환경 (dev, stg, prod, total)
    target_environment: str = "total"

    created_by: str = ""
    created_at: str = ""
    updated_at: str | None = None
    activated_at: str | None = None


@dataclass(frozen=True, slots=True)
class SchemaPolicyHistoryItem:
    """스키마 정책 이력 항목 - Value Object"""

    version: int
    status: SchemaPolicyStatus
    created_by: str
    created_at: str
    description: str | None = None
