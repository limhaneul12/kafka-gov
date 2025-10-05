"""공유 정책 타입 정의"""

from __future__ import annotations

from enum import Enum

import msgspec


class DomainPolicySeverity(str, Enum):
    """정책 위반 심각도"""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DomainResourceType(str, Enum):
    """리소스 타입"""

    TOPIC = "topic"
    SCHEMA = "schema"


class DomainEnvironment(str, Enum):
    """환경 타입"""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class DomainPolicyViolation(msgspec.Struct, frozen=True):
    """정책 위반 정보 (공통)"""

    resource_type: DomainResourceType
    resource_name: str
    rule_id: str
    message: str
    severity: DomainPolicySeverity
    field: str | None = None

    @property
    def is_blocking(self) -> bool:
        """차단 수준 위반 여부"""
        return self.severity in (DomainPolicySeverity.ERROR, DomainPolicySeverity.CRITICAL)
