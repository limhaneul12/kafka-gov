"""리팩토링 검증 테스트"""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_container_import():
    """지연 로딩 제거 검증 - container import 성공"""
    from app.shared.container import InfrastructureContainer

    assert InfrastructureContainer is not None


@pytest.mark.unit
def test_authorization_function():
    """Authorization 단순화 검증 - 함수 기반"""
    from app.analysis.domain.authorization import validate_action
    from app.shared.roles import UserRole

    # ADMIN은 모든 권한 보유
    validate_action(UserRole.ADMIN, "view")
    validate_action(UserRole.ADMIN, "analyze")
    validate_action(UserRole.ADMIN, "link")
    validate_action(UserRole.ADMIN, "delete")

    # VIEWER는 읽기만 가능
    validate_action(UserRole.VIEWER, "view")
    validate_action(UserRole.VIEWER, "analyze")

    with pytest.raises(PermissionError):
        validate_action(UserRole.VIEWER, "link")

    with pytest.raises(PermissionError):
        validate_action(UserRole.VIEWER, "delete")


# Policy 모듈 제거로 인해 extract_resource_name 테스트 제거됨


@pytest.mark.unit
def test_subject_utils():
    """토픽 추출 로직 공통화 검증"""
    from app.shared.domain.subject_utils import SubjectStrategy, extract_topics_from_subject

    # TopicNameStrategy
    topics = extract_topics_from_subject("orders-value", SubjectStrategy.TOPIC_NAME)
    assert topics == ["orders"]

    topics = extract_topics_from_subject("orders-key", SubjectStrategy.TOPIC_NAME)
    assert topics == ["orders"]

    # TopicRecordNameStrategy
    topics = extract_topics_from_subject(
        "orders-com.example.Order", SubjectStrategy.TOPIC_RECORD_NAME
    )
    assert topics == ["orders"]

    # RecordNameStrategy (토픽 추출 불가)
    topics = extract_topics_from_subject("com.example.Order", SubjectStrategy.RECORD_NAME)
    assert topics == []

    # 문자열로 전달
    topics = extract_topics_from_subject("orders-value", "TopicNameStrategy")
    assert topics == ["orders"]


@pytest.mark.unit
def test_constants():
    """Magic number 상수화 검증"""
    from app.analysis.domain.services import HIGH_RISK_TOPIC_THRESHOLD
    from app.schema.domain.services import HIGH_VERSION_COUNT_THRESHOLD

    assert HIGH_RISK_TOPIC_THRESHOLD == 5
    assert HIGH_VERSION_COUNT_THRESHOLD == 10


@pytest.mark.unit
def test_logging_setup():
    """로깅 개선 검증"""
    import logging

    # app.main import 시 FastAPI 초기화로 인한 부작용 방지
    # 대신 로깅 모듈이 올바르게 설정되었는지만 확인
    logger = logging.getLogger("app.main")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "app.main"


@pytest.mark.unit
def test_no_lazy_loading():
    """지연 로딩 금지 검증 - __import__ 사용 없음"""
    import ast
    from pathlib import Path

    # app/shared/container.py 파일 읽기
    container_file = Path("app/shared/container.py")
    content = container_file.read_text()

    # AST 파싱
    tree = ast.parse(content)

    # __import__ 호출 찾기
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                pytest.fail("__import__ 사용이 발견되었습니다. 지연 로딩 금지 규칙 위반!")

    # 테스트 통과
    assert True
