document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const sessionId = document.getElementById('session-id').value;
    const documentUploadForm = document.getElementById('document-upload-form');
    const documentInput = document.getElementById('document-input');
    const uploadButton = document.getElementById('upload-button');
    const sendButton = document.getElementById('send-button');
    const loaderOverlay = document.getElementById('loader-overlay');
    
    // Check if vectorstore exists
    function checkVectorStore() {
        fetch('/api/check-vectorstore/')
            .then(response => response.json())
            .then(data => {
                if (data.has_vectorstore) {
                    enableChat();
                } else {
                    disableChat();
                }
            })
            .catch(error => {
                console.error('Error checking vectorstore:', error);
            });
    }
    
    // Enable chat functionality
    function enableChat() {
        messageInput.disabled = false;
        sendButton.disabled = false;
        
        // Clear placeholder text if it's the default
        if (chatMessages.innerHTML.includes('Please upload a document to start chatting')) {
            chatMessages.innerHTML = '<div class="text-center text-muted"><p>Start a conversation with the chatbot.</p></div>';
        }
    }
    
    // Disable chat functionality
    function disableChat() {
        messageInput.disabled = true;
        sendButton.disabled = true;
        
        // Set placeholder text if chat is empty
        if (chatMessages.children.length === 0) {
            chatMessages.innerHTML = '<div class="text-center text-muted"><p>Please upload a document to start chatting.</p></div>';
        }
    }
    
    // Handle document upload
    documentUploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData();
        const file = documentInput.files[0];
        
        if (!file) {
            alert('Please select a file to upload.');
            return;
        }
        
        if (!file.name.endsWith('.pdf')) {
            alert('Only PDF files are supported.');
            return;
        }
        
        formData.append('document', file);
        
        // Show loader
        loaderOverlay.style.display = 'flex';
        
        // Disable form elements
        documentInput.disabled = true;
        uploadButton.disabled = true;
        
        // Send upload request
        fetch('/api/upload-document/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear file input
                documentInput.value = '';
                
                // Enable chat
                enableChat();
                
                // Add system message about document upload
                const systemMessage = document.createElement('div');
                systemMessage.className = 'message assistant-message';
                systemMessage.textContent = `Document "${data.document_name}" has been uploaded and processed. You can now ask questions about its content.`;
                chatMessages.appendChild(systemMessage);
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error uploading document:', error);
            alert('An error occurred while uploading the document. Please try again.');
        })
        .finally(() => {
            // Hide loader
            loaderOverlay.style.display = 'none';
            
            // Re-enable form elements
            documentInput.disabled = false;
            uploadButton.disabled = false;
        });
    });
    
    // Handle chat form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        
        if (!message) {
            return;
        }
        
        // Add user message to chat
        addMessage('user', message);
        
        // Clear input
        messageInput.value = '';
        
        // Disable input while waiting for response
        messageInput.disabled = true;
        sendButton.disabled = true;
        
        // Create a typing indicator
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'message assistant-message typing-indicator';
        typingIndicator.innerHTML = '<div class="typing-dots"><span>.</span><span>.</span><span>.</span></div>';
        chatMessages.appendChild(typingIndicator);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Send message to server
        fetch('/api/send-message/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        })
        .then(response => response.json())
        .then(data => {
            // Remove typing indicator
            chatMessages.removeChild(typingIndicator);
            
            // Add assistant message
            addMessage('assistant', data.assistant_message.content);
            
            // Add source documents if available
            if (data.source_documents && data.source_documents.length > 0) {
                addSourceDocuments(data.source_documents);
            }
        })
        .catch(error => {
            console.error('Error sending message:', error);
            
            // Remove typing indicator
            chatMessages.removeChild(typingIndicator);
            
            // Add error message
            const errorMessage = document.createElement('div');
            errorMessage.className = 'message assistant-message error';
            errorMessage.textContent = 'Sorry, an error occurred. Please try again.';
            chatMessages.appendChild(errorMessage);
        })
        .finally(() => {
            // Re-enable input
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
        });
    });
    
    // Add a message to the chat
    function addMessage(role, content) {
        // Clear placeholder if present
        if (chatMessages.innerHTML.includes('Start a conversation with the chatbot')) {
            chatMessages.innerHTML = '';
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        messageDiv.textContent = content;
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Add source documents
    function addSourceDocuments(sources) {
        const sourceDiv = document.createElement('div');
        sourceDiv.className = 'source-documents';
        
        const sourceTitle = document.createElement('div');
        sourceTitle.className = 'source-document-title';
        sourceTitle.textContent = 'Sources:';
        sourceDiv.appendChild(sourceTitle);
        
        sources.forEach(source => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-document';
            sourceItem.innerHTML = `<strong>${source.file_name}</strong>: ${source.content}...`;
            sourceDiv.appendChild(sourceItem);
        });
        
        chatMessages.appendChild(sourceDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Helper function to get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Check vectorstore on load
    checkVectorStore();
});