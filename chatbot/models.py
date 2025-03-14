from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Document(models.Model):
    """Model to store information about uploaded documents"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class ChatSession(models.Model):
    """Model to store chat sessions for each user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Session {self.id} - {self.user.username}"

class Message(models.Model):
    """Model to store individual chat messages"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

class VectorStore(models.Model):
    """Model to store metadata about vector stores"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    file_path = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"VectorStore {self.id} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class DocumentVectorMapping(models.Model):
    """Model to track which documents are included in which vector stores"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    vector_store = models.ForeignKey(VectorStore, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('document', 'vector_store')
    
    def __str__(self):
        return f"Doc {self.document.id} in VectorStore {self.vector_store.id}"