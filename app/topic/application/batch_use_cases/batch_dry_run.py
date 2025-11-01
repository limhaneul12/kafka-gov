"""토픽 배치 Dry-Run 유스케이스"""

from __future__ import annotations

import logging

from app.cluster.domain.services import IConnectionManager
from app.shared.constants import AuditAction, AuditStatus, AuditTarget
from app.shared.domain.policy_types import (
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
)
from app.topic.domain.models import DomainTopicBatch, DomainTopicPlan, DomainTopicSpec
from app.topic.domain.policies.management import (
    IPolicyRepository,
    PolicyReference,
    PolicyStatus,
    PolicyType,
)
from app.topic.domain.policies.validation import PolicyResolver
from app.topic.domain.repositories import IAuditRepository, ITopicMetadataRepository
from app.topic.domain.services import TopicPlannerService
from app.topic.infrastructure.adapter.kafka_adapter import KafkaTopicAdapter


def _translate_policy_error(error: Exception) -> str:
    """정책 검증 에러를 사용자 친화적인 메시지로 변환

    Args:
        error: 원본 에러

    Returns:
        사용자 친화적인 에러 메시지
    """
    error_str = str(error)

    # Pydantic ValidationError 파싱
    if "validation error" in error_str.lower():
        # 정책 타입 추출
        policy_type = "정책"
        if "CustomNamingRules" in error_str:
            policy_type = "Naming 정책"
        elif "CustomGuardrailPreset" in error_str:
            policy_type = "Guardrail 정책"

        # 필수 필드 추출
        missing_fields = []
        if "pattern" in error_str and "required" in error_str:
            missing_fields.append("pattern (토픽 이름 패턴)")
        if "preset_name" in error_str and "required" in error_str:
            missing_fields.append("preset_name (프리셋 이름)")
        if "version" in error_str and "required" in error_str:
            missing_fields.append("version (버전)")

        if missing_fields:
            fields_str = "\n".join(f"  • {field}" for field in missing_fields)
            return f"{policy_type}의 필수 항목이 누락되었습니다:\n{fields_str}\n\n관리자에게 문의하거나 정책을 다시 설정해주세요."

        # 기타 검증 에러
        return f"{policy_type} 설정이 올바르지 않습니다. 관리자에게 문의해주세요."

    # Guardrail policy 필드 누락
    if "missing required fields" in error_str.lower():
        return "Guardrail 정책의 필수 항목(preset_name, version)이 누락되었습니다.\n\n정책을 다시 생성하거나 관리자에게 문의해주세요."

    # 일반 에러
    return "정책 검증 중 오류가 발생했습니다. 관리자에게 문의해주세요."


