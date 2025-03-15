"""Document processing for Z-Cite Streamlit application."""

import os
import tempfile
from typing import Dict, List, Optional, Tuple

from z_cite_streamlit.db import ChromaDBManager
from z_cite_streamlit.ocr import OCRManager
from z_cite_streamlit.utils import generate_id
from z_cite_streamlit.zotero import ZoteroManager


class DocumentProcessor:
    """Processor for document operations."""

    def __init__(
        self,
        db_manager: ChromaDBManager,
        zotero_manager: ZoteroManager,
        ocr_manager: OCRManager
    ):
        """Initialize document processor.
        
        Args:
            db_manager: ChromaDB manager instance.
            zotero_manager: Zotero manager instance.
            ocr_manager: OCR manager instance.
        """
        self.db_manager = db_manager
        self.zotero_manager = zotero_manager
        self.ocr_manager = ocr_manager
        
        # Processing options
        self.chunk_size = 512
        self.chunk_overlap = 50
        self.store_ocr = True
        self.use_stored_ocr = True
        self.always_rerun_ocr = False
    
    def set_processing_options(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        store_ocr: bool = True,
        use_stored_ocr: bool = True,
        always_rerun_ocr: bool = False
    ):
        """Set processing options.
        
        Args:
            chunk_size: Size of text chunks in tokens.
            chunk_overlap: Overlap between chunks in tokens.
            store_ocr: Whether to store OCR text in Zotero attachments.
            use_stored_ocr: Whether to use stored OCR text when available.
            always_rerun_ocr: Whether to always re-run OCR (ignore stored text).
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.store_ocr = store_ocr
        self.use_stored_ocr = use_stored_ocr
        self.always_rerun_ocr = always_rerun_ocr
    
    def process_library(
        self,
        library_type: str,
        library_id: str,
        callback=None,
        limit: Optional[int] = None
    ) -> Tuple[int, int, List[str]]:
        """Process all documents in a library.
        
        Args:
            library_type: Library type ('user' or 'group').
            library_id: Library ID.
            callback: Optional callback function to report progress.
            limit: Optional limit on the number of documents to process.
            
        Returns:
            Tuple of (total documents, processed documents, errors).
        """
        # Get documents from the library
        documents = self.zotero_manager.get_documents(library_type, library_id)
        
        # Apply limit if specified
        if limit is not None and limit > 0:
            documents = documents[:limit]
        
        total_documents = len(documents)
        processed_documents = 0
        errors = []
        
        # Process each document
        for i, document in enumerate(documents):
            try:
                # Report progress
                if callback:
                    callback(i, total_documents, document["title"], "OCR")
                
                # Process the document
                success = self.process_document(document)
                
                if success:
                    processed_documents += 1
                else:
                    errors.append(f"Failed to process {document['title']}")
            except Exception as e:
                errors.append(f"Error processing {document['title']}: {str(e)}")
        
        return total_documents, processed_documents, errors
    
    def process_document(self, document: Dict) -> bool:
        """Process a single document.
        
        Args:
            document: Document metadata.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Extract document info
            doc_id = document["id"]
            zotero_key = document["zotero_key"]
            
            # Check for existing OCR attachment
            ocr_text = None
            if self.use_stored_ocr and not self.always_rerun_ocr:
                ocr_attachment = self.zotero_manager.find_ocr_attachment(zotero_key)
                
                if ocr_attachment:
                    # Download and extract OCR text from attachment
                    ocr_text, _ = self.zotero_manager.download_and_parse_ocr_attachment(ocr_attachment)
            
            # If no OCR text or always re-run OCR, run OCR
            if ocr_text is None or self.always_rerun_ocr:
                # Get PDF attachment
                pdf_attachment = self.zotero_manager.get_pdf_attachment(zotero_key)
                
                if not pdf_attachment:
                    return False
                
                # Download PDF to temporary file
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                    temp_path = temp_file.name
                
                try:
                    # Download PDF
                    if not self.zotero_manager.download_pdf(pdf_attachment, temp_path):
                        os.unlink(temp_path)
                        return False
                    
                    # Run OCR
                    ocr_text = self.ocr_manager.process_pdf(temp_path)
                    
                    # Store OCR results in Zotero as attachment if enabled
                    if self.store_ocr:
                        self.zotero_manager.store_ocr_as_attachment(zotero_key, ocr_text)
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            
            # Store document in ChromaDB
            self.db_manager.add_document(doc_id, {
                "title": document["title"],
                "authors": document["authors"],
                "publication_date": document["publication_date"],
                "document_type": document["document_type"],
                "library_id": document["library_id"],
                "zotero_key": zotero_key,
            })
            
            # In Phase 3, we'll implement text chunking and embedding generation
            # For now, just store a single chunk with the OCR text
            chunk_id = generate_id("chunk")
            self.db_manager.add_chunk(chunk_id, doc_id, ocr_text, {
                "page_number": 1,
                "section": "Full Document",
                "version_hash": str(hash(ocr_text)),
            })
            
            return True
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            return False
    
    def add_library(self, library_data: Dict) -> bool:
        """Add a library to ChromaDB.
        
        Args:
            library_data: Library metadata.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            library_id = library_data["id"]
            
            # Store library in ChromaDB
            self.db_manager.add_library(library_id, {
                "zotero_id": library_data["library_id"],
                "name": library_data["name"],
                "library_type": library_data["library_type"],
                "description": library_data.get("description", ""),
                "auto_update": True,
                "last_pulled": "",
            })
            
            return True
        except Exception as e:
            print(f"Error adding library: {str(e)}")
            return False