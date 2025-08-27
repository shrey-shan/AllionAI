"""
Utility functions for RAG operations
"""
import os
import logging
from typing import List, Dict, Any
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

def get_pdf_files_from_directories(directories: List[str]) -> List[str]:
    """Get all PDF files from specified directories"""
    pdf_files = []
    
    for directory in directories:
        if not os.path.exists(directory):
            logger.warning(f"Directory does not exist: {directory}")
            continue
            
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(root, file))
                        
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
    
    return pdf_files

def calculate_pdf_hash(pdf_path: str) -> str:
    """Calculate hash of PDF file for change detection"""
    try:
        with open(pdf_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {pdf_path}: {e}")
        return ""

def check_pdf_changes(pdf_directory: str, hash_file: str = "./pdf_hashes.json") -> bool:
    """Check if any PDFs have changed since last processing"""
    import json
    
    current_hashes = {}
    pdf_files = get_pdf_files_from_directories(pdf_directory)
    
    for pdf_file in pdf_files:
        current_hashes[pdf_file] = calculate_pdf_hash(pdf_file)
    
    # Load previous hashes
    previous_hashes = {}
    if os.path.exists(hash_file):
        try:
            with open(hash_file, 'r') as f:
                previous_hashes = json.load(f)
        except Exception as e:
            logger.error(f"Error loading hash file: {e}")
    
    # Check for changes
    changed = current_hashes != previous_hashes
    
    if changed:
        # Save current hashes
        try:
            with open(hash_file, 'w') as f:
                json.dump(current_hashes, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving hash file: {e}")
    
    return changed

def format_response_for_voice(response: str, max_length: int = 500) -> str:
    """Format response for voice output (truncate if too long)"""
    if len(response) <= max_length:
        return response
    
    # Try to cut at sentence boundary
    sentences = response.split('. ')
    truncated = ""
    
    for sentence in sentences:
        if len(truncated + sentence + '. ') <= max_length - 20:  # Leave room for ending
            truncated += sentence + '. '
        else:
            break
    
    if truncated:
        return truncated + "Would you like me to provide more details?"
    else:
        # If even first sentence is too long, just truncate
        return response[:max_length-20] + "... Would you like more details?"