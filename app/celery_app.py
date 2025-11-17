"""
Celery Application Configuration
Handles async task processing for embeddings and document processing
"""

import logging
from celery import Celery, Task
from app.config import settings

logger = logging.getLogger(__name__)

# Create Celery app
app = Celery(__name__)

# Configure Celery from settings
app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,

    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # Task timeout (30 minutes)
    task_soft_time_limit=1800,
    task_time_limit=1900,

    # Retry settings
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,

    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,

    # Logging
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
)

# Auto-discover tasks from all installed apps
app.autodiscover_tasks(['app.tasks'], force=True)

class CallbackTask(Task):
    """Task class with callback support"""
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

app.Task = CallbackTask

logger.info("✓ Celery app initialized")
logger.info(f"  Broker: {settings.CELERY_BROKER_URL}")
logger.info(f"  Result Backend: {settings.CELERY_RESULT_BACKEND}")
