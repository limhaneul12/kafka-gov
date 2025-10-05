"""Schema Application 유스케이스"""

from __future__ import annotations

import hashlib
import logging
import uuid
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import orjson

from app.analysis.domain.repositories import ICorrelationRepository
from app.shared.constants import AuditAction, AuditStatus, AuditTarget
from app.shared.domain.events import SchemaRegisteredEvent
from app.shared.domain.policy_types import DomainPolicySeverity
from app.shared.infrastructure.event_bus import get_event_bus

from ..domain.models import (
    ChangeId,
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSchemaApplyResult,
    DomainSchemaArtifact,
    DomainSchemaBatch,
    DomainSchemaDeleteImpact,
    DomainSchemaPlan,
    DomainSchemaSource,
    DomainSchemaSourceType,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSchemaUploadResult,
    DomainSubjectStrategy,
    SubjectName,
)
from ..domain.policies import SchemaPolicyEngine
from ..domain.repositories.interfaces import (
    IObjectStorageRepository,
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaRegistryRepository,
)
from ..domain.services import SchemaDeleteAnalyzer, SchemaPlannerService


class SchemaBatchDryRunUseCase:
    """스키마 배치 Dry-Run 유스케이스"""

    def __init__(
        self,
        registry_repository: ISchemaRegistryRepository,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
        policy_engine: SchemaPolicyEngine,
    ) -> None:
        self.registry_repository = registry_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.policy_engine = policy_engine
        self.planner_service = SchemaPlannerService(registry_repository, policy_engine)

    async def execute(self, batch: DomainSchemaBatch, actor: str) -> DomainSchemaPlan:
        await self.audit_repository.log_operation(
            change_id=batch.change_id,
            action=AuditAction.DRY_RUN,
            target=AuditTarget.BATCH,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Schema dry-run started for {len(batch.specs)} subjects",
        )

        try:
            plan = await self.planner_service.create_plan(batch)

            # 정책 위반 분석
            if plan.violations:
                self._analyze_policy_violations(list(plan.violations), actor)

            await self.metadata_repository.save_plan(plan, actor)
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.DRY_RUN,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message="Schema dry-run completed",
                snapshot={"summary": plan.summary()},
            )
            return plan
        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.DRY_RUN,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Schema dry-run failed: {exc!s}",
            )
            raise

    def _analyze_policy_violations(self, violations: list, actor: str) -> None:
        """정책 위반 분석 (통합 형식 활용)"""

        # DomainPolicySeverity Enum 기반 분석 가능
        blocking_count = sum(
            1
            for v in violations
            if v.severity in (DomainPolicySeverity.ERROR, DomainPolicySeverity.CRITICAL)
        )

        # 로깅이나 추가 처리
        print(f"Policy violations analysis - Total: {len(violations)}, Blocking: {blocking_count}")


