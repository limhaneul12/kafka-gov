"""에러를 사용자 친화적 메시지로 변환하는 Helper"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..schemas import FailureDetail


def translate_validation_error(e: ValidationError, parsed: dict[str, Any]) -> FailureDetail:
    """Pydantic ValidationError를 사용자 친화적 FailureDetail로 변환

    Args:
        e: Pydantic ValidationError
        parsed: 파싱된 YAML 딕셔너리

    Returns:
        사용자 친화적 에러 메시지가 포함된 FailureDetail
    """
    user_friendly_errors = []
    suggestions = []

    for err in e.errors():
        loc = " → ".join(str(x) for x in err["loc"])
        msg = err["msg"]

        # 일반적인 에러를 사용자 친화적으로 변환
        if "Field required" in msg:
            user_friendly_errors.append(f"❌ 필수 필드 누락: {loc}")  # type: ignore[arg-type]
            if "env" in str(err["loc"]):
                suggestions.append("최상위에 'env: dev' (또는 stg/prod)를 추가하세요")
            elif "change_id" in str(err["loc"]):
                suggestions.append("최상위에 'change_id: 2025-10-20_001' 형식으로 추가하세요")
            elif "items" in str(err["loc"]):
                suggestions.append("'topics:' 대신 'items:'를 사용하세요")
        elif "Extra inputs are not permitted" in msg:
            field_name = str(err["loc"][-1]) if err["loc"] else "unknown"
            user_friendly_errors.append(f"❌ 허용되지 않는 필드: {field_name}")  # type: ignore[arg-type]
            if field_name == "topics":
                suggestions.append("'topics:' 대신 'items:'를 사용하세요")
            elif "environment" in field_name:
                suggestions.append("'environment'는 metadata가 아니라 최상위에 'env'로 지정하세요")
        elif "retention.ms" in str(err["loc"]) or "compression.type" in str(err["loc"]):
            user_friendly_errors.append(f"❌ 잘못된 필드명: {loc}")  # type: ignore[arg-type]
            suggestions.append("Kafka config는 점(.)이 아니라 언더스코어(_)를 사용하세요")
            suggestions.append(
                "예: retention.ms → retention_ms, compression.type → compression_type"
            )
        else:
            user_friendly_errors.append(f"❌ {loc}: {msg}")  # type: ignore[arg-type]

    # 공통 제안사항 추가
    if not suggestions:
        suggestions = [
            "올바른 YAML 형식: env, change_id, items 필드가 필요합니다",
            "items는 리스트이며, 각 항목에 name, action, config, metadata가 필요합니다",
        ]

    error_summary = "\n".join(user_friendly_errors[:5])  # 최대 5개까지만

    return FailureDetail(
        topic_name=None,
        failure_type="validation",
        error_message=f"YAML 형식 오류:\n{error_summary}",
        suggestions=[
            *suggestions,
            "📖 올바른 예시를 보려면 '배치 생성 (YAML)' 탭의 Example을 참고하세요",
        ],
        raw_error=str(e),
    )


def translate_usecase_failure(fail_item: dict[str, Any]) -> FailureDetail:
    """UseCase 실패 항목을 FailureDetail로 변환

    Args:
        fail_item: UseCase에서 반환된 실패 항목 (dict)

    Returns:
        사용자 친화적 에러 메시지가 포함된 FailureDetail
    """
    topic_name = fail_item.get("topic", "unknown")
    error_msg = fail_item.get("error", "Unknown error")

    # 정책 위반 여부 확인
    is_policy_violation = "policy" in error_msg.lower() or "violation" in error_msg.lower()

    return FailureDetail(
        topic_name=topic_name,
        failure_type="policy_violation" if is_policy_violation else "kafka_error",
        error_message=error_msg,
        suggestions=[
            "정책 설정을 확인하세요",
            "토픽 이름 규칙을 확인하세요",
            "Guardrail 설정(파티션, 복제 등)을 확인하세요",
        ]
        if is_policy_violation
        else [
            "Kafka 클러스터 상태를 확인하세요",
            "네트워크 연결을 확인하세요",
        ],
        raw_error=str(fail_item),
    )
