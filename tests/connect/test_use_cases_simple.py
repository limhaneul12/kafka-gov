"""Connect Use Cases 간단 테스트 - 통합 테스트 대신 단위 테스트"""

import pytest


class TestConnectorOperationsSimple:
    """커넥터 Operations 간단 테스트"""

    @pytest.mark.asyncio
    async def test_connector_operations_exists(self):
        """ConnectorOperations 클래스 존재 확인"""
        from app.connect.application.use_cases import ConnectorOperations

        assert ConnectorOperations is not None

    @pytest.mark.asyncio
    async def test_task_operations_exists(self):
        """TaskOperations 클래스 존재 확인"""
        from app.connect.application.use_cases import TaskOperations

        assert TaskOperations is not None

    @pytest.mark.asyncio
    async def test_topic_operations_exists(self):
        """TopicOperations 클래스 존재 확인"""
        from app.connect.application.use_cases import TopicOperations

        assert TopicOperations is not None

    @pytest.mark.asyncio
    async def test_plugin_operations_exists(self):
        """PluginOperations 클래스 존재 확인"""
        from app.connect.application.use_cases import PluginOperations

        assert PluginOperations is not None


class TestConnectorStateControl:
    """커넥터 상태 제어 간단 테스트"""

    @pytest.mark.asyncio
    async def test_connector_state_control_exists(self):
        """ConnectorStateControl 클래스 존재 확인"""
        from app.connect.application.use_cases import ConnectorStateControl

        assert ConnectorStateControl is not None
