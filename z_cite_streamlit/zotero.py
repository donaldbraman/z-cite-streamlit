"""Zotero API integration for Z-Cite Streamlit application."""

import os
import tempfile
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import requests
from pyzotero import zotero

from z_cite_streamlit.utils import generate_id


class ZoteroManager:
    """Manager for Zotero API operations."""

    def __init__(self, api_key: str = None, default_group_id: str = "5140532"):
        """Initialize Zotero manager.
        
        Args:
            api_key: Zotero API key. If None, will try to get from environment.
            default_group_id: Default group library ID to use (Climate Crimes library).
        """
        self.api_key = api_key or os.environ.get("ZOTERO_API_KEY")
        self.library_type = None
        self.library_id = None
        self.zot = None
        self.default_group_id = default_group_id
        
        # Initialize if API key is available
        if self.api_key:
            self.initialize()
    
    def initialize(self, api_key: Optional[str] = None) -> bool:
        """Initialize or reinitialize the Zotero client with the given API key.
        
        Args:
            api_key: Optional new API key to use.
            
        Returns:
            True if initialization was successful, False otherwise.
        """
        if api_key:
            self.api_key = api_key
        
        if not self.api_key:
            return False
        
        try:
            # Test the API key by getting user ID
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get("https://api.zotero.org/keys/current", headers=headers)
            
            if response.status_code != 200:
                return False
            
            # Get user ID but don't set it as the default library
            # We'll use group libraries instead as specified in the requirements
            user_data = response.json()
            user_id = user_data.get("userID")
            
            # Initialize Zotero client with the default group library
            self.switch_library("group", self.default_group_id)
            return True
            
        except Exception:
            return False
    
    def test_connection(self) -> bool:
        """Test the connection to the Zotero API.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        if not self.zot:
            return False
        
        try:
            # Try to get a single item to test connection
            self.zot.items(limit=1)
            return True
        except Exception:
            return False
    
    def get_libraries(self) -> List[Dict]:
        """Get all available libraries for the user.
        
        Returns:
            List of libraries with metadata.
        """
        if not self.zot:
            return []
        
        libraries = []
        
        try:
            # Get group libraries (we focus on group libraries as per requirements)
            groups = self.zot.groups()
            for group in groups:
                group_id = group.get("id")
                libraries.append({
                    "id": f"group_{group_id}",
                    "name": group.get("data", {}).get("name", f"Group {group_id}"),
                    "library_type": "group",
                    "library_id": group_id,
                    "editable": group.get("data", {}).get("libraryEditing") == "members",
                    "description": group.get("data", {}).get("description", ""),
                })
                
            # If no libraries were found, add a warning message
            if not libraries:
                print("Warning: No group libraries found. Make sure your API key has access to group libraries.")
                
            # Mark the Climate Crimes library as the default if it exists
            self._mark_default_library(libraries)
        except Exception as e:
            print(f"Error getting libraries: {str(e)}")
        
        return libraries
    
    def switch_library(self, library_type: str, library_id: str) -> bool:
        """Switch to a different library.
        
        Args:
            library_type: Library type ('user' or 'group').
            library_id: Library ID.
            
        Returns:
            True if switch was successful, False otherwise.
        """
        if not self.api_key:
            return False
        
        try:
            self.library_type = library_type
            self.library_id = library_id
            self.zot = zotero.Zotero(library_id, library_type, self.api_key)
            return True
        except Exception:
            return False
            
    def _mark_default_library(self, libraries: List[Dict]) -> None:
        """Mark the default library (Climate Crimes) in the list.
        
        Args:
            libraries: List of libraries.
        """
        for lib in libraries:
            if lib["library_id"] == self.default_group_id:
                lib["is_default"] = True
            else:
                lib["is_default"] = False
    
    def get_documents(self, library_type: str, library_id: str) -> List[Dict]:
        """Get all documents from a library.
        
        Args:
            library_type: Library type ('user' or 'group').
            library_id: Library ID.
            
        Returns:
            List of documents with metadata.
        """
        # Switch to the specified library
        if not self.switch_library(library_type, library_id):
            return []
        
        documents = []
        
        try:
            # Get all items with attachments
            items = self.zot.items(itemType="-attachment")
            
            for item in items:
                # Get basic metadata
                item_key = item.get("key")
                item_data = item.get("data", {})
                
                # Get attachment info
                has_pdf = False
                children = self.zot.children(item_key)
                
                for child in children:
                    child_data = child.get("data", {})
                    if child_data.get("contentType") == "application/pdf":
                        has_pdf = True
                        break
                
                # Only include items with PDF attachments
                if has_pdf:
                    # Extract authors
                    creators = item_data.get("creators", [])
                    authors = []
                    
                    for creator in creators:
                        if creator.get("creatorType") in ["author", "editor"]:
                            name_parts = []
                            if creator.get("firstName"):
                                name_parts.append(creator.get("firstName"))
                            if creator.get("lastName"):
                                name_parts.append(creator.get("lastName"))
                            
                            if name_parts:
                                authors.append(" ".join(name_parts))
                            elif creator.get("name"):
                                authors.append(creator.get("name"))
                    
                    # Create document entry
                    document = {
                        "id": f"doc_{item_key}",
                        "zotero_key": item_key,
                        "title": item_data.get("title", "Untitled Document"),
                        "authors": authors,
                        "publication_date": item_data.get("date", ""),
                        "document_type": item_data.get("itemType", ""),
                        "library_id": f"{library_type}_{library_id}",
                        "has_ocr": self._has_ocr_attachment(item_key),
                    }
                    
                    documents.append(document)
            
        except Exception as e:
            print(f"Error getting documents: {str(e)}")
        
        return documents
    
    def _has_ocr_attachment(self, item_key: str) -> bool:
        """Check if an item has an OCR attachment.
        
        Args:
            item_key: Zotero item key.
            
        Returns:
            True if the item has an OCR attachment, False otherwise.
        """
        try:
            children = self.zot.children(item_key)
            
            for child in children:
                child_data = child.get("data", {})
                if (child_data.get("contentType") == "text/plain" and 
                    child_data.get("filename", "").startswith("z-cite-ocr")):
                    return True
            
            return False
        except Exception:
            return False
    
    def find_ocr_attachment(self, item_key: str) -> Optional[Dict]:
        """Find OCR attachment for an item.
        
        Args:
            item_key: Zotero item key.
            
        Returns:
            OCR attachment data if found, None otherwise.
        """
        try:
            children = self.zot.children(item_key)
            
            for child in children:
                child_data = child.get("data", {})
                if (child_data.get("contentType") == "text/plain" and 
                    child_data.get("filename", "").startswith("z-cite-ocr")):
                    return child
            
            return None
        except Exception:
            return None
    
    def download_and_parse_ocr_attachment(self, attachment: Dict) -> Tuple[str, str]:
        """Download and parse OCR attachment.
        
        Args:
            attachment: OCR attachment data.
            
        Returns:
            Tuple of (OCR text, version hash).
        """
        try:
            # Get attachment key
            attachment_key = attachment.get("key")
            
            # Download attachment content
            content = self.zot.file(attachment_key)
            
            # Parse content
            text_content = content.decode("utf-8")
            
            # Extract version hash
            version_hash = ""
            for line in text_content.split("\n")[:10]:
                if line.startswith("Version:"):
                    version_hash = line.replace("Version:", "").strip()
                    break
            
            # Extract OCR text (everything after the separator line)
            separator = "-" * 80
            parts = text_content.split(separator, 1)
            
            if len(parts) > 1:
                ocr_text = parts[1].strip()
            else:
                ocr_text = text_content
            
            return ocr_text, version_hash
        except Exception as e:
            print(f"Error downloading OCR attachment: {str(e)}")
            return "", ""
    
    def store_ocr_as_attachment(self, item_key: str, ocr_text: str) -> bool:
        """Store OCR text as an attachment in Zotero.
        
        Args:
            item_key: Zotero item key.
            ocr_text: OCR text to store.
            
        Returns:
            True if successful, False otherwise.
        """
        if not self.zot:
            return False
        
        try:
            # Generate version hash (timestamp-based for simplicity)
            version_hash = f"{int(time.time())}"
            
            # Create temporary file with OCR text and metadata
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(f"Z-Cite OCR Text\n")
                temp_file.write(f"Version: {version_hash}\n")
                temp_file.write(f"Processed: {datetime.now().isoformat()}\n")
                temp_file.write(f"Document: {item_key}\n")
                temp_file.write("-" * 80 + "\n\n")
                temp_file.write(ocr_text)
                temp_path = temp_file.name
            
            # Check if OCR attachment already exists
            existing_attachment = self.find_ocr_attachment(item_key)
            
            if existing_attachment:
                # Update existing attachment
                attachment_key = existing_attachment.get("key")
                self.zot.update_attachment(attachment_key, temp_path)
            else:
                # Create new attachment
                self.zot.attachment_simple([{
                    'path': temp_path,
                    'filename': 'z-cite-ocr.txt',
                    'contentType': 'text/plain',
                    'parentItem': item_key
                }])
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            return True
        except Exception as e:
            print(f"Error storing OCR attachment: {str(e)}")
            return False
    
    def get_pdf_attachment(self, item_key: str) -> Optional[Dict]:
        """Get PDF attachment for an item.
        
        Args:
            item_key: Zotero item key.
            
        Returns:
            PDF attachment data if found, None otherwise.
        """
        try:
            children = self.zot.children(item_key)
            
            for child in children:
                child_data = child.get("data", {})
                if child_data.get("contentType") == "application/pdf":
                    return child
            
            return None
        except Exception:
            return None
    
    def download_pdf(self, attachment: Dict, output_path: str) -> bool:
        """Download PDF attachment to a file.
        
        Args:
            attachment: PDF attachment data.
            output_path: Path to save the PDF to.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get attachment key
            attachment_key = attachment.get("key")
            
            # Download attachment content
            content = self.zot.file(attachment_key)
            
            # Save to file
            with open(output_path, "wb") as f:
                f.write(content)
            
            return True
        except Exception as e:
            print(f"Error downloading PDF: {str(e)}")
            return False