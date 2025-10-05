"""Shared Interface Schemas (Pydantic)"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BrokerResponse(BaseModel):
    """브로커 정보 응답 스키마"""

    model_config = ConfigDict(from_attributes=True)

    broker_id: int
    host: str
    port: int
    is_controller: bool
    leader_partition_count: int


class ClusterStatusResponse(BaseModel):
    """클러스터 상태 응답 스키마"""

    model_config = ConfigDict(from_attributes=True)

    cluster_id: str
    controller_id: int
    brokers: list[BrokerResponse]
    total_topics: int
    total_partitions: int
