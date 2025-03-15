"""ChromaDB integration for Z-Cite Streamlit application."""

import os
from typing import Dict, List, Optional, Union

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


class ChromaDBManager:
    """Manager for ChromaDB operations."""

    def __init__(self, db_path: str = "./chroma_db"):
        """Initialize ChromaDB manager.
        
        Args:
            db_path: Path to the ChromaDB database.
        """
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # Initialize embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/all-MiniLM-L6-v2"  # Default model, can be replaced with Legal-BERT later
        )
        
        # Initialize collections
        self._init_collections()
    
    def _init_collections(self):
        """Initialize ChromaDB collections."""
        # Documents collection
        collection_names = self.client.list_collections()
        
        # Create or get documents collection
        if "documents" not in collection_names:
            self.documents_collection = self.client.create_collection(
                name="documents",
                embedding_function=self.embedding_function,
                metadata={"description": "Document metadata"}
            )
        else:
            self.documents_collection = self.client.get_collection(
                name="documents",
                embedding_function=self.embedding_function
            )
        
        # Chunks collection
        if "chunks" not in collection_names:
            self.chunks_collection = self.client.create_collection(
                name="chunks",
                embedding_function=self.embedding_function,
                metadata={"description": "Document chunks with embeddings"}
            )
        else:
            self.chunks_collection = self.client.get_collection(
                name="chunks",
                embedding_function=self.embedding_function
            )
        
        # Libraries collection
        if "libraries" not in collection_names:
            self.libraries_collection = self.client.create_collection(
                name="libraries",
                embedding_function=self.embedding_function,
                metadata={"description": "Library information"}
            )
        else:
            self.libraries_collection = self.client.get_collection(
                name="libraries",
                embedding_function=self.embedding_function
            )
    
    def add_document(self, doc_id: str, metadata: Dict):
        """Add a document to the documents collection.
        
        Args:
            doc_id: Unique document ID.
            metadata: Document metadata.
        """
        self.documents_collection.add(
            ids=[doc_id],
            metadatas=[metadata],
            documents=[""]  # Empty document as we only store metadata here
        )
    
    def add_chunk(self, chunk_id: str, document_id: str, text: str, metadata: Dict):
        """Add a chunk to the chunks collection.
        
        Args:
            chunk_id: Unique chunk ID.
            document_id: Reference to parent document.
            text: Text content of the chunk.
            metadata: Chunk metadata.
        """
        # Update metadata with document_id
        metadata["document_id"] = document_id
        
        self.chunks_collection.add(
            ids=[chunk_id],
            metadatas=[metadata],
            documents=[text]
        )
    
    def add_library(self, library_id: str, metadata: Dict):
        """Add a library to the libraries collection.
        
        Args:
            library_id: Unique library ID.
            metadata: Library metadata.
        """
        self.libraries_collection.add(
            ids=[library_id],
            metadatas=[metadata],
            documents=[""]  # Empty document as we only store metadata here
        )
    
    def search_chunks(
        self, 
        query: str, 
        n_results: int = 10, 
        threshold: float = 0.7,
        library_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """Search for chunks matching the query.
        
        Args:
            query: Search query.
            n_results: Maximum number of results to return.
            threshold: Minimum similarity threshold.
            library_ids: Optional list of library IDs to filter by.
            
        Returns:
            List of matching chunks with metadata.
        """
        # Prepare where clause if library_ids is provided
        where_clause = None
        if library_ids:
            # We need to get document_ids for the specified libraries
            library_docs = []
            for lib_id in library_ids:
                docs = self.documents_collection.get(
                    where={"library_id": lib_id}
                )
                if docs and docs["ids"]:
                    library_docs.extend(docs["ids"])
            
            if library_docs:
                where_clause = {"document_id": {"$in": library_docs}}
        
        # Perform the search
        results = self.chunks_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause
        )
        
        # Process results
        processed_results = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                # Get similarity score
                distance = results["distances"][0][i] if "distances" in results else 0
                similarity = 1 - distance  # Convert distance to similarity
                
                # Skip results below threshold
                if similarity < threshold:
                    continue
                
                # Get document metadata
                doc_id = results["metadatas"][0][i]["document_id"]
                doc_result = self.documents_collection.get(
                    ids=[doc_id]
                )
                
                doc_metadata = {}
                if doc_result and doc_result["metadatas"] and doc_result["metadatas"][0]:
                    doc_metadata = doc_result["metadatas"][0]
                
                # Combine results
                processed_results.append({
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "document_metadata": doc_metadata,
                    "similarity": similarity
                })
        
        return processed_results
    
    def get_libraries(self) -> List[Dict]:
        """Get all libraries.
        
        Returns:
            List of libraries with metadata.
        """
        try:
            results = self.libraries_collection.get()
        except Exception as e:
            print(f"Error getting libraries: {str(e)}")
            return []
        
        libraries = []
        if results and results["ids"]:
            for i, lib_id in enumerate(results["ids"]):
                libraries.append({
                    "id": lib_id,
                    "metadata": results["metadatas"][i]
                })
        
        return libraries
    
    def get_statistics(self) -> Dict:
        """Get database statistics.
        
        Returns:
            Dictionary with statistics.
        """
        try:
            libraries = self.libraries_collection.get()
            documents = self.documents_collection.get()
            chunks = self.chunks_collection.get()
            
            return {
                "libraries": len(libraries["ids"]) if libraries and "ids" in libraries else 0,
                "documents": len(documents["ids"]) if documents and "ids" in documents else 0,
                "chunks": len(chunks["ids"]) if chunks and "ids" in chunks else 0,
            }
        except Exception as e:
            print(f"Error getting statistics: {str(e)}")
            return {
                "libraries": 0,
                "documents": 0,
                "chunks": 0,
            }