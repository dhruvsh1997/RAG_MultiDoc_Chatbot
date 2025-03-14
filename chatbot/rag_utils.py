import os
import pickle
import tempfile
import uuid
from django.conf import settings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from django.db import transaction

from .models import Document, VectorStore, DocumentVectorMapping

def load_pdf(file_path):
    """Load a PDF file"""
    loader = PyPDFLoader(file_path)
    return loader.load()

def split_documents(documents):
    """Split documents into chunks"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)
    return chunks

def create_vectorstore(chunks):
    """Create a vector store from document chunks"""
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    return vectorstore

def setup_llm(api_key):
    """Set up the Groq LLM"""
    return ChatGroq(
        model_name="llama-3.3-70b-versatile",
        temperature=0.3,
        groq_api_key=api_key
    )

def create_rag_chain(llm, vectorstore):
    """Create a RAG chain for question answering"""
    template = """
    Use the following pieces of context to answer the question at the end.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    
    Context: {context}
    
    Question: {question}
    
    Answer:
    """
    
    QA_CHAIN_PROMPT = PromptTemplate(
        input_variables=["context", "question"],
        template=template,
    )
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
        chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
        return_source_documents=True
    )
    
    return qa_chain

def save_vectorstore(vectorstore, path):
    """Save vector store to disk"""
    with open(path, "wb") as f:
        pickle.dump(vectorstore, f)

def load_vectorstore(path):
    """Load vector store from disk"""
    if not os.path.exists(path):
        return None
        
    with open(path, "rb") as f:
        vectorstore = pickle.load(f)
    return vectorstore

def process_document(document, vector_store_path=None):
    """Process a document and create/update vector store"""
    # Get the path to the uploaded file
    file_path = document.file.path
    
    # Load the document
    documents = load_pdf(file_path)
    
    # Split the document into chunks
    chunks = split_documents(documents)
    
    # Add document metadata to chunks
    for chunk in chunks:
        chunk.metadata["document_id"] = document.id
        chunk.metadata["original_file_name"] = os.path.basename(file_path)
    
    # Check if vector store already exists
    if vector_store_path and os.path.exists(vector_store_path):
        # Load existing vector store
        vectorstore = load_vectorstore(vector_store_path)
        # Add new document chunks to existing vector store
        vectorstore.add_documents(chunks)
    else:
        # Create new vector store
        vectorstore = create_vectorstore(chunks)
        
        # Generate a new vector store path if none was provided
        if not vector_store_path:
            vector_store_path = os.path.join(settings.VECTORS_DIR, f"vector_store_{uuid.uuid4()}.pkl")
    
    # Save the updated vector store
    save_vectorstore(vectorstore, vector_store_path)
    
    return vectorstore, vector_store_path

@transaction.atomic
def process_uploaded_document(document):
    """Process an uploaded document and update the vector store"""
    # Get the active vector store or create a new one
    vector_store = VectorStore.objects.filter(is_active=True).first()
    
    if vector_store:
        vector_store_path = vector_store.file_path
    else:
        vector_store_path = os.path.join(settings.VECTORS_DIR, f"vector_store_{uuid.uuid4()}.pkl")
        vector_store = VectorStore.objects.create(file_path=vector_store_path)
    
    # Process the document
    vectorstore, updated_path = process_document(document, vector_store_path)
    
    # Update the vector store path if it changed
    if updated_path != vector_store_path:
        vector_store.file_path = updated_path
        vector_store.save()
    
    # Create mapping between document and vector store
    DocumentVectorMapping.objects.create(
        document=document,
        vector_store=vector_store
    )
    
    return vectorstore, vector_store

def get_answer(question, groq_api_key):
    """Get an answer to a question using the active vector store"""
    # Get the active vector store
    vector_store = VectorStore.objects.filter(is_active=True).first()
    
    if not vector_store or not os.path.exists(vector_store.file_path):
        return {
            "answer": "I don't have any documents to search through. Please upload a document first.",
            "source_documents": []
        }
    
    # Load the vector store
    vectorstore = load_vectorstore(vector_store.file_path)
    
    # Set up the LLM and RAG chain
    llm = setup_llm(groq_api_key)
    qa_chain = create_rag_chain(llm, vectorstore)
    
    # Get the answer
    result = qa_chain({"query": question})
    
    # Find source documents
    source_docs = vectorstore.similarity_search(question, k=3)
    
    # Prepare source document details
    source_doc_details = []
    
    for doc in source_docs:
        if 'document_id' in doc.metadata:
            document_id = doc.metadata['document_id']
            try:
                document = Document.objects.get(id=document_id)
                source_doc_details.append({
                    "document_id": document_id,
                    "file_name": document.title,
                    "content": doc.page_content[:200]  # First 200 chars preview
                })
            except Document.DoesNotExist:
                # Document may have been deleted
                continue
    
    return {
        "answer": result["result"],
        "source_documents": source_doc_details[:2]  # Limit to 2 source documents
    }