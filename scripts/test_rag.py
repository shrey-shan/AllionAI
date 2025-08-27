import asyncio
import os
import sys
from datetime import datetime
import logging
from dotenv import load_dotenv

# Add project root to path to allow imports from src
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
load_dotenv(os.path.join(base_dir, ".env"))

from src.assistant_core import Assistant
from src.rag_capabilities import RepairAssistantStateMachine
from src.configs.rag_config import RAGConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_header():
    """Prints a standard header for the test suite."""
    logger.info("="*60)
    logger.info("🧪 AllionAI RAG Testing Suite")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Python Path: {os.path.dirname(sys.executable)}")
    logger.info(f"Working Directory: {os.getcwd()}")
    logger.info("")

def check_env():
    """Checks and reports on required environment variables and files."""
    logger.info("Environment Check:")
    openai_key = "Set" if os.getenv("OPENAI_API_KEY") else "Not Set"
    logger.info(f"   OPENAI_API_KEY: {openai_key}")

    pdf_dir = RAGConfig.PDF_DIRECTORY
    pdf_dir_exists = os.path.isdir(pdf_dir)
    logger.info(f"   PDF Source Exists ('{pdf_dir}'): {pdf_dir_exists}")
    if not pdf_dir_exists:
        logger.warning("PDF source directory not found. RAG will have no documents.")
    logger.info("")
    return pdf_dir_exists

def log_response_details(response: dict, query: str):
    """Log detailed response information for evaluation"""
    logger.info(f"📋 RESPONSE EVALUATION FOR: '{query}'")
    logger.info("="*50)
    logger.info(f"   Source Type: {response.get('source_type', 'unknown')}")
    logger.info(f"   Confidence: {response.get('confidence', 0.0)}")
    logger.info(f"   Search Attempts: {response.get('search_attempts', 0)}")
    logger.info(f"   Final State: {response.get('state', 'unknown')}")
    logger.info("")
    logger.info("📝 FULL ANSWER:")
    logger.info("-" * 30)
    
    # Split answer into lines for better readability in logs
    answer = response.get('answer', 'No answer provided')
    for line in answer.split('\n'):
        if line.strip():  # Only log non-empty lines
            logger.info(f"   {line}")
    
    logger.info("-" * 30)
    
    # Log additional metadata if available
    if 'error' in response:
        logger.error(f"   ERROR: {response['error']}")
    
    if response.get('source_type') == 'web' and 'web_sources' in response:
        logger.info("   Web Sources Used:")
        for i, source in enumerate(response['web_sources'], 1):
            logger.info(f"   {i}. {source.get('title', 'Unknown')} - {source.get('url', 'No URL')}")
    
    logger.info("="*50)

async def test_rag_standalone():
    """
    Tests the RepairAssistantStateMachine's core functionality directly.
    """
    logger.info("\n--- Running Standalone RAG Test ---\n")
    logger.info("🧪 Testing Standalone RAG State Machine")
    logger.info("="*40)

    test_passed = False
    try:
        logger.info("1. Initializing RAG State Machine...")
        rag_config = RAGConfig()
        rag_manager = RepairAssistantStateMachine(rag_config)
        logger.info("RAG State Machine initialized.")

        logger.info("\n2. Checking health status...")
        health = rag_manager.get_health()
        logger.info(f"   Health: {health}")
        if not health.get("initialized"):
            raise ValueError("RAG manager reports it is not initialized.")
        logger.info("✅ Health status is OK.")

        logger.info("\n3. Performing a direct query...")
        query = "What is a common cause for P0171?"
        logger.info(f"   Query: '{query}'")

        response = await rag_manager.process_query(query)
        
        # Log the detailed response for evaluation
        log_response_details(response, query)

        if not response or not response.get('answer'):
            logger.warning("Query processed but returned no answer.")
        else:
            logger.info("✅ Direct query successful.")

        logger.info("\n✅ Standalone RAG Test Passed!")
        test_passed = True

    except Exception as e:
        logger.error(f"❌ Standalone RAG Test Failed: {e}", exc_info=True)

    return test_passed

