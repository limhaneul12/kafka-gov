from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


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

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "requires_approval": self.requires_approval,
            "reasons": list(self.reasons),
        }


def ensure_approval(
    assessment: HighRiskAssessment,
    approval_override: ApprovalOverride | None,
) -> dict[str, Any]:
    approval_required = assessment.requires_approval
    approval_data = approval_override.to_audit_dict() if approval_override is not None else None

    if approval_required and approval_data is None:
        reasons = "; ".join(assessment.reasons)
        raise ValueError(
            f"approval_override is required for high-risk apply operations ({reasons})"
        )

    return {
        "risk": assessment.to_audit_dict(),
        "approval_override": approval_data,
    }


def assess_topic_batch_risk(batch, plan) -> HighRiskAssessment:
    reasons: list[str] = []

    env_value = getattr(batch.env, "value", str(batch.env)).lower()
    if env_value == "prod":
        reasons.append("production topic change")

    if any(
        getattr(item.action, "value", str(item.action)).lower() == "delete" for item in plan.items
    ):
        reasons.append("topic deletion")

    if any(_topic_durability_reduced(item) for item in plan.items):
        reasons.append("durability reduction")

    unique_reasons = tuple(dict.fromkeys(reasons))
    return HighRiskAssessment(requires_approval=bool(unique_reasons), reasons=unique_reasons)


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


def _topic_durability_reduced(plan_item) -> bool:
    current = getattr(plan_item, "current_config", None) or {}
    target = getattr(plan_item, "target_config", None) or {}

    current_rf = _config_int(current, "replication_factor", "replication.factor")
    target_rf = _config_int(target, "replication_factor", "replication.factor")
    if current_rf is not None and target_rf is not None and target_rf < current_rf:
        return True

    current_isr = _config_int(current, "min_insync_replicas", "min.insync.replicas")
    target_isr = _config_int(target, "min_insync_replicas", "min.insync.replicas")
    return current_isr is not None and target_isr is not None and target_isr < current_isr


def _config_int(config: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = config.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None
