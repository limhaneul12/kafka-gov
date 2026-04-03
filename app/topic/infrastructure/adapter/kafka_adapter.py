from importlib import import_module

_kafka_adapter_module = import_module("app.infra.kafka.kafka_adapter")

KafkaTopicAdapter = _kafka_adapter_module.KafkaTopicAdapter

__all__ = ["KafkaTopicAdapter"]
