"""
Celery configuration for Content Repurposer backend.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('content_repurposer')

# Load config from Django settings, namespace='CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'publish-scheduled-posts-every-minute': {
        'task': 'apps.repurposer.tasks.publish_scheduled_posts',
        'schedule': 60.0,  # Run every minute
    },
    'create-recurring-posts-daily': {
        'task': 'apps.repurposer.tasks.create_recurring_posts',
        'schedule': crontab(hour=0, minute=5),  # Run at 00:05 daily
    },
}

app.conf.timezone = 'UTC'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
