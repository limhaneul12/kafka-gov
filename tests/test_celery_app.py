from app.celery_app import celery_app


def test_celery_app_identity() -> None:
    assert celery_app.main == "kafka_gov"


def test_celery_app_uses_redis_settings() -> None:
    assert celery_app.conf.broker_url == "redis://redis:6379/0"
    assert celery_app.conf.result_backend == "redis://redis:6379/0"
