"""Schema Catalog Incremental Sync Service

SR → DB 증분 동기화 (jobs.md 스펙 준수)
- AsyncSchemaRegistryClient만 사용 (바퀴 재발명 금지)
- 세마포어/타임아웃/백오프
- rule_set, metadata 누락 없이 수집
"""

import asyncio
import hashlib
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import orjson
from confluent_kafka.schema_registry import AsyncSchemaRegistryClient
from confluent_kafka.schema_registry.error import SchemaRegistryError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schema.infrastructure.catalog_models import SchemaSubjectModel, SchemaVersionModel
from app.schema.infrastructure.models import SchemaArtifactModel, SchemaMetadataModel

logger = logging.getLogger(__name__)


@dataclass
class SyncMetrics:
    """동기화 메트릭"""

    subjects_total: int = 0
    subjects_new: int = 0
    versions_total: int = 0
    versions_new: int = 0
    subjects_removed: int = 0
    versions_removed: int = 0
    artifacts_removed: int = 0
    metadata_removed: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    removed_subjects: set[str] = field(default_factory=set, repr=False)


class CatalogSyncService:
    """Schema Catalog 증분 동기화 서비스

    OSS Advisory Mode:
    - SR 권위를 존중, 있는 그대로 수집
    - 우리의 가치는 분석/관찰 추가
    - 차단 없음
    """

    def __init__(
        self,
        sr_client: AsyncSchemaRegistryClient,
        session: AsyncSession,
        *,
        max_concurrent: int = 15,
        timeout_seconds: float = 3.0,
        max_retries: int = 3,
    ) -> None:
        """
        Args:
            sr_client: AsyncSchemaRegistryClient 인스턴스
            session: Database session
            max_concurrent: 동시 SR 호출 제한 (세마포어)
            timeout_seconds: 개별 호출 타임아웃
            max_retries: 재시도 횟수
        """
        self.sr_client = sr_client
        self.session = session
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = timeout_seconds
        self.max_retries = max_retries

    async def sync_all(self) -> SyncMetrics:
        """전체 증분 동기화 실행

        Returns:
            SyncMetrics: 동기화 결과 메트릭
        """
        start_time = datetime.now()
        metrics = SyncMetrics()

        try:
            # 1. SR에서 모든 subject 목록 조회
            logger.info("[CatalogSync] Fetching subjects from SR...")
            subjects = await asyncio.wait_for(
                self.sr_client.get_subjects(),
                timeout=self.timeout * 2,  # list 호출은 여유
            )
            metrics.subjects_total = len(subjects)
            logger.info(f"[CatalogSync] Found {len(subjects)} subjects")

            # 1-1. 제거 대상 계산 (SR에 없어진 subject)
            existing_subjects: set[str] = set()

            subject_stmt = await self.session.execute(select(SchemaSubjectModel.subject))
            existing_subjects.update(row[0] for row in subject_stmt)

            artifact_stmt = await self.session.execute(select(SchemaArtifactModel.subject))
            existing_subjects.update(row[0] for row in artifact_stmt)

            metadata_stmt = await self.session.execute(select(SchemaMetadataModel.subject))
            existing_subjects.update(row[0] for row in metadata_stmt)

            stale_subjects = existing_subjects - set(subjects)

            if stale_subjects:
                logger.info("[CatalogSync] Removing %d stale subjects", len(stale_subjects))

                # 삭제될 버전 개수 계산
                version_count_stmt = await self.session.execute(
                    select(func.count())
                    .select_from(SchemaVersionModel)
                    .where(SchemaVersionModel.subject.in_(stale_subjects))
                )
                versions_removed = int(version_count_stmt.scalar() or 0)

                # 삭제될 아티팩트 개수 계산
                artifact_count_stmt = await self.session.execute(
                    select(func.count())
                    .select_from(SchemaArtifactModel)
                    .where(SchemaArtifactModel.subject.in_(stale_subjects))
                )
                artifacts_removed = int(artifact_count_stmt.scalar() or 0)

                await self.session.execute(
                    delete(SchemaVersionModel).where(SchemaVersionModel.subject.in_(stale_subjects))
                )
                await self.session.execute(
                    delete(SchemaArtifactModel).where(
                        SchemaArtifactModel.subject.in_(stale_subjects)
                    )
                )
                metadata_delete = await self.session.execute(
                    delete(SchemaMetadataModel).where(
                        SchemaMetadataModel.subject.in_(stale_subjects)
                    )
                )
                await self.session.execute(
                    delete(SchemaSubjectModel).where(SchemaSubjectModel.subject.in_(stale_subjects))
                )
                await self.session.commit()

                metrics.subjects_removed += len(stale_subjects)
                metrics.versions_removed += versions_removed
                metrics.artifacts_removed += artifacts_removed
                metrics.metadata_removed += metadata_delete.rowcount or 0
                metrics.removed_subjects.update(stale_subjects)

            # 2. 각 subject별 증분 동기화 (세마포어 제한)
            tasks = [self._sync_subject(subject, metrics) for subject in subjects]
            await asyncio.gather(*tasks, return_exceptions=True)

        except TimeoutError:
            logger.error("[CatalogSync] Timeout fetching subjects list")
            metrics.errors += 1
        except Exception as e:
            logger.error(f"[CatalogSync] Unexpected error: {e}", exc_info=True)
            metrics.errors += 1

        # 메트릭 계산
        metrics.duration_seconds = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"[CatalogSync] Complete: {metrics.subjects_new} new subjects, "
            f"{metrics.versions_new} new versions, "
            f"{metrics.errors} errors, "
            f"{metrics.duration_seconds:.2f}s"
        )

        return metrics

    async def _sync_subject(self, subject: str, metrics: SyncMetrics) -> None:
        """개별 subject 증분 동기화

        Args:
            subject: Subject 이름
            metrics: 메트릭 누적용
        """
        async with self.semaphore:
            try:
                # DB에서 현재 latest_version 조회
                stmt = await self.session.execute(
                    select(SchemaSubjectModel.latest_version).where(
                        SchemaSubjectModel.subject == subject
                    )
                )
                current_latest = stmt.scalar_one_or_none()

                # SR에서 최신 버전 조회
                latest_registered = await self._get_latest_version_with_retry(subject)
                if not latest_registered or latest_registered.version is None:
                    return

                # 증분 체크: 새 버전이 없으면 skip
                if current_latest and latest_registered.version <= current_latest:
                    logger.debug(f"[{subject}] No new versions")
                    return

                # 새 버전들 수집
                start_version = (current_latest or 0) + 1
                new_versions = range(start_version, latest_registered.version + 1)

                for version in new_versions:
                    await self._sync_version(subject, version)
                    metrics.versions_new += 1
                    metrics.versions_total += 1

                # Subject 메타 업데이트
                await self._update_subject_meta(subject, int(latest_registered.version))

                if not current_latest:
                    metrics.subjects_new += 1

            except Exception as e:
                logger.warning(f"[{subject}] Sync failed: {e}")
                metrics.errors += 1

    async def _get_latest_version_with_retry(self, subject: str):
        """재시도 로직이 포함된 최신 버전 조회"""
        for attempt in range(self.max_retries):
            try:
                return await asyncio.wait_for(
                    self.sr_client.get_latest_version(subject), timeout=self.timeout
                )
            except TimeoutError:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (2**attempt))  # 지수 백오프
                continue
            except SchemaRegistryError as e:
                logger.debug(f"[{subject}] SR error: {e}")
                return None
        return None

    async def _sync_version(self, subject: str, version: int) -> None:
        """특정 버전 동기화

        jobs.md 핵심: rule_set, sr_metadata 누락 없이 수집
        """
        try:
            # SR에서 버전 정보 가져오기 (RegisteredSchema)
            registered_schema = await asyncio.wait_for(
                self.sr_client.get_version(subject, version), timeout=self.timeout
            )

            if not registered_schema or not registered_schema.schema:
                return

            schema_str = registered_schema.schema.schema_str or ""

            # 정규화 & 해시 (중복 감지용)
            canonical_hash = self._canonicalize_and_hash(schema_str)

            # rule_set, metadata 추출 (있으면)
            rule_set = getattr(registered_schema, "rule_set", None)
            sr_metadata = getattr(registered_schema, "metadata", None)

            # references 추출
            references = []
            if hasattr(registered_schema, "references") and registered_schema.references:
                references = [
                    {"name": ref.name, "subject": ref.subject, "version": ref.version}
                    for ref in registered_schema.references
                ]

            # fields_meta 추출 (Avro만 지원)
            fields_meta = None
            if registered_schema.schema.schema_type == "AVRO":
                fields_meta = self._extract_fields_meta(schema_str)

            # DB 저장
            version_model = SchemaVersionModel(
                subject=subject,
                version=version,
                schema_type=registered_schema.schema.schema_type,
                schema_id=registered_schema.schema_id,
                schema_str=schema_str,
                schema_canonical_hash=canonical_hash,
                references=references if references else None,
                rule_set=rule_set.to_dict() if rule_set and hasattr(rule_set, "to_dict") else None,
                sr_metadata=sr_metadata.to_dict()
                if sr_metadata and hasattr(sr_metadata, "to_dict")
                else None,
                fields_meta=fields_meta,
                lint_report=None,  # lint는 별도 서비스에서
            )

            await self.session.merge(version_model)  # upsert
            await self.session.commit()

            logger.debug(f"[{subject}] v{version} synced (hash: {canonical_hash[:8]}...)")

        except Exception as e:
            logger.warning(f"[{subject}] v{version} sync failed: {e}")
            await self.session.rollback()

    async def _update_subject_meta(self, subject: str, latest_version: int) -> None:
        """Subject 메타데이터 업데이트"""
        try:
            # Compatibility level 조회
            compat_level = None
            try:
                config = await asyncio.wait_for(
                    self.sr_client.get_config(subject), timeout=self.timeout
                )
                if config is not None:
                    compat_level = getattr(config, "compatibility_level", None)
                    if compat_level is None and isinstance(config, dict):
                        compat_level = config.get("compatibilityLevel")
            except Exception:
                pass  # 없으면 null

            # Mode 조회 (READONLY 여부)
            mode_readonly = False
            try:
                get_mode: Callable[[str], Any] | None = getattr(self.sr_client, "get_mode", None)
                if callable(get_mode):
                    maybe_coro = get_mode(subject)
                    if asyncio.iscoroutine(maybe_coro):
                        mode = await asyncio.wait_for(maybe_coro, timeout=self.timeout)
                        mode_readonly = mode == "READONLY"
            except Exception:
                pass

            # Naming에서 env 추론 (간단 정규식)
            env = self._extract_env_from_subject(subject)

            # Subject 모델 업데이트
            subject_model = SchemaSubjectModel(
                subject=subject,
                latest_version=latest_version,
                compat_level=compat_level,
                mode_readonly=mode_readonly,
                env=env,
                owner_team=None,  # 추후 naming 전략으로 추출
                pii_score=0.0,
                risk_score=0.0,
            )

            await self.session.merge(subject_model)
            await self.session.commit()

        except Exception as e:
            logger.warning(f"[{subject}] Meta update failed: {e}")
            await self.session.rollback()

    def _canonicalize_and_hash(self, schema_str: str) -> str:
        """스키마 정규화 & SHA-256 해시

        중복/변형 감지를 위해 공백·주석 제거 후 해싱
        """
        try:
            # JSON 파싱 후 재직렬화 (공백 제거, 키 정렬)
            schema_dict = orjson.loads(schema_str)
            canonical = orjson.dumps(schema_dict, option=orjson.OPT_SORT_KEYS)
            return hashlib.sha256(canonical).hexdigest()
        except Exception:
            # 파싱 실패 시 원본 해시
            return hashlib.sha256(schema_str.encode()).hexdigest()

    def _extract_env_from_subject(self, subject: str) -> str | None:
        """Subject명에서 환경 추출

        예: dev.metrics.quality-value → dev
        """
        patterns = [
            r"^(dev|stg|prod)\.",  # dev., stg., prod.
            r"^(d|s|p)\.",  # d., s., p. (약어)
        ]

        for pattern in patterns:
            match = re.match(pattern, subject)
            if match:
                env_abbr = match.group(1)
                # 약어 확장
                env_map = {"d": "dev", "s": "stg", "p": "prod"}
                return env_map.get(env_abbr, env_abbr)

        return None

    def _extract_fields_meta(self, schema_str: str) -> dict[str, Any] | None:
        """Avro 스키마에서 필드 메타 추출

        PII 후보, 네이밍 패턴 등
        """
        try:
            schema_dict = orjson.loads(schema_str)
            fields = schema_dict.get("fields", [])

            fields_meta = []
            for field in fields:
                field_name = field.get("name", "")
                field_type = field.get("type", "")

                # PII 후보 감지 (간단 패턴)
                is_pii_candidate = any(
                    keyword in field_name.lower()
                    for keyword in ["email", "phone", "ssn", "passport", "address", "name"]
                )

                fields_meta.append(
                    {
                        "name": field_name,
                        "type": str(field_type),
                        "pii_candidate": is_pii_candidate,
                    }
                )

            return {"fields": fields_meta}

        except Exception:
            return None
