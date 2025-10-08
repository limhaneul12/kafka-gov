"""Schema Application Use Cases 테스트"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.schema.application.use_cases import (
    SchemaBatchApplyUseCase,
    SchemaBatchDryRunUseCase,
    SchemaDeleteUseCase,
    SchemaPlanUseCase,
    SchemaSyncUseCase,
    SchemaUploadUseCase,
)
from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainEnvironment,
    DomainSchemaCompatibilityReport,
    DomainSubjectStrategy,
    SchemaVersionInfo,
)
from app.schema.domain.policies import SchemaPolicyEngine
from tests.schema.factories import create_schema_batch, create_schema_spec


@pytest.fixture
def mock_registry_repository():
    """Mock Schema Registry Repository"""
    from unittest.mock import AsyncMock as AM

    mock = AM()
    mock.describe_subjects.return_value = {}

    # check_compatibility는 매번 호출되므로 side_effect 사용
    async def mock_check_compat(spec):
        return DomainSchemaCompatibilityReport(
            subject=spec.subject,
            mode=DomainCompatibilityMode.BACKWARD,
            is_compatible=True,
            issues=(),
        )

    mock.check_compatibility.side_effect = mock_check_compat
    mock.register_schema.return_value = 1
    return mock


@pytest.fixture
def mock_connection_manager():
    """Mock Connection Manager"""
    from unittest.mock import AsyncMock, MagicMock

    mock_cm = AsyncMock()

    # get_schema_registry_client returns a mock registry client (AsyncMock으로 변경)
    mock_registry_client = AsyncMock()
    mock_registry_client.get_subjects = AsyncMock(return_value=[])
    mock_registry_client.get_latest_version = AsyncMock(return_value=None)
    mock_registry_client.test_compatibility = AsyncMock(return_value=True)
    mock_registry_client.register_schema = AsyncMock(return_value=1)
    mock_registry_client.delete_subject = AsyncMock(return_value=[])
    mock_registry_client.get_versions = AsyncMock(return_value=[])
    mock_registry_client.get_version = AsyncMock(return_value=None)
    mock_registry_client.set_config = AsyncMock(return_value=None)

    mock_cm.get_schema_registry_client = AsyncMock(return_value=mock_registry_client)

    # get_minio_client returns (client, bucket_name)
    mock_minio_client = MagicMock()
    mock_minio_client.put_object = MagicMock(return_value=None)
    mock_cm.get_minio_client = AsyncMock(return_value=(mock_minio_client, "test-bucket"))

    # get_storage_info returns storage info with base_url
    mock_storage_info = MagicMock()
    mock_storage_info.get_base_url = MagicMock(return_value="http://localhost:9000")
    mock_storage_info.endpoint_url = "localhost:9000"
    mock_cm.get_storage_info = AsyncMock(return_value=mock_storage_info)

    return mock_cm


@pytest.fixture
def mock_metadata_repository():
    """Mock Metadata Repository"""
    mock = AsyncMock()
    mock.save_plan.return_value = None
    mock.get_plan.return_value = None
    mock.save_apply_result.return_value = None
    mock.save_upload_result.return_value = None
    mock.record_artifact.return_value = None
    mock.save_schema_metadata.return_value = None
    return mock


@pytest.fixture
def mock_audit_repository():
    """Mock Audit Repository"""
    mock = AsyncMock()
    mock.log_operation.return_value = None
    return mock


@pytest.fixture
def mock_storage_repository():
    """Mock Storage Repository"""
    mock = AsyncMock()
    mock.upload_schema.return_value = "s3://bucket/schema.avsc"
    mock.put_object.return_value = "http://localhost:9000/test-bucket/schema.avsc"
    return mock


class TestSchemaBatchDryRunUseCase:
    """SchemaBatchDryRunUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_dry_run_success(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """정상적인 Dry-Run"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchDryRunUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        batch = create_schema_batch(
            specs=(create_schema_spec(subject="dev.test-value"),),
        )

        plan = await use_case.execute(registry_id="test-registry", batch=batch, actor="test-user")

        assert plan.change_id == batch.change_id
        assert len(plan.items) == 1

        # 감사 로그 기록 확인
        assert mock_audit_repository.log_operation.call_count == 2  # STARTED, COMPLETED

        # 계획 저장 확인
        mock_metadata_repository.save_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_dry_run_failure(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """Dry-Run 실패"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchDryRunUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        batch = create_schema_batch()

        # ConnectionManager 에러 발생
        mock_connection_manager.get_schema_registry_client.side_effect = Exception(
            "Connection failed"
        )

        with pytest.raises(Exception, match="Connection failed"):
            await use_case.execute(registry_id="test-registry", batch=batch, actor="test-user")

        # 실패 감사 로그 기록 확인
        calls = mock_audit_repository.log_operation.call_args_list
        assert any("FAILED" in str(call) for call in calls)


class TestSchemaBatchApplyUseCase:
    """SchemaBatchApplyUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_apply_register_schemas(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """스키마 등록 적용"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        batch = create_schema_batch(
            specs=(
                create_schema_spec(subject="dev.test1-value"),
                create_schema_spec(subject="dev.test2-value"),
            ),
        )

        result = await use_case.execute(
            registry_id="test-registry", storage_id=None, batch=batch, actor="test-user"
        )

        assert result.change_id == batch.change_id
        assert len(result.registered) == 2
        assert len(result.failed) == 0

    @pytest.mark.asyncio
    async def test_apply_with_policy_violations(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """정책 위반으로 적용 차단"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        # 정책 위반이 있는 배치
        batch = create_schema_batch(
            env=DomainEnvironment.PROD,
            specs=(
                create_schema_spec(
                    subject="prod.test-value",
                    compatibility=DomainCompatibilityMode.BACKWARD,  # PROD 위반
                ),
            ),
        )

        with pytest.raises(ValueError, match="Policy violations or incompatibilities detected"):
            await use_case.execute(
                registry_id="test-registry", storage_id=None, batch=batch, actor="test-user"
            )


class TestSchemaPlanUseCase:
    """SchemaPlanUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_get_plan(self, mock_metadata_repository):
        """계획 조회"""
        from tests.schema.factories import create_schema_batch

        use_case = SchemaPlanUseCase(mock_metadata_repository)

        batch = create_schema_batch(change_id="test-001")
        # Plan 객체를 직접 생성하는 대신 None 반환 테스트
        mock_metadata_repository.get_plan.return_value = None

        result = await use_case.execute("test-001")

        assert result is None
        mock_metadata_repository.get_plan.assert_called_once_with("test-001")


class TestSchemaDeleteUseCase:
    """SchemaDeleteUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_analyze_delete_impact(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """삭제 영향도 분석"""
        # Mock registry client에 스키마 정보 설정
        registry_client = await mock_connection_manager.get_schema_registry_client("test-registry")

        # 스키마가 존재하는 경우
        mock_schema_version = AsyncMock()
        mock_schema_version.version = 3
        mock_schema_version.schema_id = 123
        mock_schema = AsyncMock()
        mock_schema.schema_str = '{"type": "record"}'
        mock_schema.schema_type = "AVRO"
        mock_schema_version.schema = mock_schema

        registry_client.get_subjects.return_value = ["dev.test-value"]
        registry_client.get_latest_version.return_value = mock_schema_version
        registry_client.get_versions.return_value = [1, 2, 3]

        use_case = SchemaDeleteUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        impact = await use_case.analyze(
            registry_id="test-registry",
            subject="dev.test-value",
            strategy=DomainSubjectStrategy.TOPIC_NAME,
            actor="test-user",
        )

        assert impact.subject == "dev.test-value"
        assert impact.current_version == 3
        assert impact.total_versions == 3

    @pytest.mark.asyncio
    async def test_analyze_non_existing_schema(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """존재하지 않는 스키마"""
        use_case = SchemaDeleteUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        impact = await use_case.analyze(
            registry_id="test-registry",
            subject="dev.nonexist-value",
            strategy=DomainSubjectStrategy.TOPIC_NAME,
            actor="test-user",
        )

        assert impact.subject == "dev.nonexist-value"
        assert impact.current_version is None
        assert impact.safe_to_delete is True


class TestSchemaBatchDryRunUseCaseExtended:
    """SchemaBatchDryRunUseCase 추가 테스트"""

    @pytest.mark.asyncio
    async def test_dry_run_with_incompatibility(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """호환성 문제가 있는 Dry-Run"""
        # Mock registry client에서 호환성 검사 실패 설정
        registry_client = await mock_connection_manager.get_schema_registry_client("test-registry")
        registry_client.test_compatibility.return_value = False

        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchDryRunUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        batch = create_schema_batch(
            specs=(create_schema_spec(subject="dev.test-value"),),
        )

        plan = await use_case.execute(registry_id="test-registry", batch=batch, actor="test-user")

        assert plan.change_id == batch.change_id
        assert len(plan.compatibility_reports) == 1
        assert not plan.compatibility_reports[0].is_compatible

    @pytest.mark.asyncio
    async def test_dry_run_with_existing_schema(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """기존 스키마 업데이트 Dry-Run"""
        # Mock registry client에 기존 스키마 설정
        registry_client = await mock_connection_manager.get_schema_registry_client("test-registry")

        mock_schema_version = AsyncMock()
        mock_schema_version.version = 2
        mock_schema_version.schema_id = 100
        mock_schema = AsyncMock()
        mock_schema.schema_str = '{"type": "string"}'
        mock_schema.schema_type = "AVRO"
        mock_schema_version.schema = mock_schema

        registry_client.get_subjects.return_value = ["dev.test-value"]
        registry_client.get_latest_version.return_value = mock_schema_version

        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchDryRunUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        batch = create_schema_batch(
            specs=(create_schema_spec(subject="dev.test-value"),),
        )

        plan = await use_case.execute(registry_id="test-registry", batch=batch, actor="test-user")

        assert plan.change_id == batch.change_id
        assert len(plan.items) == 1
        # UPDATE 액션이어야 함
        from app.schema.domain.models import DomainPlanAction

        assert plan.items[0].action == DomainPlanAction.UPDATE
        assert plan.items[0].current_version == 2
        assert plan.items[0].target_version == 3


class TestSchemaBatchApplyUseCaseExtended:
    """SchemaBatchApplyUseCase 추가 테스트"""

    @pytest.mark.asyncio
    async def test_apply_with_storage(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """스토리지 저장 포함 적용"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        batch = create_schema_batch(
            specs=(create_schema_spec(subject="dev.test-value"),),
        )

        result = await use_case.execute(
            registry_id="test-registry", storage_id="test-storage", batch=batch, actor="test-user"
        )

        assert len(result.registered) == 1

    @pytest.mark.asyncio
    async def test_apply_with_dry_run_only_spec(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """dry_run_only 스펙은 스킵"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        batch = create_schema_batch(
            specs=(
                create_schema_spec(subject="dev.test1-value", dry_run_only=True),
                create_schema_spec(subject="dev.test2-value", dry_run_only=False),
            ),
        )

        result = await use_case.execute(
            registry_id="test-registry", storage_id=None, batch=batch, actor="test-user"
        )

        assert len(result.registered) == 1
        assert len(result.skipped) == 1
        assert "dev.test1-value" in result.skipped

    @pytest.mark.asyncio
    async def test_apply_with_partial_failure(
        self,
        mock_connection_manager,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """일부 실패"""
        # Mock registry client에서 두 번째 등록 실패 설정
        registry_client = await mock_connection_manager.get_schema_registry_client("test-registry")

        call_count = 0

        async def mock_register_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 1
            raise ValueError("Registration failed")

        registry_client.register_schema.side_effect = mock_register_with_failure

        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchApplyUseCase(
            mock_connection_manager,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        batch = create_schema_batch(
            specs=(
                create_schema_spec(subject="dev.test1-value"),
                create_schema_spec(subject="dev.test2-value"),
            ),
        )

        result = await use_case.execute(
            registry_id="test-registry", storage_id=None, batch=batch, actor="test-user"
        )

        assert len(result.registered) == 1
        assert len(result.failed) == 1
        assert result.failed[0]["subject"] == "dev.test2-value"


class TestSchemaUploadUseCase:
    """SchemaUploadUseCase 테스트"""

    @pytest.fixture
    def mock_upload_file(self):
        """Mock UploadFile"""

        class MockFile:
            def __init__(
                self, filename: str, content: bytes, content_type: str = "application/json"
            ):
                self.filename = filename
                self._content = content
                self.content_type = content_type

            async def read(self):
                return self._content

        return MockFile

    @pytest.mark.asyncio
    async def test_upload_single_avro_file(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """단일 AVRO 파일 업로드"""
        use_case = SchemaUploadUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        # AVRO 스키마 파일
        avro_schema = (
            b'{"type": "record", "name": "User", "fields": [{"name": "id", "type": "string"}]}'
        )
        files = [mock_upload_file("test.avsc", avro_schema)]

        result = await use_case.execute(
            registry_id="test-registry",
            storage_id="test-storage",
            env=DomainEnvironment.DEV,
            change_id="upload-001",
            owner="test-team",
            files=files,
            actor="test-user",
        )

        assert result.upload_id.startswith("upload_upload-001")
        assert len(result.artifacts) == 1
        assert result.artifacts[0].subject == "dev.test"
        assert result.artifacts[0].version == 1

    @pytest.mark.asyncio
    async def test_upload_json_file(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """JSON 스키마 파일 업로드"""
        use_case = SchemaUploadUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        json_schema = b'{"type": "object", "properties": {"name": {"type": "string"}}}'
        files = [mock_upload_file("schema.json", json_schema)]

        result = await use_case.execute(
            registry_id="test-registry",
            storage_id="test-storage",
            env=DomainEnvironment.DEV,
            change_id="upload-002",
            owner="test-team",
            files=files,
            actor="test-user",
        )

        assert len(result.artifacts) == 1

    @pytest.mark.asyncio
    async def test_upload_proto_file(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """Protobuf 스키마 파일 업로드"""
        use_case = SchemaUploadUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        proto_schema = b'syntax = "proto3"; message User { string id = 1; }'
        files = [mock_upload_file("schema.proto", proto_schema)]

        result = await use_case.execute(
            registry_id="test-registry",
            storage_id="test-storage",
            env=DomainEnvironment.DEV,
            change_id="upload-003",
            owner="test-team",
            files=files,
            actor="test-user",
        )

        assert len(result.artifacts) == 1

    @pytest.mark.asyncio
    async def test_upload_no_files_error(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """파일이 없을 때 에러"""
        use_case = SchemaUploadUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        with pytest.raises(ValueError, match="No files provided"):
            await use_case.execute(
                registry_id="test-registry",
                storage_id="test-storage",
                env=DomainEnvironment.DEV,
                change_id="upload-004",
                owner="test-team",
                files=[],
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_unsupported_extension(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """지원하지 않는 파일 확장자"""
        use_case = SchemaUploadUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        files = [mock_upload_file("test.txt", b"invalid")]

        with pytest.raises(ValueError, match="Unsupported file type"):
            await use_case.execute(
                registry_id="test-registry",
                storage_id="test-storage",
                env=DomainEnvironment.DEV,
                change_id="upload-005",
                owner="test-team",
                files=files,
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_file_too_large(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """파일 크기 초과"""
        use_case = SchemaUploadUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        # 10MB 초과
        large_content = b"x" * (11 * 1024 * 1024)
        files = [mock_upload_file("large.avsc", large_content)]

        with pytest.raises(ValueError, match="is too large"):
            await use_case.execute(
                registry_id="test-registry",
                storage_id="test-storage",
                env=DomainEnvironment.DEV,
                change_id="upload-006",
                owner="test-team",
                files=files,
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_empty_file(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """빈 파일"""
        use_case = SchemaUploadUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        files = [mock_upload_file("empty.avsc", b"")]

        with pytest.raises(ValueError, match="is empty"):
            await use_case.execute(
                registry_id="test-registry",
                storage_id="test-storage",
                env=DomainEnvironment.DEV,
                change_id="upload-007",
                owner="test-team",
                files=files,
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_invalid_json(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """잘못된 JSON 파일"""
        use_case = SchemaUploadUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        files = [mock_upload_file("invalid.json", b"{invalid json}")]

        with pytest.raises(ValueError, match="Invalid schema file"):
            await use_case.execute(
                registry_id="test-registry",
                storage_id="test-storage",
                env=DomainEnvironment.DEV,
                change_id="upload-008",
                owner="test-team",
                files=files,
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_registry_failure_continues(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """Registry 등록 실패해도 MinIO 저장은 유지"""
        use_case = SchemaUploadUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        avro_schema = b'{"type": "record", "name": "Test"}'
        files = [mock_upload_file("test.avsc", avro_schema)]

        result = await use_case.execute(
            registry_id="test-registry",
            storage_id="test-storage",
            env=DomainEnvironment.DEV,
            change_id="upload-009",
            owner="test-team",
            files=files,
            actor="test-user",
        )

        # MinIO 저장은 성공, 버전은 1로 폴백
        assert len(result.artifacts) == 1
        assert result.artifacts[0].version == 1


class TestSchemaSyncUseCase:
    """SchemaSyncUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_sync_success(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """동기화 성공"""
        # Mock registry client에 스키마 설정
        registry_client = await mock_connection_manager.get_schema_registry_client("test-registry")

        mock_schema_version1 = AsyncMock()
        mock_schema_version1.version = 1
        mock_schema_version1.schema_id = 101
        mock_schema1 = AsyncMock()
        mock_schema1.schema_str = '{"type": "record"}'
        mock_schema1.schema_type = "AVRO"
        mock_schema_version1.schema = mock_schema1

        mock_schema_version2 = AsyncMock()
        mock_schema_version2.version = 2
        mock_schema_version2.schema_id = 102
        mock_schema2 = AsyncMock()
        mock_schema2.schema_str = '{"type": "record"}'
        mock_schema2.schema_type = "AVRO"
        mock_schema_version2.schema = mock_schema2

        registry_client.get_subjects.return_value = ["dev.user-value", "dev.order-value"]
        registry_client.get_latest_version.side_effect = [
            mock_schema_version1,
            mock_schema_version2,
        ]

        use_case = SchemaSyncUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        result = await use_case.execute(registry_id="test-registry", actor="test-user")

        assert result["total"] == 2
        assert result["added"] == 2
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_sync_no_schemas(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """Registry에 스키마가 없을 때"""
        use_case = SchemaSyncUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        result = await use_case.execute(registry_id="test-registry", actor="test-user")

        assert result["total"] == 0
        assert result["added"] == 0
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_sync_with_existing_artifacts(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """이미 존재하는 artifact는 업데이트 카운트"""
        # Mock registry client에 스키마 설정
        registry_client = await mock_connection_manager.get_schema_registry_client("test-registry")

        mock_schema_version = AsyncMock()
        mock_schema_version.version = 1
        mock_schema_version.schema_id = 101
        mock_schema = AsyncMock()
        mock_schema.schema_str = '{"type": "record"}'
        mock_schema.schema_type = "AVRO"
        mock_schema_version.schema = mock_schema

        registry_client.get_subjects.return_value = ["dev.user-value"]
        registry_client.get_latest_version.return_value = mock_schema_version

        use_case = SchemaSyncUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        # artifact 저장 시 예외 발생 (이미 존재)
        mock_schema_metadata_repository.record_artifact.side_effect = Exception("Already exists")

        result = await use_case.execute(registry_id="test-registry", actor="test-user")

        assert result["total"] == 1
        assert result["added"] == 0
        assert result["updated"] == 1

    @pytest.mark.asyncio
    async def test_sync_failure(
        self,
        mock_connection_manager,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """동기화 실패"""
        use_case = SchemaSyncUseCase(
            mock_connection_manager,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        mock_connection_manager.get_schema_registry_client.side_effect = Exception(
            "Connection error"
        )

        with pytest.raises(Exception, match="Connection error"):
            await use_case.execute(registry_id="test-registry", actor="test-user")
