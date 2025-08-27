import os
import sys
import logging
from dotenv import load_dotenv

# Add project root to path to allow imports from src
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
load_dotenv(os.path.join(base_dir, ".env"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_rag_vectorstore():
    """
    Initializes the RAG system by processing source documents and building the vector store.
    This is a one-time setup script to be run before starting the agent.
    """
    logger.info("="*60)
    logger.info("🚀 Starting RAG Vector Store Setup Process")
    logger.info("="*60)

    try:
        # These imports are inside the function to ensure the path is set up first
        from src.configs.rag_config import RAGConfig
        from src.rag_capabilities import RepairAssistantStateMachine

        logger.info("   - Loading RAG configuration...")
        rag_config = RAGConfig()

        if not getattr(rag_config, 'RAG_ENABLED', True):
            logger.warning("   - RAG is disabled in the configuration. Exiting setup.")
            return

        pdf_dir = RAGConfig.PDF_DIRECTORY
        if not os.path.isdir(pdf_dir):
            logger.error(f"   - PDF source directory not found at '{pdf_dir}'.")
            logger.error("   - Please create the directory and add your PDF files.")
            return

        logger.info("   - Initializing RAG State Machine to build the vector store...")
        logger.info("   - This may take a few minutes depending on the number of documents...")
        
        state_machine = RepairAssistantStateMachine(rag_config)
        
        logger.info("   - RAG State Machine initialized. Verifying setup...")
        health = state_machine.get_health()
        logger.info(f"   - Health check result: {health}")
        if health.get("initialized"):
            logger.info("✅ RAG setup completed successfully. Vector store is ready.")
        else:
            logger.error("❌ RAG setup failed. The system did not initialize correctly.")

    except ImportError as e:
        logger.error(f"Failed to import a required module: {e}")
        logger.error("Please ensure all dependencies from requirements.txt and requirements_rag.txt are installed.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during RAG setup: {e}", exc_info=True)

    logger.info("="*60)

if __name__ == "__main__":
    setup_rag_vectorstore()