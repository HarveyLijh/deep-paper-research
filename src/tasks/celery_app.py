# src/tasks/celery_app.py
from celery import Celery
from src.config.settings import settings

# Initialize Celery
celery_app = Celery('paper_discovery',
                    broker=settings.CELERY_BROKER_URL,
                    backend=settings.CELERY_RESULT_BACKEND)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'src.tasks.paper_tasks.*': {'queue': 'paper_processing'},
        'src.tasks.api_tasks.*': {'queue': 'api_calls'}
    },
    task_default_queue='default',
    # Rate limits
    task_annotations={
        'src.tasks.api_tasks.semantic_scholar_call': {'rate_limit': '100/m'},
        'src.tasks.api_tasks.gpt_call': {'rate_limit': '60/m'}
    },
    # Retry settings
    task_retry_delay_start=1,
    task_max_retries=3,
    # Task expiration
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,      # 10 minutes
)
