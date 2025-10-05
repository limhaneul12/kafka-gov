"""Schema MySQL Repository 구현체 (Session Factory 패턴)"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schema.domain.models import (
    ChangeId,
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainPlanAction,
    DomainPolicyViolation,
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
        """계획 저장"""
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
                    "violations": [
                        {
                            "subject": v.subject,
                            "rule": v.rule,
                            "message": v.message,
                            "severity": v.severity,
                            "field": v.field,
                        }
                        for v in plan.violations
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

                plan_model = SchemaPlanModel(
                    change_id=plan.change_id,
                    env=plan.env.value,
                    plan_data=plan_data,
                    can_apply=plan.can_apply,
                    created_by=created_by,
                )

                session.add(plan_model)
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

                # 정책 위반 역직렬화
                violations: list[DomainPolicyViolation] = [
                    DomainPolicyViolation(
                        subject=v["subject"],
                        rule=v["rule"],
                        message=v["message"],
                        severity=v["severity"],
                        field=v["field"],
                    )
                    for v in plan_data["violations"]
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
                    violations=tuple(violations),
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
        """아티팩트 기록"""
        async with self.session_factory() as session:
            try:
                artifact_model = SchemaArtifactModel(
                    subject=artifact.subject,
                    version=artifact.version,
                    storage_url=artifact.storage_url,
                    checksum=artifact.checksum,
                    change_id=change_id,
                    schema_type="UNKNOWN",  # 실제 구현에서는 artifact에서 가져와야 함
                )

                session.add(artifact_model)
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
        """모든 스키마 아티팩트 목록 조회"""
        async with self.session_factory() as session:
            try:
                stmt = select(SchemaArtifactModel).order_by(
                    SchemaArtifactModel.subject, SchemaArtifactModel.version.desc()
                )
                result = await session.execute(stmt)
                artifact_models = result.scalars().all()

                return [
                    DomainSchemaArtifact(
                        subject=artifact.subject,
                        version=artifact.version,
                        storage_url=artifact.storage_url,
                        checksum=artifact.checksum,
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
