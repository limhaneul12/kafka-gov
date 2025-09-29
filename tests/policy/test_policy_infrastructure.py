"""Policy 인프라스트럭처 테스트"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.policy.domain.models import (
    DomainConfigurationRule,
    DomainEnvironment,
    DomainNamingRule,
    DomainPolicySet,
    DomainResourceType,
)
from app.policy.infrastructure.file_repository import FilePolicyRepository
from app.policy.infrastructure.memory_repository import MemoryPolicyRepository


class TestMemoryPolicyRepository:
    """MemoryPolicyRepository 테스트"""

    @pytest.fixture
    def repository(self) -> MemoryPolicyRepository:
        """메모리 저장소 픽스처"""
        return MemoryPolicyRepository()

    @pytest.fixture
    def sample_policy_set(self) -> DomainPolicySet:
        """샘플 정책 집합 픽스처"""
        naming_rule = DomainNamingRule(pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$")
        partition_rule = DomainConfigurationRule(
            config_key="partitions",
            min_value=3,
            required=True,
        )

        return DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(naming_rule, partition_rule),
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_save_and_retrieve_policy_set(
        self, repository: MemoryPolicyRepository, sample_policy_set: DomainPolicySet
    ) -> None:
        """정책 집합을 저장하고 조회해야 한다."""
        # Act - 저장
        await repository.save_policy_set(sample_policy_set)

        # Act - 조회
        retrieved = await repository.get_policy_set(
            DomainEnvironment.PROD, DomainResourceType.TOPIC
        )

        # Assert
        assert retrieved is not None
        assert retrieved == sample_policy_set
        assert retrieved.environment == DomainEnvironment.PROD
        assert retrieved.resource_type == DomainResourceType.TOPIC
        assert len(retrieved.rules) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_return_none_for_nonexistent_policy_set(
        self, repository: MemoryPolicyRepository
    ) -> None:
        """존재하지 않는 정책 집합에 대해 None을 반환해야 한다."""
        # Act
        retrieved = await repository.get_policy_set(
            DomainEnvironment.DEV, DomainResourceType.SCHEMA
        )

        # Assert
        assert retrieved is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_overwrite_existing_policy_set(
        self, repository: MemoryPolicyRepository, sample_policy_set: DomainPolicySet
    ) -> None:
        """기존 정책 집합을 덮어써야 한다."""
        # Arrange - 첫 번째 정책 저장
        await repository.save_policy_set(sample_policy_set)

        # 새로운 정책 생성
        new_naming_rule = DomainNamingRule(pattern=r"^new-[a-z]+$")
        new_policy_set = DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(new_naming_rule,),
        )

        # Act - 덮어쓰기
        await repository.save_policy_set(new_policy_set)

        # Assert
        retrieved = await repository.get_policy_set(
            DomainEnvironment.PROD, DomainResourceType.TOPIC
        )
        assert retrieved == new_policy_set
        assert len(retrieved.rules) == 1  # 새로운 정책으로 교체됨

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_delete_existing_policy_set(
        self, repository: MemoryPolicyRepository, sample_policy_set: DomainPolicySet
    ) -> None:
        """기존 정책 집합을 삭제해야 한다."""
        # Arrange
        await repository.save_policy_set(sample_policy_set)

        # Act
        result = await repository.delete_policy_set(
            DomainEnvironment.PROD, DomainResourceType.TOPIC
        )

        # Assert
        assert result is True
        retrieved = await repository.get_policy_set(
            DomainEnvironment.PROD, DomainResourceType.TOPIC
        )
        assert retrieved is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_return_false_when_deleting_nonexistent_policy_set(
        self, repository: MemoryPolicyRepository
    ) -> None:
        """존재하지 않는 정책 집합 삭제 시 False를 반환해야 한다."""
        # Act
        result = await repository.delete_policy_set(
            DomainEnvironment.DEV, DomainResourceType.SCHEMA
        )

        # Assert
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_list_environments(
        self, repository: MemoryPolicyRepository, sample_policy_set: DomainPolicySet
    ) -> None:
        """등록된 환경 목록을 반환해야 한다."""
        # Arrange
        await repository.save_policy_set(sample_policy_set)

        dev_policy = DomainPolicySet(
            environment=DomainEnvironment.DEV,
            resource_type=DomainResourceType.TOPIC,
            rules=(),
        )
        await repository.save_policy_set(dev_policy)

        # Act
        environments = await repository.list_environments()

        # Assert
        assert len(environments) == 2
        assert DomainEnvironment.PROD in environments
        assert DomainEnvironment.DEV in environments

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_list_resource_types_for_environment(
        self, repository: MemoryPolicyRepository
    ) -> None:
        """환경별 리소스 타입 목록을 반환해야 한다."""
        # Arrange
        topic_policy = DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(),
        )
        schema_policy = DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.SCHEMA,
            rules=(),
        )

        await repository.save_policy_set(topic_policy)
        await repository.save_policy_set(schema_policy)

        # Act
        resource_types = await repository.list_resource_types(DomainEnvironment.PROD)

        # Assert
        assert len(resource_types) == 2
        assert DomainResourceType.TOPIC in resource_types
        assert DomainResourceType.SCHEMA in resource_types

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_return_empty_list_for_nonexistent_environment(
        self, repository: MemoryPolicyRepository
    ) -> None:
        """존재하지 않는 환경에 대해 빈 목록을 반환해야 한다."""
        # Act
        resource_types = await repository.list_resource_types(DomainEnvironment.STG)

        # Assert
        assert len(resource_types) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_handle_multiple_policy_sets(
        self, repository: MemoryPolicyRepository
    ) -> None:
        """여러 정책 집합을 처리해야 한다."""
        # Arrange
        policies = [
            DomainPolicySet(DomainEnvironment.DEV, DomainResourceType.TOPIC, ()),
            DomainPolicySet(DomainEnvironment.DEV, DomainResourceType.SCHEMA, ()),
            DomainPolicySet(DomainEnvironment.PROD, DomainResourceType.TOPIC, ()),
            DomainPolicySet(DomainEnvironment.PROD, DomainResourceType.SCHEMA, ()),
        ]

        for policy in policies:
            await repository.save_policy_set(policy)

        # Act & Assert
        for policy in policies:
            retrieved = await repository.get_policy_set(policy.environment, policy.resource_type)
            assert retrieved == policy


class TestFilePolicyRepository:
    """FilePolicyRepository 테스트"""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """임시 디렉토리 픽스처"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def repository(self, temp_dir: Path) -> FilePolicyRepository:
        """파일 저장소 픽스처"""
        return FilePolicyRepository(temp_dir / "policies")

    @pytest.fixture
    def sample_policy_set(self) -> DomainPolicySet:
        """샘플 정책 집합 픽스처"""
        naming_rule = DomainNamingRule(pattern=r"^[a-z][a-z0-9-]*[a-z0-9]$")
        return DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(naming_rule,),
        )

    @pytest.mark.unit
    def test_should_create_config_directory(self, temp_dir: Path) -> None:
        """설정 디렉토리를 생성해야 한다."""
        # Arrange
        config_dir = temp_dir / "policies"
        assert not config_dir.exists()

        # Act
        FilePolicyRepository(config_dir)

        # Assert
        assert config_dir.exists()
        assert config_dir.is_dir()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_save_policy_set_to_file(
        self, repository: FilePolicyRepository, sample_policy_set: DomainPolicySet, temp_dir: Path
    ) -> None:
        """정책 집합을 파일에 저장해야 한다."""
        # Act
        await repository.save_policy_set(sample_policy_set)

        # Assert
        expected_file = temp_dir / "policies" / "prod_topic.json"
        assert expected_file.exists()

        # 파일 내용 검증
        with expected_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["environment"] == "prod"
        assert data["resource_type"] == "topic"
        assert len(data["rules"]) == 1
        assert data["rules"][0]["rule_id"] == "naming.pattern"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_return_none_for_nonexistent_file(
        self, repository: FilePolicyRepository
    ) -> None:
        """존재하지 않는 파일에 대해 None을 반환해야 한다."""
        # Act
        retrieved = await repository.get_policy_set(
            DomainEnvironment.DEV, DomainResourceType.SCHEMA
        )

        # Assert
        assert retrieved is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_handle_corrupted_file_gracefully(
        self, repository: FilePolicyRepository, temp_dir: Path
    ) -> None:
        """손상된 파일을 우아하게 처리해야 한다."""
        # Arrange - 잘못된 JSON 파일 생성
        corrupted_file = temp_dir / "policies" / "dev_topic.json"
        corrupted_file.parent.mkdir(parents=True, exist_ok=True)
        with corrupted_file.open("w", encoding="utf-8") as f:
            f.write("invalid json content")

        # Act
        retrieved = await repository.get_policy_set(DomainEnvironment.DEV, DomainResourceType.TOPIC)

        # Assert
        assert retrieved is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_delete_policy_file(
        self, repository: FilePolicyRepository, sample_policy_set: DomainPolicySet, temp_dir: Path
    ) -> None:
        """정책 파일을 삭제해야 한다."""
        # Arrange
        await repository.save_policy_set(sample_policy_set)
        policy_file = temp_dir / "policies" / "prod_topic.json"
        assert policy_file.exists()

        # Act
        result = await repository.delete_policy_set(
            DomainEnvironment.PROD, DomainResourceType.TOPIC
        )

        # Assert
        assert result is True
        assert not policy_file.exists()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_return_false_when_deleting_nonexistent_file(
        self, repository: FilePolicyRepository
    ) -> None:
        """존재하지 않는 파일 삭제 시 False를 반환해야 한다."""
        # Act
        result = await repository.delete_policy_set(
            DomainEnvironment.DEV, DomainResourceType.SCHEMA
        )

        # Assert
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_list_environments_from_files(
        self, repository: FilePolicyRepository, temp_dir: Path
    ) -> None:
        """파일에서 환경 목록을 읽어야 한다."""
        # Arrange - 테스트 파일들 생성
        policy_dir = temp_dir / "policies"
        policy_dir.mkdir(parents=True, exist_ok=True)

        test_files = [
            "dev_topic.json",
            "prod_topic.json",
            "prod_schema.json",
            "invalid_file.json",  # 잘못된 형식
        ]

        for filename in test_files:
            (policy_dir / filename).touch()

        # Act
        environments = await repository.list_environments()

        # Assert
        assert len(environments) == 2
        assert DomainEnvironment.DEV in environments
        assert DomainEnvironment.PROD in environments

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_list_resource_types_for_environment(
        self, repository: FilePolicyRepository, temp_dir: Path
    ) -> None:
        """환경별 리소스 타입 목록을 반환해야 한다."""
        # Arrange
        policy_dir = temp_dir / "policies"
        policy_dir.mkdir(parents=True, exist_ok=True)

        prod_files = [
            "prod_topic.json",
            "prod_schema.json",
        ]
        dev_files = [
            "dev_topic.json",
        ]

        for filename in prod_files + dev_files:
            (policy_dir / filename).touch()

        # Act
        prod_resource_types = await repository.list_resource_types(DomainEnvironment.PROD)
        dev_resource_types = await repository.list_resource_types(DomainEnvironment.DEV)

        # Assert
        assert len(prod_resource_types) == 2
        assert DomainResourceType.TOPIC in prod_resource_types
        assert DomainResourceType.SCHEMA in prod_resource_types

        assert len(dev_resource_types) == 1
        assert DomainResourceType.TOPIC in dev_resource_types

    @pytest.mark.unit
    def test_should_generate_correct_file_path(
        self, repository: FilePolicyRepository, temp_dir: Path
    ) -> None:
        """올바른 파일 경로를 생성해야 한다."""
        # Act
        file_path = repository._get_file_path(DomainEnvironment.PROD, DomainResourceType.TOPIC)

        # Assert
        expected_path = temp_dir / "policies" / "prod_topic.json"
        assert file_path == expected_path

    @pytest.mark.unit
    def test_should_serialize_policy_set_correctly(
        self, repository: FilePolicyRepository, sample_policy_set: DomainPolicySet
    ) -> None:
        """정책 집합을 올바르게 직렬화해야 한다."""
        # Act
        data = repository._serialize_policy_set(sample_policy_set)

        # Assert
        assert data["environment"] == "prod"
        assert data["resource_type"] == "topic"
        assert len(data["rules"]) == 1

        rule_data = data["rules"][0]
        assert rule_data["rule_id"] == "naming.pattern"
        assert "description" in rule_data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_handle_empty_directory(self, repository: FilePolicyRepository) -> None:
        """빈 디렉토리를 처리해야 한다."""
        # Act
        environments = await repository.list_environments()
        resource_types = await repository.list_resource_types(DomainEnvironment.PROD)

        # Assert
        assert len(environments) == 0
        assert len(resource_types) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_should_overwrite_existing_file(
        self, repository: FilePolicyRepository, sample_policy_set: DomainPolicySet, temp_dir: Path
    ) -> None:
        """기존 파일을 덮어써야 한다."""
        # Arrange - 첫 번째 저장
        await repository.save_policy_set(sample_policy_set)

        # 새로운 정책 생성
        new_naming_rule = DomainNamingRule(pattern=r"^new-[a-z]+$")
        new_policy_set = DomainPolicySet(
            environment=DomainEnvironment.PROD,
            resource_type=DomainResourceType.TOPIC,
            rules=(new_naming_rule,),
        )

        # Act - 덮어쓰기
        await repository.save_policy_set(new_policy_set)

        # Assert
        policy_file = temp_dir / "policies" / "prod_topic.json"
        with policy_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # 새로운 규칙의 패턴이 저장되었는지 확인
        assert len(data["rules"]) == 1
        rule_data = data["rules"][0]
        assert rule_data["rule_id"] == "naming.pattern"
