from django.contrib import admin
from .models import Document, ChatSession, Message, VectorStore, DocumentVectorMapping

class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'uploaded_at')
    search_fields = ('title', 'user__username')
    list_filter = ('uploaded_at',)

class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'last_activity')
    search_fields = ('user__username',)
    list_filter = ('created_at', 'last_activity')

class MessageAdmin(admin.ModelAdmin):
    list_display = ('role', 'content_preview', 'session', 'timestamp')
    search_fields = ('content', 'session__user__username')
    list_filter = ('role', 'timestamp')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

class VectorStoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'updated_at', 'is_active')
    list_filter = ('is_active', 'created_at', 'updated_at')

class DocumentVectorMappingAdmin(admin.ModelAdmin):
    list_display = ('document', 'vector_store')
    list_filter = ('vector_store',)

# Register the models with their admin classes
admin.site.register(Document, DocumentAdmin)
admin.site.register(ChatSession, ChatSessionAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(VectorStore, VectorStoreAdmin)
admin.site.register(DocumentVectorMapping, DocumentVectorMappingAdmin)