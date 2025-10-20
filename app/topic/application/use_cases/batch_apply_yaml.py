"""YAML 기반 토픽 배치 Apply 유스케이스"""

from __future__ import annotations

import yaml as pyyaml
from pydantic import ValidationError

from ...domain.models import DomainTopicApplyResult
from ...interface.adapters import safe_convert_request_to_batch
from ...interface.helpers import translate_usecase_failure, translate_validation_error
from ...interface.schemas import FailureDetail, TopicBatchApplyResponse, TopicBatchRequest
from .batch_apply import TopicBatchApplyUseCase


class TopicBatchApplyFromYAMLUseCase:
    """YAML 문자열을 파싱하여 토픽 배치를 적용하는 유스케이스"""

    def __init__(self, batch_apply_use_case: TopicBatchApplyUseCase) -> None:
        self.batch_apply_use_case = batch_apply_use_case

    async def execute(
        self, cluster_id: str, yaml_content: str, actor: str
    ) -> TopicBatchApplyResponse:
        """YAML 기반 토픽 배치 Apply 실행

        Args:
            cluster_id: Kafka Cluster ID
            yaml_content: YAML 문자열
            actor: 실행자

        Returns:
            TopicBatchApplyResponse
        """
        # 1. YAML 파싱
        try:
            parsed = pyyaml.safe_load(yaml_content)
        except Exception as e:
            # YAML 파싱 실패
            failure = FailureDetail(
                topic_name=None,
                failure_type="yaml_parsing",
                error_message=f"YAML 파싱 실패: {e!s}",
                suggestions=[
                    "YAML 문법을 확인하세요",
                    "들여쓰기가 올바른지 확인하세요",
                    "특수문자는 따옴표로 감싸야 합니다",
                ],
                raw_error=str(e),
            )
            return TopicBatchApplyResponse(
                env="unknown",
                change_id="failed",
                applied=[],
                skipped=[],
                failed=[failure],
                audit_id="n/a",
                summary={
                    "total_items": 0,
                    "applied_count": 0,
                    "skipped_count": 0,
                    "failed_count": 1,
                },
            )

        # 2. Pydantic 검증
        try:
            batch_request = TopicBatchRequest.model_validate(parsed)
        except ValidationError as e:
            # 스키마 검증 실패 - Helper로 사용자 친화적 메시지 생성
            failure = translate_validation_error(e, parsed)
            return TopicBatchApplyResponse(
                env=parsed.get("env", "unknown"),
                change_id=parsed.get("change_id", "failed"),
                applied=[],
                skipped=[],
                failed=[failure],
                audit_id="n/a",
                summary={
                    "total_items": 0,
                    "applied_count": 0,
                    "skipped_count": 0,
                    "failed_count": 1,
                },
            )

        # 3. Domain 객체로 변환
        try:
            batch = safe_convert_request_to_batch(batch_request)
        except Exception as e:
            failure = FailureDetail(
                topic_name=None,
                failure_type="validation",
                error_message=f"Domain 변환 실패: {e!s}",
                suggestions=["내부 오류입니다. 관리자에게 문의하세요"],
                raw_error=str(e),
            )
            return TopicBatchApplyResponse(
                env=batch_request.env,
                change_id=batch_request.change_id,
                applied=[],
                skipped=[],
                failed=[failure],
                audit_id="n/a",
                summary={
                    "total_items": 0,
                    "applied_count": 0,
                    "skipped_count": 0,
                    "failed_count": 1,
                },
            )

        # 4. 배치 Apply UseCase 호출
        try:
            result: DomainTopicApplyResult = await self.batch_apply_use_case.execute(
                cluster_id, batch, actor
            )

            # UseCase 결과를 Response로 변환
            failed_details = [
                translate_usecase_failure(fail_item)
                for fail_item in result.failed
                if isinstance(fail_item, dict)
            ]

            return TopicBatchApplyResponse(
                env=batch_request.env,
                change_id=batch_request.change_id,
                applied=list(result.applied),
                skipped=list(result.skipped),
                failed=failed_details,
                audit_id=result.audit_id,
                summary=result.summary(),
            )
        except Exception as e:
            # 예상치 못한 에러
            failure = FailureDetail(
                topic_name=None,
                failure_type="kafka_error",
                error_message=f"토픽 생성 실패: {e!s}",
                suggestions=["관리자에게 문의하세요", "로그를 확인하세요"],
                raw_error=str(e),
            )
            return TopicBatchApplyResponse(
                env=batch_request.env,
                change_id=batch_request.change_id,
                applied=[],
                skipped=[],
                failed=[failure],
                audit_id="n/a",
                summary={
                    "total_items": 0,
                    "applied_count": 0,
                    "skipped_count": 0,
                    "failed_count": 1,
                },
            )
