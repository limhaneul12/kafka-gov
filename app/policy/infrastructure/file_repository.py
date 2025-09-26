"""파일 기반 정책 저장소"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..domain import Environment, IPolicyRepository, PolicySet, ResourceType


class FilePolicyRepository(IPolicyRepository):
    """파일 기반 정책 저장소 (YAML/JSON 설정 파일)"""
    
    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_policy_set(
        self, 
        environment: Environment, 
        resource_type: ResourceType
    ) -> PolicySet | None:
        """정책 집합 조회"""
        file_path = self._get_file_path(environment, resource_type)
        
        if not file_path.exists():
            return None
        
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            return self._deserialize_policy_set(data)
        except Exception:
            return None
    
    async def save_policy_set(self, policy_set: PolicySet) -> None:
        """정책 집합 저장"""
        file_path = self._get_file_path(policy_set.environment, policy_set.resource_type)
        
        data = self._serialize_policy_set(policy_set)
        
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def delete_policy_set(
        self, 
        environment: Environment, 
        resource_type: ResourceType
    ) -> bool:
        """정책 집합 삭제"""
        file_path = self._get_file_path(environment, resource_type)
        
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    async def list_environments(self) -> list[Environment]:
        """등록된 환경 목록"""
        environments = set()
        
        for file_path in self.config_dir.glob("*.json"):
            try:
                env_str, _ = file_path.stem.split("_", 1)
                environments.add(Environment(env_str))
            except (ValueError, AttributeError):
                continue
        
        return list(environments)
    
    async def list_resource_types(self, environment: Environment) -> list[ResourceType]:
        """환경별 리소스 타입 목록"""
        resource_types = []
        
        for file_path in self.config_dir.glob(f"{environment.value}_*.json"):
            try:
                _, rt_str = file_path.stem.split("_", 1)
                resource_types.append(ResourceType(rt_str))
            except (ValueError, AttributeError):
                continue
        
        return resource_types
    
    def _get_file_path(self, environment: Environment, resource_type: ResourceType) -> Path:
        """설정 파일 경로 생성"""
        filename = f"{environment.value}_{resource_type.value}.json"
        return self.config_dir / filename
    
    def _serialize_policy_set(self, policy_set: PolicySet) -> dict[str, Any]:
        """PolicySet을 JSON 직렬화 가능한 형태로 변환"""
        # 실제 구현에서는 PolicyRule들을 JSON으로 직렬화해야 함
        # 여기서는 간단한 구조만 제공
        return {
            "environment": policy_set.environment.value,
            "resource_type": policy_set.resource_type.value,
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "description": rule.description,
                    # 실제로는 각 규칙 타입별로 직렬화 로직 필요
                }
                for rule in policy_set.rules
            ],
        }
    
    def _deserialize_policy_set(self, data: dict[str, Any]) -> PolicySet | None:
        """JSON 데이터를 PolicySet으로 역직렬화"""
        # 실제 구현에서는 규칙 타입별로 역직렬화 로직 필요
        # 여기서는 None 반환 (구현 필요)
        return None
