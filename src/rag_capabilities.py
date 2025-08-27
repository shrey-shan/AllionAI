#!/usr/bin/env python3
"""
AllionAI State Machine Implementation
=====================================

Key Features:
- PDF-first search strategy (checks local knowledge base first)
- Graceful fallback to web search when PDF search yields no results
- Conversational flow with appropriate user messaging
- Integration with existing RAG capabilities
- State persistence and error handling

State Flow:
1. IDLE -> PROCESSING (when query received)
2. PROCESSING -> PDF_SEARCH (always check local knowledge first)  
3. PDF_SEARCH -> ANSWER_FOUND (if relevant info found in PDFs)
4. PDF_SEARCH -> WEB_SEARCH (if no relevant info in PDFs)
5. WEB_SEARCH -> WEB_SUMMARIZING (processing web results)
6. WEB_SUMMARIZING -> ANSWER_FOUND (providing web-based answer)
7. ANSWER_FOUND -> IDLE (ready for next query)
"""

import asyncio
import logging
import os
import json
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from pathlib import Path
import time
import re
import urllib.parse

# RAG dependencies
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# Web scraping dependencies
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentState(Enum):
    """State machine states"""
    IDLE = auto()
    PROCESSING = auto()
    PDF_SEARCH = auto()
    ANSWER_FOUND = auto()
    WEB_SEARCH = auto()
    WEB_SUMMARIZING = auto()
    ERROR = auto()
    CONVERSATION = auto()


@dataclass
class QueryContext:
    """Context data for query processing"""
    original_query: str
    processed_query: str
    pdf_results: List[Dict[str, Any]] = field(default_factory=list)
    web_results: List[Dict[str, Any]] = field(default_factory=list)
    final_answer: str = ""
    confidence_score: float = 0.0
    source_type: str = "unknown"
    search_attempts: int = 0
    error_message: str = ""
    conversational_context: Dict[str, Any] = field(default_factory=dict)
    
    def reset_for_new_query(self, new_query: str):
        """Reset context for a new query"""
        self.original_query = new_query
        self.processed_query = new_query.strip().lower()
        self.pdf_results = []
        self.web_results = []
        self.final_answer = ""
        self.confidence_score = 0.0
        self.source_type = "unknown"
        self.search_attempts = 0
        self.error_message = ""


class DocumentSearchTool:
    """Real document search tool using vector store"""
    def __init__(self, vectorstore, rag_chain):
        self.name = "search_documents"
        self.vectorstore = vectorstore
        self.rag_chain = rag_chain
    
    async def func(self, query: str) -> str:
        """Real search function using RAG chain"""
        try:
            # Use the RAG chain to get answer
            result = self.rag_chain.invoke(query)
            return result
        except Exception as e:
            logger.error(f"Error in document search: {e}")
            return f"Error searching documents: {str(e)}"


