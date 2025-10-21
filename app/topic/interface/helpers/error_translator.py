"""에러를 사용자 친화적 메시지로 변환하는 Helper

Chain of Responsibility 패턴 사용:
- 각 에러 타입별 핸들러가 처리 가능 여부를 판단
- 확장 가능하고 테스트 용이한 구조
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import ValidationError

from ..schemas import FailureDetail


class ErrorHandler(ABC):
    """에러 핸들러 추상 베이스 클래스"""

    def __init__(self) -> None:
        self._next_handler: ErrorHandler | None = None

    def set_next(self, handler: ErrorHandler) -> ErrorHandler:
        """다음 핸들러 설정"""
        self._next_handler = handler
        return handler

    @abstractmethod
    def can_handle(self, err: dict[str, Any]) -> bool:
        """이 핸들러가 처리 가능한 에러인지 판단"""

    @abstractmethod
    def handle(self, err: dict[str, Any]) -> tuple[str, list[str]]:
        """에러 처리 후 (에러 메시지, 제안 리스트) 반환"""

    def process(self, err: dict[str, Any]) -> tuple[str, list[str]]:
        """에러 처리 (Chain of Responsibility)"""
        if self.can_handle(err):
            return self.handle(err)
        if self._next_handler:
            return self._next_handler.process(err)
        return self._default_handle(err)

    def _default_handle(self, err: dict[str, Any]) -> tuple[str, list[str]]:
        """기본 핸들러 (처리 불가능한 경우)"""
        loc = " → ".join(str(x) for x in err["loc"])
        msg = err["msg"]
        return (f"❌ {loc}: {msg}", [])


class FieldRequiredHandler(ErrorHandler):
    """필수 필드 누락 에러 핸들러"""

    def can_handle(self, err: dict[str, Any]) -> bool:
        return "Field required" in err["msg"]

    def handle(self, err: dict[str, Any]) -> tuple[str, list[str]]:
        loc = " → ".join(str(x) for x in err["loc"])
        error_msg = f"❌ 필수 필드 누락: {loc}"
        suggestions = self._get_field_suggestions(err["loc"])
        return (error_msg, suggestions)

    def _get_field_suggestions(self, loc: tuple[str | int, ...]) -> list[str]:
        """필드별 제안사항 반환"""
        loc_str = str(loc)
        if "env" in loc_str:
            return ["최상위에 'env: dev' (또는 stg/prod)를 추가하세요"]
        if "change_id" in loc_str:
            return ["최상위에 'change_id: 2025-10-20_001' 형식으로 추가하세요"]
        if "items" in loc_str:
            return ["'topics:' 대신 'items:'를 사용하세요"]
        return []


class ExtraInputsHandler(ErrorHandler):
    """허용되지 않는 필드 에러 핸들러"""

    def can_handle(self, err: dict[str, Any]) -> bool:
        return "Extra inputs are not permitted" in err["msg"]

    def handle(self, err: dict[str, Any]) -> tuple[str, list[str]]:
        field_name = str(err["loc"][-1]) if err["loc"] else "unknown"
        error_msg = f"❌ 허용되지 않는 필드: {field_name}"
        suggestions = self._get_field_suggestions(field_name)
        return (error_msg, suggestions)

    def _get_field_suggestions(self, field_name: str) -> list[str]:
        """필드명별 제안사항 반환"""
        if field_name == "topics":
            return ["'topics:' 대신 'items:'를 사용하세요"]
        if "environment" in field_name:
            return ["'environment'는 metadata가 아니라 최상위에 'env'로 지정하세요"]
        return []


class KafkaConfigHandler(ErrorHandler):
    """Kafka 설정 필드명 에러 핸들러"""

    def can_handle(self, err: dict[str, Any]) -> bool:
        loc_str = str(err["loc"])
        return "retention.ms" in loc_str or "compression.type" in loc_str

    def handle(self, err: dict[str, Any]) -> tuple[str, list[str]]:
        loc = " → ".join(str(x) for x in err["loc"])
        error_msg = f"❌ 잘못된 필드명: {loc}"
        suggestions = [
            "Kafka config는 점(.)이 아니라 언더스코어(_)를 사용하세요",
            "예: retention.ms → retention_ms, compression.type → compression_type",
        ]
        return (error_msg, suggestions)


def _build_error_handler_chain() -> ErrorHandler:
    """에러 핸들러 체인 생성"""
    # Chain: FieldRequired → ExtraInputs → KafkaConfig
    field_required = FieldRequiredHandler()
    extra_inputs = ExtraInputsHandler()
    kafka_config = KafkaConfigHandler()

    field_required.set_next(extra_inputs).set_next(kafka_config)
    return field_required


def translate_validation_error(e: ValidationError, parsed: dict[str, Any]) -> FailureDetail:
    """Pydantic ValidationError를 사용자 친화적 FailureDetail로 변환

    Args:
        e: Pydantic ValidationError
        parsed: 파싱된 YAML 딕셔너리

    Returns:
        사용자 친화적 에러 메시지가 포함된 FailureDetail
    """
    # 에러 핸들러 체인 생성
    handler_chain = _build_error_handler_chain()

    user_friendly_errors: list[str] = []
    suggestions: list[str] = []

    # 각 에러를 핸들러 체인으로 처리
    for err in e.errors():
        error_msg, error_suggestions = handler_chain.process(err)
        user_friendly_errors.append(error_msg)
        suggestions.extend(error_suggestions)

    # 공통 제안사항 추가 (에러별 제안이 없는 경우)
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
