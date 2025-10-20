"""Topic Interface 레이어 헬퍼 함수"""

from __future__ import annotations

from collections import defaultdict
from io import StringIO

import orjson
import pandas as pd

from ..domain.models import (
    DomainTopicPlan,
    DryRunItemReport,
    DryRunReport,
    DryRunSummary,
    ViolationDetail,
)

# ============================================================================
# Report 생성 함수
# ============================================================================


def generate_csv_report(plan: DomainTopicPlan) -> str:
    """Dry-Run 결과를 CSV 형식으로 생성 (pandas 사용)

    Args:
        plan: DomainTopicPlan 객체

    Returns:
        CSV 문자열
    """
    # Violation 맵 생성 (defaultdict 사용)
    violation_map: defaultdict[str, list[ViolationDetail]] = defaultdict(list)
    for violation in plan.violations:
        target = str(violation.target) if hasattr(violation, "target") else "unknown"
        violation_map[target].append(violation)  # type: ignore[arg-type]

    # 행 생성 클로저 함수
    def create_violation_row(item_name: str, action: str, v: ViolationDetail) -> dict[str, str]:
        return {
            "Topic Name": item_name,
            "Action": action,
            "Status": "❌ VIOLATION",
            "Violation Type": getattr(v, "policy_type", "unknown"),
            "Violation Message": getattr(v, "message", str(v)),
            "Severity": getattr(v, "level", "error"),
        }

    def create_ok_row(item_name: str, action: str) -> dict[str, str]:
        return {
            "Topic Name": item_name,
            "Action": action,
            "Status": "✅ OK",
            "Violation Type": "-",
            "Violation Message": "-",
            "Severity": "-",
        }

    # DataFrame 생성 (comprehension 사용)
    all_rows: list[dict[str, str]] = [
        row
        for item in plan.items
        for row in (
            [
                create_violation_row(
                    str(item.name),
                    item.action.value if hasattr(item.action, "value") else str(item.action),
                    v,
                )
                for v in violation_map.get(str(item.name), [])
            ]
            if violation_map.get(str(item.name))
            else [
                create_ok_row(
                    str(item.name),
                    item.action.value if hasattr(item.action, "value") else str(item.action),
                )
            ]
        )
    ]

    df = pd.DataFrame(all_rows)

    # Summary DataFrame
    error_violations = [v for v in plan.violations if getattr(v, "level", "") == "error"]
    summary_df = pd.DataFrame(
        [
            {"Metric": "Total Topics", "Value": len(plan.items)},
            {"Metric": "Violations", "Value": len(plan.violations)},
            {"Metric": "Error Violations", "Value": len(error_violations)},
            {"Metric": "Can Apply", "Value": "Yes" if len(error_violations) == 0 else "No"},
        ]
    )

    # 합쳐서 CSV로 변환
    output = StringIO()
    df.to_csv(output, index=False)
    output.write("\n")
    summary_df.to_csv(output, index=False)

    return output.getvalue()


def generate_json_report(plan: DomainTopicPlan) -> bytes:
    """Dry-Run 결과를 JSON 형식으로 생성 (orjson 사용)

    Args:
        plan: DomainTopicPlan 객체

    Returns:
        JSON bytes (orjson)
    """
    # Violation 변환 (comprehension)
    violation_details: list[ViolationDetail] = [
        ViolationDetail(
            target=str(getattr(v, "target", "unknown")),
            policy_type=getattr(v, "policy_type", "unknown"),
            message=getattr(v, "message", str(v)),
            level=getattr(v, "level", "error"),
        )
        for v in plan.violations
    ]

    # Violation 맵 생성 (defaultdict 사용)
    violation_map: defaultdict[str, list[ViolationDetail]] = defaultdict(list)
    for v_detail in violation_details:
        violation_map[v_detail.target].append(v_detail)

    # Items 변환
    item_reports: list[DryRunItemReport] = [
        DryRunItemReport(
            name=item.name,
            action=item.action.value if hasattr(item.action, "value") else str(item.action),
            diff=item.diff if hasattr(item, "diff") else {},
            violations=tuple(violation_map.get(str(item.name), [])),
        )
        for item in plan.items
    ]

    # Summary 생성
    error_violations: list[ViolationDetail] = [v for v in violation_details if v.level == "error"]
    summary = DryRunSummary(
        total_items=len(plan.items),
        total_violations=len(violation_details),
        error_violations=len(error_violations),
        can_apply=len(error_violations) == 0,
    )

    # DryRunReport 도메인 모델 생성
    report = DryRunReport(
        change_id=plan.change_id,
        env=plan.env,
        summary=summary,
        items=tuple(item_reports),
        violations=tuple(violation_details),
    )

    # orjson으로 직렬화 (option: OPT_INDENT_2 for readability)
    return orjson.dumps(report.to_dict(), option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS)
