from django.db import models
from django.contrib.auth.models import User
from tinymce.models import HTMLField

class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True) 

    class Meta:
        unique_together = ('user', 'name')  
        ordering = ['name']

    def __str__(self):
        return self.name

class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=255)
    content = HTMLField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')
    image = models.ImageField(upload_to='notes/images/', null=True, blank=True)
    file = models.FileField(upload_to='notes/files/', null=True, blank=True)
    is_shared = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(User, related_name='shared_notes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  

    def __str__(self):
        return self.title
    
class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = HTMLField()
    due_date = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(User, related_name='shared_tasks', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return self.title
    