"""Z-Cite Streamlit Application for semantic search of Zotero libraries."""

import os
import sys
from typing import Dict, List, Optional
import tempfile

import streamlit as st

from z_cite_streamlit.db import ChromaDBManager
from z_cite_streamlit.document import DocumentProcessor
from z_cite_streamlit.ocr import OCRManager
from z_cite_streamlit.search import SearchManager
from z_cite_streamlit.utils import (
    get_db_path, get_setting, highlight_text, save_settings, format_timestamp
)
from z_cite_streamlit.zotero import ZoteroManager


# Set page configuration
st.set_page_config(
    page_title="Z-Cite Semantic Search",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_session_state():
    """Initialize session state variables."""
    if "db_manager" not in st.session_state:
        db_path = get_db_path()
        st.session_state.db_manager = ChromaDBManager(db_path=db_path)
    
    if "search_manager" not in st.session_state:
        st.session_state.search_manager = SearchManager(db_manager=st.session_state.db_manager)
    
    if "zotero_manager" not in st.session_state:
        zotero_api_key = os.environ.get("ZOTERO_API_KEY", "")
        # Use the Climate Crimes library as the default
        st.session_state.zotero_manager = ZoteroManager(api_key=zotero_api_key, default_group_id="5140532")
    
    if "ocr_manager" not in st.session_state:
        google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        st.session_state.ocr_manager = OCRManager(api_key=google_api_key)
    
    if "document_processor" not in st.session_state:
        st.session_state.document_processor = DocumentProcessor(
            db_manager=st.session_state.db_manager,
            zotero_manager=st.session_state.zotero_manager,
            ocr_manager=st.session_state.ocr_manager
        )
    
    # Initialize settings with defaults if not already set
    defaults = {
        "auto_update": True,
        "threshold": 0.7,
        "results_limit": 10,
        "selected_libraries": ["group_5140532"],  # Default to Climate Crimes library
        "zotero_api_key": "",
        "google_api_key": "",
        "chunk_size": 512,
        "chunk_overlap": 50,
        "store_ocr": True,
        "use_stored_ocr": True,
        "always_rerun_ocr": False,
        "processing_libraries": [],
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_header():
    """Render the application header."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("Z-Cite Semantic Search")
    
    with col2:
        st.checkbox(
            "Auto-update on startup",
            value=get_setting("auto_update", True),
            key="auto_update_checkbox",
            on_change=lambda: save_settings({"auto_update": st.session_state.auto_update_checkbox}),
        )


def render_tabs():
    """Render the application tabs."""
    tab1, tab2, tab3 = st.tabs(["Search", "Libraries", "Settings"])
    
    with tab1:
        render_search_tab()
    
    with tab2:
        render_libraries_tab()
    
    with tab3:
        render_settings_tab()


def render_search_tab():
    """Render the search tab."""
    # Search query input
    query = st.text_input("Search Query:", key="search_query")
    
    # Advanced options (collapsible)
    with st.expander("Advanced Options", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            threshold = st.slider(
                "Threshold:",
                min_value=0.0,
                max_value=1.0,
                value=get_setting("threshold", 0.7),
                step=0.05,
                format="%.2f",
                key="threshold_slider",
                on_change=lambda: save_settings({"threshold": st.session_state.threshold_slider}),
            )
        
        with col2:
            results_limit = st.number_input(
                "Results limit:",
                min_value=1,
                max_value=100,
                value=get_setting("results_limit", 10),
                step=1,
                key="results_limit_input",
                on_change=lambda: save_settings({"results_limit": st.session_state.results_limit_input}),
            )
        
        # Libraries to search (if any are available)
        libraries = st.session_state.db_manager.get_libraries()
        if libraries:
            st.write("Libraries to search:")
            selected_libraries = []
            
            for lib in libraries:
                lib_id = lib["id"]
                lib_name = lib["metadata"].get("name", lib_id)
                lib_type = lib["metadata"].get("library_type", "unknown")
                
                if st.checkbox(
                    f"{lib_name} ({lib_type})",
                    value=lib_id in get_setting("selected_libraries", []),
                    key=f"lib_checkbox_{lib_id}",
                ):
                    selected_libraries.append(lib_id)
            
            # Update selected libraries in session state
            save_settings({"selected_libraries": selected_libraries})
    
    # Search button
    if st.button("Search", key="search_button"):
        if not query:
            st.warning("Please enter a search query.")
            return
        
        with st.spinner("Searching..."):
            # Get search parameters
            threshold = get_setting("threshold", 0.7)
            results_limit = get_setting("results_limit", 10)
            selected_libraries = get_setting("selected_libraries", [])
            
            # Perform search
            results = st.session_state.search_manager.search(
                query=query,
                n_results=results_limit,
                threshold=threshold,
                library_ids=selected_libraries if selected_libraries else None,
            )
            
            # Format results for display
            formatted_results = st.session_state.search_manager.format_results(results)
            
            # Store results in session state
            st.session_state.search_results = formatted_results
    
    # Display results if available
    if "search_results" in st.session_state and st.session_state.search_results:
        st.write("## Results")
        
        if not st.session_state.search_results:
            st.info("No results found. Try adjusting your search query or lowering the threshold.")
            return
        
        # Display each result
        for i, result in enumerate(st.session_state.search_results):
            with st.container():
                st.write(f"### {result['title']} by {result['authors']}")
                st.write(f"**{result['similarity']}% Match**")
                
                # Display metadata
                metadata = []
                if result['metadata'].get('document_type'):
                    metadata.append(f"Type: {result['metadata']['document_type']}")
                if result['metadata'].get('publication_date'):
                    metadata.append(f"Date: {result['metadata']['publication_date']}")
                if result['metadata'].get('page_number'):
                    metadata.append(f"Page: {result['metadata']['page_number']}")
                
                if metadata:
                    st.write(" | ".join(metadata))
                
                # Display highlighted text
                st.markdown(highlight_text(result["text"], st.session_state.search_query))
                
                st.divider()
    elif "search_results" in st.session_state and not st.session_state.search_results:
        st.info("No results found. Try adjusting your search query or lowering the threshold.")


def render_libraries_tab():
    """Render the libraries tab."""
    st.write("## Library Management")
    
    # Zotero API key input
    zotero_api_key = st.text_input(
        "Zotero API Key:", 
        type="password", 
        value=get_setting("zotero_api_key", ""),
        key="zotero_api_key_input",
        help="Your Zotero API key. You can find this in your Zotero account settings."
    )
    
    # Save API key to session state and reinitialize Zotero manager if changed
    if zotero_api_key != get_setting("zotero_api_key", ""):
        save_settings({"zotero_api_key": zotero_api_key})
        st.session_state.zotero_manager.initialize(zotero_api_key)
        # Also set environment variable for persistence
        os.environ["ZOTERO_API_KEY"] = zotero_api_key
    
    # Test connection button
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Test Connection", key="test_zotero_connection"):
            if st.session_state.zotero_manager.test_connection():
                st.success("Connection successful!")
            else:
                st.error("Connection failed. Please check your API key.")
    
    # Fetch libraries button
    if st.button("Fetch Libraries", key="fetch_libraries_button"):
        if not zotero_api_key:
            st.warning("Please enter your Zotero API key.")
        else:
            with st.spinner("Fetching libraries..."):
                libraries = st.session_state.zotero_manager.get_libraries()
                
                if not libraries:
                    st.warning("No group libraries found or connection failed. Make sure your API key has access to group libraries.")
                else:
                    # Store libraries in session state
                    st.session_state.zotero_libraries = libraries
                    st.success(f"Found {len(libraries)} libraries.")
    
    # Library selection
    st.write("### Available Libraries")
    
    if "zotero_libraries" in st.session_state and st.session_state.zotero_libraries:
        # Get existing libraries from ChromaDB
        existing_libraries = {lib["id"]: lib for lib in st.session_state.db_manager.get_libraries()}
        
        # Display libraries with checkboxes
        selected_libraries = []
        for lib in st.session_state.zotero_libraries:
            lib_id = lib["id"]
            lib_name = lib["name"]
            lib_type = lib["library_type"]
            is_default = lib.get("is_default", False)
            
            # Check if library exists in ChromaDB
            exists_in_db = lib_id in existing_libraries
            
            # Add a marker for the Climate Crimes library
            climate_crimes_marker = " (Default)" if lib_id == "group_5140532" else ""
            
            # Add status indicator
            status = "✅ Indexed" if exists_in_db else "❌ Not indexed"
            
            # Display checkbox with library info
            if st.checkbox(
                f"{lib_name}{climate_crimes_marker} - {status}",
                value=lib_id in get_setting("processing_libraries", []),
                key=f"lib_checkbox_{lib_id}"
            ):
                selected_libraries.append(lib_id)
        
        # Update selected libraries in session state
        save_settings({"processing_libraries": selected_libraries})
        
        # Select/Deselect All buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select All", key="select_all_libraries"):
                for lib in st.session_state.zotero_libraries:
                    st.session_state[f"lib_checkbox_{lib['id']}"] = True
                save_settings({"processing_libraries": [lib["id"] for lib in st.session_state.zotero_libraries]})
                st.rerun()
        
        with col2:
            if st.button("Deselect All", key="deselect_all_libraries"):
                for lib in st.session_state.zotero_libraries:
                    st.session_state[f"lib_checkbox_{lib['id']}"] = False
                save_settings({"processing_libraries": []})
                st.rerun()
        
        # Process libraries button
        if st.button("Process Selected Libraries", key="process_libraries_button"):
            selected_libraries = get_setting("processing_libraries", [])
            
            if not selected_libraries:
                st.warning("Please select at least one library to process.")
            else:
                # Store selected libraries in ChromaDB if they don't exist
                for lib_id in selected_libraries:
                    lib_data = next((lib for lib in st.session_state.zotero_libraries if lib["id"] == lib_id), None)
                    
                    if lib_data and lib_id not in existing_libraries:
                        st.session_state.document_processor.add_library(lib_data)
                
                # Set processing status
                st.session_state.processing_status = {
                    "active": True,
                    "libraries": selected_libraries,
                    "current_library": None,
                    "current_document": None,
                    "total_documents": 0,
                    "processed_documents": 0,
                    "current_index": 0,
                    "stage": "OCR",
                    "errors": [],
                }
                
                # Rerun to start processing
                st.rerun()
    else:
        st.info("Click 'Fetch Libraries' to retrieve your Zotero libraries.")
    
    # Processing status
    st.write("### Processing Status")
    
    if "processing_status" in st.session_state and st.session_state.processing_status["active"]:
        status = st.session_state.processing_status
        
        # Display progress bars
        if status["total_documents"] > 0:
            progress = status["processed_documents"] / status["total_documents"]
            st.progress(progress, text=f"Processing: {status['processed_documents']} of {status['total_documents']} documents")
        
        # Display current document
        if status["current_document"]:
            st.write(f"Processing: {status['current_document']}")
        
        # Display errors
        if status["errors"]:
            with st.expander("Errors", expanded=False):
                for error in status["errors"]:
                    st.error(error)
        
        # Process the next library if not already processing
        if not status["current_library"] and status["libraries"]:
            # Get the next library to process
            lib_id = status["libraries"][0]
            status["current_library"] = lib_id
            
            # Get library data
            lib_data = next((lib for lib in st.session_state.zotero_libraries if lib["id"] == lib_id), None)
            
            if lib_data:
                st.write(f"Processing library: {lib_data['name']}")
                
                # Process the library
                library_type = lib_data["library_type"]
                library_id = lib_data["library_id"]
                
                # Define callback function for progress updates
                def progress_callback(index, total, document_title, stage):
                    status = st.session_state.processing_status
                    status["current_index"] = index
                    status["total_documents"] = total
                    status["current_document"] = document_title
                    status["stage"] = stage
                    # Can't update UI from callback, but we'll update the session state
                
                # Process the library
                total, processed, errors = st.session_state.document_processor.process_library(
                    library_type, library_id, progress_callback
                )
                
                # Update status
                status["processed_documents"] += processed
                status["errors"].extend(errors)
                status["libraries"].pop(0)  # Remove the processed library
                status["current_library"] = None
                
                # If no more libraries, mark as complete
                if not status["libraries"]:
                    status["active"] = False
                    st.success(f"Processing complete! Processed {status['processed_documents']} documents.")
                
                # Rerun to update UI
                st.rerun()
    else:
        st.info("Select libraries and click 'Process Selected Libraries' to start processing.")


def render_settings_tab():
    """Render the settings tab."""
    st.write("## Settings")
    st.write("This tab will be implemented in Phase 4.")
    
    # Placeholder for API configuration
    st.write("### API Configuration")
    
    # Zotero API Key
    zotero_api_key = st.text_input(
        "Zotero API Key:", 
        type="password", 
        value=get_setting("zotero_api_key", ""),
        key="settings_zotero_api_key",
        help="Your Zotero API key. You can find this in your Zotero account settings."
    )
    
    # Google API Key
    google_api_key = st.text_input(
        "Google API Key:", 
        type="password", 
        value=get_setting("google_api_key", ""),
        key="settings_google_api_key",
        help="Your Google API key for OCR processing."
    )
    
    # Save API keys if changed
    if zotero_api_key != get_setting("zotero_api_key", ""):
        save_settings({"zotero_api_key": zotero_api_key})
        st.session_state.zotero_manager.initialize(zotero_api_key)
        os.environ["ZOTERO_API_KEY"] = zotero_api_key
    
    if google_api_key != get_setting("google_api_key", ""):
        save_settings({"google_api_key": google_api_key})
        st.session_state.ocr_manager.initialize(google_api_key)
        os.environ["GOOGLE_API_KEY"] = google_api_key
    
    # Placeholder for processing options
    st.write("### Processing Options")
    
    # Chunk Size
    chunk_size = st.number_input(
        "Chunk Size:", 
        value=get_setting("chunk_size", 512),
        min_value=128,
        max_value=2048,
        step=64,
        key="settings_chunk_size",
        help="Size of text chunks in tokens."
    )
    
    # Chunk Overlap
    chunk_overlap = st.number_input(
        "Chunk Overlap:", 
        value=get_setting("chunk_overlap", 50),
        min_value=0,
        max_value=512,
        step=10,
        key="settings_chunk_overlap",
        help="Overlap between chunks in tokens."
    )
    
    # Auto-update on startup
    auto_update = st.checkbox(
        "Auto-update on startup", 
        value=get_setting("auto_update", True),
        key="settings_auto_update",
        help="Automatically update libraries on application startup."
    )
    
    # Save processing options if changed
    if chunk_size != get_setting("chunk_size", 512):
        save_settings({"chunk_size": chunk_size})
    
    if chunk_overlap != get_setting("chunk_overlap", 50):
        save_settings({"chunk_overlap": chunk_overlap})
    
    if auto_update != get_setting("auto_update", True):
        save_settings({"auto_update": auto_update})
    
    # Placeholder for OCR storage options
    st.write("### OCR Storage Options")
    
    # Store OCR text in Zotero attachments
    store_ocr = st.checkbox(
        "Store OCR text in Zotero attachments", 
        value=get_setting("store_ocr", True),
        key="settings_store_ocr",
        help="Store OCR text as attachments in Zotero."
    )
    
    # Use stored OCR text when available
    use_stored_ocr = st.checkbox(
        "Use stored OCR text when available", 
        value=get_setting("use_stored_ocr", True),
        key="settings_use_stored_ocr",
        help="Use stored OCR text when available instead of re-running OCR."
    )
    
    # Always re-run OCR
    always_rerun_ocr = st.checkbox(
        "Always re-run OCR (ignore stored text)", 
        value=get_setting("always_rerun_ocr", False),
        key="settings_always_rerun_ocr",
        help="Always re-run OCR even if stored text is available."
    )
    
    # Save OCR options if changed
    if store_ocr != get_setting("store_ocr", True):
        save_settings({"store_ocr": store_ocr})
    
    if use_stored_ocr != get_setting("use_stored_ocr", True):
        save_settings({"use_stored_ocr": use_stored_ocr})
    
    if always_rerun_ocr != get_setting("always_rerun_ocr", False):
        save_settings({"always_rerun_ocr": always_rerun_ocr})
    
    # Update document processor options
    st.session_state.document_processor.set_processing_options(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        store_ocr=store_ocr,
        use_stored_ocr=use_stored_ocr,
        always_rerun_ocr=always_rerun_ocr
    )
    
    # Placeholder for database settings
    st.write("### Database")
    st.text_input("Database Location:", value=get_db_path(), key="db_path_input")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Backup Database", key="backup_db_button"):
            st.info("Database backup will be implemented in Phase 4.")
    
    with col2:
        if st.button("Restore Database", key="restore_db_button"):
            st.info("Database restore will be implemented in Phase 4.")
    
    # Display statistics
    st.write("### Statistics")
    stats = st.session_state.db_manager.get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Libraries", stats["libraries"])
    with col2:
        st.metric("Documents", stats["documents"])
    with col3:
        st.metric("Chunks", stats["chunks"])
    with col4:
        # Calculate database size (placeholder for now)
        db_size = "N/A"
        st.metric("Database Size", db_size)


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()
    
    # Check for auto-update on startup
    if get_setting("auto_update", True) and "first_run" not in st.session_state:
        st.session_state.first_run = True
        
        # Check if Zotero API key is available
        zotero_api_key = get_setting("zotero_api_key", "")
        if zotero_api_key and st.session_state.zotero_manager.test_connection():
            # Get libraries
            libraries = st.session_state.zotero_manager.get_libraries()
            
            if libraries:
                # Store libraries in session state
                st.session_state.zotero_libraries = libraries
                
                # Get selected libraries
                selected_libraries = get_setting("selected_libraries", [])
                
                if selected_libraries:
                    # Set processing status
                    st.session_state.processing_status = {
                        "active": True,
                        "libraries": selected_libraries,
                        "current_library": None,
                        "current_document": None,
                        "total_documents": 0,
                        "processed_documents": 0,
                        "current_index": 0,
                        "stage": "OCR",
                        "errors": [],
                    }
    
    # Render header
    render_header()
    
    # Render tabs
    render_tabs()
    
    # Add footer
    st.write("---")
    st.write("Z-Cite Semantic Search | Version 0.2.0")


if __name__ == "__main__":
    main()