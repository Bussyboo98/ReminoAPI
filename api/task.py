from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import *
from django.urls import reverse

@shared_task
def send_task_reminders():
    """
    Send reminders for tasks that are due within the next day and are not completed.
    """
    now = timezone.now()
    reminder_time = now + timezone.timedelta(days=1)
    tasks = Task.objects.filter(
        due_date__lte=reminder_time,
        due_date__gte=now,
        is_completed=False
    )
    
    for task in tasks:
        user = task.user
        # Construct the absolute URL to the task detail view
        task_detail_path = reverse('api:task-detail', kwargs={'pk': task.pk})
        task_url = f"{settings.SITE_URL}{task_detail_path}"
        
        # Prepare the email content
        subject = f"Reminder: Task '{task.title}' is due soon"
        message = (
            f"Dear {user.username},\n\n"
            f"This is a reminder that your task '{task.title}' is due on {task.due_date.strftime('%Y-%m-%d %H:%M')}.\n\n"
            f"You can view the task here: {task_url}\n\n"
            "Best regards,\nREMINO Team"
        )
        
        # Send the email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=False,
        )
