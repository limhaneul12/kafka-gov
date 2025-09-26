"""Schema Interface Enum 정의"""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    """배포 환경 구분"""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class SchemaType(str, Enum):
    """스키마 타입 (Confluent Schema Registry 지원 포맷)"""

    AVRO = "AVRO"
    JSON = "JSON"
    PROTOBUF = "PROTOBUF"


class CompatibilityMode(str, Enum):
    """스키마 호환성 모드"""

    NONE = "NONE"
    BACKWARD = "BACKWARD"
    BACKWARD_TRANSITIVE = "BACKWARD_TRANSITIVE"
    FORWARD = "FORWARD"
    FORWARD_TRANSITIVE = "FORWARD_TRANSITIVE"
    FULL = "FULL"
    FULL_TRANSITIVE = "FULL_TRANSITIVE"


class SubjectStrategy(str, Enum):
    """스키마 레지스트리 주제 전략"""

    TOPIC_NAME = "TopicNameStrategy"
    RECORD_NAME = "RecordNameStrategy"
    TOPIC_RECORD_NAME = "TopicRecordNameStrategy"


class SchemaSourceType(str, Enum):
    """스키마 소스 타입"""

    INLINE = "inline"
    FILE = "file"
    YAML = "yaml"
