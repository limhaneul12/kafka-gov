"""Celery 애플리케이션 설정"""

from celery import Celery
from celery.schedules import crontab

# Celery 인스턴스 생성
celery_app = Celery(
    "kafka_gov",
    broker="redis://localhost:6379/0",  # Redis broker
    backend="redis://localhost:6379/0",  # Result backend
    include=["app.tasks.metrics_tasks"],  # 태스크 모듈
)

# Celery 설정 (type-safe)
conf = celery_app.conf
if conf is None:
    raise RuntimeError("Celery configuration is not available")

conf.update(
    # 타임존
    timezone="UTC",
    enable_utc=True,
    # 결과 만료 시간
    result_expires=3600,
    # 태스크 직렬화
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 워커 설정
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Periodic Task 스케줄 설정
    beat_schedule={
        "collect-metrics-every-5-minutes": {
            "task": "app.tasks.metrics_tasks.collect_and_store_metrics",
            "schedule": crontab(minute="*/5"),  # 5분마다 실행
            "args": (),
        },
        "cleanup-old-snapshots-daily": {
            "task": "app.tasks.metrics_tasks.cleanup_old_snapshots",
            "schedule": crontab(hour=2, minute=0),  # 매일 02:00
            "args": (7,),  # 7일 이상 된 데이터 삭제
        },
    },
)
