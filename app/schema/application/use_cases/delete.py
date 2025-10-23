"""스키마 삭제 유스케이스"""

from __future__ import annotations

import logging
import uuid

from app.cluster.domain.services import IConnectionManager
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter

from ...domain.models import DomainSchemaDeleteImpact, DomainSubjectStrategy, SubjectName
from ...domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
)
from ...domain.services import SchemaDeleteAnalyzer


class SchemaDeleteUseCase:
    """스키마 삭제 유스케이스 (멀티 레지스트리 지원)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository

    async def analyze(
        self,
        registry_id: str,
        subject: SubjectName,
        strategy: DomainSubjectStrategy,
        actor: str,
    ) -> DomainSchemaDeleteImpact:
        """스키마 삭제 영향도 분석

        Args:
            registry_id: Schema Registry ID
            subject: 분석할 Subject 이름
            strategy: Subject 전략
            actor: 분석 요청자

        Returns:
            삭제 영향도 분석 결과
        """
        # 1. ConnectionManager로 Schema Registry Client 획득
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

        # 2. 영향도 분석 수행
        delete_analyzer = SchemaDeleteAnalyzer(registry_repository)  # type: ignore[arg-type]
        impact = await delete_analyzer.analyze_delete_impact(subject, strategy)

        # 감사 로그 기록
        await self.audit_repository.log_operation(
            change_id=f"delete_analysis_{uuid.uuid4().hex[:8]}",
            action="DELETE_ANALYSIS",
            target=subject,
            actor=actor,
            status="completed",
            message=f"Delete impact analysis: {len(impact.warnings)} warnings, safe={impact.safe_to_delete}",
            snapshot={
                "subject": subject,
                "current_version": impact.current_version,
                "affected_topics": list(impact.affected_topics),
                "warnings": list(impact.warnings),
                "safe_to_delete": impact.safe_to_delete,
            },
        )

        return impact

    async def delete(
        self,
        registry_id: str,
        subject: SubjectName,
        strategy: DomainSubjectStrategy,
        actor: str,
        force: bool = False,
    ) -> DomainSchemaDeleteImpact:
        """스키마 삭제 실행 (영향도 분석 포함)

        Args:
            registry_id: Schema Registry ID
            subject: 삭제할 Subject 이름
            strategy: Subject 전략
            actor: 삭제 요청자
            force: 강제 삭제 여부 (경고 무시)

        Returns:
            삭제 영향도 분석 결과

        Raises:
            ValueError: 안전하지 않은 삭제 시도 (force=False)
        """
        # 1. ConnectionManager로 Schema Registry Client 획득
        registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
        registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

        # 2. 영향도 분석
        delete_analyzer = SchemaDeleteAnalyzer(registry_repository)  # type: ignore[arg-type]
        impact = await delete_analyzer.analyze_delete_impact(subject, strategy)

        # 2. 안전성 검증
        if not force and not impact.safe_to_delete:
            warning_msg = "; ".join(impact.warnings)
            raise ValueError(
                f"스키마 삭제가 안전하지 않습니다: {warning_msg}. "
                f"강제 삭제하려면 force=True를 사용하세요."
            )

        # 3. 실제 삭제 수행
        try:
            # Schema Registry에서 삭제
            await registry_repository.delete_subject(subject)

            # DB에서 artifact도 삭제
            try:
                await self.metadata_repository.delete_artifact_by_subject(subject)
            except Exception as db_error:
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to delete artifact from DB for {subject}: {db_error}")

            # 4. 감사 로그 기록 (성공)
            await self.audit_repository.log_operation(
                change_id=f"delete_{uuid.uuid4().hex[:8]}",
                action="DELETE",
                target=subject,
                actor=actor,
                status="success",
                message=f"Schema deleted (force={force})",
                snapshot={
                    "subject": subject,
                    "deleted_version": impact.current_version,
                    "affected_topics": list(impact.affected_topics),
                    "force": force,
                },
            )

        except Exception as e:
            # 5. 감사 로그 기록 (실패)
            await self.audit_repository.log_operation(
                change_id=f"delete_{uuid.uuid4().hex[:8]}",
                action="DELETE",
                target=subject,
                actor=actor,
                status="failed",
                message=f"Schema deletion failed: {e}",
                snapshot={
                    "subject": subject,
                    "error": str(e),
                },
            )
            raise

        return impact
