import json
import os
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import Document, ChatSession, Message, VectorStore
from .rag_utils import process_uploaded_document, get_answer

#All Views
def login_view(request):
    """Handle user login"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('chat')
    else:
        form = AuthenticationForm()
    return render(request, 'chatbot/login.html', {'form': form})

def register_view(request):
    """Handle user registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat')
    else:
        form = UserCreationForm()
    return render(request, 'chatbot/register.html', {'form': form})

@login_required
def chat_view(request):
    """Render the main chat interface"""
    # Check if there's an active chat session, or create one
    chat_session = ChatSession.objects.filter(user=request.user).order_by('-created_at').first()
    
    if not chat_session:
        chat_session = ChatSession.objects.create(user=request.user)
    
    # Get previous messages for this session
    messages = Message.objects.filter(session=chat_session)
    
    # Check if there's an active vector store
    has_vectorstore = VectorStore.objects.filter(is_active=True).exists()
    
    context = {
        'messages': messages,
        'session_id': chat_session.id,
        'has_vectorstore': has_vectorstore,
    }
    
    return render(request, 'chatbot/chat.html', context)

@login_required
@require_POST
def upload_document(request):
    """Handle document upload and processing"""
    if 'document' not in request.FILES:
        return JsonResponse({'error': 'No document provided'}, status=400)
    
    file = request.FILES['document']
    
    # Validate file type (only PDF)
    if not file.name.endswith('.pdf'):
        return JsonResponse({'error': 'Only PDF files are supported'}, status=400)
    
    # Create the document
    document = Document.objects.create(
        user=request.user,
        title=file.name,
        file=file
    )
    
    try:
        # Process the document asynchronously (in a real app, this would be a background task)
        # For simplicity, we're doing it synchronously here
        vectorstore, vector_store = process_uploaded_document(document)
        
        return JsonResponse({
            'success': True,
            'document_id': document.id,
            'document_name': document.title,
            'vector_store_id': vector_store.id,
        })
    except Exception as e:
        # If there's an error, delete the document
        document.delete()
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def send_message(request):
    """Handle sending a message and getting a response"""
    try:
        data = json.loads(request.body)
        message_text = data.get('message')
        session_id = data.get('session_id')
        
        if not message_text:
            return JsonResponse({'error': 'No message provided'}, status=400)
        
        # Get the chat session
        try:
            chat_session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            # Create a new session if the provided one doesn't exist
            chat_session = ChatSession.objects.create(user=request.user)
        
        # Save the user message
        user_message = Message.objects.create(
            session=chat_session,
            role='user',
            content=message_text
        )
        
        # Get the answer from the RAG system
        groq_api_key = settings.GROQ_API_KEY
        response = get_answer(message_text, groq_api_key)
        
        # Save the assistant message
        assistant_message = Message.objects.create(
            session=chat_session,
            role='assistant',
            content=response['answer']
        )
        
        return JsonResponse({
            'user_message': {
                'id': user_message.id,
                'content': user_message.content,
                'timestamp': user_message.timestamp.isoformat(),
            },
            'assistant_message': {
                'id': assistant_message.id,
                'content': assistant_message.content,
                'timestamp': assistant_message.timestamp.isoformat(),
            },
            'source_documents': response['source_documents']
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def check_vectorstore(request):
    """Check if an active vector store exists"""
    has_vectorstore = VectorStore.objects.filter(is_active=True).exists()
    
    return JsonResponse({
        'has_vectorstore': has_vectorstore
    })