class SchemaBatchApplyUseCase:
    """스키마 배치 Apply 유스케이스"""

    def __init__(
        self,
        registry_repository: ISchemaRegistryRepository,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
        storage_repository: IObjectStorageRepository | None,
        policy_engine: SchemaPolicyEngine,
    ) -> None:
        self.registry_repository = registry_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.storage_repository = storage_repository
        self.policy_engine = policy_engine
        self.planner_service = SchemaPlannerService(registry_repository, policy_engine)
        self.event_bus = get_event_bus()

    async def execute(self, batch: DomainSchemaBatch, actor: str) -> DomainSchemaApplyResult:
        audit_id = str(uuid.uuid4())
        await self.audit_repository.log_operation(
            change_id=batch.change_id,
            action=AuditAction.APPLY,
            target=AuditTarget.BATCH,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Schema apply started for {len(batch.specs)} subjects",
        )

        try:
            plan = await self.planner_service.create_plan(batch)
            if not plan.can_apply:
                raise ValueError("Policy violations or incompatibilities detected; apply aborted")

            registered: list[str] = []
            skipped: list[str] = []
            failed: list[dict[str, str]] = []
            artifacts: list[DomainSchemaArtifact] = []

            for spec in batch.specs:
                if spec.dry_run_only:
                    skipped.append(spec.subject)
                    continue

                try:
                    version = await self.registry_repository.register_schema(spec)
                    artifact = await self._persist_artifact(spec, version, batch.change_id)
                    if artifact:
                        artifacts.append(artifact)
                    registered.append(spec.subject)

                    # 🆕 Domain Event 발행
                    await self._publish_schema_registered_event(
                        spec=spec,
                        version=version,
                        batch=batch,
                        actor=actor,
                    )

                except Exception as exc:
                    failed.append({"subject": spec.subject, "error": str(exc)})

            result = DomainSchemaApplyResult(
                change_id=batch.change_id,
                env=batch.env,
                registered=tuple(registered),
                skipped=tuple(skipped),
                failed=tuple(failed),
                audit_id=audit_id,
                artifacts=tuple(artifacts),
            )

            await self.metadata_repository.save_apply_result(result, actor)
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message="Schema apply completed",
                snapshot={"summary": result.summary()},
            )

            return result
        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action=AuditAction.APPLY,
                target=AuditTarget.BATCH,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Schema apply failed: {exc!s}",
            )
            raise

    async def _persist_artifact(
        self,
        spec: DomainSchemaSpec,
        version: int,
        change_id: ChangeId,
    ) -> DomainSchemaArtifact | None:
        if self.storage_repository is None:
            return None

        payload: str | None = None
        if spec.schema:
            payload = spec.schema
        elif spec.source and spec.source.inline:
            payload = spec.source.inline
        elif spec.source and spec.source.yaml:
            payload = spec.source.yaml

        if payload is None:
            return None

        key = f"{spec.environment.value}/{spec.subject}/{version}/schema.txt"
        metadata = {"change_id": change_id, "schema_type": spec.schema_type.value}
        storage_url = await self.storage_repository.put_object(
            key=key,
            data=payload.encode(),
            metadata=metadata,
        )

        artifact = DomainSchemaArtifact(
            subject=spec.subject,
            version=version,
            storage_url=storage_url,
            checksum=spec.schema_hash or spec.fingerprint(),
        )
        await self.metadata_repository.record_artifact(artifact, change_id)

    async def _publish_schema_registered_event(
        self,
        spec: DomainSchemaSpec,
        version: int,
        batch: DomainSchemaBatch,
        actor: str,
    ) -> None:
        """스키마 등록 이벤트 발행"""
        # Schema Registry에서 schema_id 조회
        subjects_info = await self.registry_repository.describe_subjects([spec.subject])
        schema_info = subjects_info.get(spec.subject)
        schema_id: int = (
            schema_info.schema_id if schema_info and schema_info.schema_id is not None else 0
        )

        event = SchemaRegisteredEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            aggregate_id=batch.change_id,
            occurred_at=datetime.now(),
            subject=spec.subject,
            version=version,
            schema_type=spec.schema_type.value,
            schema_id=schema_id,
            compatibility_mode=spec.compatibility.value,
            subject_strategy=batch.subject_strategy.value,
            environment=batch.env.value,
            actor=actor,
        )

        await self.event_bus.publish(event)


class SchemaPlanUseCase:
    """스키마 계획 조회 유스케이스"""

    def __init__(self, metadata_repository: ISchemaMetadataRepository) -> None:
        self.metadata_repository = metadata_repository

    async def execute(self, change_id: ChangeId) -> DomainSchemaPlan | None:
        return await self.metadata_repository.get_plan(change_id)


