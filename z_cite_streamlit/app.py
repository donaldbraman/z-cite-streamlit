"""Z-Cite Streamlit Application for semantic search of Zotero libraries."""

import os
import sys
from typing import Dict, List, Optional

import streamlit as st

from z_cite_streamlit.db import ChromaDBManager
from z_cite_streamlit.search import SearchManager
from z_cite_streamlit.utils import get_db_path, get_setting, highlight_text, save_settings


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
    
    # Initialize settings with defaults if not already set
    defaults = {
        "auto_update": True,
        "threshold": 0.7,
        "results_limit": 10,
        "selected_libraries": [],
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
    st.write("This tab will be implemented in Phase 2.")
    
    # Placeholder for Zotero API key input
    st.text_input("Zotero API Key:", type="password", key="zotero_api_key")
    
    if st.button("Fetch Libraries", key="fetch_libraries_button"):
        st.info("Library fetching will be implemented in Phase 2.")
    
    # Placeholder for library selection
    st.write("### Available Libraries")
    st.info("Library selection will be implemented in Phase 2.")
    
    # Placeholder for processing status
    st.write("### Processing Status")
    st.info("Processing status will be implemented in Phase 2.")


def render_settings_tab():
    """Render the settings tab."""
    st.write("## Settings")
    st.write("This tab will be implemented in Phase 4.")
    
    # Placeholder for API configuration
    st.write("### API Configuration")
    st.text_input("Zotero API Key:", type="password", key="settings_zotero_api_key")
    st.text_input("Google API Key:", type="password", key="google_api_key")
    
    # Placeholder for processing options
    st.write("### Processing Options")
    st.number_input("Chunk Size:", value=512, key="chunk_size")
    st.number_input("Chunk Overlap:", value=50, key="chunk_overlap")
    st.checkbox("Auto-update on startup", value=True, key="settings_auto_update")
    
    # Placeholder for OCR storage options
    st.write("### OCR Storage Options")
    st.checkbox("Store OCR text in Zotero attachments", value=True, key="store_ocr")
    st.checkbox("Use stored OCR text when available", value=True, key="use_stored_ocr")
    st.checkbox("Always re-run OCR (ignore stored text)", value=False, key="always_rerun_ocr")
    
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
    
    # Render header
    render_header()
    
    # Render tabs
    render_tabs()
    
    # Add footer
    st.write("---")
    st.write("Z-Cite Semantic Search | Version 0.1.0")


if __name__ == "__main__":
    main()