class TopicBatchDryRunUseCase:
    """토픽 배치 Dry-Run 유스케이스 (멀티 클러스터 지원)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ITopicMetadataRepository,
        audit_repository: IAuditRepository,
        policy_repository: IPolicyRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.policy_repository = policy_repository

    async def execute(
        self, cluster_id: str, batch: DomainTopicBatch, actor: str
    ) -> DomainTopicPlan:
        """Dry-Run 실행"""
        # 감사 로그 기록
        await self.audit_repository.log_topic_operation(
            change_id=batch.change_id,
            action=AuditAction.DRY_RUN,
            target=AuditTarget.BATCH,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Dry-run started for {len(batch.specs)} topics",
        )

        try:
            # 1. ConnectionManager로 AdminClient 획득
            admin_client = await self.connection_manager.get_kafka_admin_client(cluster_id)

            # 2. Adapter 생성
            topic_repository = KafkaTopicAdapter(admin_client)

            # 3. 정책 검증 (Naming + Guardrail)
            violations = await self._validate_policies(batch.specs, batch.env)

            # 4. Planner Service 생성 및 계획 수립
            planner_service = TopicPlannerService(topic_repository)  # type: ignore[arg-type]
            plan = await planner_service.create_plan(batch, actor)

            # 5. violations를 plan에 추가
            plan_with_violations = DomainTopicPlan(
                change_id=plan.change_id,
                env=plan.env,
                items=plan.items,
                violations=tuple(violations) if violations else plan.violations,
            )
            plan = plan_with_violations

            # 계획 저장
            await self.metadata_repository.save_plan(plan, actor)

            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action=AuditAction.DRY_RUN,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message=f"Dry-run completed: {len(plan.items)} items, {len(plan.violations)} violations",
                snapshot={"plan_summary": plan.summary()},
            )

            return plan

        except Exception as e:
            # 감사 로그 기록
            await self.audit_repository.log_topic_operation(
                change_id=batch.change_id,
                action=AuditAction.DRY_RUN,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Dry-run failed: {e!s}",
            )
            raise

    async def _validate_policies(self, specs: tuple[DomainTopicSpec, ...], env: str) -> list:
        """환경별 ACTIVE 정책 검증

        Args:
            specs: 검증할 토픽 스펙 목록
            env: 환경 (dev, stg, prod)

        Returns:
            violations 리스트 (빈 리스트면 정책 없음 또는 모두 통과)
        """
        logger = logging.getLogger(__name__)

        try:
            # 1. 환경별 ACTIVE 정책 조회
            naming_policy = await self._get_active_policy(PolicyType.NAMING, env)
            guardrail_policy = await self._get_active_policy(PolicyType.GUARDRAIL, env)

            # 2. 정책이 하나도 없으면 스킵
            if not naming_policy and not guardrail_policy:
                logger.info(f"No active policies for env={env}. Skipping policy validation.")
                return []

            # 3. PolicyResolver로 Validator 생성
            resolver = PolicyResolver(
                naming_policy_repo=self.policy_repository,
                guardrail_policy_repo=self.policy_repository,
            )

            # PolicyReference 생성
            naming_ref = (
                PolicyReference(policy_id=naming_policy.policy_id) if naming_policy else None
            )
            guardrail_ref = (
                PolicyReference(policy_id=guardrail_policy.policy_id) if guardrail_policy else None
            )

            validator = await resolver.resolve(naming_ref, guardrail_ref)

            if not validator:
                logger.info("No validator created. Skipping policy validation.")
                return []

            # 4. 각 spec에 대해 검증
            all_violations = []
            for spec in specs:
                violations = validator.validate(spec)
                if violations:
                    all_violations.extend(violations)
                    logger.warning(
                        f"Policy violations for {spec.name}: {[v.message for v in violations]}"
                    )

            if all_violations:
                logger.error(f"Total {len(all_violations)} policy violations found")
            else:
                logger.info("All specs passed policy validation")

            return all_violations

        except Exception as e:
            logger.error(f"Policy validation error: {e}", exc_info=True)
            # 정책 검증 에러를 violations로 반환 (사용자에게 경고 표시)
            logger.warning(
                "Policy validation failed, returning as violations for user confirmation"
            )

            # 사용자 친화적인 에러 메시지 생성
            user_friendly_message = _translate_policy_error(e)

            return [
                DomainPolicyViolation(
                    resource_type=DomainResourceType.TOPIC,
                    resource_name="POLICY_CONFIG_ERROR",
                    rule_id="policy.configuration.invalid",
                    message=user_friendly_message,
                    severity=DomainPolicySeverity.ERROR,
                    field=None,
                )
            ]

    async def _get_active_policy(self, policy_type: PolicyType, env: str):
        """환경별 ACTIVE 정책 조회 (우선순위: env-specific > total)

        Args:
            policy_type: 정책 타입 (naming/guardrail)
            env: 환경 (dev/stg/prod)

        Returns:
            StoredPolicy 또는 None
        """
        policies = await self.policy_repository.list_policies(
            policy_type=policy_type,
            status=PolicyStatus.ACTIVE,
        )

        # env-specific 정책 우선
        for policy in policies:
            if policy.target_environment == env:
                return policy

        # total (global) 정책 fallback
        for policy in policies:
            if policy.target_environment == "total":
                return policy

        # 정책 없음
        return None
