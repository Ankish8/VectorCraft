"""
Celery configuration for VectorCraft async processing
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Task serialization
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task routing
CELERY_ROUTES = {
    'vectorization_tasks.vectorize_image': {'queue': 'vectorization'},
    'vectorization_tasks.batch_vectorize': {'queue': 'batch_processing'},
    'vectorization_tasks.extract_palettes': {'queue': 'image_analysis'},
    'vectorization_tasks.cleanup_old_files': {'queue': 'maintenance'},
}

# Task result expiration
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_DISABLE_RATE_LIMITS = False

# Task timeout settings
CELERY_TASK_SOFT_TIME_LIMIT = 600  # 10 minutes
CELERY_TASK_TIME_LIMIT = 900  # 15 minutes

# Retry configuration
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Beat schedule for periodic tasks
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-files': {
        'task': 'vectorization_tasks.cleanup_old_files',
        'schedule': 3600.0,  # every hour
        'args': (7,)  # days to keep files
    },
    'health-check': {
        'task': 'vectorization_tasks.health_check',
        'schedule': 60.0,  # every minute
    },
}

# Monitoring
CELERY_SEND_TASK_EVENTS = True
CELERY_SEND_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# Task annotations for monitoring
CELERY_TASK_ANNOTATIONS = {
    '*': {
        'rate_limit': '10/m',
        'time_limit': 900,
        'soft_time_limit': 600,
    },
    'vectorization_tasks.vectorize_image': {
        'rate_limit': '5/m',
        'time_limit': 1800,  # 30 minutes
        'soft_time_limit': 1200,  # 20 minutes
    },
    'vectorization_tasks.batch_vectorize': {
        'rate_limit': '1/m',
        'time_limit': 3600,  # 1 hour
        'soft_time_limit': 2400,  # 40 minutes
    }
}

def create_celery_app(app=None):
    """
    Create and configure Celery app
    """
    celery = Celery(
        'vectorcraft',
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_BACKEND,
        include=['vectorization_tasks']
    )
    
    # Update configuration
    celery.conf.update(
        task_serializer=CELERY_TASK_SERIALIZER,
        result_serializer=CELERY_RESULT_SERIALIZER,
        accept_content=CELERY_ACCEPT_CONTENT,
        timezone=CELERY_TIMEZONE,
        enable_utc=CELERY_ENABLE_UTC,
        task_routes=CELERY_ROUTES,
        result_expires=CELERY_RESULT_EXPIRES,
        worker_prefetch_multiplier=CELERY_WORKER_PREFETCH_MULTIPLIER,
        worker_max_tasks_per_child=CELERY_WORKER_MAX_TASKS_PER_CHILD,
        worker_disable_rate_limits=CELERY_WORKER_DISABLE_RATE_LIMITS,
        task_soft_time_limit=CELERY_TASK_SOFT_TIME_LIMIT,
        task_time_limit=CELERY_TASK_TIME_LIMIT,
        task_always_eager=CELERY_TASK_ALWAYS_EAGER,
        task_eager_propagates=CELERY_TASK_EAGER_PROPAGATES,
        task_reject_on_worker_lost=CELERY_TASK_REJECT_ON_WORKER_LOST,
        beat_schedule=CELERY_BEAT_SCHEDULE,
        send_task_events=CELERY_SEND_TASK_EVENTS,
        send_events=CELERY_SEND_EVENTS,
        task_send_sent_event=CELERY_TASK_SEND_SENT_EVENT,
        task_annotations=CELERY_TASK_ANNOTATIONS
    )
    
    if app:
        # Flask app context for Celery tasks
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery

# Create default Celery app
celery_app = create_celery_app()