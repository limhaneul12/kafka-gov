"""Connect Types 테스트 - Pydantic 모델 검증"""

import pytest
from pydantic import ValidationError

from app.connect.domain.types import PluginInfoDict


class TestPluginInfoDict:
    """PluginInfoDict Pydantic 모델 테스트"""

    def test_plugin_info_with_class_alias(self):
        """'class' 필드를 alias로 받기"""
        data = {
            "class": "io.confluent.connect.s3.S3SinkConnector",
            "type": "sink",
            "version": "11.0.6",
        }

        plugin = PluginInfoDict(**data)

        assert plugin.class_ == "io.confluent.connect.s3.S3SinkConnector"
        assert plugin.type == "sink"
        assert plugin.version == "11.0.6"

    def test_plugin_info_with_class_underscore(self):
        """'class_' 필드로 직접 받기 (populate_by_name=True)"""
        data = {
            "class_": "io.confluent.connect.s3.S3SinkConnector",
            "type": "sink",
            "version": "11.0.6",
        }

        plugin = PluginInfoDict(**data)

        assert plugin.class_ == "io.confluent.connect.s3.S3SinkConnector"

    def test_plugin_info_dict_serialization(self):
        """dict로 직렬화 시 alias 사용"""
        plugin = PluginInfoDict(
            class_="io.confluent.connect.s3.S3SinkConnector",
            type="sink",
            version="11.0.6",
        )

        # by_alias=True로 직렬화하면 'class'로 출력
        data = plugin.model_dump(by_alias=True)

        assert "class" in data
        assert data["class"] == "io.confluent.connect.s3.S3SinkConnector"

    def test_plugin_info_missing_fields(self):
        """필수 필드 누락 시 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            PluginInfoDict(type="sink", version="11.0.6")  # class 누락

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("class",) for err in errors)

    def test_plugin_info_source_type(self):
        """source 타입 플러그인"""
        plugin = PluginInfoDict(
            class_="org.apache.kafka.connect.mirror.MirrorSourceConnector",
            type="source",
            version="7.7.0",
        )

        assert plugin.type == "source"

    def test_plugin_info_json_schema(self):
        """JSON Schema 생성 확인"""
        schema = PluginInfoDict.model_json_schema()

        assert "properties" in schema
        assert "class" in schema["properties"]  # alias가 스키마에 반영됨
        assert "required" in schema
