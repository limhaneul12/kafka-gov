from __future__ import annotations

from dataclasses import dataclass

from app.shared.domain.policy_types import (
    DomainPolicySeverity,
    DomainPolicyViolation,
    DomainResourceType,
)
from app.shared.domain.preflight_policy import (
    DomainPolicyDecision,
    DomainPolicyPackEvaluation,
    DomainPolicyRuleResult,
    DomainRiskLevel,
)
from app.topic.domain.models import DomainTopicBatch, DomainTopicPlan
from app.topic.domain.models.types_enum import DomainEnvironment

DEFAULT_TOPIC_POLICY_PACK_V1 = "policy-pack.v1.topic.default"


@dataclass(frozen=True, slots=True)
class TopicPolicyPackResult:
    violations: tuple[DomainPolicyViolation, ...]
    evaluation: DomainPolicyPackEvaluation


class DefaultTopicPolicyPackV1:
    def evaluate(self, batch: DomainTopicBatch, plan: DomainTopicPlan) -> TopicPolicyPackResult:
        base_rules = tuple(self._rule_from_violation(violation) for violation in plan.violations)
        custom_rules = tuple(self._build_custom_rules(batch, plan))
        all_rules = base_rules + custom_rules

        return TopicPolicyPackResult(
            violations=plan.violations
            + tuple(
                self._violation_from_rule(rule)
                for rule in custom_rules
                if rule.decision is not DomainPolicyDecision.WARN
            )
            + tuple(
                self._violation_from_rule(rule)
                for rule in custom_rules
                if rule.decision is DomainPolicyDecision.WARN
            ),
            evaluation=DomainPolicyPackEvaluation(
                pack_name=DEFAULT_TOPIC_POLICY_PACK_V1,
                resource_type=DomainResourceType.TOPIC,
                rules=all_rules,
            ),
        )

    def _build_custom_rules(
        self,
        batch: DomainTopicBatch,
        plan: DomainTopicPlan,
    ) -> list[DomainPolicyRuleResult]:
        rules: list[DomainPolicyRuleResult] = []
        env = batch.env

        for spec in batch.specs:
            if spec.environment != batch.env:
                rules.append(
                    self._rule(
                        code="topic.environment.mismatch",
                        severity=DomainPolicySeverity.ERROR,
                        risk_level=DomainRiskLevel.HIGH,
                        decision=DomainPolicyDecision.REJECT,
                        reason=(
                            f"topic '{spec.name}' environment prefix '{spec.environment.value}' "
                            f"does not match batch env '{batch.env.value}'"
                        ),
                        resource_name=spec.name,
                        field="name",
                    )
                )

            if (
                spec.action.value != "delete"
                and spec.metadata is not None
                and not spec.metadata.doc
            ):
                rules.append(
                    self._rule(
                        code="topic.metadata.doc.missing",
                        severity=(
                            DomainPolicySeverity.ERROR
                            if env in (DomainEnvironment.STG, DomainEnvironment.PROD)
                            else DomainPolicySeverity.WARNING
                        ),
                        risk_level=(
                            DomainRiskLevel.MEDIUM
                            if env in (DomainEnvironment.STG, DomainEnvironment.PROD)
                            else DomainRiskLevel.LOW
                        ),
                        decision=(
                            DomainPolicyDecision.APPROVAL_REQUIRED
                            if env in (DomainEnvironment.STG, DomainEnvironment.PROD)
                            else DomainPolicyDecision.WARN
                        ),
                        reason=f"topic '{spec.name}' is missing metadata.doc",
                        resource_name=spec.name,
                        field="metadata.doc",
                    )
                )

            if spec.action.value == "delete":
                rules.append(
                    self._rule(
                        code="topic.delete.requires_approval",
                        severity=DomainPolicySeverity.ERROR,
                        risk_level=(
                            DomainRiskLevel.CRITICAL
                            if env is DomainEnvironment.PROD
                            else DomainRiskLevel.HIGH
                        ),
                        decision=DomainPolicyDecision.APPROVAL_REQUIRED,
                        reason=f"topic '{spec.name}' delete requires explicit approval",
                        resource_name=spec.name,
                    )
                )

        for item in plan.items:
            if (
                item.action.value != "ALTER"
                or item.current_config is None
                or item.target_config is None
            ):
                continue

            current_partitions = _config_int(item.current_config, "partitions")
            target_partitions = _config_int(item.target_config, "partitions")
            if (
                current_partitions is not None
                and target_partitions is not None
                and target_partitions < current_partitions
            ):
                rules.append(
                    self._rule(
                        code="topic.partition.decrease.forbidden",
                        severity=DomainPolicySeverity.ERROR,
                        risk_level=DomainRiskLevel.CRITICAL,
                        decision=DomainPolicyDecision.REJECT,
                        reason=(
                            f"topic '{item.name}' partitions cannot decrease from "
                            f"{current_partitions} to {target_partitions}"
                        ),
                        resource_name=item.name,
                        field="config.partitions",
                    )
                )
            elif (
                current_partitions is not None
                and target_partitions is not None
                and target_partitions > current_partitions
            ):
                rules.append(
                    self._rule(
                        code="topic.partition.increase.requires_approval",
                        severity=DomainPolicySeverity.ERROR,
                        risk_level=DomainRiskLevel.HIGH,
                        decision=DomainPolicyDecision.APPROVAL_REQUIRED,
                        reason=(
                            f"topic '{item.name}' partitions increase from "
                            f"{current_partitions} to {target_partitions}"
                        ),
                        resource_name=item.name,
                        field="config.partitions",
                    )
                )

            current_rf = _config_int(
                item.current_config, "replication_factor", "replication.factor"
            )
            target_rf = _config_int(item.target_config, "replication_factor", "replication.factor")
            min_rf = _minimum_replication_factor(env)
            if target_rf is not None and target_rf < min_rf:
                rules.append(
                    self._rule(
                        code="topic.replication_factor.minimum",
                        severity=DomainPolicySeverity.ERROR,
                        risk_level=DomainRiskLevel.CRITICAL,
                        decision=DomainPolicyDecision.REJECT,
                        reason=(
                            f"topic '{item.name}' replication factor {target_rf} is below "
                            f"the {env.value} minimum of {min_rf}"
                        ),
                        resource_name=item.name,
                        field="config.replication_factor",
                    )
                )
            if current_rf is not None and target_rf is not None and target_rf != current_rf:
                rules.append(
                    self._rule(
                        code="topic.replication_factor.change.forbidden",
                        severity=DomainPolicySeverity.ERROR,
                        risk_level=DomainRiskLevel.CRITICAL,
                        decision=DomainPolicyDecision.REJECT,
                        reason=(
                            f"topic '{item.name}' replication factor change from {current_rf} "
                            f"to {target_rf} is not supported by preflight apply"
                        ),
                        resource_name=item.name,
                        field="config.replication_factor",
                    )
                )

            current_retention = _config_int(item.current_config, "retention.ms")
            target_retention = _config_int(item.target_config, "retention.ms")
            if (
                current_retention is not None
                and target_retention is not None
                and target_retention < current_retention
            ):
                rules.append(
                    self._rule(
                        code="topic.retention.decrease.requires_approval",
                        severity=DomainPolicySeverity.ERROR,
                        risk_level=DomainRiskLevel.HIGH,
                        decision=DomainPolicyDecision.APPROVAL_REQUIRED,
                        reason=(
                            f"topic '{item.name}' retention.ms decreases from {current_retention} "
                            f"to {target_retention}"
                        ),
                        resource_name=item.name,
                        field="config.retention_ms",
                    )
                )

            current_cleanup = _config_value(item.current_config, "cleanup.policy")
            target_cleanup = _config_value(item.target_config, "cleanup.policy")
            if current_cleanup and target_cleanup and current_cleanup != target_cleanup:
                rules.append(
                    self._rule(
                        code="topic.cleanup_policy.change.requires_approval",
                        severity=DomainPolicySeverity.ERROR,
                        risk_level=DomainRiskLevel.HIGH,
                        decision=DomainPolicyDecision.APPROVAL_REQUIRED,
                        reason=(
                            f"topic '{item.name}' cleanup policy changes from {current_cleanup} "
                            f"to {target_cleanup}"
                        ),
                        resource_name=item.name,
                        field="config.cleanup_policy",
                    )
                )

            current_isr = _config_int(item.current_config, "min.insync.replicas")
            target_isr = _config_int(item.target_config, "min.insync.replicas")
            if current_isr is not None and target_isr is not None and target_isr < current_isr:
                rules.append(
                    self._rule(
                        code="topic.min_insync_replicas.decrease.requires_approval",
                        severity=DomainPolicySeverity.ERROR,
                        risk_level=DomainRiskLevel.HIGH,
                        decision=DomainPolicyDecision.APPROVAL_REQUIRED,
                        reason=(
                            f"topic '{item.name}' min.insync.replicas decreases from {current_isr} "
                            f"to {target_isr}"
                        ),
                        resource_name=item.name,
                        field="config.min_insync_replicas",
                    )
                )

        return rules

    def _rule_from_violation(self, violation: DomainPolicyViolation) -> DomainPolicyRuleResult:
        severity = violation.severity.value
        if violation.severity is DomainPolicySeverity.WARNING:
            risk_level = DomainRiskLevel.LOW
            decision = DomainPolicyDecision.WARN
        elif violation.severity is DomainPolicySeverity.CRITICAL:
            risk_level = DomainRiskLevel.CRITICAL
            decision = DomainPolicyDecision.REJECT
        else:
            risk_level = DomainRiskLevel.HIGH
            decision = DomainPolicyDecision.REJECT

        return DomainPolicyRuleResult(
            code=violation.rule_id,
            severity=severity,
            risk_level=risk_level,
            decision=decision,
            reason=violation.message,
            resource_type=violation.resource_type,
            resource_name=violation.resource_name,
            field=violation.field,
        )

    def _violation_from_rule(self, rule: DomainPolicyRuleResult) -> DomainPolicyViolation:
        severity = (
            DomainPolicySeverity.WARNING
            if rule.decision is not DomainPolicyDecision.REJECT
            else DomainPolicySeverity.ERROR
        )
        return DomainPolicyViolation(
            resource_type=rule.resource_type,
            resource_name=rule.resource_name,
            rule_id=rule.code,
            message=rule.reason,
            severity=severity,
            field=rule.field,
        )

    def _rule(
        self,
        *,
        code: str,
        severity: DomainPolicySeverity,
        risk_level: DomainRiskLevel,
        decision: DomainPolicyDecision,
        reason: str,
        resource_name: str,
        field: str | None = None,
    ) -> DomainPolicyRuleResult:
        return DomainPolicyRuleResult(
            code=code,
            severity=severity.value,
            risk_level=risk_level,
            decision=decision,
            reason=reason,
            resource_type=DomainResourceType.TOPIC,
            resource_name=resource_name,
            field=field,
        )


def _config_int(config: dict[str, str], *keys: str) -> int | None:
    for key in keys:
        raw = config.get(key)
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def _config_value(config: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        raw = config.get(key)
        if raw is not None:
            return str(raw)
    return None


def _minimum_replication_factor(env: DomainEnvironment) -> int:
    if env is DomainEnvironment.PROD:
        return 3
    if env is DomainEnvironment.STG:
        return 2
    return 1
