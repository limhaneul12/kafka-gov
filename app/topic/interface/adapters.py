"""Topic Interface TypeAdapter 기반 변환 어댑터"""

from __future__ import annotations

from pydantic import TypeAdapter, ValidationError

from ..domain.models import (
    TopicAction as DomainTopicAction,
    TopicBatch,
    TopicConfig as DomainTopicConfig,
    TopicMetadata as DomainTopicMetadata,
    TopicPlan,
    TopicSpec as DomainTopicSpec,
)
from .schema import (
    PolicyViolation as ResponseViolation,
    TopicBatchDryRunResponse,
    TopicBatchRequest,
    TopicItem,
    TopicPlanItem as ResponsePlanItem,
)


class TopicTypeAdapters:
    """Topic 모듈 TypeAdapter 컬렉션"""
    
    # Domain 모델 어댑터들
    topic_spec_adapter = TypeAdapter[DomainTopicSpec]
    topic_config_adapter = TypeAdapter[DomainTopicConfig]
    topic_metadata_adapter = TypeAdapter[DomainTopicMetadata]
    topic_batch_adapter = TypeAdapter[TopicBatch]
    
    # Interface 모델 어댑터들
    topic_item_adapter = TypeAdapter[TopicItem]
    topic_batch_request_adapter = TypeAdapter[TopicBatchRequest]
    
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
                    "compression_type": item.config.compression_type,
                    "retention_ms": item.config.retention_ms,
                    "min_insync_replicas": item.config.min_insync_replicas,
                    "max_message_bytes": item.config.max_message_bytes,
                    "segment_ms": item.config.segment_ms,
                }
                domain_config = cls.topic_config_adapter.validate_python(config_data)

            # 메타데이터 변환
            domain_metadata = None
            if item.metadata:
                metadata_data = {
                    "owner": item.metadata.owner,
                    "sla": item.metadata.sla,
                    "doc": item.metadata.doc,
                    "tags": tuple(item.metadata.tags),
                }
                domain_metadata = cls.topic_metadata_adapter.validate_python(metadata_data)

            # TopicSpec 생성
            spec_data = {
                "name": item.name,
                "action": DomainTopicAction(item.action.value),
                "config": domain_config,
                "metadata": domain_metadata,
                "reason": item.reason,
            }
            
            return cls.topic_spec_adapter.validate_python(spec_data)
            
        except ValidationError as e:
            raise ValueError(f"Failed to convert TopicItem to TopicSpec: {e}") from e

    @classmethod
    def convert_request_to_batch(cls, request: TopicBatchRequest) -> TopicBatch:
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
            
            return cls.topic_batch_adapter.validate_python(batch_data)
            
        except ValidationError as e:
            raise ValueError(f"Failed to convert TopicBatchRequest to TopicBatch: {e}") from e

    @classmethod
    def convert_plan_to_response(
        cls, plan: TopicPlan, request: TopicBatchRequest
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
                name=v.name,
                rule=v.rule,
                message=v.message,
                severity=v.severity,
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


# 전역 어댑터 인스턴스 (성능 최적화)
topic_adapters = TopicTypeAdapters()


def safe_convert_item_to_spec(item: TopicItem) -> DomainTopicSpec:
    """안전한 TopicItem → TopicSpec 변환 (전역 함수)"""
    return topic_adapters.convert_item_to_spec(item)


def safe_convert_request_to_batch(request: TopicBatchRequest) -> TopicBatch:
    """안전한 TopicBatchRequest → TopicBatch 변환 (전역 함수)"""
    return topic_adapters.convert_request_to_batch(request)


def safe_convert_plan_to_response(
    plan: TopicPlan, request: TopicBatchRequest
) -> TopicBatchDryRunResponse:
    """안전한 TopicPlan → TopicBatchDryRunResponse 변환 (전역 함수)"""
    return topic_adapters.convert_plan_to_response(plan, request)
