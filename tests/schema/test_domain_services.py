"""Schema Domain Services 테스트"""

from __future__ import annotations

import pytest

from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainSchemaCompatibilityReport,
    DomainSubjectStrategy,
    SchemaVersionInfo,
)
from app.schema.domain.policies import SchemaPolicyEngine
from app.schema.domain.services import (
    SchemaDeleteAnalyzer,
    SchemaImpactAnalyzer,
    SchemaPlannerService,
)
from tests.schema.factories import create_schema_batch, create_schema_spec


class TestSchemaImpactAnalyzer:
    """SchemaImpactAnalyzer 테스트"""

    @pytest.mark.asyncio
    async def test_analyze_impact_topic_name_strategy(self, mock_registry_repository):
        """TopicName 전략으로 영향도 분석"""
        analyzer = SchemaImpactAnalyzer(mock_registry_repository)

        impact = await analyzer.analyze_impact(
            subject="dev.user-value",
            strategy=DomainSubjectStrategy.TOPIC_NAME,
        )

        assert impact.subject == "dev.user-value"
        assert len(impact.topics) > 0  # 토픽 추출됨
        assert impact.consumers == ()  # 컨슈머 정보는 없음

    @pytest.mark.asyncio
    async def test_analyze_impact_record_name_strategy(self, mock_registry_repository):
        """RecordName 전략으로 영향도 분석"""
        analyzer = SchemaImpactAnalyzer(mock_registry_repository)

        impact = await analyzer.analyze_impact(
            subject="com.example.User",
            strategy=DomainSubjectStrategy.RECORD_NAME,
        )

        assert impact.subject == "com.example.User"
        assert impact.consumers == ()


class TestSchemaDeleteAnalyzer:
    """SchemaDeleteAnalyzer 테스트"""

    @pytest.mark.asyncio
    async def test_analyze_non_existing_schema(self, mock_registry_repository):
        """존재하지 않는 스키마 삭제 분석"""
        analyzer = SchemaDeleteAnalyzer(mock_registry_repository)

        # Repository: 스키마 없음
        mock_registry_repository.describe_subjects.return_value = {}

        impact = await analyzer.analyze_delete_impact(
            subject="dev.nonexist-value",
            strategy=DomainSubjectStrategy.TOPIC_NAME,
        )

        assert impact.subject == "dev.nonexist-value"
        assert impact.current_version is None
        assert impact.total_versions == 0
        assert impact.safe_to_delete is True
        assert len(impact.warnings) > 0

    @pytest.mark.asyncio
    async def test_analyze_existing_schema(self, mock_registry_repository):
        """기존 스키마 삭제 분석"""
        analyzer = SchemaDeleteAnalyzer(mock_registry_repository)

        # Repository: 스키마 존재
        mock_registry_repository.describe_subjects.return_value = {
            "dev.user-value": SchemaVersionInfo(
                version=5,
                schema_id=123,
                schema='{"type": "record"}',
                schema_type="AVRO",
                references=[],
                hash="abc123",
            )
        }

        impact = await analyzer.analyze_delete_impact(
            subject="dev.user-value",
            strategy=DomainSubjectStrategy.TOPIC_NAME,
        )

        assert impact.subject == "dev.user-value"
        assert impact.current_version == 5
        assert impact.total_versions == 5
        assert len(impact.affected_topics) > 0

    @pytest.mark.asyncio
    async def test_prod_schema_warning(self, mock_registry_repository):
        """프로덕션 스키마 삭제 경고"""
        analyzer = SchemaDeleteAnalyzer(mock_registry_repository)

        mock_registry_repository.describe_subjects.return_value = {
            "prod.user-value": SchemaVersionInfo(
                version=3,
                schema_id=456,
                schema='{"type": "record"}',
                schema_type="AVRO",
                references=[],
                hash="def456",
            )
        }

        impact = await analyzer.analyze_delete_impact(
            subject="prod.user-value",
            strategy=DomainSubjectStrategy.TOPIC_NAME,
        )

        # 프로덕션 경고 포함
        assert any("프로덕션" in w for w in impact.warnings)
        assert impact.safe_to_delete is False


