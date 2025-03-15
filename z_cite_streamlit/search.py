"""Search functionality for Z-Cite Streamlit application."""

from typing import Dict, List, Optional

from sentence_transformers import SentenceTransformer

from z_cite_streamlit.db import ChromaDBManager


class SearchManager:
    """Manager for search operations."""

    def __init__(self, db_manager: ChromaDBManager):
        """Initialize search manager.
        
        Args:
            db_manager: ChromaDB manager instance.
        """
        self.db_manager = db_manager
        
        # Initialize embedding model
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")  # Default model, can be replaced with Legal-BERT later
    
    def search(
        self, 
        query: str, 
        n_results: int = 10, 
        threshold: float = 0.7,
        library_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """Search for documents matching the query.
        
        Args:
            query: Search query.
            n_results: Maximum number of results to return.
            threshold: Minimum similarity threshold.
            library_ids: Optional list of library IDs to filter by.
            
        Returns:
            List of matching documents with metadata.
        """
        # Perform search using ChromaDB manager
        results = self.db_manager.search_chunks(
            query=query,
            n_results=n_results,
            threshold=threshold,
            library_ids=library_ids
        )
        
        # Sort results by similarity score (highest first)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results
    
    def format_results(self, results: List[Dict]) -> List[Dict]:
        """Format search results for display.
        
        Args:
            results: Search results from search method.
            
        Returns:
            Formatted results for display.
        """
        formatted_results = []
        
        for result in results:
            # Extract document metadata
            doc_metadata = result["document_metadata"]
            
            # Format title and authors
            title = doc_metadata.get("title", "Untitled Document")
            authors = doc_metadata.get("authors", [])
            authors_str = ", ".join(authors) if authors else "Unknown Author"
            
            # Format similarity score as percentage
            similarity_pct = int(result["similarity"] * 100)
            
            # Format chunk text (truncate if too long)
            text = result["text"]
            if len(text) > 500:
                text = text[:497] + "..."
            
            # Create formatted result
            formatted_result = {
                "title": title,
                "authors": authors_str,
                "similarity": similarity_pct,
                "text": text,
                "document_id": result["document_id"],
                "chunk_id": result["chunk_id"],
                "metadata": {
                    "page_number": result["metadata"].get("page_number"),
                    "section": result["metadata"].get("section"),
                    "publication_date": doc_metadata.get("publication_date"),
                    "document_type": doc_metadata.get("document_type")
                }
            }
            
            formatted_results.append(formatted_result)
        
        return formatted_results