"""Dry-Run 리포트 생성 Helper"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from ..schemas import TopicBatchDryRunResponse


def generate_csv_report(plan: TopicBatchDryRunResponse) -> str:
    """Dry-Run 결과를 CSV 형식으로 변환

    Args:
        plan: Dry-Run 결과

    Returns:
        CSV 문자열
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # 헤더
    writer.writerow(
        [
            "Topic Name",
            "Action",
            "Current Partitions",
            "New Partitions",
            "Current Replication",
            "New Replication",
            "Changes",
            "Warnings",
        ]
    )

    # 데이터 행
    for item in plan.plan:
        diff = item.diff or {}
        warnings_str = "; ".join(w.message for w in item.warnings) if item.warnings else ""  # type: ignore[union-attr]

        writer.writerow(
            [
                item.name,
                item.action,
                diff.get("partitions", {}).get("current", ""),  # type: ignore[union-attr]
                diff.get("partitions", {}).get("new", ""),  # type: ignore[union-attr]
                diff.get("replication_factor", {}).get("current", ""),  # type: ignore[union-attr]
                diff.get("replication_factor", {}).get("new", ""),  # type: ignore[union-attr]
                json.dumps(diff),
                warnings_str,
            ]
        )

    return output.getvalue()


def generate_json_report(plan: TopicBatchDryRunResponse) -> dict[str, Any]:
    """Dry-Run 결과를 JSON 형식으로 변환

    Args:
        plan: Dry-Run 결과

    Returns:
        JSON 딕셔너리
    """
    return {
        "env": plan.env,
        "change_id": plan.change_id,
        "total_items": plan.total_items,  # type: ignore[attr-defined]
        "summary": plan.summary,
        "plan": [
            {
                "name": item.name,
                "action": item.action,
                "diff": item.diff,
                "warnings": [{"rule": w.rule, "message": w.message} for w in item.warnings]  # type: ignore[union-attr]
                if item.warnings  # type: ignore[attr-defined]
                else [],
            }
            for item in plan.plan
        ],
    }


def prepare_report_response(
    plan: TopicBatchDryRunResponse, format: str, change_id: str
) -> tuple[str, str, str]:
    """Report 응답 준비 (format에 따른 content, media_type, filename 생성)

    Args:
        plan: Dry-Run 결과
        format: Report 형식 ("csv" 또는 "json")
        change_id: 변경 ID (파일명 생성용)

    Returns:
        tuple: (content, media_type, filename)
    """
    if format == "csv":
        content = generate_csv_report(plan)
        media_type = "text/csv"
        filename = f"dry-run-report-{change_id}.csv"
    else:  # json
        content_dict = generate_json_report(plan)
        content = json.dumps(content_dict, indent=2, ensure_ascii=False)
        media_type = "application/json"
        filename = f"dry-run-report-{change_id}.json"

    return content, media_type, filename