class SchemaUploadUseCase:
    """스키마 업로드 유스케이스"""

    def __init__(
        self,
        storage_repository: IObjectStorageRepository,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
        registry_repository: ISchemaRegistryRepository,
    ) -> None:
        self.storage_repository = storage_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.registry_repository = registry_repository
        self.event_bus = get_event_bus()

    async def execute(
        self,
        *,
        env: DomainEnvironment,
        change_id: ChangeId,
        owner: str,
        files: list[Any],  # FastAPI UploadFile 객체들
        actor: str,
    ) -> DomainSchemaUploadResult:
        """스키마 파일 업로드 처리"""
        upload_id = f"upload_{change_id}_{uuid.uuid4().hex[:8]}"

        await self.audit_repository.log_operation(
            change_id=change_id,
            action=AuditAction.UPLOAD,
            target=AuditTarget.FILES,
            actor=actor,
            status=AuditStatus.STARTED,
            message=f"Schema upload started: {len(files)} files",
        )

        try:
            # 1. 파일 검증
            validated_files = await self._validate_files(files)

            # 2. 파일 처리 및 업로드 (MinIO + Schema Registry)
            artifact_results = [
                await self._process_and_upload_file(
                    file_info, env, change_id, upload_id, owner, actor
                )
                for file_info in validated_files
            ]
            artifacts: list[DomainSchemaArtifact] = [
                artifact for artifact in artifact_results if artifact is not None
            ]

            # 3. 결과 생성
            result = DomainSchemaUploadResult(upload_id=upload_id, artifacts=tuple(artifacts))

            # 4. 메타데이터 저장
            await self.metadata_repository.save_upload_result(result, actor)

            # 5. 감사 로그 완료 (상세 정보 포함)
            schema_details = ", ".join([f"{a.subject} (v{a.version})" for a in artifacts[:3]])
            if len(artifacts) > 3:
                schema_details += f" 외 {len(artifacts) - 3}개"

            await self.audit_repository.log_operation(
                change_id=change_id,
                action=AuditAction.REGISTER,
                target=artifacts[0].subject if artifacts else AuditTarget.UNKNOWN,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message=f"스키마 등록 완료: {schema_details}",
                snapshot={
                    "summary": result.summary(),
                    "artifacts": [
                        {
                            "subject": a.subject,
                            "version": a.version,
                            "type": a.schema_type.value if a.schema_type else "UNKNOWN",
                        }
                        for a in artifacts
                    ],
                },
            )

            return result

        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=change_id,
                action=AuditAction.UPLOAD,
                target=AuditTarget.FILES,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Schema upload failed: {exc!s}",
            )
            raise

    async def _validate_files(self, files: list[Any]) -> list[dict[str, Any]]:
        """파일 검증 및 메타데이터 추출"""
        if not files:
            raise ValueError("No files provided")

        supported_extensions = {".avsc", ".json", ".proto", ".zip"}
        max_file_size = 10 * 1024 * 1024  # 10MB

        validated_files: list[dict[str, Any]] = []

        for file in files:
            filename = getattr(file, "filename", "unknown")
            if not filename:
                raise ValueError("File must have a filename")

            file_path = Path(filename)
            extension = file_path.suffix.lower()

            if extension not in supported_extensions:
                raise ValueError(
                    f"Unsupported file type: {extension}. Supported: {', '.join(supported_extensions)}"
                )

            content = await file.read()
            if len(content) > max_file_size:
                raise ValueError(
                    f"File {filename} is too large (max: {max_file_size // (1024 * 1024)}MB)"
                )

            if len(content) == 0:
                raise ValueError(f"File {filename} is empty")

            validated_files.append(
                {
                    "filename": filename,
                    "extension": extension,
                    "content": content,
                    "size": len(content),
                    "content_type": getattr(file, "content_type", "application/octet-stream"),
                }
            )

        return validated_files

    async def _process_and_upload_file(
        self,
        file_info: dict[str, Any],
        env: DomainEnvironment,
        change_id: ChangeId,
        upload_id: str,
        owner: str,
        actor: str,
    ) -> DomainSchemaArtifact | None:
        """개별 파일 처리 및 업로드"""
        if self.storage_repository is None:
            return None

        extension = file_info["extension"]

        if extension == ".zip":
            return await self._process_zip_file(file_info, env, change_id, upload_id)

        return await self._process_schema_file(file_info, env, change_id, upload_id, owner, actor)

    async def _process_zip_file(
        self, file_info: dict[str, Any], env: DomainEnvironment, change_id: ChangeId, upload_id: str
    ) -> DomainSchemaArtifact | None:
        """압축 파일 처리"""
        content = file_info["content"]
        filename = file_info["filename"]

        try:
            with zipfile.ZipFile(BytesIO(content), "r") as zip_file:
                file_list = zip_file.namelist()
                if not file_list:
                    raise ValueError(f"ZIP file {filename} is empty")

                schema_files = [
                    f for f in file_list if Path(f).suffix.lower() in {".avsc", ".json", ".proto"}
                ]

                if not schema_files:
                    raise ValueError(f"No schema files found in ZIP: {filename}")

                key = f"{env.value}/uploads/{upload_id}/{filename}"
                metadata = {
                    "change_id": change_id,
                    "upload_id": upload_id,
                    "file_type": "zip_bundle",
                    "schema_count": str(len(schema_files)),
                }

                storage_url = await self.storage_repository.put_object(
                    key=key,
                    data=content,
                    metadata=metadata,
                )

                artifact = DomainSchemaArtifact(
                    subject=f"bundle.{Path(filename).stem}",
                    version=1,
                    storage_url=storage_url,
                    checksum=self._calculate_checksum(content),
                )

                await self.metadata_repository.record_artifact(artifact, change_id)
                return artifact

        except zipfile.BadZipFile as e:
            raise ValueError(f"Invalid ZIP file: {filename}") from e

    async def _process_schema_file(
        self,
        file_info: dict[str, Any],
        env: DomainEnvironment,
        change_id: ChangeId,
        upload_id: str,
        owner: str,
        actor: str,
    ) -> DomainSchemaArtifact | None:
        """스키마 파일 처리 및 Schema Registry 자동 등록"""
        if self.storage_repository is None:
            return None

        filename = file_info["filename"]
        content = file_info["content"]
        extension = file_info["extension"]

        schema_type = self._infer_schema_type(extension)

        try:
            content_str = content.decode("utf-8")
            if extension in {".avsc", ".json"}:
                orjson.loads(content_str)
        except (UnicodeDecodeError, orjson.JSONDecodeError) as e:
            raise ValueError(f"Invalid schema file {filename}: {e}") from e

        # 1. MinIO 저장
        key = f"{env.value}/uploads/{upload_id}/{filename}"
        metadata = {
            "change_id": change_id,
            "upload_id": upload_id,
            "file_type": "schema",
            "schema_type": schema_type,
        }

        storage_url = await self.storage_repository.put_object(
            key=key,
            data=content,
            metadata=metadata,
        )

        subject_name = f"{env.value}.{Path(filename).stem}"

        # 2. Schema Registry 자동 등록
        try:
            # DomainSchemaSpec 생성
            schema_spec = DomainSchemaSpec(
                subject=subject_name,
                schema_type=DomainSchemaType(schema_type),
                compatibility=DomainCompatibilityMode.BACKWARD,  # 기본값
                schema=content_str,
                source=DomainSchemaSource(
                    type=DomainSchemaSourceType.INLINE,
                    inline=content_str,
                ),
            )

            # Schema Registry에 등록
            version = await self.registry_repository.register_schema(schema_spec)

            # 스키마 메타데이터 저장 (owner 포함)
            await self.metadata_repository.save_schema_metadata(
                subject=subject_name,
                metadata={"owner": owner, "created_by": actor, "updated_by": actor},
            )

            # 등록 성공 시 이벤트 발행
            await self._publish_schema_registered_event(
                spec=schema_spec,
                version=version,
                change_id=change_id,
                env=env,
                actor=actor,
            )

            # Artifact 생성 (실제 등록된 버전 사용)
            artifact = DomainSchemaArtifact(
                subject=subject_name,
                version=version,
                storage_url=storage_url,
                checksum=self._calculate_checksum(content),
                schema_type=DomainSchemaType(schema_type),
            )

        except Exception as e:
            # Schema Registry 등록 실패 시에도 MinIO 저장은 유지하고 경고 로그
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Schema Registry registration failed for {subject_name}: {e}. "
                f"File saved to MinIO but not registered."
            )

            # MinIO만 저장된 artifact 반환
            artifact = DomainSchemaArtifact(
                subject=subject_name,
                version=1,
                storage_url=storage_url,
                checksum=self._calculate_checksum(content),
                schema_type=DomainSchemaType(schema_type),
            )

        await self.metadata_repository.record_artifact(artifact, change_id)
        return artifact

    def _infer_schema_type(self, extension: str) -> str:
        """파일 확장자로 스키마 타입 추론"""
        type_mapping = {
            ".avsc": "AVRO",
            ".json": "JSON",
            ".proto": "PROTOBUF",
        }
        return type_mapping.get(extension.lower(), "JSON")

    def _calculate_checksum(self, content: bytes) -> str:
        """콘텐츠 체크섬 계산"""
        return hashlib.sha256(content).hexdigest()[:16]

    async def _publish_schema_registered_event(
        self,
        spec: DomainSchemaSpec,
        version: int,
        change_id: ChangeId,
        env: DomainEnvironment,
        actor: str,
    ) -> None:
        """스키마 등록 이벤트 발행"""
        from ..domain.models import DomainSubjectStrategy

        # Schema Registry에서 schema_id 조회
        subjects_info = await self.registry_repository.describe_subjects([spec.subject])
        schema_info = subjects_info.get(spec.subject)
        schema_id: int = (
            schema_info.schema_id if schema_info and schema_info.schema_id is not None else 0
        )

        event = SchemaRegisteredEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            aggregate_id=change_id,
            occurred_at=datetime.now(),
            subject=spec.subject,
            version=version,
            schema_type=spec.schema_type.value,
            schema_id=schema_id,
            compatibility_mode=spec.compatibility.value,
            subject_strategy=DomainSubjectStrategy.TOPIC_NAME.value,
            environment=env.value,
            actor=actor,
        )

        await self.event_bus.publish(event)


