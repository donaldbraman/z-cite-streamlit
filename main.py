"""Z-Cite Streamlit Application entry point."""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "streamlit==1.35.0",
#   "chromadb==0.4.22",
#   "sentence-transformers==3.4.1",
#   "numpy<2.0.0",
# ]
# [tool.uv]
# exclude-newer = "2025-03-15T00:00:00Z"
# ///

import streamlit as st
from z_cite_streamlit.app import main

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        import traceback
        st.code(traceback.format_exc())