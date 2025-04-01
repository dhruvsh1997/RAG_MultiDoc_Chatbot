from django.apps import AppConfig
#Establish Config App
class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'
    verbose_name = 'RAG Chatbot'