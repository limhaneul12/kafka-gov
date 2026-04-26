from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.schema.governance_support.preflight_policy import (
    DomainPolicyPackEvaluation,
    DomainRiskLevel,
)


class ApprovalOverride(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(..., min_length=10, max_length=500)
    approver: str = Field(..., min_length=2, max_length=100)
    expires_at: datetime = Field(
        ...,
        validation_alias=AliasChoices("expiresAt", "expires_at"),
        serialization_alias="expiresAt",
    )

    @field_validator("expires_at")
    @classmethod
    def validate_future_expiry(cls, value: datetime) -> datetime:
        reference_now = datetime.now(value.tzinfo or UTC)
        if value <= reference_now:
            raise ValueError("approval override has expired")
        return value

    def to_audit_dict(self) -> dict[str, str]:
        return {
            "reason": self.reason,
            "approver": self.approver,
            "expires_at": self.expires_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class HighRiskAssessment:
    requires_approval: bool
    reasons: tuple[str, ...]
    risk_level: DomainRiskLevel = DomainRiskLevel.HIGH

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "requires_approval": self.requires_approval,
            "reasons": list(self.reasons),
            "risk_level": self.risk_level.value,
        }


class PolicyBlockedError(RuntimeError):
    def __init__(self, evaluation: DomainPolicyPackEvaluation) -> None:
        reasons = "; ".join(evaluation.reasons[:3]) or evaluation.summary()
        super().__init__(f"policy blocked: {reasons}")
        self.risk = evaluation.risk_metadata()
        self.approval = evaluation.approval_metadata(
            mode="apply",
            approval_override_present=False,
        )


class ApprovalRequiredError(RuntimeError):
    def __init__(self, evaluation: DomainPolicyPackEvaluation) -> None:
        reasons = "; ".join(rule.reason for rule in evaluation.approval_rules[:3])
        suffix = f" ({reasons})" if reasons else ""
        super().__init__(f"approval_override is required for high-risk apply operations{suffix}")
        self.risk = evaluation.risk_metadata()
        self.approval = evaluation.approval_metadata(
            mode="apply",
            approval_override_present=False,
        )


def evaluation_to_high_risk_assessment(
    evaluation: DomainPolicyPackEvaluation,
) -> HighRiskAssessment:
    if evaluation.blocking:
        return HighRiskAssessment(
            requires_approval=False,
            reasons=evaluation.reasons,
            risk_level=evaluation.risk_level,
        )

    approval_reasons = tuple(rule.reason for rule in evaluation.approval_rules)
    return HighRiskAssessment(
        requires_approval=evaluation.approval_required,
        reasons=approval_reasons,
        risk_level=evaluation.risk_level,
    )


def ensure_approval(
    assessment: HighRiskAssessment | DomainPolicyPackEvaluation,
    approval_override: ApprovalOverride | None,
) -> dict[str, Any]:
    if isinstance(assessment, DomainPolicyPackEvaluation):
        evaluation: DomainPolicyPackEvaluation | None = assessment
        normalized_assessment = evaluation_to_high_risk_assessment(assessment)
    else:
        evaluation = None
        normalized_assessment = assessment

    if evaluation is not None and evaluation.blocking:
        raise PolicyBlockedError(evaluation)

    approval_required = normalized_assessment.requires_approval
    approval_data = approval_override.to_audit_dict() if approval_override is not None else None

    if approval_required and approval_data is None:
        if evaluation is not None:
            raise ApprovalRequiredError(evaluation)

        reasons = "; ".join(normalized_assessment.reasons)
        raise ValueError(
            f"approval_override is required for high-risk apply operations ({reasons})"
        )

    if evaluation is not None:
        return {
            "risk": evaluation.risk_metadata(),
            "approval": evaluation.approval_metadata(
                mode="apply",
                approval_override_present=approval_data is not None,
            ),
            "approval_override": approval_data,
            "policy_pack": evaluation.to_audit_dict(),
        }

    return {
        "risk": normalized_assessment.to_audit_dict(),
        "approval_override": approval_data,
    }


def assess_schema_batch_risk(batch, plan) -> HighRiskAssessment:
    reasons: list[str] = []

    env_value = getattr(batch.env, "value", str(batch.env)).lower()
    if env_value == "prod":
        reasons.append("production schema change")

    if any(
        getattr(item.action, "value", str(item.action)).lower() == "update" for item in plan.items
    ):
        reasons.append("existing schema version update")

    if any(
        getattr(spec.compatibility, "value", str(spec.compatibility)).upper() == "NONE"
        for spec in batch.specs
        if not getattr(spec, "dry_run_only", False)
    ):
        reasons.append("compatibility NONE")

    unique_reasons = tuple(dict.fromkeys(reasons))
    return HighRiskAssessment(requires_approval=bool(unique_reasons), reasons=unique_reasons)
