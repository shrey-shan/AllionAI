"""
API endpoints for RAG functionality
Can be used for testing and direct access to RAG features
"""
import sys
import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Add project root to the Python path to allow importing from the 'src' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Assuming these are the correct components based on imports in other files
from src.rag_capabilities import RepairAssistantStateMachine
from src.configs.rag_config import RAGConfig

app = FastAPI(title="RAG API", description="API for RAG functionality")

# Initialize the RAG Manager
rag_manager = RepairAssistantStateMachine()
rag_manager_initialized = False

class QueryRequest(BaseModel):
    query: str
    use_internet_fallback: Optional[bool] = True

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    search_path: List[str]
    confidence: float
    timestamp: str

@app.on_event("startup")
async def startup_event():
    """Initialize RAG manager on startup"""
    global rag_manager_initialized
    await rag_manager.initialize()
    rag_manager_initialized = True

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Query the RAG system directly"""
    try:
        if not rag_manager_initialized:
            raise HTTPException(status_code=503, detail="RAG system is not initialized yet.")

        response = await rag_manager.state_machine.process_query(request.query)
        
        return QueryResponse(
            answer=response.answer,
            sources=response.sources,
            search_path=[state.value for state in response.search_path],
            confidence=response.confidence,
            timestamp=response.timestamp
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "rag_initialized": rag_manager_initialized,
        "timestamp": rag_manager.state_machine.search_path[-1].value if rag_manager_initialized and rag_manager.state_machine.search_path else "not_initialized"
    }

@app.post("/initialize")
async def initialize_rag():
    """Manually initialize or reinitialize the RAG system"""
    global rag_manager_initialized
    try:
        await rag_manager.initialize()
        rag_manager_initialized = True
        return {"success": True, "message": "RAG system initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initialization error: {str(e)}")

@app.get("/pdf-status")
async def get_pdf_status():
    """Get status of loaded PDFs"""
    global rag_manager_initialized
    try:
        if not rag_manager_initialized:
            return {"status": "not_initialized", "pdfs": ""}
        
        # Get vectorstore info
        vectorstore = rag_manager.vectorstore
        if vectorstore:
            collection = vectorstore._collection
            count = collection.count()
            return {
                "status": "initialized",
                "document_count": count,
                "pdf_directory": RAGConfig.PDF_DIRECTORY
            }
        else:
            return {"status": "no_vectorstore", "pdfs": []}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting PDF status: {str(e)}")
