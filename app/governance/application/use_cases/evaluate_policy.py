"""정책 평가 유스케이스 — 대상 리소스에 활성 정책을 적용하고 위반 사항을 반환"""

from __future__ import annotations

import logging
from datetime import datetime

from app.governance.domain.models.commands import EvaluatePolicyCommand
from app.governance.domain.models.governance import (
    GovernancePolicy,
    PolicyEvaluation,
    PolicyViolation,
)
from app.governance.domain.models.queries import EvaluationSummary
from app.governance.domain.repositories.governance_repository import (
    IPolicyEvaluationRepository,
    IPolicyRepository,
)

logger = logging.getLogger(__name__)


class EvaluatePolicyUseCase:
    """대상 리소스에 활성 정책을 일괄 적용

    비즈니스 규칙:
    - scope/도메인/환경 필터에 매치되는 활성 정책만 적용
    - 각 정책의 규칙을 실행하여 위반 목록 생성
    - critical 위반이 있으면 승인 필요 플래그 설정
    """

    def __init__(
        self,
        policy_repository: IPolicyRepository,
        evaluation_repository: IPolicyEvaluationRepository,
    ) -> None:
        self._policy_repo = policy_repository
        self._eval_repo = evaluation_repository

    async def execute(self, command: EvaluatePolicyCommand) -> EvaluationSummary:
        policies = await self._policy_repo.list_active()

        applicable: list[GovernancePolicy] = [
            p
            for p in policies
            if p.applies_to(
                domain=command.domain,
                environment=command.environment,
                product_id=command.product_id,
            )
        ]

        evaluations: list[PolicyEvaluation] = []
        total_violations = 0
        has_critical = False

        for policy in applicable:
            violations = self._run_policy(policy, command)
            score = max(0.0, 1.0 - len(violations) * 0.1)

            evaluation = PolicyEvaluation(
                policy_id=policy.policy_id,
                policy_name=policy.name,
                target_id=command.target_id,
                violations=tuple(violations),
                evaluated_at=datetime.now(),
                score=score,
            )

            await self._eval_repo.save(evaluation)
            evaluations.append(evaluation)

            total_violations += len(violations)
            if evaluation.has_critical:
                has_critical = True

        overall_score = sum(e.score for e in evaluations) / len(evaluations) if evaluations else 1.0

        logger.info(
            "policy_evaluation_completed",
            extra={
                "target_id": command.target_id,
                "policies_evaluated": len(evaluations),
                "total_violations": total_violations,
                "has_critical": has_critical,
            },
        )

        return EvaluationSummary(
            evaluations=evaluations,
            total_violations=total_violations,
            has_critical=has_critical,
            overall_score=overall_score,
            requires_approval=has_critical,
        )

    def _run_policy(
        self,
        policy: GovernancePolicy,
        command: EvaluatePolicyCommand,
    ) -> list[PolicyViolation]:
        """정책의 각 규칙을 실행하여 위반 목록을 반환

        NOTE: 실제 규칙 실행 로직은 인프라 레이어의 policy engine에 위임한다.
        여기서는 규칙 메타데이터 기반의 기본 검증만 수행.
        확장 시 PolicyEngine 포트를 주입받아 사용.
        """
        violations: list[PolicyViolation] = [
            PolicyViolation(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                message=rule.message,
                severity=rule.severity,
                resource_id=command.target_id,
                resource_type=command.target_type,
            )
            for rule in policy.rules
        ]

        return violations
