"""토픽 일괄 삭제 유스케이스"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from app.shared.constants import ActivityType, AuditAction, AuditStatus
from app.topic.domain.models import (
    DomainEnvironment,
    DomainTopicAction,
    DomainTopicBatch,
    DomainTopicSpec,
    TopicName,
)
from app.topic.domain.repositories.interfaces import IAuditRepository, ITopicMetadataRepository


class TopicBulkDeleteUseCase:
    """토픽 일괄 삭제 유스케이스 - 아키텍처 규격 준수"""

    def __init__(
        self,
        apply_use_case: Any,  # TopicBatchApplyUseCase - Application 레이어 간 순환 참조 방지
        audit_repository: IAuditRepository,
        metadata_repository: ITopicMetadataRepository,
    ) -> None:
        """
        Args:
            apply_use_case: TopicBatchApplyUseCase 인스턴스
                (Any 사용 이유: 같은 Application 레이어의 UseCase 간 순환 참조 방지)
            audit_repository: 감사 로그 저장소
            metadata_repository: 토픽 메타데이터 저장소
        """
        self.apply_use_case = apply_use_case
        self.audit_repository = audit_repository
        self.metadata_repository = metadata_repository
        self.logger = logging.getLogger(__name__)

    async def execute(
        self, cluster_id: str, topic_names: list[TopicName], actor: str
    ) -> dict[str, Any]:
        """
        여러 토픽을 병렬로 삭제합니다.

        Args:
            cluster_id: 클러스터 ID
            topic_names: 삭제할 토픽명 목록
            actor: 작업 수행자

        Returns:
            dict: {"succeeded": [...], "failed": [...], "message": "..."}
        """
        if not topic_names:
            return {
                "succeeded": [],
                "failed": [],
                "message": "No topics specified for deletion",
            }

        async def delete_single_topic(name: TopicName) -> tuple[TopicName, bool]:
            """단일 토픽 삭제 (성공 여부 반환)"""
            try:
                # 토픽 메타데이터 조회 (team 정보)
                metadata = await self.metadata_repository.get_topic_metadata(name)
                team = metadata.get("owner") if metadata else None

                # 개별 배치 생성
                batch = DomainTopicBatch(
                    change_id=f"delete_{name}_{int(datetime.now(UTC).timestamp())}",
                    env=DomainEnvironment.UNKNOWN,
                    specs=(
                        DomainTopicSpec(
                            name=name,
                            action=DomainTopicAction.DELETE,
                            config=None,
                            metadata=None,
                        ),
                    ),
                )

                # Apply Use Case를 통해 삭제 (cluster_id 전달)
                result = await self.apply_use_case.execute(cluster_id, batch, actor)
                success = name in result.applied

                # 감사 로그 기록
                await self.audit_repository.log_topic_operation(
                    change_id=batch.change_id,
                    action=AuditAction.DELETE,
                    target=ActivityType.TOPIC,
                    actor=actor,
                    status=AuditStatus.COMPLETED if success else AuditStatus.FAILED,
                    message=f"Deleted topic: {name}" if success else f"Failed to delete: {name}",
                    snapshot={"topic_name": name},
                    team=team,
                )

                return (name, success)

            except Exception as e:
                self.logger.error(f"Failed to delete topic {name}: {e}", exc_info=True)
                # 토픽 메타데이터 조회 (team 정보)
                try:
                    metadata = await self.metadata_repository.get_topic_metadata(name)
                    team = metadata.get("owner") if metadata else None
                except Exception:
                    team = None

                # 실패 로그 기록
                await self.audit_repository.log_topic_operation(
                    change_id=f"delete_{name}_failed_{int(datetime.now(UTC).timestamp())}",
                    action=AuditAction.DELETE,
                    target=ActivityType.TOPIC,
                    actor=actor,
                    status=AuditStatus.FAILED,
                    message=f"Exception during delete: {e!s}",
                    snapshot={"topic_name": name, "error": str(e)},
                    team=team,
                )
                return (name, False)

        # 모든 토픽을 병렬로 삭제
        results_tuple = await asyncio.gather(*[delete_single_topic(name) for name in topic_names])
        results: list[tuple[TopicName, bool]] = list(results_tuple)

        # 결과 분류
        succeeded: list[TopicName] = [name for name, success in results if success]
        failed: list[TopicName] = [name for name, success in results if not success]

        return {
            "succeeded": succeeded,
            "failed": failed,
            "message": f"Deleted {len(succeeded)} topics, {len(failed)} failed",
        }
