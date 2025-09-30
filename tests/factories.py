"""테스트용 팩토리 함수들"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def create_test_schema_data(
    *,
    subject: str = "test-subject",
    version: int = 1,
    schema_type: str = "AVRO",
    schema_str: str | None = None,
    compatibility: str = "BACKWARD",
) -> dict[str, Any]:
    """테스트용 스키마 데이터 생성"""
    if schema_str is None:
        schema_str = """{
            "type": "record",
            "name": "TestRecord",
            "namespace": "com.example",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "value", "type": "int"}
            ]
        }"""

    return {
        "subject": subject,
        "version": version,
        "schema_type": schema_type,
        "schema_str": schema_str,
        "compatibility": compatibility,
        "created_at": datetime.now(UTC),
    }


def create_test_topic_data(
    *,
    name: str = "test-topic",
    partitions: int = 3,
    replication_factor: int = 1,
    config: dict[str, str] | None = None,
) -> dict[str, Any]:
    """테스트용 토픽 데이터 생성"""
    if config is None:
        config = {
            "retention.ms": "86400000",
            "cleanup.policy": "delete",
        }

    return {
        "name": name,
        "partitions": partitions,
        "replication_factor": replication_factor,
        "config": config,
        "created_at": datetime.now(UTC),
    }


def create_test_policy_data(
    *,
    name: str = "test-policy",
    description: str = "Test policy description",
    rule_type: str = "NAMING",
    pattern: str = "^[a-z-]+$",
    severity: str = "ERROR",
    enabled: bool = True,
) -> dict[str, Any]:
    """테스트용 정책 데이터 생성"""
    return {
        "name": name,
        "description": description,
        "rule_type": rule_type,
        "pattern": pattern,
        "severity": severity,
        "enabled": enabled,
        "created_at": datetime.now(UTC),
    }


def create_test_analysis_result_data(
    *,
    topic_name: str = "test-topic",
    analysis_type: str = "COMPATIBILITY",
    status: str = "SUCCESS",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """테스트용 분석 결과 데이터 생성"""
    if details is None:
        details = {
            "checks_passed": 5,
            "checks_failed": 0,
            "warnings": [],
        }

    return {
        "topic_name": topic_name,
        "analysis_type": analysis_type,
        "status": status,
        "details": details,
        "created_at": datetime.now(UTC),
    }
