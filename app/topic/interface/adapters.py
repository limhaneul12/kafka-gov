"""Topic Interface TypeAdapter 기반 변환 어댑터"""

from __future__ import annotations

import logging

import msgspec

from ..domain.models import (
    DomainTopicAction,
    DomainTopicBatch,
    DomainTopicConfig,
    DomainTopicMetadata,
    DomainTopicPlan,
    DomainTopicSpec,
)
from .schema import (
    KafkaCoreMetadata as InterfaceKafkaCoreMetadata,
    PolicyViolation as ResponseViolation,
    TopicBatchDryRunResponse,
    TopicBatchRequest,
    TopicConfig as InterfaceTopicConfig,
    TopicItem,
    TopicPlanItem as ResponsePlanItem,
)


class TopicTypeAdapters:
    """Topic 모듈 TypeAdapter 컬렉션"""

    @classmethod
    def convert_item_to_spec(cls, item: TopicItem) -> DomainTopicSpec:
        """TopicItem을 DomainTopicSpec으로 안전하게 변환

        Args:
            item: 변환할 TopicItem

        Returns:
            변환된 DomainTopicSpec

        Raises:
            ValidationError: 변환 중 검증 실패 시
        """
        try:
            # 설정 변환
            domain_config = None
            if item.config:
                config_data = {
                    "partitions": item.config.partitions,
                    "replication_factor": item.config.replication_factor,
                    "cleanup_policy": item.config.cleanup_policy,
                    "retention_ms": item.config.retention_ms,
                    "min_insync_replicas": item.config.min_insync_replicas,
                    "max_message_bytes": item.config.max_message_bytes,
                    "segment_ms": item.config.segment_ms,
                }
                domain_config = msgspec.convert(config_data, DomainTopicConfig)

            # 메타데이터 변환
            domain_metadata = None
            if item.metadata:
                metadata_data = {
                    "owner": item.metadata.owner,
                    "doc": item.metadata.doc,
                    "tags": tuple(item.metadata.tags),
                }
                domain_metadata = msgspec.convert(metadata_data, DomainTopicMetadata)

            # TopicSpec 생성
            spec_data = {
                "name": item.name,
                "action": DomainTopicAction(item.action.value),
                "config": domain_config,
                "metadata": domain_metadata,
            }

            return msgspec.convert(spec_data, DomainTopicSpec)

        except msgspec.ValidationError as e:
            raise ValueError(f"Failed to convert TopicItem to TopicSpec: {e}") from e

    @classmethod
    def convert_request_to_batch(cls, request: TopicBatchRequest) -> DomainTopicBatch:
        """TopicBatchRequest를 TopicBatch로 안전하게 변환

        Args:
            request: 변환할 TopicBatchRequest

        Returns:
            변환된 TopicBatch

        Raises:
            ValidationError: 변환 중 검증 실패 시
        """
        try:
            # 각 아이템을 TopicSpec으로 변환
            specs = tuple(cls.convert_item_to_spec(item) for item in request.items)

            # TopicBatch 생성
            batch_data = {
                "change_id": request.change_id,
                "env": request.env,
                "specs": specs,
            }

            return msgspec.convert(batch_data, DomainTopicBatch)

        except msgspec.ValidationError as e:
            raise ValueError(f"Failed to convert TopicBatchRequest to TopicBatch: {e}") from e

    @classmethod
    def convert_plan_to_response(
        cls, plan: DomainTopicPlan, request: TopicBatchRequest
    ) -> TopicBatchDryRunResponse:
        """TopicPlan을 TopicBatchDryRunResponse로 변환

        Args:
            plan: 변환할 TopicPlan
            request: 원본 요청 (환경, change_id 참조용)

        Returns:
            변환된 TopicBatchDryRunResponse
        """
        # 계획 아이템 변환
        plan_items: list[ResponsePlanItem] = [
            ResponsePlanItem(
                name=item.name,
                action=item.action.value,
                diff=item.diff,
                current_config=item.current_config,
                target_config=item.target_config,
            )
            for item in plan.items
        ]

        # 위반 사항 변환
        violations: list[ResponseViolation] = [
            ResponseViolation(
                name=v.resource_name,
                rule=v.rule_id,
                message=v.message,
                severity=v.severity.value,
                field=v.field,
            )
            for v in plan.violations
        ]

        return TopicBatchDryRunResponse(
            env=request.env,
            change_id=request.change_id,
            plan=plan_items,
            violations=violations,
            summary=plan.summary(),
        )


