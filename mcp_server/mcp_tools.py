import os
import openai
import sys  # Import sys for stderr
from typing import List, Dict, Union


# Import the shared mcp_server instance using absolute path
from mcp_server.app import mcp_server

# Rename imported function to avoid recursion
from mcp_server.data_loader import (
    get_available_documents,
    get_document_headings as _get_headings_from_loader,
)
from mcp_server.search import search_chunks

# --- Tool Implementations (using decorators) ---


@mcp_server.tool()
def list_documents() -> List[str]:
    """MCP Tool: Lists available documentation markdown files."""
    return get_available_documents()


@mcp_server.tool()
def get_document_headings(filename: str) -> List[Dict[str, Union[int, str]]]:
    """MCP Tool: Retrieves the heading structure for a specified file.

    Args:
        filename: The exact filename from list_documents.
    """
    # Basic validation
    available_docs = get_available_documents()
    if filename not in available_docs:
        # Return empty list or could raise an error formatted for MCP result
        # For simplicity, returning empty list if file not found.
        # Print warnings to stderr to avoid breaking MCP JSON communication
        print(
            f"Warning: get_document_headings called for non-existent file: "
            f"{filename}",
            file=sys.stderr,
        )
        return []
    # Call the renamed imported function
    return _get_headings_from_loader(filename)


@mcp_server.tool()
def search_documentation(
    query: str, filename: str = "", max_results: int = 5
) -> List[Dict[str, Union[str, float]]]:
    """
    MCP Tool: Searches documentation chunks based on a query.

    Returns a list of dicts with filename, heading, content snippet, score,
    and source_url.

    Args:
        query: The natural language question or search query.
        filename: Optional. The specific filename (from list_documents) to
                  search within. If empty, searches all documents.
        max_results: Optional. Maximum number of relevant sections to return
                     (default 5, max 20).
    """
    if max_results < 1:
        max_results = 1
    if max_results > 20:  # Limit max results for performance/context window
        max_results = 20

    # Explicitly treat empty string filename as None (no filter)
    effective_filename = filename if filename else None

    search_results = search_chunks(query, effective_filename, max_results)

    # Format for MCP output (ensure structure matches expected output)
    # The search_chunks function already returns the desired format.
    # Return the full content without truncation.
    formatted_results = []
    for res in search_results:
        formatted_results.append(
            {
                "filename": res["filename"],
                "heading": res["heading"],
                "content": res["content"],  # Use the full content
                "score": float(res["score"]),  # Ensure score is float
                "source_url": res.get("source_url", ""),
            }
        )

    return formatted_results


# No need for register_tools function anymore, decorators handle it.
# The manual __signature__ assignments are also removed as the decorator
# should infer the schema from type hints and docstrings.

