"""스키마 업로드 유스케이스"""

from __future__ import annotations

import hashlib
import logging
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import orjson

from app.cluster.domain.services import IConnectionManager
from app.schema.infrastructure.schema_registry_adapter import ConfluentSchemaRegistryAdapter
from app.schema.infrastructure.storage.minio_adapter import MinIOObjectStorageAdapter
from app.shared.constants import AuditAction, AuditStatus, AuditTarget
from app.shared.domain.events import SchemaRegisteredEvent
from app.shared.infrastructure.event_bus import get_event_bus

from ...domain.models import (
    ChangeId,
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSchemaArtifact,
    DomainSchemaSource,
    DomainSchemaSourceType,
    DomainSchemaSpec,
    DomainSchemaType,
    DomainSchemaUploadResult,
    DomainSubjectStrategy,
)
from ...domain.repositories.interfaces import (
    ISchemaAuditRepository,
    ISchemaMetadataRepository,
)


@dataclass
class UploadContext:
    """업로드 작업의 공통 컨텍스트 정보"""

    registry_repository: ConfluentSchemaRegistryAdapter
    storage_repository: MinIOObjectStorageAdapter
    env: DomainEnvironment
    change_id: ChangeId
    upload_id: str
    owner: str
    actor: str
    compatibility_mode: DomainCompatibilityMode | None


