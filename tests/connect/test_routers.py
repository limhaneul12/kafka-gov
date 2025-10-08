"""Connect Routers 테스트"""

import pytest


class TestConnectorCrudRouter:
    """Connector CRUD Router 테스트"""

    def test_router_import(self):
        """Router import 가능"""
        from app.connect.interface.routers.connector_crud_router import router

        assert router is not None

    def test_router_has_routes(self):
        """Router에 route가 등록되어 있는지"""
        from app.connect.interface.routers.connector_crud_router import router

        assert len(router.routes) > 0


class TestConnectorControlRouter:
    """Connector Control Router 테스트"""

    def test_router_import(self):
        """Router import 가능"""
        from app.connect.interface.routers.connector_control_router import router

        assert router is not None

    def test_router_has_routes(self):
        """Router에 route가 등록되어 있는지"""
        from app.connect.interface.routers.connector_control_router import router

        assert len(router.routes) > 0


class TestTasksRouter:
    """Tasks Router 테스트"""

    def test_router_import(self):
        """Router import 가능"""
        from app.connect.interface.routers.tasks_router import router

        assert router is not None

    def test_router_has_routes(self):
        """Router에 route가 등록되어 있는지"""
        from app.connect.interface.routers.tasks_router import router

        assert len(router.routes) > 0


class TestTopicsRouter:
    """Topics Router 테스트"""

    def test_router_import(self):
        """Router import 가능"""
        from app.connect.interface.routers.topics_router import router

        assert router is not None

    def test_router_has_routes(self):
        """Router에 route가 등록되어 있는지"""
        from app.connect.interface.routers.topics_router import router

        assert len(router.routes) > 0


class TestPluginsRouter:
    """Plugins Router 테스트"""

    def test_router_import(self):
        """Router import 가능"""
        from app.connect.interface.routers.plugins_router import router

        assert router is not None

    def test_router_has_routes(self):
        """Router에 route가 등록되어 있는지"""
        from app.connect.interface.routers.plugins_router import router

        assert len(router.routes) > 0


class TestMetadataRouter:
    """Metadata Router 테스트"""

    def test_router_import(self):
        """Router import 가능"""
        from app.connect.interface.routers.metadata_router import router

        assert router is not None

    def test_router_has_routes(self):
        """Router에 route가 등록되어 있는지"""
        from app.connect.interface.routers.metadata_router import router

        assert len(router.routes) > 0
