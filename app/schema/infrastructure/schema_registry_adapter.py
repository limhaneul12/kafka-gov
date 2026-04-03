from importlib import import_module

_schema_registry_module = import_module("app.infra.kafka.schema_registry_adapter")

ConfluentSchemaRegistryAdapter = _schema_registry_module.ConfluentSchemaRegistryAdapter

__all__ = ["ConfluentSchemaRegistryAdapter"]