async def test_rag_integration():
    """
    Tests that the RAG tools are correctly integrated into the main Assistant agent.
    """
    logger.info("\n--- Running RAG Integration Test ---\n")
    logger.info("🚀 Testing RAG Integration with Main Assistant")
    logger.info("="*50)

    test_passed = False
    try:
        logger.info("1. Initializing Assistant...")
        assistant = Assistant()
        logger.info("Assistant initialized.")

        logger.info("\n2. Checking System Status...")
        status = await assistant.get_system_status()
        logger.info(f"   System status: {status}")

        if not status.get("rag_enabled"):
            logger.warning("RAG is disabled. Skipping integration test.")
            return True

        if not status.get("rag_initialized"):
            raise ValueError("Assistant reports RAG is not initialized.")
        logger.info("✅ System status reports RAG is ready.")

        logger.info("\n3. Checking for RAG tools...")
        tools = assistant.tools
        tool_names = [getattr(t, 'name', str(t)) for t in tools]
        logger.info(f"   Available tools: {tool_names}")

        if "search_documents" not in tool_names:
            logger.warning("`search_documents` tool not found in tools list.")
        else:
            logger.info("✅ `search_documents` tool is present.")

        # Test multiple queries to demonstrate different flows
        logger.info("\n4. Testing repair query processing...")
        
        test_queries = [
            "What causes P0420 code?",
            "How to replace brake pads?",
            "Symptoms of bad oxygen sensor",
            "P0171 diagnostic procedure"
        ]
        
        for i, test_query in enumerate(test_queries, 1):
            logger.info(f"\n   Test Query {i}: '{test_query}'")
            result = await assistant.rag_manager.process_query(test_query)
            
            # Log detailed response for each query
            log_response_details(result, test_query)
            
            if result.get('answer'):
                logger.info(f"✅ Query {i} processed successfully.")
            else:
                logger.warning(f"⚠️  Query {i} returned no answer.")

        logger.info("\n✅ RAG Integration Test Passed!")
        test_passed = True

    except Exception as e:
        logger.error(f"❌ RAG Integration Test Failed: {e}", exc_info=True)

    return test_passed

async def run_evaluation_suite():
    """
    Run a comprehensive evaluation of different query types
    """
    logger.info("\n--- Running Comprehensive Query Evaluation ---\n")
    logger.info("🔍 Testing Various Query Types and State Machine Flows")
    logger.info("="*60)
    
    try:
        assistant = Assistant()
        
        # Test different types of automotive queries
        evaluation_queries = [
            # DTC queries (should hit PDF first, then web if needed)
            ("DTC Query", "What does P0301 mean?"),
            ("DTC Query", "How to diagnose P0420?"),
            
            # Repair procedures (likely to need web search)
            ("Repair Query", "How to replace Honda Civic brake pads?"),
            ("Repair Query", "Toyota Camry oil change procedure"),
            
            # Diagnostic symptoms (should check PDF first)
            ("Symptom Query", "Car stalls at idle"),
            ("Symptom Query", "Engine misfiring symptoms"),
            
            # Non-automotive (should be rejected)
            ("Non-Auto Query", "What is the weather today?"),
            ("Non-Auto Query", "How to cook pasta?"),
        ]
        
        for category, query in evaluation_queries:
            logger.info(f"\n{'='*20} {category.upper()} {'='*20}")
            logger.info(f"Testing: '{query}'")
            
            result = await assistant.rag_manager.process_query(query)
            log_response_details(result, query)
            
            # Add brief analysis
            source = result.get('source_type', 'unknown')
            confidence = result.get('confidence', 0.0)
            
            if source == 'pdf':
                logger.info("🎯 Analysis: Found answer in PDF knowledge base")
            elif source == 'web':
                logger.info("🌐 Analysis: Used web search (PDF insufficient)")
            elif source == 'assistant':
                logger.info("🤖 Analysis: Assistant response (likely non-automotive)")
            else:
                logger.info("❓ Analysis: Unknown source type")
            
            logger.info(f"   Confidence Level: {'High' if confidence > 0.7 else 'Medium' if confidence > 0.4 else 'Low'} ({confidence:.2f})")
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ Comprehensive evaluation completed!")
        
    except Exception as e:
        logger.error(f"❌ Evaluation suite failed: {e}", exc_info=True)

async def main():
    print_header()
    check_env()

    # Run basic tests
    standalone_result = await test_rag_standalone()
    integration_result = await test_rag_integration()
    
    # Run comprehensive evaluation if basic tests pass
    if standalone_result and integration_result:
        await run_evaluation_suite()

    logger.info("="*60)
    logger.info("🎉 All Tests Completed!")
    logger.info(f"   - Standalone RAG Test: {'PASSED' if standalone_result else 'FAILED'}")
    logger.info(f"   - RAG Integration Test: {'PASSED' if integration_result else 'FAILED'}")
    logger.info("="*60)

    if not standalone_result or not integration_result:
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())