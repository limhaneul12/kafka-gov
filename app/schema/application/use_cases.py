"""Schema Application 유스케이스"""

from __future__ import annotations

import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from ..domain.models import (
    ChangeId,
    Environment,
    SchemaApplyResult,
    SchemaArtifact,
    SchemaBatch,
    SchemaPlan,
    SchemaSpec,
    SchemaUploadResult,
)
from ..domain.policies import SchemaPolicyEngine
from ..domain.repositories.interfaces import (
    IObjectStorageRepository,
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
    ISchemaRegistryRepository,
)
from ..domain.services import SchemaPlannerService


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

    async def execute(self, batch: SchemaBatch, actor: str) -> SchemaPlan:
        await self.audit_repository.log_operation(
            change_id=batch.change_id,
            action="DRY_RUN",
            target="BATCH",
            actor=actor,
            status="STARTED",
            message=f"Schema dry-run started for {len(batch.specs)} subjects",
        )

        try:
            plan = await self.planner_service.create_plan(batch)
            await self.metadata_repository.save_plan(plan, actor)
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action="DRY_RUN",
                target="BATCH",
                actor=actor,
                status="COMPLETED",
                message="Schema dry-run completed",
                snapshot={"summary": plan.summary()},
            )
            return plan
        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action="DRY_RUN",
                target="BATCH",
                actor=actor,
                status="FAILED",
                message=f"Schema dry-run failed: {exc!s}",
            )
            raise


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

    async def execute(self, batch: SchemaBatch, actor: str) -> SchemaApplyResult:
        audit_id = str(uuid.uuid4())
        await self.audit_repository.log_operation(
            change_id=batch.change_id,
            action="APPLY",
            target="BATCH",
            actor=actor,
            status="STARTED",
            message=f"Schema apply started for {len(batch.specs)} subjects",
        )

        try:
            plan = await self.planner_service.create_plan(batch)
            if not plan.can_apply:
                raise ValueError("Policy violations or incompatibilities detected; apply aborted")

            registered: list[str] = []
            skipped: list[str] = []
            failed: list[dict[str, str]] = []
            artifacts: list[SchemaArtifact] = []

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
                except Exception as exc:  # pragma: no cover - 실제 구현에서 세부 처리
                    failed.append({"subject": spec.subject, "error": str(exc)})

            result = SchemaApplyResult(
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
                action="APPLY",
                target="BATCH",
                actor=actor,
                status="COMPLETED",
                message="Schema apply completed",
                snapshot={"summary": result.summary()},
            )

            return result
        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=batch.change_id,
                action="APPLY",
                target="BATCH",
                actor=actor,
                status="FAILED",
                message=f"Schema apply failed: {exc!s}",
            )
            raise

    async def _persist_artifact(
        self,
        spec: SchemaSpec,
        version: int,
        change_id: ChangeId,
    ) -> SchemaArtifact | None:
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

        artifact = SchemaArtifact(
            subject=spec.subject,
            version=version,
            storage_url=storage_url,
            checksum=spec.schema_hash or spec.fingerprint(),
        )
        await self.metadata_repository.record_artifact(artifact, change_id)
        return artifact

    async def _validate_files(self, files: list[Any]) -> list[dict[str, Any]]:
        """파일 검증 및 메타데이터 추출"""
        if not files:
            raise ValueError("No files provided")
        
        # 지원되는 파일 확장자
        supported_extensions = {".avsc", ".json", ".proto", ".zip"}
        max_file_size = 10 * 1024 * 1024  # 10MB
        
        validated_files = []
        
        for file in files:
            # 파일 이름 및 확장자 검증
            filename = getattr(file, 'filename', 'unknown')
            if not filename:
                raise ValueError("File must have a filename")
            
            file_path = Path(filename)
            extension = file_path.suffix.lower()
            
            if extension not in supported_extensions:
                raise ValueError(
                    f"Unsupported file type: {extension}. "
                    f"Supported: {', '.join(supported_extensions)}"
                )
            
            # 파일 내용 읽기
            content = await file.read()
            if len(content) > max_file_size:
                raise ValueError(
                    f"File {filename} is too large: {len(content)} bytes "
                    f"(max: {max_file_size} bytes)"
                )
            
            if len(content) == 0:
                raise ValueError(f"File {filename} is empty")
            
            # 파일 정보 저장
            validated_files.append({
                "filename": filename,
                "extension": extension,
                "content": content,
                "size": len(content),
                "content_type": getattr(file, 'content_type', 'application/octet-stream'),
            })
        
        return validated_files
    
    async def _process_and_upload_file(
        self,
        file_info: dict[str, Any],
        env: Environment,
        change_id: ChangeId,
        upload_id: str,
    ) -> SchemaArtifact | None:
        """개별 파일 처리 및 업로드"""
        if self.storage_repository is None:
            return None
        
        extension = file_info["extension"]
        
        # ZIP 파일 처리
        if extension == ".zip":
            return await self._process_zip_file(file_info, env, change_id, upload_id)
        
        # 일반 스키마 파일 처리
        return await self._process_schema_file(file_info, env, change_id, upload_id)
    
    async def _process_zip_file(
        self,
        file_info: dict[str, Any],
        env: Environment,
        change_id: ChangeId,
        upload_id: str,
    ) -> SchemaArtifact | None:
        """압축 파일 처리"""
        content = file_info["content"]
        filename = file_info["filename"]
        
        try:
            with zipfile.ZipFile(BytesIO(content), 'r') as zip_file:
                # ZIP 내용 검증
                file_list = zip_file.namelist()
                if not file_list:
                    raise ValueError(f"ZIP file {filename} is empty")
                
                # 지원되는 파일만 필터링
                schema_files = [
                    f for f in file_list 
                    if Path(f).suffix.lower() in {".avsc", ".json", ".proto"}
                ]
                
                if not schema_files:
                    raise ValueError(f"No schema files found in ZIP: {filename}")
                
                # ZIP 전체를 Object Storage에 업로드
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
                
                # 아티팩트 생성
                artifact = SchemaArtifact(
                    subject=f"bundle.{Path(filename).stem}",
                    version=1,  # 업로드 버전
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
        env: Environment,
        change_id: ChangeId,
        upload_id: str,
    ) -> SchemaArtifact | None:
        """스키마 파일 처리"""
        if self.storage_repository is None:
            return None
            
        filename = file_info["filename"]
        content = file_info["content"]
        extension = file_info["extension"]
        
        # 스키마 타입 추론
        schema_type = self._infer_schema_type(extension)
        
        # 스키마 내용 기본 검증
        try:
            content_str = content.decode('utf-8')
            if extension in {".avsc", ".json"}:
                import json
                json.loads(content_str)  # JSON 파싱 검증
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid schema file {filename}: {e}") from e
        
        # Object Storage에 업로드
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
        
        # Subject 이름 추론 (파일명 기반)
        subject_name = f"{env.value}.{Path(filename).stem}"
        
        # 아티팩트 생성
        artifact = SchemaArtifact(
            subject=subject_name,
            version=1,  # 업로드 버전
            storage_url=storage_url,
            checksum=self._calculate_checksum(content),
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
        import hashlib
        return hashlib.sha256(content).hexdigest()[:16]


class SchemaPlanUseCase:
    """스키마 배치 계획 조회 유스케이스"""

    def __init__(
        self,
        metadata_repository: ISchemaMetadataRepository,
    ) -> None:
        self.metadata_repository = metadata_repository

    async def execute(self, change_id: ChangeId) -> SchemaPlan | None:
        return await self.metadata_repository.get_plan(change_id)


class SchemaUploadUseCase:
    """스키마 업로드 유스케이스"""

    def __init__(
        self,
        storage_repository: IObjectStorageRepository,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
    ) -> None:
        self.storage_repository = storage_repository
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository

    async def execute(
        self,
        *,
        env: Environment,
        change_id: ChangeId,
        files: list[Any],  # FastAPI UploadFile 객체들
        actor: str,
    ) -> SchemaUploadResult:
        """스키마 파일 업로드 처리"""
        upload_id = f"upload_{change_id}_{uuid.uuid4().hex[:8]}"
        
        await self.audit_repository.log_operation(
            change_id=change_id,
            action="UPLOAD",
            target="FILES",
            actor=actor,
            status="STARTED",
            message=f"Schema upload started: {len(files)} files",
        )
        
        try:
            # 1. 파일 검증
            validated_files = await self._validate_files(files)
            
            # 2. 파일 처리 및 업로드
            artifacts: list[SchemaArtifact] = []
            
            for file_info in validated_files:
                artifact = await self._process_and_upload_file(
                    file_info, env, change_id, upload_id
                )
                if artifact:
                    artifacts.append(artifact)
            
            # 3. 결과 생성
            result = SchemaUploadResult(
                upload_id=upload_id,
                artifacts=tuple(artifacts),
            )
            
            # 4. 메타데이터 저장
            await self.metadata_repository.save_upload_result(result, actor)
            
            # 5. 감사 로그 완료
            await self.audit_repository.log_operation(
                change_id=change_id,
                action="UPLOAD",
                target="FILES",
                actor=actor,
                status="COMPLETED",
                message=f"Schema upload completed: {len(artifacts)} artifacts",
                snapshot={"summary": result.summary()},
            )
            
            return result
            
        except Exception as exc:
            await self.audit_repository.log_operation(
                change_id=change_id,
                action="UPLOAD",
                target="FILES",
                actor=actor,
                status="FAILED",
                message=f"Schema upload failed: {exc!s}",
            )
            raise