class SchemaSyncUseCase:
    """Schema Registry → DB 동기화 유스케이스"""

    def __init__(
        self,
        registry_repository: ISchemaRegistryRepository,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
    ) -> None:
        self.registry_repository = registry_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository

    async def execute(self, actor: str) -> dict[str, int]:
        """Schema Registry의 모든 스키마를 DB로 동기화

        Returns:
            동기화 결과 (총 subject 수, 새로 추가된 수, 업데이트된 수)
        """
        change_id = f"sync_{uuid.uuid4().hex[:8]}"

        await self.audit_repository.log_operation(
            change_id=change_id,
            action=AuditAction.SYNC,
            target=AuditTarget.SCHEMA_REGISTRY,
            actor=actor,
            status=AuditStatus.STARTED,
            message="Schema synchronization started",
        )

        try:
            # 1. Schema Registry에서 모든 subject 조회
            all_subjects = await self.registry_repository.list_all_subjects()

            if not all_subjects:
                await self.audit_repository.log_operation(
                    change_id=change_id,
                    action=AuditAction.SYNC,
                    target=AuditTarget.SCHEMA_REGISTRY,
                    actor=actor,
                    status=AuditStatus.COMPLETED,
                    message="No schemas found in Schema Registry",
                )
                return {"total": 0, "added": 0, "updated": 0}

            # 2. 각 subject의 최신 버전 정보 조회
            subjects_info = await self.registry_repository.describe_subjects(all_subjects)

            # 3. DB에 artifact로 저장
            added_count = 0
            updated_count = 0

            for subject, info in subjects_info.items():
                artifact = DomainSchemaArtifact(
                    subject=subject,
                    version=info.version,
                    storage_url=f"registry://{subject}/versions/{info.version}",
                    checksum=info.hash,
                )

                try:
                    await self.metadata_repository.record_artifact(artifact, change_id)
                    added_count += 1
                except Exception as e:
                    # 이미 존재하는 경우는 무시
                    logger = logging.getLogger(__name__)
                    logger.debug(
                        f"Artifact already exists or failed: {subject} v{info.version}: {e}"
                    )
                    updated_count += 1

            result = {
                "total": len(subjects_info),
                "added": added_count,
                "updated": updated_count,
            }

            await self.audit_repository.log_operation(
                change_id=change_id,
                action=AuditAction.SYNC,
                target=AuditTarget.SCHEMA_REGISTRY,
                actor=actor,
                status=AuditStatus.COMPLETED,
                message=f"Schema synchronization completed: {result['total']} total, {result['added']} added",
                snapshot=result,
            )

            return result

        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=change_id,
                action=AuditAction.SYNC,
                target=AuditTarget.SCHEMA_REGISTRY,
                actor=actor,
                status=AuditStatus.FAILED,
                message=f"Schema synchronization failed: {exc!s}",
            )
            raise


