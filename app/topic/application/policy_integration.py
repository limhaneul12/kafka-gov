"""Topic 모듈과 Policy 모듈 통합"""

from __future__ import annotations

from ...policy import (
    Environment,
    PolicyEvaluationService,
    PolicyTarget,
    PolicyViolation,
    ResourceType,
)
from ..domain.models import TopicSpec


class TopicPolicyAdapter:
    """Topic과 Policy 모듈 간 어댑터"""

    def __init__(self, policy_service: PolicyEvaluationService) -> None:
        self._policy_service = policy_service

    async def validate_topic_specs(
        self,
        environment: Environment,
        topic_specs: list[TopicSpec],
        actor: str,
    ) -> list[PolicyViolation]:
        """Topic 스펙들을 정책으로 검증

        Args:
            environment: 대상 환경
            topic_specs: 검증할 토픽 스펙 목록
            actor: 요청자

        Returns:
            정책 위반 목록
        """
        # TopicSpec을 PolicyTarget으로 변환
        policy_targets = [self._convert_topic_spec_to_policy_target(spec) for spec in topic_specs]

        # 정책 평가 실행
        return await self._policy_service.evaluate_batch(
            environment=environment,
            resource_type=ResourceType.TOPIC,
            targets=policy_targets,
            actor=actor,
        )

    async def validate_single_topic(
        self,
        environment: Environment,
        topic_spec: TopicSpec,
        actor: str,
    ) -> list[PolicyViolation]:
        """단일 토픽 스펙 검증"""
        return await self.validate_topic_specs(
            environment=environment,
            topic_specs=[topic_spec],
            actor=actor,
        )

    def _convert_topic_spec_to_policy_target(self, topic_spec: TopicSpec) -> PolicyTarget:
        """TopicSpec을 PolicyTarget으로 변환"""
        config_dict = {}

        # 기본 설정값들을 dict로 변환
        if topic_spec.partitions is not None:
            config_dict["partitions"] = topic_spec.partitions
        if topic_spec.replication_factor is not None:
            config_dict["replication.factor"] = topic_spec.replication_factor

        # 추가 설정이 있다면 병합
        if topic_spec.config:
            config_dict.update(topic_spec.config)

        return {
            "name": topic_spec.name,
            "config": config_dict,
            "metadata": {
                "owner": topic_spec.metadata.owner if topic_spec.metadata else None,
                "sla": topic_spec.metadata.sla if topic_spec.metadata else None,
                "doc": topic_spec.metadata.doc if topic_spec.metadata else None,
                "tags": topic_spec.metadata.tags if topic_spec.metadata else [],
            }
            if topic_spec.metadata
            else {},
        }

    def has_blocking_violations(self, violations: list[PolicyViolation]) -> bool:
        """차단 수준의 위반이 있는지 확인"""
        return self._policy_service.has_blocking_violations(violations)


def create_topic_policy_adapter(policy_service: PolicyEvaluationService) -> TopicPolicyAdapter:
    """TopicPolicyAdapter 팩토리 함수"""
    return TopicPolicyAdapter(policy_service)
