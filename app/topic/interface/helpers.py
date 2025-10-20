"""Topic Interface 레이어 헬퍼 함수"""

import csv
import io
import json

import yaml
from fastapi import HTTPException, UploadFile, status

from ..domain.models import DomainTopicPlan


def validate_yaml_file(file: UploadFile) -> None:
    """
    업로드된 파일의 YAML 타입 검증

    Args:
        file: FastAPI UploadFile 객체

    Raises:
        HTTPException: 파일이 YAML이 아닐 경우 (400)
    """
    if not file.filename or not file.filename.endswith((".yaml", ".yml")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only YAML files (.yaml, .yml) are allowed",
        )


async def parse_yaml_content(content: bytes) -> dict:
    """
    업로드된 YAML 컨텐츠 파싱 및 기본 검증

    Args:
        content: YAML 파일의 바이트 컨텐츠

    Returns:
        파싱된 YAML 데이터 (dict)

    Raises:
        HTTPException: 파일이 비어있거나, YAML 파싱 실패, 또는 구조가 잘못된 경우 (400)
    """
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    try:
        yaml_data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YAML format: {e!s}",
        ) from e

    if not isinstance(yaml_data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YAML must be a dictionary with 'kind', 'env', 'change_id', 'items'",
        )

    if yaml_data.get("kind") != "TopicBatch":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="kind must be 'TopicBatch'",
        )

    return yaml_data


# ============================================================================
# Report 생성 함수
# ============================================================================


def generate_csv_report(plan: DomainTopicPlan) -> str:
    """Dry-Run 결과를 CSV 형식으로 생성

    Args:
        plan: DomainTopicPlan 객체

    Returns:
        CSV 문자열
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        ["Topic Name", "Action", "Status", "Violation Type", "Violation Message", "Severity"]
    )

    # Violation 맵 생성
    violation_map: dict[str, list] = {}
    for violation in plan.violations:
        target = str(violation.target) if hasattr(violation, "target") else "unknown"
        if target not in violation_map:
            violation_map[target] = []
        violation_map[target].append(violation)

    # Plan Items
    for item in plan.items:
        violations = violation_map.get(str(item.name), [])
        if violations:
            for v in violations:
                writer.writerow(
                    [
                        item.name,
                        item.action.value if hasattr(item.action, "value") else str(item.action),
                        "❌ VIOLATION",
                        getattr(v, "policy_type", "unknown"),
                        getattr(v, "message", str(v)),
                        getattr(v, "level", "error"),
                    ]
                )
        else:
            writer.writerow(
                [
                    item.name,
                    item.action.value if hasattr(item.action, "value") else str(item.action),
                    "✅ OK",
                    "-",
                    "-",
                    "-",
                ]
            )

    # Summary
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total Topics", len(plan.items)])
    writer.writerow(["Violations", len(plan.violations)])
    error_violations = [v for v in plan.violations if getattr(v, "level", "") == "error"]
    writer.writerow(["Error Violations", len(error_violations)])
    writer.writerow(["Can Apply", "Yes" if len(error_violations) == 0 else "No"])

    return output.getvalue()


def generate_json_report(plan: DomainTopicPlan) -> str:
    """Dry-Run 결과를 JSON 형식으로 생성

    Args:
        plan: DomainTopicPlan 객체

    Returns:
        JSON 문자열
    """
    # Violation 맵 생성
    violation_map: dict[str, list] = {}
    for violation in plan.violations:
        target = str(violation.target) if hasattr(violation, "target") else "unknown"
        if target not in violation_map:
            violation_map[target] = []
        violation_map[target].append(
            {
                "policy_type": getattr(violation, "policy_type", "unknown"),
                "message": getattr(violation, "message", str(violation)),
                "level": getattr(violation, "level", "error"),
            }
        )

    error_violations = [v for v in plan.violations if getattr(v, "level", "") == "error"]

    report = {
        "change_id": plan.change_id,
        "env": plan.env,
        "summary": {
            "total_items": len(plan.items),
            "total_violations": len(plan.violations),
            "error_violations": len(error_violations),
            "can_apply": len(error_violations) == 0,
        },
        "items": [
            {
                "name": str(item.name),
                "action": item.action.value if hasattr(item.action, "value") else str(item.action),
                "diff": item.diff if hasattr(item, "diff") else {},
                "violations": violation_map.get(str(item.name), []),
            }
            for item in plan.items
        ],
        "violations": [
            {
                "target": str(getattr(v, "target", "unknown")),
                "policy_type": getattr(v, "policy_type", "unknown"),
                "message": getattr(v, "message", str(v)),
                "level": getattr(v, "level", "error"),
            }
            for v in plan.violations
        ],
    }

    return json.dumps(report, indent=2, ensure_ascii=False)
