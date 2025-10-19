"""Schema Domain Enums"""

from __future__ import annotations

from enum import Enum


class DomainEnvironment(str, Enum):
    """배포 환경"""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class DomainSchemaType(str, Enum):
    """Schema Registry 지원 스키마 타입"""

    AVRO = "AVRO"
    JSON = "JSON"
    PROTOBUF = "PROTOBUF"


class DomainCompatibilityMode(str, Enum):
    """스키마 호환성 모드"""

    NONE = "NONE"
    BACKWARD = "BACKWARD"
    BACKWARD_TRANSITIVE = "BACKWARD_TRANSITIVE"
    FORWARD = "FORWARD"
    FORWARD_TRANSITIVE = "FORWARD_TRANSITIVE"
    FULL = "FULL"
    FULL_TRANSITIVE = "FULL_TRANSITIVE"


class DomainSubjectStrategy(str, Enum):
    """스키마 주제 전략"""

    TOPIC_NAME = "TopicNameStrategy"
    RECORD_NAME = "RecordNameStrategy"
    TOPIC_RECORD_NAME = "TopicRecordNameStrategy"


class DomainSchemaSourceType(str, Enum):
    """스키마 소스 타입"""

    INLINE = "inline"
    FILE = "file"
    YAML = "yaml"


class DomainPlanAction(str, Enum):
    """배치 계획 액션"""

    REGISTER = "REGISTER"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    NONE = "NONE"
