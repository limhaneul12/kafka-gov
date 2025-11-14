"""Schema MySQL Repository 구현체 (Session Factory 패턴)"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.schema.domain.models import (
    ChangeId,
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainPlanAction,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaCompatibilityIssue,
    DomainSchemaCompatibilityReport,
    DomainSchemaImpactRecord,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaUploadResult,
)
from app.schema.domain.repositories.interfaces import ISchemaMetadataRepository
from app.schema.infrastructure.models import (
    SchemaApplyResultModel,
    SchemaArtifactModel,
    SchemaMetadataModel,
    SchemaPlanModel,
    SchemaUploadResultModel,
)

logger = logging.getLogger(__name__)


class MySQLSchemaMetadataRepository(ISchemaMetadataRepository):
    """MySQL 기반 스키마 메타데이터 리포지토리 (Session Factory 패턴)

    각 메서드가 session_factory를 통해 독립적으로 session을 생성하고 관리합니다.
    Transaction 경계가 명확하며, context manager가 자동으로 commit/rollback을 처리합니다.
    """

    def __init__(
        self, session_factory: Callable[..., AbstractAsyncContextManager[AsyncSession]]
    ) -> None:
        self.session_factory = session_factory

    async def save_plan(self, plan: DomainSchemaPlan, created_by: str) -> None:
        """계획 저장 (UPSERT: 동일 change_id면 업데이트)"""
        async with self.session_factory() as session:
            try:
                # SchemaPlan 도메인 객체를 JSON으로 직렬화
                plan_data = {
                    "change_id": plan.change_id,
                    "env": plan.env.value,
                    "items": [
                        {
                            "subject": item.subject,
                            "action": item.action.value,
                            "current_version": item.current_version,
                            "target_version": item.target_version,
                            "diff": item.diff,
                        }
                        for item in plan.items
                    ],
                    "compatibility_reports": [
                        {
                            "subject": report.subject,
                            "mode": report.mode.value
                            if hasattr(report.mode, "value")
                            else report.mode,
                            "is_compatible": report.is_compatible,
                            "issues": [
                                {
                                    "path": issue.path,
                                    "message": issue.message,
                                    "issue_type": issue.issue_type,
                                }
                                for issue in report.issues
                            ],
                        }
                        for report in plan.compatibility_reports
                    ],
                    "impacts": [
                        {
                            "subject": impact.subject,
                            "topics": list(impact.topics),
                            "consumers": list(impact.consumers),
                        }
                        for impact in plan.impacts
                    ],
                }

                # UPSERT: 동일 change_id가 있으면 업데이트
                insert_stmt = mysql_insert(SchemaPlanModel).values(
                    change_id=plan.change_id,
                    env=plan.env.value,
                    plan_data=plan_data,
                    can_apply=plan.can_apply,
                    created_by=created_by,
                )

                # ON DUPLICATE KEY UPDATE
                upsert_stmt = insert_stmt.on_duplicate_key_update(
                    env=insert_stmt.inserted.env,
                    plan_data=insert_stmt.inserted.plan_data,
                    can_apply=insert_stmt.inserted.can_apply,
                    status="pending",  # 다시 pending으로 초기화
                    updated_by=created_by,
                )

                await session.execute(upsert_stmt)
                await session.flush()

                logger.info(f"Schema plan saved: {plan.change_id}")

            except Exception as e:
                logger.error(f"Failed to save schema plan {plan.change_id}: {e}")
                raise

    async def get_plan(self, change_id: ChangeId) -> DomainSchemaPlan | None:
        """계획 조회"""
        async with self.session_factory() as session:
            try:
                stmt = select(SchemaPlanModel).where(SchemaPlanModel.change_id == change_id)
                result = await session.execute(stmt)
                plan_model = result.scalar_one_or_none()

                if plan_model is None:
                    return None

                # JSON 데이터를 SchemaPlan 도메인 객체로 역직렬화
                plan_data = plan_model.plan_data

                # 계획 아이템 역직렬화

                items: list[DomainSchemaPlanItem] = [
                    DomainSchemaPlanItem(
                        subject=item["subject"],
                        action=DomainPlanAction(item["action"]),
                        current_version=item["current_version"],
                        target_version=item["target_version"],
                        diff=item["diff"],
                    )
                    for item in plan_data["items"]
                ]

                compatibility_reports: list[DomainSchemaCompatibilityReport] = [
                    DomainSchemaCompatibilityReport(
                        subject=report["subject"],
                        mode=DomainCompatibilityMode(report["mode"]),
                        is_compatible=report["is_compatible"],
                        issues=tuple(
                            DomainSchemaCompatibilityIssue(
                                path=issue["path"],
                                message=issue["message"],
                                issue_type=issue["issue_type"],
                            )
                            for issue in report["issues"]
                        ),
                    )
                    for report in plan_data.get("compatibility_reports", [])
                ]

                # 영향도 정보 역직렬화
                impacts: list[DomainSchemaImpactRecord] = [
                    DomainSchemaImpactRecord(
                        subject=impact["subject"],
                        topics=tuple(impact["topics"]),
                        consumers=tuple(impact["consumers"]),
                    )
                    for impact in plan_data.get("impacts", [])
                ]

                # Environment enum으로 변환
                env = DomainEnvironment(plan_data["env"])

                return DomainSchemaPlan(
                    change_id=plan_data["change_id"],
                    env=env,
                    items=tuple(items),
                    compatibility_reports=tuple(compatibility_reports),
                    impacts=tuple(impacts),
                )

            except Exception as e:
                logger.error(f"Failed to get schema plan {change_id}: {e}")
                raise

    async def save_apply_result(self, result: DomainSchemaApplyResult, applied_by: str) -> None:
        """적용 결과 저장"""
        async with self.session_factory() as session:
            try:
                # SchemaApplyResult 도메인 객체를 JSON으로 직렬화
                result_data = {
                    "change_id": result.change_id,
                    "env": result.env.value,
                    "registered": list(result.registered),
                    "skipped": list(result.skipped),
                    "failed": [
                        {
                            "subject": failed_item.get("subject", "unknown"),
                            "error": failed_item.get("error", "unknown error"),
                        }
                        for failed_item in result.failed
                    ],
                    "audit_id": result.audit_id,
                    "artifacts": [
                        {
                            "subject": artifact.subject,
                            "version": artifact.version,
                            "storage_url": artifact.storage_url,
                            "checksum": artifact.checksum,
                        }
                        for artifact in result.artifacts
                    ],
                    "summary": result.summary(),
                }

                registered_count: int = len(result.registered)
                failed_count: int = len(result.failed)

                result_model = SchemaApplyResultModel(
                    change_id=result.change_id,
                    result_data=result_data,
                    registered_count=registered_count,
                    failed_count=failed_count,
                    applied_by=applied_by,
                )

                session.add(result_model)
                await session.flush()

                logger.info(f"Schema apply result saved: {result.change_id}")

            except Exception as e:
                logger.error(f"Failed to save schema apply result {result.change_id}: {e}")
                raise

    async def record_artifact(self, artifact: DomainSchemaArtifact, change_id: ChangeId) -> None:
        """아티팩트 기록 (Upsert 패턴)"""
        async with self.session_factory() as session:
            try:
                # MySQL INSERT ... ON DUPLICATE KEY UPDATE
                stmt = mysql_insert(SchemaArtifactModel).values(
                    subject=artifact.subject,
                    version=artifact.version,
                    storage_url=artifact.storage_url,
                    checksum=artifact.checksum,
                    change_id=change_id,
                    schema_type=artifact.schema_type.value if artifact.schema_type else "UNKNOWN",
                )

                # 중복 시 업데이트
                stmt = stmt.on_duplicate_key_update(
                    storage_url=artifact.storage_url,
                    checksum=artifact.checksum,
                    change_id=change_id,
                    schema_type=artifact.schema_type.value if artifact.schema_type else "UNKNOWN",
                )

                await session.execute(stmt)
                await session.flush()

                logger.info(f"Schema artifact recorded: {artifact.subject} v{artifact.version}")

            except Exception as e:
                logger.error(f"Failed to record schema artifact {artifact.subject}: {e}")
                raise

    async def save_upload_result(self, upload: DomainSchemaUploadResult, uploaded_by: str) -> None:
        """업로드 결과 저장"""
        async with self.session_factory() as session:
            try:
                # 아티팩트 목록을 JSON으로 변환
                artifacts_data = [
                    {
                        "subject": artifact.subject,
                        "version": artifact.version,
                        "storage_url": artifact.storage_url,
                        "checksum": artifact.checksum,
                    }
                    for artifact in upload.artifacts
                ]

                # 업로드 결과 모델 생성
                upload_model = SchemaUploadResultModel(
                    upload_id=upload.upload_id,
                    change_id=upload.upload_id.split("_")[1]
                    if "_" in upload.upload_id
                    else "unknown",
                    artifacts={"items": artifacts_data},
                    artifact_count=len(upload.artifacts),
                    uploaded_by=uploaded_by,
                )

                session.add(upload_model)
                await session.flush()

                logger.info(
                    f"Upload result saved: {upload.upload_id} ({len(upload.artifacts)} artifacts)"
                )

            except Exception as e:
                logger.error(
                    f"Failed to save upload result {upload.upload_id if hasattr(upload, 'upload_id') else 'unknown'}: {e}"
                )
                # 업로드 결과 저장 실패는 치명적이지 않으므로 예외를 발생시키지 않음

    async def list_artifacts(self) -> list[DomainSchemaArtifact]:
        """모든 스키마 아티팩트 목록 조회 (호환성 모드 포함)"""
        async with self.session_factory() as session:
            try:
                # 1. 모든 artifact 조회
                stmt_artifacts = select(SchemaArtifactModel).order_by(
                    SchemaArtifactModel.subject, SchemaArtifactModel.version.desc()
                )
                result_artifacts = await session.execute(stmt_artifacts)
                artifact_models = result_artifacts.scalars().all()

                # 2. 모든 subject의 metadata 조회 (N+1 방지)
                subjects = {artifact.subject for artifact in artifact_models}
                stmt_metadata = select(SchemaMetadataModel).where(
                    SchemaMetadataModel.subject.in_(subjects)
                )
                result_metadata = await session.execute(stmt_metadata)
                metadata_models = result_metadata.scalars().all()

                # 3. subject -> (compatibility_mode, owner) 매핑
                compat_map: dict[str, DomainCompatibilityMode | None] = {}
                owner_map: dict[str, str | None] = {}

                for metadata in metadata_models:
                    # 호환성 모드 추출
                    if metadata.description and "Compatibility:" in metadata.description:
                        parts = metadata.description.split("Compatibility:")
                        if len(parts) > 1:
                            mode_str = parts[1].strip()
                            try:
                                compat_map[metadata.subject] = DomainCompatibilityMode(mode_str)
                            except ValueError:
                                compat_map[metadata.subject] = None
                    else:
                        compat_map[metadata.subject] = None

                    # Owner 정보
                    owner_map[metadata.subject] = metadata.owner

                # 4. DomainSchemaArtifact 생성 (owner 포함)
                return [
                    DomainSchemaArtifact(
                        subject=artifact.subject,
                        version=artifact.version,
                        storage_url=artifact.storage_url,
                        checksum=artifact.checksum,
                        compatibility_mode=compat_map.get(artifact.subject),
                        owner=owner_map.get(artifact.subject),
                    )
                    for artifact in artifact_models
                ]

            except Exception as e:
                logger.error(f"Failed to list schema artifacts: {e}")
                raise

    async def delete_artifact_by_subject(self, subject: str) -> None:
        """Subject별 아티팩트 및 메타데이터 삭제"""
        async with self.session_factory() as session:
            try:
                from sqlalchemy import delete

                # Artifact 삭제
                stmt_artifact = delete(SchemaArtifactModel).where(
                    SchemaArtifactModel.subject == subject
                )
                result_artifact = await session.execute(stmt_artifact)

                # Metadata 삭제 (카운트에 영향)
                stmt_metadata = delete(SchemaMetadataModel).where(
                    SchemaMetadataModel.subject == subject
                )
                result_metadata = await session.execute(stmt_metadata)

                await session.flush()

                logger.info(
                    f"Deleted {result_artifact.rowcount} artifact(s) and "
                    f"{result_metadata.rowcount} metadata for subject: {subject}"
                )

            except Exception as e:
                logger.error(f"Failed to delete artifacts for subject {subject}: {e}")
                raise

    async def save_schema_metadata(self, subject: str, metadata: dict[str, Any]) -> None:
        """스키마 메타데이터 저장 (호환성 모드 포함)"""
        async with self.session_factory() as session:
            try:
                # 기존 메타데이터 조회
                stmt = select(SchemaMetadataModel).where(SchemaMetadataModel.subject == subject)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                # description 생성 (호환성 모드 포함)
                compatibility_mode = metadata.get("compatibility_mode", "BACKWARD")
                description = f"Compatibility: {compatibility_mode}"

                if existing:
                    # 업데이트
                    existing.owner = metadata.get("owner", existing.owner)
                    existing.updated_by = metadata.get("updated_by", "system")
                    existing.description = description
                else:
                    # 새로 생성
                    metadata_model = SchemaMetadataModel(
                        subject=subject,
                        owner=metadata.get("owner"),
                        created_by=metadata.get("created_by", "system"),
                        updated_by=metadata.get("updated_by", "system"),
                        description=description,
                    )
                    session.add(metadata_model)

                await session.flush()
                logger.info(
                    f"Schema metadata saved: {subject} (compatibility: {compatibility_mode})"
                )

            except Exception as e:
                logger.error(f"Failed to save schema metadata {subject}: {e}")
                raise
