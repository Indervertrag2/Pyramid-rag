from celery import Celery
import os

# Create Celery instance
celery_app = Celery(
    "pyramid_rag",
    broker=os.getenv('CELERY_BROKER_URL', 'redis://pyramid-redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://pyramid-redis:6379/0'),
    include=[
        "app.workers.document_tasks",
        "app.workers.embedding_tasks"
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,  # 1 hour
    task_track_started=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)