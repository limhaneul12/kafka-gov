from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.schema.domain.models import DomainSchemaBatch, DomainSchemaPlan
from app.schema.domain.models.policy import DomainPolicyViolation
from app.schema.domain.models.types_enum import DomainEnvironment
from app.schema.governance_support.policy_types import DomainResourceType
from app.schema.governance_support.preflight_policy import (
    DomainPolicyDecision,
    DomainPolicyPackEvaluation,
    DomainPolicyRuleResult,
    DomainRiskLevel,
)

DEFAULT_SCHEMA_POLICY_PACK_V1 = "policy-pack.v1.schema.default"


@dataclass(frozen=True, slots=True)
class SchemaPolicyPackResult:
    violations: tuple[DomainPolicyViolation, ...]
    evaluation: DomainPolicyPackEvaluation


class DefaultSchemaPolicyPackV1:
    def evaluate(self, batch: DomainSchemaBatch, plan: DomainSchemaPlan) -> SchemaPolicyPackResult:
        base_rules = tuple(self._rule_from_violation(violation) for violation in plan.violations)
        compatibility_rules = tuple(self._rules_from_compatibility_reports(plan))
        custom_rules = tuple(self._build_custom_rules(batch, plan))
        all_rules = base_rules + compatibility_rules + custom_rules

        generated_violations = tuple(
            self._violation_from_rule(rule)
            for rule in compatibility_rules + custom_rules
            if rule.code not in {violation.rule for violation in plan.violations}
        )

        return SchemaPolicyPackResult(
            violations=plan.violations + generated_violations,
            evaluation=DomainPolicyPackEvaluation(
                pack_name=DEFAULT_SCHEMA_POLICY_PACK_V1,
                resource_type=DomainResourceType.SCHEMA,
                rules=all_rules,
            ),
        )

    def _build_custom_rules(
        self,
        batch: DomainSchemaBatch,
        plan: DomainSchemaPlan,
    ) -> list[DomainPolicyRuleResult]:
        rules: list[DomainPolicyRuleResult] = []

        for spec, item in zip(batch.specs, plan.items, strict=True):
            if spec.compatibility.value == "NONE":
                if batch.env is DomainEnvironment.PROD:
                    rules.append(
                        self._rule(
                            code="schema.compatibility.none.forbidden",
                            severity="error",
                            risk_level=DomainRiskLevel.CRITICAL,
                            decision=DomainPolicyDecision.REJECT,
                            reason=f"schema '{spec.subject}' cannot use compatibility NONE in prod",
                            resource_name=spec.subject,
                            field="compatibility",
                        )
                    )
                else:
                    rules.append(
                        self._rule(
                            code="schema.compatibility.none.requires_approval",
                            severity="warning",
                            risk_level=DomainRiskLevel.HIGH,
                            decision=DomainPolicyDecision.APPROVAL_REQUIRED,
                            reason=f"schema '{spec.subject}' uses compatibility NONE",
                            resource_name=spec.subject,
                            field="compatibility",
                        )
                    )

            if spec.metadata is None:
                rules.append(
                    self._rule(
                        code="schema.metadata.missing",
                        severity=("error" if batch.env is DomainEnvironment.PROD else "warning"),
                        risk_level=(
                            DomainRiskLevel.HIGH
                            if batch.env in (DomainEnvironment.STG, DomainEnvironment.PROD)
                            else DomainRiskLevel.LOW
                        ),
                        decision=(
                            DomainPolicyDecision.APPROVAL_REQUIRED
                            if batch.env in (DomainEnvironment.STG, DomainEnvironment.PROD)
                            else DomainPolicyDecision.WARN
                        ),
                        reason=f"schema '{spec.subject}' is missing metadata.owner/doc context",
                        resource_name=spec.subject,
                        field="metadata",
                    )
                )
            elif not spec.metadata.doc:
                rules.append(
                    self._rule(
                        code="schema.metadata.doc.missing",
                        severity=("error" if batch.env is DomainEnvironment.PROD else "warning"),
                        risk_level=(
                            DomainRiskLevel.MEDIUM
                            if batch.env in (DomainEnvironment.STG, DomainEnvironment.PROD)
                            else DomainRiskLevel.LOW
                        ),
                        decision=(
                            DomainPolicyDecision.APPROVAL_REQUIRED
                            if batch.env in (DomainEnvironment.STG, DomainEnvironment.PROD)
                            else DomainPolicyDecision.WARN
                        ),
                        reason=f"schema '{spec.subject}' is missing metadata.doc",
                        resource_name=spec.subject,
                        field="metadata.doc",
                    )
                )

            if item.action.value != "UPDATE" or item.current_schema is None or item.schema is None:
                continue

            old_schema = _parse_schema(item.current_schema)
            new_schema = _parse_schema(item.schema)
            if old_schema is None or new_schema is None:
                continue

            rules.extend(
                self._rule(
                    code="schema.field.required_without_default.forbidden",
                    severity="error",
                    risk_level=DomainRiskLevel.CRITICAL,
                    decision=DomainPolicyDecision.REJECT,
                    reason=(
                        f"schema '{spec.subject}' adds required field '{field_name}' without a default"
                    ),
                    resource_name=spec.subject,
                    field=f"schema.fields.{field_name}",
                )
                for field_name in _added_required_fields_without_default(old_schema, new_schema)
            )

            rules.extend(
                self._rule(
                    code="schema.field.type_change.forbidden",
                    severity="error",
                    risk_level=DomainRiskLevel.CRITICAL,
                    decision=DomainPolicyDecision.REJECT,
                    reason=f"schema '{spec.subject}' changes field type for '{field_name}'",
                    resource_name=spec.subject,
                    field=f"schema.fields.{field_name}",
                )
                for field_name in _changed_field_types(old_schema, new_schema)
            )

            rules.extend(
                self._rule(
                    code="schema.enum_narrowing.requires_approval",
                    severity="warning",
                    risk_level=DomainRiskLevel.HIGH,
                    decision=DomainPolicyDecision.APPROVAL_REQUIRED,
                    reason=f"schema '{spec.subject}' narrows enum symbols for '{field_name}'",
                    resource_name=spec.subject,
                    field=f"schema.fields.{field_name}",
                )
                for field_name in _enum_narrowing_fields(old_schema, new_schema)
            )

        return rules

    def _rules_from_compatibility_reports(
        self, plan: DomainSchemaPlan
    ) -> list[DomainPolicyRuleResult]:
        rules: list[DomainPolicyRuleResult] = []
        for report in plan.compatibility_reports:
            if report.is_compatible:
                continue

            issue_suffix = f": {report.issues[0].message}" if report.issues else ""
            rules.append(
                self._rule(
                    code="schema.compatibility.backward_incompatible",
                    severity="error",
                    risk_level=DomainRiskLevel.CRITICAL,
                    decision=DomainPolicyDecision.REJECT,
                    reason=(
                        f"schema '{report.subject}' is incompatible under {report.mode.value}{issue_suffix}"
                    ),
                    resource_name=report.subject,
                    field="compatibility",
                )
            )
        return rules

    def _rule_from_violation(self, violation: DomainPolicyViolation) -> DomainPolicyRuleResult:
        severity = violation.severity.lower()
        if severity == "error":
            risk_level = DomainRiskLevel.HIGH
            decision = DomainPolicyDecision.REJECT
        else:
            risk_level = DomainRiskLevel.LOW
            decision = DomainPolicyDecision.WARN

        return DomainPolicyRuleResult(
            code=violation.rule,
            severity=severity,
            risk_level=risk_level,
            decision=decision,
            reason=violation.message,
            resource_type=DomainResourceType.SCHEMA,
            resource_name=violation.subject,
            field=violation.field,
        )

    def _violation_from_rule(self, rule: DomainPolicyRuleResult) -> DomainPolicyViolation:
        severity = "error" if rule.decision is DomainPolicyDecision.REJECT else "warning"
        return DomainPolicyViolation(
            subject=rule.resource_name,
            rule=rule.code,
            message=rule.reason,
            severity=severity,
            field=rule.field,
        )

    def _rule(
        self,
        *,
        code: str,
        severity: str,
        risk_level: DomainRiskLevel,
        decision: DomainPolicyDecision,
        reason: str,
        resource_name: str,
        field: str | None = None,
    ) -> DomainPolicyRuleResult:
        return DomainPolicyRuleResult(
            code=code,
            severity=severity,
            risk_level=risk_level,
            decision=decision,
            reason=reason,
            resource_type=DomainResourceType.SCHEMA,
            resource_name=resource_name,
            field=field,
        )


