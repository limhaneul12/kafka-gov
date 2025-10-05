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
def mock_metadata_repository():
    """Mock Metadata Repository"""
    mock = AsyncMock()
    mock.save_plan.return_value = None
    mock.get_plan.return_value = None
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
    return mock


class TestSchemaBatchDryRunUseCase:
    """SchemaBatchDryRunUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_dry_run_success(
        self,
        mock_registry_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """정상적인 Dry-Run"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchDryRunUseCase(
            mock_registry_repository,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        batch = create_schema_batch(
            specs=(create_schema_spec(subject="dev.test-value"),),
        )

        plan = await use_case.execute(batch, actor="test-user")

        assert plan.change_id == batch.change_id
        assert len(plan.items) == 1

        # 감사 로그 기록 확인
        assert mock_audit_repository.log_operation.call_count == 2  # STARTED, COMPLETED

        # 계획 저장 확인
        mock_metadata_repository.save_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_dry_run_failure(
        self,
        mock_registry_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """Dry-Run 실패"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchDryRunUseCase(
            mock_registry_repository,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        batch = create_schema_batch()

        # Repository 에러 발생
        mock_registry_repository.describe_subjects.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await use_case.execute(batch, actor="test-user")

        # 실패 감사 로그 기록 확인
        calls = mock_audit_repository.log_operation.call_args_list
        assert any("FAILED" in str(call) for call in calls)


class TestSchemaBatchApplyUseCase:
    """SchemaBatchApplyUseCase 테스트"""

    @pytest.mark.asyncio
    async def test_apply_register_schemas(
        self,
        mock_registry_repository,
        mock_metadata_repository,
        mock_audit_repository,
        mock_storage_repository,
    ):
        """스키마 등록 적용"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchApplyUseCase(
            mock_registry_repository,
            mock_metadata_repository,
            mock_audit_repository,
            mock_storage_repository,
            policy_engine,
        )

        batch = create_schema_batch(
            specs=(
                create_schema_spec(subject="dev.test1-value"),
                create_schema_spec(subject="dev.test2-value"),
            ),
        )

        # Repository: 새 스키마
        mock_registry_repository.describe_subjects.return_value = {}

        # 스키마 등록 성공
        mock_registry_repository.register_schema.return_value = 1

        result = await use_case.execute(batch, actor="test-user")

        assert result.change_id == batch.change_id
        assert len(result.registered) == 2
        assert len(result.failed) == 0

    @pytest.mark.asyncio
    async def test_apply_with_policy_violations(
        self,
        mock_registry_repository,
        mock_metadata_repository,
        mock_audit_repository,
        mock_storage_repository,
    ):
        """정책 위반으로 적용 차단"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchApplyUseCase(
            mock_registry_repository,
            mock_metadata_repository,
            mock_audit_repository,
            mock_storage_repository,
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

        mock_registry_repository.describe_subjects.return_value = {}

        with pytest.raises(ValueError, match="Policy violations or incompatibilities detected"):
            await use_case.execute(batch, actor="test-user")


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
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """삭제 영향도 분석"""
        use_case = SchemaDeleteUseCase(
            mock_registry_repository, mock_schema_metadata_repository, mock_schema_audit_repository
        )

        # Repository: 스키마 존재
        mock_registry_repository.describe_subjects.return_value = {
            "dev.test-value": SchemaVersionInfo(
                version=3,
                schema_id=123,
                schema='{"type": "record"}',
                schema_type="AVRO",
                references=[],
                hash="abc123",
            )
        }

        impact = await use_case.analyze(
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
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """존재하지 않는 스키마"""
        use_case = SchemaDeleteUseCase(
            mock_registry_repository, mock_schema_metadata_repository, mock_schema_audit_repository
        )

        # Repository: 스키마 없음
        mock_registry_repository.describe_subjects.return_value = {}

        impact = await use_case.analyze(
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
        mock_registry_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """호환성 문제가 있는 Dry-Run"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchDryRunUseCase(
            mock_registry_repository,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        # 호환성 검사 실패 설정
        async def mock_check_compat_fail(spec):
            return DomainSchemaCompatibilityReport(
                subject=spec.subject,
                mode=DomainCompatibilityMode.BACKWARD,
                is_compatible=False,
                issues=({"path": "/fields", "message": "Field removed"},),
            )

        mock_registry_repository.check_compatibility.side_effect = mock_check_compat_fail

        batch = create_schema_batch(
            specs=(create_schema_spec(subject="dev.test-value"),),
        )

        plan = await use_case.execute(batch, actor="test-user")

        assert plan.change_id == batch.change_id
        assert len(plan.compatibility_reports) == 1
        assert not plan.compatibility_reports[0].is_compatible

    @pytest.mark.asyncio
    async def test_dry_run_with_existing_schema(
        self,
        mock_registry_repository,
        mock_metadata_repository,
        mock_audit_repository,
    ):
        """기존 스키마 업데이트 Dry-Run"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchDryRunUseCase(
            mock_registry_repository,
            mock_metadata_repository,
            mock_audit_repository,
            policy_engine,
        )

        # 기존 스키마 존재
        mock_registry_repository.describe_subjects.return_value = {
            "dev.test-value": SchemaVersionInfo(
                version=2,
                schema_id=100,
                schema='{"type": "string"}',
                schema_type="AVRO",
                references=[],
                hash="old123",
            )
        }

        batch = create_schema_batch(
            specs=(create_schema_spec(subject="dev.test-value"),),
        )

        plan = await use_case.execute(batch, actor="test-user")

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
        mock_registry_repository,
        mock_metadata_repository,
        mock_audit_repository,
        mock_storage_repository,
    ):
        """스토리지 저장 포함 적용"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchApplyUseCase(
            mock_registry_repository,
            mock_metadata_repository,
            mock_audit_repository,
            mock_storage_repository,
            policy_engine,
        )

        mock_storage_repository.put_object.return_value = "s3://bucket/dev/test-value/1/schema.txt"

        batch = create_schema_batch(
            specs=(create_schema_spec(subject="dev.test-value"),),
        )

        result = await use_case.execute(batch, actor="test-user")

        assert len(result.registered) == 1
        # Storage에 업로드되었는지 확인
        mock_storage_repository.put_object.assert_called()

    @pytest.mark.asyncio
    async def test_apply_with_dry_run_only_spec(
        self,
        mock_registry_repository,
        mock_metadata_repository,
        mock_audit_repository,
        mock_storage_repository,
    ):
        """dry_run_only 스펙은 스킵"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchApplyUseCase(
            mock_registry_repository,
            mock_metadata_repository,
            mock_audit_repository,
            mock_storage_repository,
            policy_engine,
        )

        batch = create_schema_batch(
            specs=(
                create_schema_spec(subject="dev.test1-value", dry_run_only=True),
                create_schema_spec(subject="dev.test2-value", dry_run_only=False),
            ),
        )

        result = await use_case.execute(batch, actor="test-user")

        assert len(result.registered) == 1
        assert len(result.skipped) == 1
        assert "dev.test1-value" in result.skipped

    @pytest.mark.asyncio
    async def test_apply_with_partial_failure(
        self,
        mock_registry_repository,
        mock_metadata_repository,
        mock_audit_repository,
        mock_storage_repository,
    ):
        """일부 실패"""
        policy_engine = SchemaPolicyEngine()
        use_case = SchemaBatchApplyUseCase(
            mock_registry_repository,
            mock_metadata_repository,
            mock_audit_repository,
            mock_storage_repository,
            policy_engine,
        )

        # 첫 번째는 성공, 두 번째는 실패
        call_count = 0

        async def mock_register_with_failure(spec):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 1
            raise ValueError("Registration failed")

        mock_registry_repository.register_schema.side_effect = mock_register_with_failure

        batch = create_schema_batch(
            specs=(
                create_schema_spec(subject="dev.test1-value"),
                create_schema_spec(subject="dev.test2-value"),
            ),
        )

        result = await use_case.execute(batch, actor="test-user")

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
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """단일 AVRO 파일 업로드"""
        storage_repo = AsyncMock()
        storage_repo.put_object.return_value = "s3://bucket/dev/uploads/upload_123/test.avsc"

        use_case = SchemaUploadUseCase(
            storage_repo,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
            mock_registry_repository,
        )

        # AVRO 스키마 파일
        avro_schema = (
            b'{"type": "record", "name": "User", "fields": [{"name": "id", "type": "string"}]}'
        )
        files = [mock_upload_file("test.avsc", avro_schema)]

        # Registry 등록 성공
        mock_registry_repository.register_schema.return_value = 1
        mock_registry_repository.describe_subjects.return_value = {}

        result = await use_case.execute(
            env=DomainEnvironment.DEV,
            change_id="upload-001",
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
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """JSON 스키마 파일 업로드"""
        storage_repo = AsyncMock()
        storage_repo.put_object.return_value = "s3://bucket/dev/uploads/upload_123/schema.json"

        use_case = SchemaUploadUseCase(
            storage_repo,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
            mock_registry_repository,
        )

        json_schema = b'{"type": "object", "properties": {"name": {"type": "string"}}}'
        files = [mock_upload_file("schema.json", json_schema)]

        mock_registry_repository.register_schema.return_value = 2
        mock_registry_repository.describe_subjects.return_value = {}

        result = await use_case.execute(
            env=DomainEnvironment.DEV,
            change_id="upload-002",
            files=files,
            actor="test-user",
        )

        assert len(result.artifacts) == 1

    @pytest.mark.asyncio
    async def test_upload_proto_file(
        self,
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """Protobuf 스키마 파일 업로드"""
        storage_repo = AsyncMock()
        storage_repo.put_object.return_value = "s3://bucket/dev/uploads/upload_123/schema.proto"

        use_case = SchemaUploadUseCase(
            storage_repo,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
            mock_registry_repository,
        )

        proto_schema = b'syntax = "proto3"; message User { string id = 1; }'
        files = [mock_upload_file("schema.proto", proto_schema)]

        mock_registry_repository.register_schema.return_value = 1
        mock_registry_repository.describe_subjects.return_value = {}

        result = await use_case.execute(
            env=DomainEnvironment.DEV,
            change_id="upload-003",
            files=files,
            actor="test-user",
        )

        assert len(result.artifacts) == 1

    @pytest.mark.asyncio
    async def test_upload_no_files_error(
        self,
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """파일이 없을 때 에러"""
        storage_repo = AsyncMock()
        use_case = SchemaUploadUseCase(
            storage_repo,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
            mock_registry_repository,
        )

        with pytest.raises(ValueError, match="No files provided"):
            await use_case.execute(
                env=DomainEnvironment.DEV,
                change_id="upload-004",
                files=[],
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_unsupported_extension(
        self,
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """지원하지 않는 파일 확장자"""
        storage_repo = AsyncMock()
        use_case = SchemaUploadUseCase(
            storage_repo,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
            mock_registry_repository,
        )

        files = [mock_upload_file("test.txt", b"invalid")]

        with pytest.raises(ValueError, match="Unsupported file type"):
            await use_case.execute(
                env=DomainEnvironment.DEV,
                change_id="upload-005",
                files=files,
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_file_too_large(
        self,
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """파일 크기 초과"""
        storage_repo = AsyncMock()
        use_case = SchemaUploadUseCase(
            storage_repo,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
            mock_registry_repository,
        )

        # 10MB 초과
        large_content = b"x" * (11 * 1024 * 1024)
        files = [mock_upload_file("large.avsc", large_content)]

        with pytest.raises(ValueError, match="is too large"):
            await use_case.execute(
                env=DomainEnvironment.DEV,
                change_id="upload-006",
                files=files,
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_empty_file(
        self,
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """빈 파일"""
        storage_repo = AsyncMock()
        use_case = SchemaUploadUseCase(
            storage_repo,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
            mock_registry_repository,
        )

        files = [mock_upload_file("empty.avsc", b"")]

        with pytest.raises(ValueError, match="is empty"):
            await use_case.execute(
                env=DomainEnvironment.DEV,
                change_id="upload-007",
                files=files,
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_invalid_json(
        self,
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """잘못된 JSON 파일"""
        storage_repo = AsyncMock()
        use_case = SchemaUploadUseCase(
            storage_repo,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
            mock_registry_repository,
        )

        files = [mock_upload_file("invalid.json", b"{invalid json}")]

        with pytest.raises(ValueError, match="Invalid schema file"):
            await use_case.execute(
                env=DomainEnvironment.DEV,
                change_id="upload-008",
                files=files,
                actor="test-user",
            )

    @pytest.mark.asyncio
    async def test_upload_registry_failure_continues(
        self,
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
        mock_upload_file,
    ):
        """Registry 등록 실패해도 MinIO 저장은 유지"""
        storage_repo = AsyncMock()
        storage_repo.put_object.return_value = "s3://bucket/dev/uploads/upload_123/test.avsc"

        use_case = SchemaUploadUseCase(
            storage_repo,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
            mock_registry_repository,
        )

        avro_schema = b'{"type": "record", "name": "Test"}'
        files = [mock_upload_file("test.avsc", avro_schema)]

        # Registry 등록 실패
        mock_registry_repository.register_schema.side_effect = Exception("Registry error")
        mock_registry_repository.describe_subjects.return_value = {}

        result = await use_case.execute(
            env=DomainEnvironment.DEV,
            change_id="upload-009",
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
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """동기화 성공"""
        use_case = SchemaSyncUseCase(
            mock_registry_repository,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        # Registry에 스키마 존재
        mock_registry_repository.list_all_subjects.return_value = [
            "dev.user-value",
            "dev.order-value",
        ]
        mock_registry_repository.describe_subjects.return_value = {
            "dev.user-value": SchemaVersionInfo(
                version=1,
                schema_id=101,
                schema='{"type": "record"}',
                schema_type="AVRO",
                references=[],
                hash="hash1",
            ),
            "dev.order-value": SchemaVersionInfo(
                version=2,
                schema_id=102,
                schema='{"type": "record"}',
                schema_type="AVRO",
                references=[],
                hash="hash2",
            ),
        }

        result = await use_case.execute(actor="test-user")

        assert result["total"] == 2
        assert result["added"] == 2
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_sync_no_schemas(
        self,
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """Registry에 스키마가 없을 때"""
        use_case = SchemaSyncUseCase(
            mock_registry_repository,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        mock_registry_repository.list_all_subjects.return_value = []

        result = await use_case.execute(actor="test-user")

        assert result["total"] == 0
        assert result["added"] == 0
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_sync_with_existing_artifacts(
        self,
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """이미 존재하는 artifact는 업데이트 카운트"""
        use_case = SchemaSyncUseCase(
            mock_registry_repository,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        mock_registry_repository.list_all_subjects.return_value = ["dev.user-value"]
        mock_registry_repository.describe_subjects.return_value = {
            "dev.user-value": SchemaVersionInfo(
                version=1,
                schema_id=101,
                schema='{"type": "record"}',
                schema_type="AVRO",
                references=[],
                hash="hash1",
            ),
        }

        # artifact 저장 시 예외 발생 (이미 존재)
        mock_schema_metadata_repository.record_artifact.side_effect = Exception("Already exists")

        result = await use_case.execute(actor="test-user")

        assert result["total"] == 1
        assert result["added"] == 0
        assert result["updated"] == 1

    @pytest.mark.asyncio
    async def test_sync_failure(
        self,
        mock_registry_repository,
        mock_schema_metadata_repository,
        mock_schema_audit_repository,
    ):
        """동기화 실패"""
        use_case = SchemaSyncUseCase(
            mock_registry_repository,
            mock_schema_metadata_repository,
            mock_schema_audit_repository,
        )

        mock_registry_repository.list_all_subjects.side_effect = Exception("Connection error")

        with pytest.raises(Exception, match="Connection error"):
            await use_case.execute(actor="test-user")
