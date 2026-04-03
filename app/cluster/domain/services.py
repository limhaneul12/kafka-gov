from importlib import import_module

_connection_manager_module = import_module("app.infra.kafka.connection_manager")

ConnectionManager = _connection_manager_module.ConnectionManager
IConnectionManager = _connection_manager_module.IConnectionManager

__all__ = ["ConnectionManager", "IConnectionManager"]
