# Z-Cite Streamlit Application

A Streamlit application for semantic search of Zotero libraries using ChromaDB and sentence transformers.

## Features

- **Semantic Search**: Search your Zotero libraries using natural language queries
- **Vector Database**: Stores document chunks and embeddings in ChromaDB
- **Document Processing**: OCR, chunking, and embedding generation for Zotero documents
- **User-Friendly Interface**: Simple Streamlit interface for searching and managing libraries

## Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver

### Installation with uv

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/z-cite-streamlit.git
   cd z-cite-streamlit
   ```

2. Create a virtual environment and install the package with uv:
   ```bash
   uv venv
   uv pip install -e ".[dev,test]"
   ```

   This will install the package in development mode, allowing you to make changes to the code without reinstalling.

## Usage

### Running the Application

There are several ways to run the application using uv:

#### Option 1: Using the run_app.py script
```bash
uv run run_app.py
```

#### Option 2: Using the main.py script directly
```bash
uv run --script main.py
```

#### Option 3: Using streamlit directly
```bash
uv run -m streamlit run main.py
```

### Running Tests

You can run tests using the run_tests.py script:

```bash
uv run run_tests.py
```

Or directly with pytest:
```bash
uv run -m pytest
```

### Locking Dependencies

To lock dependencies for reproducible builds:

```bash
uv lock
```

This will create a `uv.lock` file that pins exact versions of all dependencies.

### Syncing the Environment

To update your environment with the latest dependencies:

```bash
uv sync
```

### Searching Documents

1. Enter your search query in the search box
2. Adjust the threshold and results limit if needed
3. Click the "Search" button
4. View the results with highlighted matches

## Project Structure

```
z-cite-streamlit/
├── z_cite_streamlit/
│   ├── __init__.py
│   ├── app.py          # Streamlit application
│   ├── db.py           # ChromaDB integration
│   ├── search.py       # Search functionality
│   └── utils.py        # Utility functions
├── tests/
│   └── __init__.py
├── main.py             # Entry point
├── run_app.py          # Script to run the application
├── run_tests.py        # Script to run tests
├── pyproject.toml      # Project configuration with uv settings
└── README.md           # This file
```

## Development

### Installing Development Dependencies

```bash
uv pip install -e ".[dev,test]"
```

### Running Tests

```bash
uv run run_tests.py
```

### Code Formatting

```bash
uv run -m black z_cite_streamlit tests
```

## License

[MIT License](LICENSE)