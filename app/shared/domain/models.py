"""Shared Domain Models"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import msgspec


class AuditActivity(msgspec.Struct, frozen=True, kw_only=True):
    """감사 활동 도메인 모델 (불변)"""

    activity_type: str  # "topic" | "schema"
    action: str  # CREATE, UPDATE, DELETE,ADD, etc.
    target: str  # 대상 이름
    message: str  # 포맷된 메시지
    actor: str  # 작업자
    team: str | None = None  # 팀 (토픽 소유자)
    timestamp: datetime
    metadata: dict[str, Any] | None = None  # 추가 메타데이터


class BrokerInfo(msgspec.Struct, frozen=True, kw_only=True):
    """Kafka 브로커 정보 도메인 모델 (불변)"""

    broker_id: int  # 브로커 ID
    host: str  # 호스트
    port: int  # 포트
    is_controller: bool  # 컨트롤러 여부
    leader_partition_count: int  # 리더 파티션 수
    disk_usage_bytes: int | None = None  # 디스크 사용량 (bytes)


class ClusterStatus(msgspec.Struct, frozen=True, kw_only=True):
    """Kafka 클러스터 상태 도메인 모델 (불변)"""

    cluster_id: str  # 클러스터 ID
    controller_id: int  # 컨트롤러 브로커 ID
    brokers: tuple[BrokerInfo, ...]  # 브로커 목록
    total_topics: int  # 전체 토픽 수
    total_partitions: int  # 전체 파티션 수
