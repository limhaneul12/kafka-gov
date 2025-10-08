"""Topic Domain 서비스 - 도메인 로직 캡슐화"""

from __future__ import annotations

from typing import Any

from .models import (
    DomainPlanAction,
    DomainTopicBatch,
    DomainTopicConfig,
    DomainTopicPlan,
    DomainTopicPlanItem,
    DomainTopicSpec,
)
from .policies import TopicPolicyEngine
from .repositories.interfaces import ITopicRepository
from .utils import (
    calculate_dict_diff,
    format_diff_string,
    validate_partition_change,
    validate_replication_factor_change,
)


class TopicPlannerService:
    """토픽 계획 수립 서비스"""

    def __init__(
        self,
        topic_repository: ITopicRepository,
        policy_engine: TopicPolicyEngine | None = None,
    ) -> None:
        self.topic_repository = topic_repository
        self.policy_engine = policy_engine or TopicPolicyEngine()

    async def create_plan(self, batch: DomainTopicBatch, actor: str = "system") -> DomainTopicPlan:
        """배치에 대한 실행 계획 생성"""

        # 직접 정책 검증
        violations = self.policy_engine.validate_batch(list(batch.specs))

        # 현재 토픽 상태 조회
        topic_names: list[str] = [spec.name for spec in batch.specs]
        current_topics = await self.topic_repository.describe_topics(topic_names)

        # 계획 아이템 생성
        plan_items: list[DomainTopicPlanItem] = [
            item
            for spec in batch.specs
            if (item := self._create_plan_item(spec, current_topics.get(spec.name))) is not None
        ]

        return DomainTopicPlan(
            change_id=batch.change_id,
            env=batch.env,
            items=tuple(plan_items),
            violations=tuple(violations),
        )

    def _create_plan_item(
        self, spec: DomainTopicSpec, current_topic: dict[str, Any] | None
    ) -> DomainTopicPlanItem | None:
        """개별 토픽에 대한 계획 아이템 생성"""
        if spec.action.value == "delete":
            if current_topic is None:
                # 삭제하려는 토픽이 존재하지 않음 - 스킵
                return None

            return DomainTopicPlanItem(
                name=spec.name,
                action=DomainPlanAction.DELETE,
                diff={"status": "exists→deleted"},
                current_config=current_topic.get("config", {}),
                target_config=None,
            )

        if current_topic is None:
            # 새 토픽 생성
            return DomainTopicPlanItem(
                name=spec.name,
                action=DomainPlanAction.CREATE,
                diff={"status": "new→created"},
                current_config=None,
                target_config=self._spec_to_config_dict(spec),
            )

        # 기존 토픽 수정
        current_config = current_topic.get("config", {})
        target_config: dict[str, str] = self._spec_to_config_dict(spec)
        diff: dict = self._calculate_config_diff(current_config, target_config)

        if not diff:
            # 변경 사항 없음 - 스킵
            return None

        return DomainTopicPlanItem(
            name=spec.name,
            action=DomainPlanAction.ALTER,
            diff=diff,
            current_config=current_config,
            target_config=target_config,
        )

    def _spec_to_config_dict(self, spec: DomainTopicSpec) -> dict[str, str]:
        """토픽 명세를 설정 딕셔너리로 변환"""
        if not spec.config:
            return {}

        config_dict: dict[str, str] = {
            "partitions": str(spec.config.partitions),
            "replication_factor": str(spec.config.replication_factor),
        }
        # Kafka 설정은 이미 문자열로 반환됨
        config_dict.update(spec.config.to_kafka_config())

        return config_dict

    def _calculate_config_diff(self, current: dict[str, Any], target: dict[str, Any]) -> dict:
        """설정 변경 사항 계산 (공통 유틸리티 사용)"""
        raw_diff = calculate_dict_diff(current, target)

        # 사람이 읽기 쉬운 형태로 변환
        return {
            key: format_diff_string(curr_val, tgt_val)
            for key, (curr_val, tgt_val) in raw_diff.items()
        }


class TopicDiffService:
    """토픽 차이 분석 서비스"""

    @staticmethod
    def compare_configs(
        current: DomainTopicConfig | None, target: DomainTopicConfig | None
    ) -> dict[str, tuple[Any, Any]] | None:
        """토픽 설정 비교 (공통 유틸리티 사용)"""
        if current is None and target is None:
            return {}

        if current is None:
            if target is not None:
                return {
                    "partitions": (None, target.partitions),
                    "replication_factor": (None, target.replication_factor),
                    **{k: (None, v) for k, v in target.to_kafka_config().items()},
                }
            return {}

        if target is None and current is not None:
            return {
                "partitions": (current.partitions, None),
                "replication_factor": (current.replication_factor, None),
                **{k: (v, None) for k, v in current.to_kafka_config().items()},
            }

        # 이 시점에서 current와 target 모두 None이 아님이 보장됨
        assert current is not None and target is not None

        # 기본 설정을 딕셔너리로 변환
        current_full: dict[str, Any] = {
            "partitions": current.partitions,
            "replication_factor": current.replication_factor,
            **current.to_kafka_config(),
        }

        target_full: dict[str, Any] = {
            "partitions": target.partitions,
            "replication_factor": target.replication_factor,
            **target.to_kafka_config(),
        }

        # 공통 유틸리티 함수 사용
        return calculate_dict_diff(current_full, target_full)

    @staticmethod
    def is_partition_increase_only(current_partitions: int, target_partitions: int) -> bool:
        """파티션 수가 증가만 하는지 확인 (Kafka는 파티션 감소 불가)

        Note:
            utils.validate_partition_change()를 사용하는 것을 권장합니다.
        """
        return validate_partition_change(current_partitions, target_partitions)

    @staticmethod
    def validate_config_changes(
        current: DomainTopicConfig | None,
        target: DomainTopicConfig | None,
    ) -> list[str]:
        """설정 변경 유효성 검증 (공통 유틸리티 사용)"""
        errors = []

        if current is None or target is None:
            return errors

        # 파티션 수 검증 (utils 사용)
        if not validate_partition_change(current.partitions, target.partitions):
            errors.append(
                f"Cannot decrease partitions from {current.partitions} to {target.partitions}. "
                f"Kafka does not support partition reduction. Consider creating a new topic."
            )

        # 복제 팩터 검증 (utils 사용)
        is_valid, error_msg = validate_replication_factor_change(
            current.replication_factor, target.replication_factor
        )
        if not is_valid and error_msg:
            errors.append(error_msg)

        return errors