class SchemaDeleteUseCase:
    """스키마 삭제 유스케이스"""

    def __init__(
        self,
        registry_repository: ISchemaRegistryRepository,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
        correlation_repository: ICorrelationRepository | None = None,
    ) -> None:
        self.registry_repository = registry_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.correlation_repository = correlation_repository
        self.delete_analyzer = SchemaDeleteAnalyzer(registry_repository)

    async def analyze(
        self,
        subject: SubjectName,
        strategy: DomainSubjectStrategy,
        actor: str,
    ) -> DomainSchemaDeleteImpact:
        """스키마 삭제 영향도 분석

        Args:
            subject: 분석할 Subject 이름
            strategy: Subject 전략
            actor: 분석 요청자

        Returns:
            삭제 영향도 분석 결과
        """
        # 영향도 분석 수행
        impact = await self.delete_analyzer.analyze_delete_impact(subject, strategy)

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
        subject: SubjectName,
        strategy: DomainSubjectStrategy,
        actor: str,
        force: bool = False,
    ) -> DomainSchemaDeleteImpact:
        """스키마 삭제 실행 (영향도 분석 포함)

        Args:
            subject: 삭제할 Subject 이름
            strategy: Subject 전략
            actor: 삭제 요청자
            force: 강제 삭제 여부 (경고 무시)

        Returns:
            삭제 영향도 분석 결과

        Raises:
            ValueError: 안전하지 않은 삭제 시도 (force=False)
        """
        # 1. 영향도 분석
        impact = await self.delete_analyzer.analyze_delete_impact(subject, strategy)

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
            await self.registry_repository.delete_subject(subject)

            # DB에서 artifact도 삭제
            try:
                await self.metadata_repository.delete_artifact_by_subject(subject)
            except Exception as db_error:
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to delete artifact from DB for {subject}: {db_error}")

            # Correlation에서 스키마 참조 제거
            if self.correlation_repository:
                try:
                    updated_count = await self.correlation_repository.remove_schema_reference(
                        subject
                    )
                    logger = logging.getLogger(__name__)
                    logger.info(f"Removed schema reference from {updated_count} correlations")
                except Exception as corr_error:
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Failed to remove correlation reference for {subject}: {corr_error}"
                    )

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