class RepairAssistantStateMachine:
    """
    Main RAG manager that includes state machine functionality.
    This class serves as both the RAG manager and the state machine.
    """
    
    def __init__(self, config=None):
        """Initialize the RAG manager with state machine"""
        # State machine properties
        self.current_state = AgentState.IDLE
        self.previous_state = AgentState.IDLE
        self.context = QueryContext("", "")
        
        # RAG manager properties that tests/assistant expect
        self.config = config
        self._is_ready = False
        self._available_tools = []
        
        # Configuration parameters
        self.pdf_confidence_threshold = 0.7
        self.max_web_results = 5
        self.web_search_timeout = 10
        
        # RAG components
        self.vectorstore = None
        self.rag_chain = None
        
        # State transition handlers
        self.state_handlers = {
            AgentState.IDLE: self._handle_idle,
            AgentState.PROCESSING: self._handle_processing,
            AgentState.PDF_SEARCH: self._handle_pdf_search,
            AgentState.WEB_SEARCH: self._handle_web_search,
            AgentState.WEB_SUMMARIZING: self._handle_web_summarizing,
            AgentState.ANSWER_FOUND: self._handle_answer_found,
            AgentState.ERROR: self._handle_error,
            AgentState.CONVERSATION: self._handle_conversation
        }
        
        # Initialize RAG system
        self._initialize_rag_system()
        
        logger.info("RepairAssistantStateMachine initialized")
    
    def _initialize_rag_system(self):
        """Initialize the real RAG system"""
        try:
            # Get configuration
            if self.config:
                pdf_directory = getattr(self.config, 'PDF_DIRECTORY', 'docs/pdf_source/')
                persist_directory = getattr(self.config, 'PERSIST_DIRECTORY', './vectorstore_multi_pdf')
                chunk_size = getattr(self.config, 'CHUNK_SIZE', 1000)
                chunk_overlap = getattr(self.config, 'CHUNK_OVERLAP', 200)
                search_k = getattr(self.config, 'RAG_SEARCH_K', 3)
            else:
                pdf_directory = 'docs/pdf_source/'
                persist_directory = './vectorstore_multi_pdf'
                chunk_size = 1000
                chunk_overlap = 200
                search_k = 3
            
            # Setup vector store
            self.vectorstore = self._setup_vectorstore(
                pdf_directory=pdf_directory,
                persist_directory=persist_directory,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            if self.vectorstore:
                # Create RAG chain
                self.rag_chain = self._create_rag_chain(search_k=search_k)
                
                # Create document search tool
                doc_search_tool = DocumentSearchTool(self.vectorstore, self.rag_chain)
                self._available_tools = [doc_search_tool]
                
                self._is_ready = True
                logger.info("RAG system initialized successfully")
            else:
                logger.warning("RAG system initialization failed - no vector store")
                self._is_ready = False
                
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            self._is_ready = False
    
    def _setup_vectorstore(self, pdf_directory: str, persist_directory: str, 
                          chunk_size: int, chunk_overlap: int):
        """Setup vector store with document embeddings"""
        try:
            # Check if vector store already exists
            if os.path.exists(persist_directory):
                logger.info("Loading existing vectorstore from disk...")
                vectorstore = Chroma(
                    persist_directory=persist_directory,
                    embedding_function=OpenAIEmbeddings()
                )
                logger.info("Loaded existing vectorstore")
                return vectorstore
            
            # If no existing store, create new one
            logger.info("Creating new vectorstore...")
            
            # Check if PDF directory exists
            if not os.path.exists(pdf_directory):
                logger.warning(f"PDF directory {pdf_directory} does not exist")
                return None
            
            # Load and process PDF documents
            all_docs = []
            pdf_files = [f for f in os.listdir(pdf_directory) if f.endswith('.pdf')]
            
            if not pdf_files:
                logger.warning(f"No PDF files found in {pdf_directory}")
                return None
            
            logger.info(f"Processing {len(pdf_files)} PDF files...")
            
            for pdf_file in pdf_files:
                pdf_path = os.path.join(pdf_directory, pdf_file)
                try:
                    loader = PyMuPDFLoader(pdf_path)
                    docs = loader.load()
                    all_docs.extend(docs)
                    logger.info(f"Loaded {len(docs)} pages from {pdf_file}")
                except Exception as e:
                    logger.error(f"Error loading {pdf_file}: {e}")
                    continue
            
            if not all_docs:
                logger.warning("No documents were successfully loaded")
                return None
            
            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap
            )
            splits = text_splitter.split_documents(all_docs)
            logger.info(f"Created {len(splits)} document chunks")
            
            # Create and persist vector store
            vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=OpenAIEmbeddings(),
                persist_directory=persist_directory
            )
            vectorstore.persist()
            logger.info("Created and persisted new vectorstore")
            
            return vectorstore
            
        except Exception as e:
            logger.error(f"Error setting up vectorstore: {e}")
            return None
    
    def _create_rag_chain(self, search_k: int = 3):
        """Create RAG chain for question answering"""
        try:
            # Setup retriever
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": search_k})
            
            # Create prompt template for automotive repair
            template = """You are an expert automotive diagnostic technician and repair specialist.
Use the following context from technical service bulletins, repair manuals, and diagnostic procedures to provide a clear and complete answer.

Context: {context}
Question: {question}

Instructions:
- Focus on automotive diagnostic and repair information
- Provide specific, actionable guidance when possible
- Include relevant diagnostic trouble codes (DTCs) if applicable
- Mention safety considerations when relevant
- If the context doesn't contain enough information, say so clearly
- Be concise but thorough

Answer:"""
            
            prompt = ChatPromptTemplate.from_template(template)
            
            # Setup LLM
            model_name = "gpt-3.5-turbo"
            if self.config and hasattr(self.config, 'OPENAI_MODEL'):
                model_name = self.config.OPENAI_MODEL
                
            temperature = 0.0
            if self.config and hasattr(self.config, 'OPENAI_TEMPERATURE'):
                temperature = self.config.OPENAI_TEMPERATURE
                
            llm = ChatOpenAI(model_name=model_name, temperature=temperature)
            
            # Document formatting function
            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)
            
            # Create RAG chain
            rag_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )
            
            logger.info("RAG chain created successfully")
            return rag_chain
            
        except Exception as e:
            logger.error(f"Error creating RAG chain: {e}")
            return None
    
    @property
    def is_ready(self) -> bool:
        """Check if RAG manager is ready"""
        return self._is_ready
    
    @property
    def available_tools(self) -> List[Any]:
        """Get available tools"""
        return self._available_tools
    
    def get_health(self) -> Dict[str, Any]:
        """
        Get health status - this is what your tests expect
        """
        return {
            "status": "ok" if self._is_ready else "not_ready",
            "initialized": self._is_ready,
            "current_state": self.current_state.name,
            "tools_available": len(self._available_tools),
            "config_loaded": self.config is not None,
            "vectorstore_ready": self.vectorstore is not None,
            "rag_chain_ready": self.rag_chain is not None
        }
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Main entry point for processing queries through state machine
        """
        logger.info(f"Processing new query: {user_query}")
        
        # Reset context for new query
        self.context.reset_for_new_query(user_query)
        
        # Start the state machine
        await self._transition_to_state(AgentState.PROCESSING)
        
        # Run the state machine until terminal state
        while self.current_state not in [AgentState.IDLE, AgentState.ERROR]:
            try:
                await self._execute_current_state()
            except Exception as e:
                logger.error(f"Error in state {self.current_state}: {e}")
                self.context.error_message = str(e)
                await self._transition_to_state(AgentState.ERROR)
        
        return self._build_response()
    
    async def _execute_current_state(self):
        """Execute handler for current state"""
        handler = self.state_handlers.get(self.current_state)
        if handler:
            await handler()
        else:
            logger.error(f"No handler found for state: {self.current_state}")
            await self._transition_to_state(AgentState.ERROR)
    
    async def _transition_to_state(self, new_state: AgentState):
        """Transition between states"""
        logger.info(f"State transition: {self.current_state.name} -> {new_state.name}")
        self.previous_state = self.current_state
        self.current_state = new_state
    
    # State handlers
    async def _handle_idle(self):
        """Handle IDLE state"""
        pass
    
    async def _handle_processing(self):
        """Handle PROCESSING state"""
        logger.info("Processing user query...")
        
        # Clean and validate query
        self.context.processed_query = self._clean_query(self.context.original_query)
        
        if not self._is_valid_automotive_query(self.context.processed_query):
            self.context.final_answer = (
                "I specialize in automotive diagnostics and repair. "
                "Could you please ask me about a specific vehicle problem, "
                "diagnostic trouble code (DTC), or repair procedure?"
            )
            self.context.source_type = "assistant"
            await self._transition_to_state(AgentState.ANSWER_FOUND)
            return
        
        # Valid automotive query - proceed to PDF search
        await self._transition_to_state(AgentState.PDF_SEARCH)
    
    async def _handle_pdf_search(self):
        """Handle PDF_SEARCH state"""
        logger.info("Searching PDF knowledge base...")
        
        self.context.search_attempts += 1
        
        # Check if RAG system is ready
        if not self.is_ready or not self.available_tools:
            logger.warning("RAG system not ready - proceeding to web search")
            await self._transition_to_state(AgentState.WEB_SEARCH)
            return
        
        try:
            # Find search tool
            search_tool = next((tool for tool in self.available_tools 
                              if tool.name == "search_documents"), None)
            
            if not search_tool:
                logger.warning("search_documents tool not available - proceeding to web search")
                await self._transition_to_state(AgentState.WEB_SEARCH)
                return
            
            # Execute search using real RAG chain
            logger.info(f"Executing PDF search for: {self.context.processed_query}")
            pdf_result = await search_tool.func(self.context.processed_query)
            
            # Process results
            if self._is_pdf_result_sufficient(pdf_result):
                logger.info("Found sufficient information in PDF knowledge base")
                self.context.final_answer = self._format_pdf_answer(pdf_result)
                self.context.source_type = "pdf"
                self.context.confidence_score = self._calculate_pdf_confidence(pdf_result)
                await self._transition_to_state(AgentState.ANSWER_FOUND)
            else:
                logger.info("PDF search insufficient - proceeding to web search")
                await self._transition_to_state(AgentState.WEB_SEARCH)
                
        except Exception as e:
            logger.error(f"Error during PDF search: {e}")
            await self._transition_to_state(AgentState.WEB_SEARCH)
    
    async def _handle_web_search(self):
        """Handle WEB_SEARCH state"""
        logger.info("Searching web for additional information...")
        
        try:
            # Perform mock web search for now (you can replace with real web search)
            web_results = await self._perform_mock_web_search(self.context.processed_query)
            self.context.web_results = web_results
            
            if web_results:
                logger.info(f"Found {len(web_results)} web results")
                await self._transition_to_state(AgentState.WEB_SUMMARIZING)
            else:
                logger.warning("No web results found")
                self.context.final_answer = (
                    "I searched both my internal knowledge base and the internet, "
                    "but couldn't find specific information about this issue. "
                    "Could you provide more details about the symptoms?"
                )
                self.context.source_type = "assistant"
                await self._transition_to_state(AgentState.ANSWER_FOUND)
                
        except Exception as e:
            logger.error(f"Error during web search: {e}")
            self.context.error_message = str(e)
            await self._transition_to_state(AgentState.ERROR)
    
    async def _handle_web_summarizing(self):
        """Handle WEB_SUMMARIZING state"""
        logger.info("Summarizing web search results...")
        
        try:
            summary = await self._summarize_web_results(self.context.web_results)
            self.context.final_answer = self._format_web_answer(summary, self.context.web_results)
            self.context.source_type = "web"
            self.context.confidence_score = self._calculate_web_confidence(self.context.web_results)
            
            logger.info("Web summarization completed")
            await self._transition_to_state(AgentState.ANSWER_FOUND)
            
        except Exception as e:
            logger.error(f"Error during web summarization: {e}")
            self.context.error_message = str(e)
            await self._transition_to_state(AgentState.ERROR)
    
    async def _handle_answer_found(self):
        """Handle ANSWER_FOUND state"""
        logger.info(f"Answer found from {self.context.source_type} with confidence {self.context.confidence_score}")
        
        if self.context.source_type == "web":
            web_note = "\n\nI found this information from current online repair resources."
            self.context.final_answer = self.context.final_answer + web_note
        
        await self._transition_to_state(AgentState.IDLE)
    
    async def _handle_error(self):
        """Handle ERROR state"""
        logger.error(f"Handling error state: {self.context.error_message}")
        
        self.context.final_answer = (
            "I encountered an issue while searching for information about your question. "
            "Could you try rephrasing your question or provide more specific details?"
        )
        self.context.source_type = "error"
        
        await self._transition_to_state(AgentState.IDLE)
    
    async def _handle_conversation(self):
        """Handle CONVERSATION state"""
        await self._transition_to_state(AgentState.PROCESSING)
    
    # Utility methods
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query"""
        cleaned = re.sub(r'\s+', ' ', query.strip())
        
        # Handle DTC codes
        dtc_pattern = r'\b[BPCU]\d{4}\b'
        dtc_matches = re.findall(dtc_pattern, query.upper())
        
        if dtc_matches:
            for dtc in dtc_matches:
                cleaned = cleaned.replace(dtc.lower(), dtc.upper())
        
        return cleaned
    
    def _is_valid_automotive_query(self, query: str) -> bool:
        """Check if query is automotive-related"""
        automotive_keywords = [
            'dtc', 'code', 'p0', 'p1', 'b0', 'u0', 'c0',
            'engine', 'brake', 'transmission', 'abs', 'airbag',
            'check engine light', 'cel', 'mil', 'obd', 'diagnostic',
            'repair', 'fix', 'problem', 'issue', 'symptom',
            'car', 'vehicle', 'truck', 'suv', 'automotive'
        ]
        
        dtc_pattern = r'\b[BPCU]\d{4}\b'
        
        if re.search(dtc_pattern, query.upper()):
            return True
        
        query_lower = query.lower()
        for keyword in automotive_keywords:
            if keyword in query_lower:
                return True
        
        return len(query.split()) <= 3  # Short queries might be valid
    
    def _is_pdf_result_sufficient(self, pdf_result: str) -> bool:
        """Check if PDF results are sufficient"""
        if not pdf_result or len(pdf_result.strip()) < 50:
            return False
        
        insufficient_indicators = [
            "could not find any relevant information",
            "no relevant documents found",
            "no matching content",
            "unable to locate",
            "not found in knowledge base",
            "context doesn't contain enough information",
            "i don't know"
        ]
        
        pdf_result_lower = pdf_result.lower()
        for indicator in insufficient_indicators:
            if indicator in pdf_result_lower:
                return False
        
        return True
    
    def _format_pdf_answer(self, pdf_result: str) -> str:
        """Format PDF search results"""
        return f"Based on my technical service bulletins and diagnostic procedures:\n\n{pdf_result}"
    
    def _calculate_pdf_confidence(self, pdf_result: str) -> float:
        """Calculate PDF result confidence"""
        if not pdf_result:
            return 0.0
        
        result_length = len(pdf_result)
        
        # Higher confidence for longer, more detailed answers
        if result_length > 500:
            return 0.9
        elif result_length > 200:
            return 0.7
        elif result_length > 100:
            return 0.5
        else:
            return 0.3
    
    async def _perform_mock_web_search(self, query: str) -> List[Dict[str, Any]]:
        """Mock web search for testing (replace with real implementation)"""
        return [
            {
                'title': f'Mock result for {query}',
                'url': 'https://example.com/mock-result',
                'snippet': f'This is a mock web search result for the query: {query}',
                'is_trusted': True
            }
        ]
    
    async def _summarize_web_results(self, web_results: List[Dict[str, Any]]) -> str:
        """Summarize web results"""
        if not web_results:
            return "No web results to summarize."
        
        summary = "Based on current online repair resources:\n\n"
        for i, result in enumerate(web_results[:3], 1):
            snippet = result.get('snippet', '')
            summary += f"{i}. {snippet}\n"
        
        return summary
    
    def _format_web_answer(self, summary: str, web_results: List[Dict[str, Any]]) -> str:
        """Format web answer with links"""
        formatted_answer = summary + "\n\nSources:\n"
        
        for i, result in enumerate(web_results[:3], 1):
            title = result.get('title', 'Repair Resource')
            url = result.get('url', '')
            if url:
                formatted_answer += f"{i}. [{title}]({url})\n"
        
        return formatted_answer
    
    def _calculate_web_confidence(self, web_results: List[Dict[str, Any]]) -> float:
        """Calculate web result confidence"""
        if not web_results:
            return 0.0
        
        num_results = len(web_results)
        trusted_count = sum(1 for result in web_results if result.get('is_trusted'))
        
        base_confidence = min(num_results * 0.15, 0.6)
        trusted_bonus = trusted_count * 0.1
        
        return min(base_confidence + trusted_bonus, 0.8)
    
    def _build_response(self) -> Dict[str, Any]:
        """Build final response"""
        response = {
            'answer': self.context.final_answer,
            'source_type': self.context.source_type,
            'confidence': self.context.confidence_score,
            'query': self.context.original_query,
            'processed_query': self.context.processed_query,
            'state': self.current_state.name,
            'search_attempts': self.context.search_attempts,
            'timestamp': time.time()
        }
        
        if self.context.error_message:
            response['error'] = self.context.error_message
        
        return response
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get state machine information"""
        return {
            'current_state': self.current_state.name,
            'previous_state': self.previous_state.name,
            'is_ready': self.is_ready,
            'tools_available': len(self.available_tools),
            'context_query': self.context.original_query,
            'search_attempts': self.context.search_attempts,
            'vectorstore_ready': self.vectorstore is not None,
            'rag_chain_ready': self.rag_chain is not None
        }


# For backward compatibility, create a wrapper that matches your test expectations
class StateManagerWrapper:
    """
    Wrapper that provides the state_machine attribute your tests expect
    """
    def __init__(self, config=None):
        self.state_machine = RepairAssistantStateMachine(config)
        logger.info("StateManagerWrapper initialized with state_machine")
    
    @property
    def available_tools(self):
        return self.state_machine.available_tools
    
    @property
    def is_ready(self):
        return self.state_machine.is_ready
    
    def get_health(self):
        return self.state_machine.get_health()