from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .policy_types import DomainResourceType


class DomainPolicyDecision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    APPROVAL_REQUIRED = "approval_required"
    REJECT = "reject"


class DomainRiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class DomainPolicyRuleResult:
    code: str
    severity: str
    risk_level: DomainRiskLevel
    decision: DomainPolicyDecision
    reason: str
    resource_type: DomainResourceType
    resource_name: str
    field: str | None = None

    @property
    def is_blocking(self) -> bool:
        return self.decision is DomainPolicyDecision.REJECT

    @property
    def requires_approval(self) -> bool:
        return self.decision is DomainPolicyDecision.APPROVAL_REQUIRED

    @property
    def is_warning(self) -> bool:
        return self.decision is DomainPolicyDecision.WARN


@dataclass(frozen=True, slots=True)
class DomainPolicyPackEvaluation:
    pack_name: str
    resource_type: DomainResourceType
    rules: tuple[DomainPolicyRuleResult, ...] = ()

    @property
    def blocking_rules(self) -> tuple[DomainPolicyRuleResult, ...]:
        return tuple(rule for rule in self.rules if rule.is_blocking)

    @property
    def approval_rules(self) -> tuple[DomainPolicyRuleResult, ...]:
        return tuple(rule for rule in self.rules if rule.requires_approval)

    @property
    def warning_rules(self) -> tuple[DomainPolicyRuleResult, ...]:
        return tuple(rule for rule in self.rules if rule.is_warning)

    @property
    def warning_count(self) -> int:
        return len(self.warning_rules)

    @property
    def blocking(self) -> bool:
        return bool(self.blocking_rules)

    @property
    def approval_required(self) -> bool:
        return bool(self.approval_rules) and not self.blocking

    @property
    def decision(self) -> DomainPolicyDecision:
        if self.blocking:
            return DomainPolicyDecision.REJECT
        if self.approval_required:
            return DomainPolicyDecision.APPROVAL_REQUIRED
        if self.warning_rules:
            return DomainPolicyDecision.WARN
        return DomainPolicyDecision.ALLOW

    @property
    def risk_level(self) -> DomainRiskLevel:
        if not self.rules:
            return DomainRiskLevel.NONE

        order = {
            DomainRiskLevel.NONE: 0,
            DomainRiskLevel.LOW: 1,
            DomainRiskLevel.MEDIUM: 2,
            DomainRiskLevel.HIGH: 3,
            DomainRiskLevel.CRITICAL: 4,
        }
        return max(self.rules, key=lambda rule: order[rule.risk_level]).risk_level

    @property
    def reasons(self) -> tuple[str, ...]:
        ordered_reasons = [rule.reason for rule in self.rules]
        return tuple(dict.fromkeys(ordered_reasons))

    def summary(self) -> str:
        if not self.rules:
            return f"{self.pack_name}: no policy issues detected"

        return (
            f"{self.pack_name}: "
            f"{len(self.blocking_rules)} reject, "
            f"{len(self.approval_rules)} approval-required, "
            f"{len(self.warning_rules)} warn"
        )

    def risk_metadata(self) -> dict[str, str | bool]:
        return {
            "level": self.risk_level.value,
            "blocking": self.blocking,
            "summary": self.summary(),
        }

    def approval_metadata(
        self, *, mode: str, approval_override_present: bool
    ) -> dict[str, str | bool]:
        if self.blocking:
            return {
                "required": False,
                "state": "rejected",
                "summary": "policy pack rejected the requested change",
            }

        if self.approval_required and approval_override_present:
            return {
                "required": True,
                "state": "approved",
                "summary": f"approval override supplied for {len(self.approval_rules)} rule(s)",
            }

        if self.approval_required:
            if mode == "dry-run":
                summary = f"approval required before apply for {len(self.approval_rules)} rule(s)"
            else:
                summary = f"approval required for {len(self.approval_rules)} rule(s)"
            return {
                "required": True,
                "state": "pending",
                "summary": summary,
            }

        return {
            "required": False,
            "state": "not_required",
            "summary": "approval gate not required for this evaluation",
        }

    def to_audit_dict(self) -> dict[str, object]:
        return {
            "pack_name": self.pack_name,
            "decision": self.decision.value,
            "risk_level": self.risk_level.value,
            "blocking": self.blocking,
            "approval_required": self.approval_required,
            "summary": self.summary(),
            "rules": [
                {
                    "code": rule.code,
                    "severity": rule.severity,
                    "risk_level": rule.risk_level.value,
                    "decision": rule.decision.value,
                    "reason": rule.reason,
                    "resource_type": rule.resource_type.value,
                    "resource_name": rule.resource_name,
                    "field": rule.field,
                }
                for rule in self.rules
            ],
        }
