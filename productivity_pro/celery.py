import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'productivity_pro.settings')

app = Celery('productivity_pro')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()



app.conf.beat_schedule = {
    'send-task-reminders-daily': {
        'task': 'your_app.tasks.send_task_reminders',
        'schedule': crontab(hour=9, minute=0),  
    },
}