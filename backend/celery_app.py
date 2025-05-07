from celery import Celery
from backend.config.settings import settings

# Initialize Celery
# The first argument is the name of the current module, useful for auto-generating names.
# The `include` argument is a list of modules to import when the worker starts,
# so it can find your @task decorated functions.
celery_app = Celery(
    'financials_tasks', # You can name this as you like
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['backend.tasks'] # We will create backend/tasks.py next
)

# Optional configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],  # Ignore other content
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # You might want to adjust concurrency settings later for production
    # worker_concurrency=4, # Example: Number of worker processes/threads
)

if __name__ == '__main__':
    celery_app.start() 