def safe_convert_item_to_spec(item: TopicItem) -> DomainTopicSpec:
    """안전한 TopicItem → TopicSpec 변환 (전역 함수)"""
    return TopicTypeAdapters.convert_item_to_spec(item)


def safe_convert_request_to_batch(request: TopicBatchRequest) -> DomainTopicBatch:
    """안전한 TopicBatchRequest → TopicBatch 변환 (전역 함수)"""
    return TopicTypeAdapters.convert_request_to_batch(request)


def safe_convert_plan_to_response(
    plan: DomainTopicPlan, request: TopicBatchRequest
) -> TopicBatchDryRunResponse:
    """안전한 TopicPlan → TopicBatchDryRunResponse 변환 (전역 함수)"""
    return TopicTypeAdapters.convert_plan_to_response(plan, request)


# ===== Kafka 메타데이터 변환 유틸 =====
def _to_int(val: object) -> int | None:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        try:
            return int(val)
        except Exception:
            return None
    try:
        return int(val)  # type: ignore[arg-type]
    except Exception:
        return None


def kafka_metadata_to_interface_config(
    kafka_metadata: dict[str, object],
) -> InterfaceTopicConfig | None:
    """Kafka 원시 메타데이터(dict) → 인터페이스 TopicConfig 매핑.

    - partitions: partition_count 또는 config["num.partitions"]
    - replication_factor: replication_factor 또는 config["replication.factor"] (없으면 leader_replicas 길이)
    - 나머지 설정은 config 맵에서 선택적으로 매핑
    """

    raw_cfg = kafka_metadata.get("config")
    cfg: dict[str, object] = raw_cfg if isinstance(raw_cfg, dict) else {}

    partitions = _to_int(kafka_metadata.get("partition_count") or cfg.get("num.partitions"))

    replication_factor_obj = kafka_metadata.get("replication_factor") or cfg.get(
        "replication.factor"
    )
    replication_factor = _to_int(replication_factor_obj)
    if replication_factor is None:
        replicas = kafka_metadata.get("leader_replicas") or kafka_metadata.get("replicas")
        if isinstance(replicas, list | tuple) and len(replicas) > 0:
            replication_factor = len(replicas)

    if partitions is None or replication_factor is None:
        return None

    data: dict[str, object] = {
        "partitions": partitions,
        "replication_factor": replication_factor,
    }

    if (v := cfg.get("cleanup.policy")) is not None:
        data["cleanup_policy"] = v
    if (v := _to_int(cfg.get("retention.ms"))) is not None:
        data["retention_ms"] = v
    if (v := _to_int(cfg.get("min.insync.replicas"))) is not None:
        data["min_insync_replicas"] = v
    if (v := _to_int(cfg.get("max.message.bytes"))) is not None:
        data["max_message_bytes"] = v
    if (v := _to_int(cfg.get("segment.ms"))) is not None:
        data["segment_ms"] = v

    try:
        return InterfaceTopicConfig.model_validate(data)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to convert to InterfaceTopicConfig. data={data}, error={e}")
        return None


def kafka_metadata_to_core_metadata(
    kafka_metadata: dict[str, object],
) -> InterfaceKafkaCoreMetadata | None:
    """Kafka 원시 메타데이터(dict) → 인터페이스 KafkaCoreMetadata 매핑.

    extra="forbid" 모델이므로 필요한 필드만 추출해 모델로 검증합니다.
    """

    partitions = _to_int(kafka_metadata.get("partition_count"))
    if partitions is None:
        cfg = kafka_metadata.get("config")
        if isinstance(cfg, dict):
            partitions = _to_int(cfg.get("num.partitions"))
    if partitions is None:
        return None

    replicas_raw = kafka_metadata.get("leader_replicas") or kafka_metadata.get("replicas")
    replicas: list[int] = []
    if isinstance(replicas_raw, list | tuple):
        for r in replicas_raw:
            iv = _to_int(r)
            if iv is not None:
                replicas.append(iv)

    created_at = kafka_metadata.get("created_at")
    created_at_s = str(created_at) if created_at is not None else None

    try:
        return msgspec.convert(
            {
                "partition_count": partitions,
                "leader_replicas": replicas,
                "created_at": created_at_s,
            },
            InterfaceKafkaCoreMetadata,
        )
    except Exception:
        return None