class TestSchemaPlannerService:
    """SchemaPlannerService 테스트"""

    @pytest.mark.asyncio
    async def test_create_plan_for_new_schemas(self, mock_registry_repository):
        """새 스키마 등록 계획"""
        policy_engine = SchemaPolicyEngine()
        service = SchemaPlannerService(mock_registry_repository, policy_engine)

        batch = create_schema_batch(
            specs=(
                create_schema_spec(subject="dev.user-value"),
                create_schema_spec(subject="dev.order-value"),
            ),
        )

        # Repository: 스키마 없음
        mock_registry_repository.describe_subjects.return_value = {}

        # 호환성 체크 성공
        mock_registry_repository.check_compatibility.return_value = DomainSchemaCompatibilityReport(
            subject="dev.user-value",
            mode=DomainCompatibilityMode.BACKWARD,
            is_compatible=True,
            issues=(),
        )

        plan = await service.create_plan(batch)

        assert plan.change_id == batch.change_id
        assert len(plan.items) == 2
        assert all(item.action.value == "REGISTER" for item in plan.items)
        assert len(plan.violations) == 0

    @pytest.mark.asyncio
    async def test_create_plan_for_update(self, mock_registry_repository):
        """기존 스키마 업데이트 계획"""
        policy_engine = SchemaPolicyEngine()
        service = SchemaPlannerService(mock_registry_repository, policy_engine)

        batch = create_schema_batch(
            specs=(create_schema_spec(subject="dev.user-value"),),
        )

        # Repository: 기존 스키마 존재
        mock_registry_repository.describe_subjects.return_value = {
            "dev.user-value": SchemaVersionInfo(
                version=2,
                schema_id=123,
                schema='{"type": "record", "name": "User"}',
                schema_type="AVRO",
                references=[],
                hash="abc123",
            )
        }

        mock_registry_repository.check_compatibility.return_value = DomainSchemaCompatibilityReport(
            subject="dev.user-value",
            mode=DomainCompatibilityMode.BACKWARD,
            is_compatible=True,
            issues=(),
        )

        plan = await service.create_plan(batch)

        assert len(plan.items) == 1
        assert plan.items[0].action.value == "UPDATE"
        assert plan.items[0].current_version == 2
        assert plan.items[0].target_version == 3

    @pytest.mark.asyncio
    async def test_plan_with_policy_violations(self, mock_registry_repository):
        """정책 위반이 있는 계획"""
        from app.schema.domain.models import DomainEnvironment

        policy_engine = SchemaPolicyEngine()
        service = SchemaPlannerService(mock_registry_repository, policy_engine)

        batch = create_schema_batch(
            env=DomainEnvironment.PROD,  # 환경을 PROD로 설정
            specs=(
                create_schema_spec(
                    subject="prod.user-value",
                    compatibility=DomainCompatibilityMode.BACKWARD,  # PROD 위반
                ),
            ),
        )

        mock_registry_repository.describe_subjects.return_value = {}
        mock_registry_repository.check_compatibility.return_value = DomainSchemaCompatibilityReport(
            subject="prod.user-value",
            mode=DomainCompatibilityMode.BACKWARD,
            is_compatible=True,
            issues=(),
        )

        plan = await service.create_plan(batch)

        assert len(plan.violations) > 0
        assert not plan.can_apply

    @pytest.mark.asyncio
    async def test_plan_with_incompatible_schema(self, mock_registry_repository):
        """호환되지 않는 스키마"""
        policy_engine = SchemaPolicyEngine()
        service = SchemaPlannerService(mock_registry_repository, policy_engine)

        batch = create_schema_batch(
            specs=(create_schema_spec(subject="dev.user-value"),),
        )

        mock_registry_repository.describe_subjects.return_value = {}

        # 호환성 체크 실패
        mock_registry_repository.check_compatibility.return_value = DomainSchemaCompatibilityReport(
            subject="dev.user-value",
            mode=DomainCompatibilityMode.BACKWARD,
            is_compatible=False,
            issues=(),
        )

        plan = await service.create_plan(batch)

        assert not plan.can_apply
        assert len(plan.compatibility_reports) > 0
        assert not plan.compatibility_reports[0].is_compatible
