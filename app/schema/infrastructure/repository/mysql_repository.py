"""Schema MySQL Repository 구현체 (Session Factory 패턴)"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
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
    DomainSchemaDiff,
    DomainSchemaImpactRecord,
    DomainSchemaPlan,
    DomainSchemaPlanItem,
    DomainSchemaType,
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
                            "reason": item.reason,
                            "diff": {
                                "type": item.diff.type,
                                "changes": list(item.diff.changes),
                                "current_version": item.diff.current_version,
                                "target_compatibility": item.diff.target_compatibility,
                                "schema_type": item.diff.schema_type,
                            },
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
                        }
                        for impact in plan.impacts
                    ],
                    "actor_context": plan.actor_context,
                }

                # Dialect에 따른 UPSERT 처리
                dialect = session.bind.dialect.name
                if dialect == "mysql":
                    insert_stmt = mysql_insert(SchemaPlanModel).values(
                        change_id=plan.change_id,
                        env=plan.env.value,
                        plan_data=plan_data,
                        can_apply=plan.can_apply,
                        created_by=created_by,
                    )
                    upsert_stmt = insert_stmt.on_duplicate_key_update(
                        env=insert_stmt.inserted.env,
                        plan_data=insert_stmt.inserted.plan_data,
                        can_apply=insert_stmt.inserted.can_apply,
                        status="pending",
                        updated_by=created_by,
                    )
                else:  # sqlite
                    insert_stmt = sqlite_insert(SchemaPlanModel).values(
                        change_id=plan.change_id,
                        env=plan.env.value,
                        plan_data=plan_data,
                        can_apply=plan.can_apply,
                        created_by=created_by,
                    )
                    upsert_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=["change_id"],
                        set_={
                            "env": insert_stmt.excluded.env,
                            "plan_data": insert_stmt.excluded.plan_data,
                            "can_apply": insert_stmt.excluded.can_apply,
                            "status": "pending",
                            "updated_by": created_by,
                        },
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
                        diff=DomainSchemaDiff(
                            type=item["diff"]["type"],
                            changes=tuple(item["diff"]["changes"]),
                            current_version=item["diff"]["current_version"],
                            target_compatibility=item["diff"]["target_compatibility"],
                            schema_type=item["diff"].get("schema_type"),
                        ),
                        reason=item.get("reason"),
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
                    actor_context=plan_data.get("actor_context"),
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
                    "details": [dict(item) for item in result.details],
                    "audit_id": result.audit_id,
                    "actor_context": result.actor_context,
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
                # Dialect에 따른 UPSERT 처리
                dialect = session.bind.dialect.name
                if dialect == "mysql":
                    stmt = mysql_insert(SchemaArtifactModel).values(
                        subject=artifact.subject,
                        version=artifact.version,
                        storage_url=artifact.storage_url,
                        checksum=artifact.checksum,
                        change_id=change_id,
                        schema_type=artifact.schema_type.value
                        if artifact.schema_type
                        else "UNKNOWN",
                    )
                    stmt = stmt.on_duplicate_key_update(
                        storage_url=stmt.inserted.storage_url,
                        checksum=stmt.inserted.checksum,
                        change_id=stmt.inserted.change_id,
                        schema_type=stmt.inserted.schema_type,
                    )
                else:  # sqlite
                    stmt = sqlite_insert(SchemaArtifactModel).values(
                        subject=artifact.subject,
                        version=artifact.version,
                        storage_url=artifact.storage_url,
                        checksum=artifact.checksum,
                        change_id=change_id,
                        schema_type=artifact.schema_type.value
                        if artifact.schema_type
                        else "UNKNOWN",
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["subject", "version"],
                        set_={
                            "storage_url": stmt.excluded.storage_url,
                            "checksum": stmt.excluded.checksum,
                            "change_id": stmt.excluded.change_id,
                            "schema_type": stmt.excluded.schema_type,
                        },
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
                    existing.updated_by = metadata.get("updated_by", existing.updated_by)
                    existing.description = description
                else:
                    # 새로 생성
                    metadata_model = SchemaMetadataModel(
                        subject=subject,
                        owner=metadata.get("owner"),
                        created_by=metadata.get("created_by", "system"),
                        updated_by=metadata.get("updated_by", metadata.get("created_by", "system")),
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

    async def search_artifacts(
        self,
        query: str | None = None,
        owner: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[DomainSchemaArtifact], int]:
        """아티팩트 검색 (필터링 및 페이지네이션)"""
        async with self.session_factory() as session:
            try:
                # Base Query: Metadata와 Artifact 조인
                # (Subject별 최신 버전을 찾기 위해 서브쿼리나 Window Function이 필요할 수 있으나,
                #  여기서는 단순화를 위해 모든 아티팩트를 대상으로 하거나, Metadata 기준 검색 후 최신 아티팩트 매핑)

                # 전략: Metadata 기준으로 검색 후, 각 Subject의 최신 Artifact 조회

                # 1. Metadata 필터링 Query
                stmt = select(SchemaMetadataModel)

                if query:
                    stmt = stmt.where(SchemaMetadataModel.subject.contains(query))

                if owner:
                    stmt = stmt.where(SchemaMetadataModel.owner == owner)

                # 전체 개수 조회
                from sqlalchemy import func

                count_stmt = select(func.count()).select_from(stmt.subquery())
                total_result = await session.execute(count_stmt)
                total_count = total_result.scalar() or 0

                # 페이지네이션 적용
                stmt = stmt.order_by(SchemaMetadataModel.subject).limit(limit).offset(offset)
                result = await session.execute(stmt)
                metadata_list = result.scalars().all()

                if not metadata_list:
                    return [], 0

                # 2. 검색된 Subject들의 최신 Artifact 조회
                subjects = [m.subject for m in metadata_list]

                # 각 Subject별 최신 버전 Artifact 조회
                # (MySQL/SQLite 호환 및 단순화를 위해 IN 절 사용 후 애플리케이션 레벨에서 그룹핑)
                stmt_artifacts = (
                    select(SchemaArtifactModel)
                    .where(SchemaArtifactModel.subject.in_(subjects))
                    .order_by(SchemaArtifactModel.subject, SchemaArtifactModel.version.desc())
                )
                result_artifacts = await session.execute(stmt_artifacts)
                all_artifacts = result_artifacts.scalars().all()

                # Subject별 최신 Artifact 추출
                latest_artifacts_map = {}
                for artifact in all_artifacts:
                    if artifact.subject not in latest_artifacts_map:
                        latest_artifacts_map[artifact.subject] = artifact

                # 3. Domain Model로 변환
                domain_artifacts = []
                for meta in metadata_list:
                    artifact = latest_artifacts_map.get(meta.subject)

                    # 호환성 모드 파싱
                    compat_mode = None
                    if meta.description and "Compatibility:" in meta.description:
                        try:
                            mode_str = meta.description.split("Compatibility:")[1].strip()
                            compat_mode = DomainCompatibilityMode(mode_str)
                        except ValueError:
                            pass

                    domain_artifacts.append(
                        DomainSchemaArtifact(
                            subject=meta.subject,
                            owner=meta.owner,
                            compatibility_mode=compat_mode,
                            # 아티팩트 정보가 있으면 채우고, 없으면(메타만 존재) None/Default
                            version=artifact.version if artifact else None,
                            storage_url=artifact.storage_url if artifact else None,
                            checksum=artifact.checksum if artifact else None,
                            schema_type=self._to_domain_schema_type(artifact.schema_type)
                            if artifact
                            else None,
                            created_at=artifact.created_at if artifact else None,
                        )
                    )

                return domain_artifacts, total_count

            except Exception as e:
                logger.error(f"Failed to search artifacts: {e}")
                return [], 0

    async def get_latest_artifact(self, subject: str) -> DomainSchemaArtifact | None:
        """Subject의 최신 아티팩트 및 메타데이터 조회"""
        async with self.session_factory() as session:
            try:
                # 1. 최신 Artifact 조회
                stmt_artifact = (
                    select(SchemaArtifactModel)
                    .where(SchemaArtifactModel.subject == subject)
                    .order_by(SchemaArtifactModel.version.desc())
                    .limit(1)
                )
                result_artifact = await session.execute(stmt_artifact)
                artifact_model = result_artifact.scalar_one_or_none()

                # 2. Metadata 조회
                stmt_metadata = select(SchemaMetadataModel).where(
                    SchemaMetadataModel.subject == subject
                )
                result_metadata = await session.execute(stmt_metadata)
                metadata_model = result_metadata.scalar_one_or_none()

                if not artifact_model and not metadata_model:
                    return None

                # 3. 호환성 모드 파싱
                compat_mode = None
                if (
                    metadata_model
                    and metadata_model.description
                    and "Compatibility:" in metadata_model.description
                ):
                    try:
                        mode_str = metadata_model.description.split("Compatibility:")[1].strip()
                        compat_mode = DomainCompatibilityMode(mode_str)
                    except ValueError:
                        pass

                return DomainSchemaArtifact(
                    subject=subject,
                    version=artifact_model.version if artifact_model else None,
                    storage_url=artifact_model.storage_url if artifact_model else None,
                    checksum=artifact_model.checksum if artifact_model else None,
                    schema_type=self._to_domain_schema_type(artifact_model.schema_type)
                    if artifact_model
                    else None,
                    compatibility_mode=compat_mode,
                    owner=metadata_model.owner if metadata_model else None,
                    created_at=artifact_model.created_at if artifact_model else None,
                )

            except Exception as e:
                logger.error(f"Failed to get latest artifact for {subject}: {e}")
                return None

    def _to_domain_schema_type(self, type_str: str | None) -> DomainSchemaType | None:
        """문자열을 DomainSchemaType Enum으로 안전하게 변환"""
        if not type_str:
            return None
        try:
            return DomainSchemaType(type_str)
        except ValueError:
            return None
