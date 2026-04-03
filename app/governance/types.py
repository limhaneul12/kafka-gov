"""거버넌스 정책/컴플라이언스 모듈 타입 정의"""

from __future__ import annotations

from enum import StrEnum, unique
from typing import TypeAlias

PolicyId: TypeAlias = str
RuleId: TypeAlias = str
ApprovalId: TypeAlias = str


@unique
class PolicyType(StrEnum):
    """정책 유형"""

    NAMING = "naming"
    GUARDRAIL = "guardrail"
    QUALITY = "quality"
    SECURITY = "security"
    RETENTION = "retention"


@unique
class PolicyStatus(StrEnum):
    """정책 상태"""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


@unique
class RiskLevel(StrEnum):
    """위험 수준"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@unique
class ApprovalStatus(StrEnum):
    """승인 상태"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@unique
class PolicyScope(StrEnum):
    """정책 적용 범위"""

    GLOBAL = "global"
    DOMAIN = "domain"
    PRODUCT = "product"
    CONTRACT = "contract"
