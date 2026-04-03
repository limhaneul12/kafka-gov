"""공통 타입 정의 — 시스템 전역에서 사용되는 TypeAlias 및 StrEnum

모든 모듈이 공유하는 기본 식별자 타입과 분류 열거형을 정의한다.
모듈 고유 타입은 각 모듈의 types.py에서 정의한다.
"""

from __future__ import annotations

from enum import StrEnum, unique
from typing import TypeAlias

# ============================================================================
# Type Aliases — 도메인 식별자
# ============================================================================

ProductId: TypeAlias = str
ContractId: TypeAlias = str
TeamId: TypeAlias = str
DomainName: TypeAlias = str
TagValue: TypeAlias = str


# ============================================================================
# Enumerations — 시스템 전역 분류
# ============================================================================


@unique
class DataClassification(StrEnum):
    """데이터 등급 분류 — 접근 제어 및 보존 정책의 기준"""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

    @property
    def sensitivity_order(self) -> int:
        return {
            DataClassification.PUBLIC: 0,
            DataClassification.INTERNAL: 1,
            DataClassification.CONFIDENTIAL: 2,
            DataClassification.RESTRICTED: 3,
        }[self]

    def __gt__(self, other: DataClassification) -> bool:
        return self.sensitivity_order > other.sensitivity_order

    def __ge__(self, other: DataClassification) -> bool:
        return self.sensitivity_order >= other.sensitivity_order


@unique
class Lifecycle(StrEnum):
    """데이터 제품 생명주기 상태"""

    INCUBATION = "incubation"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"

    @property
    def is_mutable(self) -> bool:
        return self in (Lifecycle.INCUBATION, Lifecycle.ACTIVE)

    @property
    def is_discoverable(self) -> bool:
        return self in (Lifecycle.ACTIVE, Lifecycle.DEPRECATED)


@unique
class Environment(StrEnum):
    """배포 환경"""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"


@unique
class InfraType(StrEnum):
    """데이터 제품의 물리적 구현 유형"""

    KAFKA_TOPIC = "kafka_topic"
    DATABASE_TABLE = "database_table"
    S3_BUCKET = "s3_bucket"
    API_ENDPOINT = "api_endpoint"
    FLINK_JOB = "flink_job"


@unique
class SchemaFormat(StrEnum):
    """스키마 직렬화 형식"""

    AVRO = "avro"
    JSON_SCHEMA = "json_schema"
    PROTOBUF = "protobuf"


@unique
class CompatibilityMode(StrEnum):
    """스키마 호환성 모드"""

    NONE = "NONE"
    BACKWARD = "BACKWARD"
    BACKWARD_TRANSITIVE = "BACKWARD_TRANSITIVE"
    FORWARD = "FORWARD"
    FORWARD_TRANSITIVE = "FORWARD_TRANSITIVE"
    FULL = "FULL"
    FULL_TRANSITIVE = "FULL_TRANSITIVE"


@unique
class QualityDimension(StrEnum):
    """데이터 품질 차원 (ISO 25012 기반)"""

    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"


@unique
class LineageDirection(StrEnum):
    """리니지 탐색 방향"""

    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"
    BOTH = "both"
