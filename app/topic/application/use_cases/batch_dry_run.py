"""토픽 배치 Dry-Run 유스케이스"""

from __future__ import annotations

import logging

from app.cluster.domain.services import IConnectionManager
from app.shared.constants import AuditAction, AuditStatus, AuditTarget
from app.topic.infrastructure.kafka_adapter import KafkaTopicAdapter

from ...domain.models import DomainTopicBatch, DomainTopicPlan, DomainTopicSpec
from ...domain.policies.management import (
    IPolicyRepository,
    PolicyReference,
    PolicyStatus,
    PolicyType,
)
from ...domain.policies.validation import PolicyResolver
from ...domain.repositories.interfaces import IAuditRepository, ITopicMetadataRepository
from ...domain.services import TopicPlannerService


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
            # 정책 검증 에러는 fail-open (통과) 처리
            # 정책 시스템 장애 시 토픽 생성이 막히지 않도록
            logger.warning("Policy validation failed, allowing operation (fail-open)")
            return []

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