class SchemaUploadUseCase:
    """스키마 업로드 유스케이스 (멀티 레지스트리/스토리지 지원)"""

    def __init__(
        self,
        connection_manager: IConnectionManager,
        metadata_repository: ISchemaMetadataRepository,
        audit_repository: ISchemaAuditRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.metadata_repository = metadata_repository
        self.audit_repository = audit_repository
        self.event_bus = get_event_bus()

    async def execute(
        self,
        *,
        registry_id: str,
        storage_id: str,
        env: DomainEnvironment,
        change_id: ChangeId,
        owner: str,
        files: list[Any],  # FastAPI UploadFile 객체들
        actor: str,
        compatibility_mode: DomainCompatibilityMode | None = None,
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
            # 1. ConnectionManager로 클라이언트 획득
            registry_client = await self.connection_manager.get_schema_registry_client(registry_id)
            registry_repository = ConfluentSchemaRegistryAdapter(registry_client)

            minio_client, bucket_name = await self.connection_manager.get_minio_client(storage_id)
            # ObjectStorage 정보에서 base_url 가져오기
            storage_info = await self.connection_manager.get_storage_info(storage_id)
            base_url = (
                storage_info.get_base_url()
                if hasattr(storage_info, "get_base_url")
                else f"http://{storage_info.endpoint_url}"
            )

            storage_repository = MinIOObjectStorageAdapter(
                client=minio_client,
                bucket_name=bucket_name,
                base_url=base_url,
            )

            # 2. 파일 검증
            validated_files = await self._validate_files(files)

            # 3. 업로드 컨텍스트 생성
            context = UploadContext(
                registry_repository=registry_repository,
                storage_repository=storage_repository,
                env=env,
                change_id=change_id,
                upload_id=upload_id,
                owner=owner,
                actor=actor,
                compatibility_mode=compatibility_mode,
            )

            # 4. 파일 처리 및 업로드 (MinIO + Schema Registry)
            artifact_results = [
                await self._process_and_upload_file(context, file_info)
                for file_info in validated_files
            ]
            artifacts: list[DomainSchemaArtifact] = [
                artifact for artifact in artifact_results if artifact is not None
            ]

            # 4. 결과 생성
            result = DomainSchemaUploadResult(upload_id=upload_id, artifacts=tuple(artifacts))

            # 5. 메타데이터 저장
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
        self, context: UploadContext, file_info: dict[str, Any]
    ) -> DomainSchemaArtifact | None:
        """개별 파일 처리 및 업로드"""
        extension = file_info["extension"]

        if extension == ".zip":
            return await self._process_zip_file(context, file_info)

        return await self._process_schema_file(context, file_info)

    async def _process_zip_file(
        self, context: UploadContext, file_info: dict[str, Any]
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

                key = f"{context.env.value}/uploads/{context.upload_id}/{filename}"
                metadata = {
                    "change_id": context.change_id,
                    "upload_id": context.upload_id,
                    "file_type": "zip_bundle",
                    "schema_count": str(len(schema_files)),
                }

                storage_url = await context.storage_repository.put_object(
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

                await self.metadata_repository.record_artifact(artifact, context.change_id)
                return artifact

        except zipfile.BadZipFile as e:
            raise ValueError(f"Invalid ZIP file: {filename}") from e

    async def _process_schema_file(
        self, context: UploadContext, file_info: dict[str, Any]
    ) -> DomainSchemaArtifact | None:
        """스키마 파일 처리 및 Schema Registry 자동 등록"""

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
        key = f"{context.env.value}/uploads/{context.upload_id}/{filename}"
        metadata = {
            "change_id": context.change_id,
            "upload_id": context.upload_id,
            "file_type": "schema",
            "schema_type": schema_type,
        }

        storage_url = await context.storage_repository.put_object(
            key=key,
            data=content,
            metadata=metadata,
        )

        subject_name = f"{context.env.value}.{Path(filename).stem}"

        # 2. Schema Registry 자동 등록
        try:
            # 호환성 모드 결정 (파라미터 우선, 없으면 기본값)
            if context.compatibility_mode is None:
                final_compatibility = DomainCompatibilityMode.BACKWARD
            elif isinstance(context.compatibility_mode, str):
                # 문자열로 들어온 경우 enum으로 변환
                final_compatibility = DomainCompatibilityMode(context.compatibility_mode)
            else:
                final_compatibility = context.compatibility_mode

            # DomainSchemaSpec 생성
            schema_spec = DomainSchemaSpec(
                subject=subject_name,
                schema_type=DomainSchemaType(schema_type),
                compatibility=final_compatibility,
                schema=content_str,
                source=DomainSchemaSource(
                    type=DomainSchemaSourceType.INLINE,
                    inline=content_str,
                ),
            )

            # Schema Registry에 등록
            version = await context.registry_repository.register_schema(schema_spec)

            # 호환성 모드 설정 (Subject 레벨)
            compatibility_str = (
                final_compatibility.value
                if isinstance(final_compatibility, DomainCompatibilityMode)
                else final_compatibility
            )
            await context.registry_repository.set_compatibility_mode(
                subject=subject_name, mode=compatibility_str
            )

            # 스키마 메타데이터 저장 (owner, compatibility_mode 포함)
            await self.metadata_repository.save_schema_metadata(
                subject=subject_name,
                metadata={
                    "owner": context.owner,
                    "created_by": context.actor,
                    "updated_by": context.actor,
                    "compatibility_mode": compatibility_str,
                },
            )

            # 등록 성공 시 이벤트 발행
            await self._publish_schema_registered_event(
                spec=schema_spec,
                version=version,
                change_id=context.change_id,
                env=context.env,
                actor=context.actor,
            )

            # Artifact 생성 (실제 등록된 버전 사용)
            artifact = DomainSchemaArtifact(
                subject=subject_name,
                version=version,
                storage_url=storage_url,
                checksum=self._calculate_checksum(content),
                schema_type=DomainSchemaType(schema_type),
                compatibility_mode=final_compatibility,
            )

        except Exception as e:
            # Schema Registry 등록 실패 시에도 MinIO 저장은 유지하고 경고 로그
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Schema Registry registration failed for {subject_name}: {e}. "
                f"File saved to MinIO but not registered."
            )

            # MinIO만 저장된 artifact 반환 (호환성 모드 포함)
            artifact = DomainSchemaArtifact(
                subject=subject_name,
                version=1,
                storage_url=storage_url,
                checksum=self._calculate_checksum(content),
                schema_type=DomainSchemaType(schema_type),
                compatibility_mode=final_compatibility,
            )

            # 메타데이터는 저장 (실패해도 호환성 모드 기록)
            try:
                compatibility_str_fallback = (
                    final_compatibility.value
                    if isinstance(final_compatibility, DomainCompatibilityMode)
                    else final_compatibility
                )
                await self.metadata_repository.save_schema_metadata(
                    subject=subject_name,
                    metadata={
                        "owner": context.owner,
                        "created_by": context.actor,
                        "updated_by": context.actor,
                        "compatibility_mode": compatibility_str_fallback,
                    },
                )
            except Exception as meta_error:
                logger.warning(f"Failed to save metadata for {subject_name}: {meta_error}")

        await self.metadata_repository.record_artifact(artifact, context.change_id)
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
        event = SchemaRegisteredEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            aggregate_id=change_id,
            occurred_at=datetime.now(),
            subject=spec.subject,
            version=version,
            schema_type=spec.schema_type.value,
            schema_id=0,  # Registry에서 조회 필요 시 추가
            compatibility_mode=spec.compatibility.value,
            subject_strategy=DomainSubjectStrategy.TOPIC_NAME.value,
            environment=env.value,
            actor=actor,
        )

        await self.event_bus.publish(event)
