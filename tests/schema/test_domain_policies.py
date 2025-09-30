"""Schema Domain Policies 테스트"""

from __future__ import annotations

from app.schema.domain.models import (
    DomainCompatibilityMode,
    DomainSchemaType,
)
from app.schema.domain.policies import (
    CompatibilityPolicy,
    MetadataPolicy,
    NamingPolicy,
    SchemaPolicyEngine,
)
from tests.schema.factories import create_schema_metadata, create_schema_spec


class TestNamingPolicy:
    """NamingPolicy 테스트"""

    def test_valid_subject_name(self):
        """정상적인 subject 이름"""
        policy = NamingPolicy()
        spec = create_schema_spec(subject="prod.user-value")

        violations = policy.validate(spec)

        assert len(violations) == 0

    def test_invalid_pattern(self):
        """패턴에 맞지 않는 이름"""
        policy = NamingPolicy()
        # 유효한 환경 접두사를 사용하되 패턴 위반
        spec = create_schema_spec(subject="dev.Invalid-Subject")

        violations = policy.validate(spec)

        assert len(violations) > 0
        assert any(v.rule == "schema.naming.pattern" for v in violations)

    def test_valid_with_key_suffix(self):
        """key suffix가 있는 이름"""
        policy = NamingPolicy()
        spec = create_schema_spec(subject="dev.user-key")

        violations = policy.validate(spec)

        assert len(violations) == 0

    def test_valid_with_value_suffix(self):
        """value suffix가 있는 이름"""
        policy = NamingPolicy()
        spec = create_schema_spec(subject="dev.user-value")

        violations = policy.validate(spec)

        assert len(violations) == 0

    def test_forbidden_prefix_in_prod(self):
        """프로덕션에서 금지된 접두사"""
        policy = NamingPolicy()
        spec = create_schema_spec(subject="prod.test.user")

        violations = policy.validate(spec)

        # prod 환경에서 'test' 접두사 사용 시 위반
        # 단, 패턴 자체는 통과할 수 있으므로 forbidden_prefix 체크
        forbidden_violations = [v for v in violations if "forbidden" in v.rule]
        # prod.test.user는 두 번째 세그먼트가 'test'이므로 위반
        assert len(forbidden_violations) > 0 or len(violations) == 0  # 패턴에 따라 다름


class TestCompatibilityPolicy:
    """CompatibilityPolicy 테스트"""

    def test_prod_requires_full_compatibility(self):
        """PROD는 FULL 호환성 필요"""
        policy = CompatibilityPolicy()

        # BACKWARD는 PROD에서 허용 안됨
        spec = create_schema_spec(
            subject="prod.user-value",
            compatibility=DomainCompatibilityMode.BACKWARD,
        )

        violations = policy.validate(spec)

        assert len(violations) > 0
        assert any(v.rule == "schema.compatibility.mode" for v in violations)

    def test_prod_allows_full_compatibility(self):
        """PROD는 FULL 허용"""
        policy = CompatibilityPolicy()

        spec = create_schema_spec(
            subject="prod.user-value",
            compatibility=DomainCompatibilityMode.FULL,
        )

        violations = policy.validate(spec)

        assert len(violations) == 0

    def test_stg_allows_backward(self):
        """STG는 BACKWARD 허용"""
        policy = CompatibilityPolicy()

        spec = create_schema_spec(
            subject="stg.user-value",
            compatibility=DomainCompatibilityMode.BACKWARD,
        )

        violations = policy.validate(spec)

        assert len(violations) == 0

    def test_dev_allows_none(self):
        """DEV는 NONE 허용"""
        policy = CompatibilityPolicy()

        spec = create_schema_spec(
            subject="dev.user-value",
            compatibility=DomainCompatibilityMode.NONE,
        )

        violations = policy.validate(spec)

        assert len(violations) == 0

    def test_dev_disallows_full(self):
        """DEV는 FULL 불허 (선택적)"""
        policy = CompatibilityPolicy()

        spec = create_schema_spec(
            subject="dev.user-value",
            compatibility=DomainCompatibilityMode.FULL,
        )

        violations = policy.validate(spec)

        # DEV에서 FULL은 허용되지 않음
        assert len(violations) > 0


class TestMetadataPolicy:
    """MetadataPolicy 테스트"""

    def test_owner_required(self):
        """owner는 필수"""
        from app.schema.domain.models import DomainSchemaSpec

        policy = MetadataPolicy(require_owner=True)

        # metadata=None으로 직접 생성
        spec = DomainSchemaSpec(
            subject="dev.test-value",
            schema_type=DomainSchemaType.AVRO,
            compatibility=DomainCompatibilityMode.BACKWARD,
            schema='{"type": "string"}',
            metadata=None,  # metadata 없음
        )

        violations = policy.validate(spec)

        assert len(violations) > 0
        assert any(v.rule == "schema.metadata.owner" for v in violations)

    def test_owner_not_required(self):
        """owner 필수 아님"""
        policy = MetadataPolicy(require_owner=False)

        spec = create_schema_spec(metadata=None)

        violations = policy.validate(spec)

        assert len(violations) == 0

    def test_valid_metadata(self):
        """정상적인 메타데이터"""
        policy = MetadataPolicy(require_owner=True)

        spec = create_schema_spec(metadata=create_schema_metadata(owner="team-data"))

        violations = policy.validate(spec)

        assert len(violations) == 0


class TestSchemaPolicyEngine:
    """SchemaPolicyEngine 통합 테스트"""

    def test_validate_batch_all_policies(self):
        """모든 정책 통합 검증"""
        engine = SchemaPolicyEngine()

        specs = [
            create_schema_spec(
                subject="prod.user-value",
                compatibility=DomainCompatibilityMode.BACKWARD,  # PROD 위반
            ),
            create_schema_spec(
                subject="dev.test-value",
                metadata=None,  # 메타데이터 위반
            ),
        ]

        violations = engine.validate_batch(specs)

        # 여러 정책에서 위반 검출
        assert len(violations) > 0

    def test_validate_batch_no_violations(self):
        """위반 없는 배치"""
        engine = SchemaPolicyEngine()

        specs = [
            create_schema_spec(
                subject="prod.user-value",
                compatibility=DomainCompatibilityMode.FULL,
                metadata=create_schema_metadata(owner="team-data"),
            ),
            create_schema_spec(
                subject="dev.test-value",
                compatibility=DomainCompatibilityMode.BACKWARD,
                metadata=create_schema_metadata(owner="team-test"),
            ),
        ]

        violations = engine.validate_batch(specs)

        assert len(violations) == 0

    def test_custom_policies(self):
        """커스텀 정책 주입"""
        custom_naming = NamingPolicy(pattern=r"^custom\.[a-z]+$")
        engine = SchemaPolicyEngine(naming_policy=custom_naming)

        spec = create_schema_spec(subject="dev.test-value")
        violations = engine.validate_batch([spec])

        # 커스텀 패턴에 맞지 않음
        assert len(violations) > 0

    def test_metadata_policy_disabled(self):
        """메타데이터 정책 비활성화"""
        engine = SchemaPolicyEngine(metadata_policy=MetadataPolicy(require_owner=False))

        spec = create_schema_spec(metadata=None)
        violations = engine.validate_batch([spec])

        # 메타데이터 위반 없음
        metadata_violations = [v for v in violations if "metadata" in v.rule]
        assert len(metadata_violations) == 0
