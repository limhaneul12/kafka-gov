"""거버넌스 정책/컴플라이언스 도메인 예외"""

from __future__ import annotations

from app.shared.exceptions.base_exceptions import DomainError, NotFoundError


class GovernanceError(DomainError):
    """거버넌스 도메인 예외 베이스"""


class PolicyNotFoundError(NotFoundError):
    """정책을 찾을 수 없음"""

    def __init__(self, policy_id: str) -> None:
        super().__init__("Policy", policy_id)
        self.policy_id = policy_id


class PolicyViolationError(GovernanceError):
    """정책 위반 감지"""

    def __init__(self, violations: list[str]) -> None:
        summary = "; ".join(violations[:3])
        count = len(violations)
        super().__init__(f"{count} policy violation(s): {summary}")
        self.violations = violations
        self.count = count


class ApprovalRequiredError(GovernanceError):
    """승인이 필요한 작업"""

    def __init__(self, reasons: list[str]) -> None:
        summary = "; ".join(reasons[:3])
        super().__init__(f"approval required: {summary}")
        self.reasons = reasons


class ApprovalExpiredError(GovernanceError):
    """승인이 만료됨"""

    def __init__(self, request_id: str) -> None:
        super().__init__(f"approval expired: {request_id}")
        self.request_id = request_id


class ClassificationViolationError(GovernanceError):
    """데이터 분류 등급 정책 위반"""

    def __init__(self, resource: str, required: str, actual: str) -> None:
        super().__init__(
            f"classification violation on {resource}: " f"required {required}, got {actual}"
        )
        self.resource = resource
        self.required = required
        self.actual = actual


class RetentionPolicyViolationError(GovernanceError):
    """보존 정책 위반"""

    def __init__(self, resource: str, message: str) -> None:
        super().__init__(f"retention policy violation on {resource}: {message}")
        self.resource = resource
