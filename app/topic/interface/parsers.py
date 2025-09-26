"""Topic 배치 YAML/JSON 파서"""

from __future__ import annotations

import orjson
import yaml

from ...shared.exceptions import ParseError, safe_file_read, safe_parse
from .schema import TopicBatchRequest

# 기존 호환성을 위한 별칭
TopicBatchParseError = ParseError


class TopicBatchParser:
    """토픽 배치 파서"""

    @staticmethod
    @safe_parse("YAML parsing", format_errors=(yaml.YAMLError,))
    def parse_yaml(content: str) -> TopicBatchRequest:
        """YAML 문자열을 TopicBatchRequest로 파싱"""
        # YAML 파싱
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError("YAML content must be a dictionary")

        # Pydantic 모델로 검증
        return TopicBatchRequest.model_validate(data)

    @staticmethod
    @safe_parse("JSON parsing", format_errors=(orjson.JSONDecodeError,))
    def parse_json(content: str) -> TopicBatchRequest:
        """JSON 문자열을 TopicBatchRequest로 파싱"""
        # orjson으로 JSON 파싱 (더 빠른 성능)
        data = orjson.loads(content)
        if not isinstance(data, dict):
            raise ValueError("JSON content must be an object")

        # Pydantic 모델로 검증
        return TopicBatchRequest.model_validate(data)

    @staticmethod
    def parse_auto(content: str, content_type: str | None = None) -> TopicBatchRequest:
        """자동 포맷 감지 파싱"""
        # Content-Type 기반 파싱
        if content_type:
            if "yaml" in content_type.lower() or "yml" in content_type.lower():
                return TopicBatchParser.parse_yaml(content)
            elif "json" in content_type.lower():
                return TopicBatchParser.parse_json(content)

        # 내용 기반 자동 감지
        content_stripped = content.strip()

        # JSON 시도
        if content_stripped.startswith(("{", "[")):
            try:
                return TopicBatchParser.parse_json(content)
            except TopicBatchParseError:
                pass

        # YAML 시도
        try:
            return TopicBatchParser.parse_yaml(content)
        except TopicBatchParseError:
            pass

        # 둘 다 실패하면 JSON으로 재시도 (더 명확한 에러 메시지)
        return TopicBatchParser.parse_json(content)

    @staticmethod
    @safe_parse("YAML serialization")
    def to_yaml(request: TopicBatchRequest) -> str:
        """TopicBatchRequest를 YAML 문자열로 변환"""
        # Pydantic 모델을 딕셔너리로 변환
        data = request.model_dump(exclude_none=True, by_alias=True)

        # YAML 문자열로 변환
        return yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    @staticmethod
    @safe_parse("JSON serialization")
    def to_json(request: TopicBatchRequest, indent: bool = True) -> str:
        """TopicBatchRequest를 JSON 문자열로 변환"""
        # Pydantic 모델을 딕셔너리로 변환 후 orjson으로 직렬화
        data = request.model_dump(exclude_none=True, by_alias=True)

        # orjson 옵션 설정
        option = orjson.OPT_INDENT_2 if indent else 0
        return orjson.dumps(data, option=option).decode("utf-8")


async def validate_topic_batch_file(file_path: str) -> TopicBatchRequest:
    """파일에서 토픽 배치 로드 및 검증 (비동기)"""
    # 비동기 파일 읽기
    content = await safe_file_read(file_path)

    # 파일 확장자 기반 파싱
    if file_path.endswith((".yml", ".yaml")):
        return TopicBatchParser.parse_yaml(content)
    elif file_path.endswith(".json"):
        return TopicBatchParser.parse_json(content)
    else:
        return TopicBatchParser.parse_auto(content)
