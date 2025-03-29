from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication Views URL
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Chat
    path('', views.chat_view, name='chat'),
    
    # API endpoints
    path('api/upload-document/', views.upload_document, name='upload_document'),
    path('api/send-message/', views.send_message, name='send_message'),
    path('api/check-vectorstore/', views.check_vectorstore, name='check_vectorstore'),
]