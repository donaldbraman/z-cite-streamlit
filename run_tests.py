#!/usr/bin/env python
"""Script to run tests using uv."""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest>=7.0.0",
#   "chromadb==0.4.22",
#   "sentence-transformers==3.4.1",
#   "numpy<2.0.0",
# ]
# [tool.uv]
# exclude-newer = "2025-03-15T00:00:00Z"
# ///

import os
import subprocess
import sys

def main():
    """Run tests using pytest."""
    print("Running tests with uv...")
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Run pytest
    cmd = ["pytest", "-v"]
    
    # Add any command line arguments
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    # Run the command
    result = subprocess.run(cmd, capture_output=False)
    
    # Return the exit code
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())