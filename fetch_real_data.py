#!/usr/bin/env python
"""Script to fetch real data from Zotero and add it to the ChromaDB database for Z-Cite Streamlit application."""

import os
import sys
from dotenv import load_dotenv

from z_cite_streamlit.db import ChromaDBManager
from z_cite_streamlit.document import DocumentProcessor
from z_cite_streamlit.ocr import OCRManager
from z_cite_streamlit.zotero import ZoteroManager


def get_db_path_non_streamlit() -> str:
    """Get the path to the ChromaDB database without using Streamlit.
    
    Returns:
        Path to the ChromaDB database.
    """
    # Default path
    default_path = os.path.join(os.path.expanduser("~"), ".z_cite", "chroma_db")
    
    # Create directory if it doesn't exist
    os.makedirs(default_path, exist_ok=True)
    
    return default_path


def fetch_real_data():
    """Fetch real data from Zotero and add it to the ChromaDB database."""
    print("Fetching real data from Zotero and adding to ChromaDB...")
    
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment
    zotero_api_key = os.environ.get("ZOTERO_API_KEY")
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    
    if not zotero_api_key:
        print("Error: ZOTERO_API_KEY not found in environment variables.")
        print("Please set the ZOTERO_API_KEY environment variable or create a .env file.")
        return
    
    # Initialize managers
    db_path = get_db_path_non_streamlit()
    db_manager = ChromaDBManager(db_path=db_path)
    zotero_manager = ZoteroManager(api_key=zotero_api_key, default_group_id="5140532")
    ocr_manager = OCRManager(api_key=google_api_key)
    
    # Initialize document processor
    document_processor = DocumentProcessor(
        db_manager=db_manager,
        zotero_manager=zotero_manager,
        ocr_manager=ocr_manager
    )
    
    # Test Zotero connection
    if not zotero_manager.test_connection():
        print("Error: Could not connect to Zotero API. Please check your API key.")
        return
    
    print("Connected to Zotero API successfully.")
    
    # Get libraries
    libraries = zotero_manager.get_libraries()
    
    if not libraries:
        print("No libraries found. Make sure your API key has access to group libraries.")
        return
    
    print(f"Found {len(libraries)} libraries.")
    
    # Process the Climate Crimes library
    climate_crimes_lib = next((lib for lib in libraries if lib["library_id"] == "5140532"), None)
    
    if not climate_crimes_lib:
        print("Climate Crimes library not found.")
        return
    
    print(f"Processing library: {climate_crimes_lib['name']}")
    
    # Add the library to ChromaDB
    document_processor.add_library(climate_crimes_lib)
    
    # Define progress callback
    def progress_callback(index, total, document_title, stage):
        print(f"Processing {index+1}/{total}: {document_title} ({stage})")
    
    # Process the library (limit to 5 documents for testing)
    library_type = climate_crimes_lib["library_type"]
    library_id = climate_crimes_lib["library_id"]
    
    print(f"Fetching documents from {library_type} library {library_id}...")
    
    # Process the library
    total, processed, errors = document_processor.process_library(
        library_type, library_id, progress_callback, limit=5
    )
    
    print(f"Processing complete! Processed {processed} documents.")
    
    if errors:
        print(f"Encountered {len(errors)} errors:")
        for error in errors:
            print(f"  - {error}")
    
    print(f"Database statistics: {db_manager.get_statistics()}")


if __name__ == "__main__":
    fetch_real_data()