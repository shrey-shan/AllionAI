"""
Configuration settings for RAG Agent
"""
import os
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class RAGConfig:
    """Configuration class for RAG settings"""
    
    # Vector store settings
    PERSIST_DIRECTORY: str = "./vectorstore_multi_pdf"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # Search settings
    RAG_SEARCH_K: int = 3  # Number of documents to retrieve
    CONFIDENCE_THRESHOLD: float = 0.5  # Minimum confidence for RAG results
    
    # PDF directories
    PDF_DIRECTORY: str = "docs/pdf_source/"
    
    # OpenAI settings
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_TEMPERATURE: float = 0.0
    
    # Internet search settings
    ENABLE_INTERNET_SEARCH: bool = True
    INTERNET_SEARCH_MAX_RESULTS: int = 5
    BRAVE_SEARCH_API_KEY: str = None
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_QUERIES: bool = True

    # Additional stuff
    COLLECTION_NAME: str = "allion_docs"
    VECTOR_STORE_PATH: str = "./data/chroma_db"
    
    def __init__(self):
        self.embedding_model = "gpt-3.5-turbo"
    
    def __post_init__(self):
            
        if self.BRAVE_SEARCH_API_KEY is None:
            self.BRAVE_SEARCH_API_KEY = os.getenv('BRAVE_SEARCH_API_KEY', '')