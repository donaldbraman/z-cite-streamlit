"""Tests for the search functionality."""

import unittest
from unittest.mock import MagicMock, patch

from z_cite_streamlit.db import ChromaDBManager
from z_cite_streamlit.search import SearchManager


class TestSearchManager(unittest.TestCase):
    """Test the SearchManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db_manager = MagicMock(spec=ChromaDBManager)
        self.search_manager = SearchManager(db_manager=self.mock_db_manager)

    def test_search(self):
        """Test the search method."""
        # Mock the search_chunks method of the db_manager
        self.mock_db_manager.search_chunks.return_value = [
            {
                "chunk_id": "chunk_1",
                "document_id": "doc_1",
                "text": "This is a test document.",
                "metadata": {"page_number": 1, "section": "Introduction"},
                "document_metadata": {
                    "title": "Test Document",
                    "authors": ["Test Author"],
                    "publication_date": "2023-01-01",
                    "document_type": "article",
                },
                "similarity": 0.85,
            }
        ]

        # Call the search method
        results = self.search_manager.search(
            query="test document",
            n_results=10,
            threshold=0.7,
        )

        # Assert that the search_chunks method was called with the correct arguments
        self.mock_db_manager.search_chunks.assert_called_once_with(
            query="test document",
            n_results=10,
            threshold=0.7,
            library_ids=None,
        )

        # Assert that the results are as expected
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], "chunk_1")
        self.assertEqual(results[0]["document_id"], "doc_1")
        self.assertEqual(results[0]["text"], "This is a test document.")
        self.assertEqual(results[0]["similarity"], 0.85)

    def test_format_results(self):
        """Test the format_results method."""
        # Create test results
        results = [
            {
                "chunk_id": "chunk_1",
                "document_id": "doc_1",
                "text": "This is a test document.",
                "metadata": {"page_number": 1, "section": "Introduction"},
                "document_metadata": {
                    "title": "Test Document",
                    "authors": ["Test Author"],
                    "publication_date": "2023-01-01",
                    "document_type": "article",
                },
                "similarity": 0.85,
            }
        ]

        # Call the format_results method
        formatted_results = self.search_manager.format_results(results)

        # Assert that the formatted results are as expected
        self.assertEqual(len(formatted_results), 1)
        self.assertEqual(formatted_results[0]["title"], "Test Document")
        self.assertEqual(formatted_results[0]["authors"], "Test Author")
        self.assertEqual(formatted_results[0]["similarity"], 85)  # 0.85 -> 85%
        self.assertEqual(formatted_results[0]["text"], "This is a test document.")
        self.assertEqual(formatted_results[0]["document_id"], "doc_1")
        self.assertEqual(formatted_results[0]["chunk_id"], "chunk_1")
        self.assertEqual(
            formatted_results[0]["metadata"]["page_number"], 1
        )
        self.assertEqual(
            formatted_results[0]["metadata"]["section"], "Introduction"
        )
        self.assertEqual(
            formatted_results[0]["metadata"]["publication_date"], "2023-01-01"
        )
        self.assertEqual(
            formatted_results[0]["metadata"]["document_type"], "article"
        )


if __name__ == "__main__":
    unittest.main()