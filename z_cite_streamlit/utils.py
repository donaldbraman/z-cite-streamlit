"""Utility functions for Z-Cite Streamlit application."""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import streamlit as st


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID.
    
    Args:
        prefix: Optional prefix for the ID.
        
    Returns:
        Unique ID string.
    """
    return f"{prefix}_{uuid.uuid4().hex}"


def get_db_path() -> str:
    """Get the path to the ChromaDB database.
    
    Returns:
        Path to the ChromaDB database.
    """
    # Get from session state if available
    if "db_path" in st.session_state:
        return st.session_state.db_path
    
    # Default path
    default_path = os.path.join(os.path.expanduser("~"), ".z_cite", "chroma_db")
    
    # Create directory if it doesn't exist
    os.makedirs(default_path, exist_ok=True)
    
    # Store in session state
    st.session_state.db_path = default_path
    
    return default_path


def format_timestamp(timestamp: Optional[str] = None) -> str:
    """Format a timestamp for display.
    
    Args:
        timestamp: ISO format timestamp string.
        
    Returns:
        Formatted timestamp string.
    """
    if not timestamp:
        timestamp = datetime.now().isoformat()
    
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return "Unknown"


def highlight_text(text: str, query: str, max_length: int = 500) -> str:
    """Highlight query terms in text and truncate if necessary.
    
    Args:
        text: Text to highlight.
        query: Query terms to highlight.
        max_length: Maximum length of the returned text.
        
    Returns:
        Highlighted text.
    """
    # Simple highlighting by wrapping query terms in markdown bold
    if not query or not text:
        return text[:max_length] + "..." if len(text) > max_length else text
    
    # Split query into terms
    terms = query.lower().split()
    
    # Find the first occurrence of any term
    first_pos = len(text)
    for term in terms:
        pos = text.lower().find(term)
        if pos != -1 and pos < first_pos:
            first_pos = pos
    
    # If no terms found, just truncate
    if first_pos == len(text):
        return text[:max_length] + "..." if len(text) > max_length else text
    
    # Calculate start position to show context around the first match
    start_pos = max(0, first_pos - 100)
    
    # Extract a portion of text centered around the first match
    extract = text[start_pos:start_pos + max_length]
    if start_pos > 0:
        extract = "..." + extract
    if start_pos + max_length < len(text):
        extract = extract + "..."
    
    # Highlight all terms in the extract
    for term in terms:
        # Use case-insensitive replacement with markdown bold
        term_lower = term.lower()
        i = 0
        while i < len(extract):
            pos = extract.lower().find(term_lower, i)
            if pos == -1:
                break
            
            # Get the actual case-preserved term from the text
            actual_term = extract[pos:pos + len(term)]
            
            # Replace with bold version
            extract = extract[:pos] + f"**{actual_term}**" + extract[pos + len(term):]
            
            # Move index past this replacement
            i = pos + len(actual_term) + 4  # 4 for the ** markers
    
    return extract


def save_settings(settings: Dict) -> None:
    """Save settings to session state.
    
    Args:
        settings: Dictionary of settings.
    """
    for key, value in settings.items():
        st.session_state[key] = value


def get_setting(key: str, default=None):
    """Get a setting from session state.
    
    Args:
        key: Setting key.
        default: Default value if setting not found.
        
    Returns:
        Setting value.
    """
    return st.session_state.get(key, default)