def _parse_schema(schema_text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(schema_text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _field_map(schema_dict: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = schema_dict.get("fields", [])
    if not isinstance(fields, list):
        return {}
    return {
        field["name"]: field
        for field in fields
        if isinstance(field, dict) and isinstance(field.get("name"), str)
    }


def _added_required_fields_without_default(
    old_schema: dict[str, Any], new_schema: dict[str, Any]
) -> list[str]:
    old_fields = _field_map(old_schema)
    new_fields = _field_map(new_schema)
    return [
        field_name
        for field_name in sorted(set(new_fields) - set(old_fields))
        if "default" not in new_fields[field_name]
    ]


def _changed_field_types(old_schema: dict[str, Any], new_schema: dict[str, Any]) -> list[str]:
    old_fields = _field_map(old_schema)
    new_fields = _field_map(new_schema)
    changed: list[str] = []
    for field_name in sorted(set(old_fields) & set(new_fields)):
        old_type = old_fields[field_name].get("type")
        new_type = new_fields[field_name].get("type")
        if _same_enum_family(old_type, new_type):
            continue
        if _normalized_type(old_type) != _normalized_type(new_type):
            changed.append(field_name)
    return changed


def _enum_narrowing_fields(old_schema: dict[str, Any], new_schema: dict[str, Any]) -> list[str]:
    old_fields = _field_map(old_schema)
    new_fields = _field_map(new_schema)
    narrowed: list[str] = []
    for field_name in sorted(set(old_fields) & set(new_fields)):
        old_symbols = _enum_symbols(old_fields[field_name].get("type"))
        new_symbols = _enum_symbols(new_fields[field_name].get("type"))
        if old_symbols and new_symbols and not old_symbols.issubset(new_symbols):
            narrowed.append(field_name)
    return narrowed


def _normalized_type(field_type: Any) -> str:
    return json.dumps(field_type, sort_keys=True, separators=(",", ":"))


def _enum_symbols(field_type: Any) -> set[str]:
    if isinstance(field_type, dict) and field_type.get("type") == "enum":
        symbols = field_type.get("symbols", [])
        return {symbol for symbol in symbols if isinstance(symbol, str)}

    if isinstance(field_type, list):
        collected: set[str] = set()
        for item in field_type:
            collected.update(_enum_symbols(item))
        return collected

    return set()


def _same_enum_family(old_type: Any, new_type: Any) -> bool:
    old_symbols = _enum_symbols(old_type)
    new_symbols = _enum_symbols(new_type)
    return bool(old_symbols) and bool(new_symbols)
