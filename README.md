[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/alizdavoodi-mcpdocsearch-badge.png)](https://mseep.ai/app/alizdavoodi-mcpdocsearch)

# Documentation Crawler & MCP Server

This project provides a toolset to crawl websites, generate Markdown documentation, and make that documentation searchable via a Model Context Protocol (MCP) server, designed for integration with tools like Cursor.

## Features

- **Web Crawler (`crawler_cli`)**:
  - Crawls websites starting from a given URL using `crawl4ai`.
  - Configurable crawl depth, URL patterns (include/exclude), content types, etc.
  - Optional cleaning of HTML before Markdown conversion (removes nav links, headers, footers).
  - Generates a single, consolidated Markdown file from crawled content.
  - Saves output to `./storage/` by default.
- **MCP Server (`mcp_server`)**:
  - Loads Markdown files from the `./storage/` directory.
  - Parses Markdown into semantic chunks based on headings.
  - Generates vector embeddings for each chunk using `sentence-transformers` (`multi-qa-mpnet-base-dot-v1`).
  - **Caching:** Utilizes a cache file (`storage/document_chunks_cache.pkl`) to store processed chunks and embeddings.
    - **First Run:** The initial server startup after crawling new documents may take some time as it needs to parse, chunk, and generate embeddings for all content.
    - **Subsequent Runs:** If the cache file exists and the modification times of the source `.md` files in `./storage/` haven't changed, the server loads directly from the cache, resulting in much faster startup times.
    - **Cache Invalidation:** The cache is automatically invalidated and regenerated if any `.md` file in `./storage/` is modified, added, or removed since the cache was last created.
  - Exposes MCP tools via `fastmcp` for clients like Cursor:
    - `list_documents`: Lists available crawled documents.
    - `get_document_headings`: Retrieves the heading structure for a document.
    - `search_documentation`: Performs semantic search over document chunks using vector similarity.
- **Cursor Integration**: Designed to run the MCP server via `stdio` transport for use within Cursor.

## Workflow

1. **Crawl:** Use the `crawler_cli` tool to crawl a website and generate a `.md` file in `./storage/`.
2. **Run Server:** Configure and run the `mcp_server` (typically managed by an MCP client like Cursor).
3. **Load & Embed:** The server automatically loads, chunks, and embeds the content from the `.md` files in `./storage/`.
4. **Query:** Use the MCP client (e.g., Cursor Agent) to interact with the server's tools (`list_documents`, `search_documentation`, etc.) to query the crawled content.

## Setup

This project uses [`uv`](https://github.com/astral-sh/uv) for dependency management and execution.

1. **Install `uv`**: Follow the instructions on the [uv website](https://github.com/astral-sh/uv).
2. **Clone the repository:**

   ```bash
   git clone https://github.com/alizdavoodi/MCPDocSearch.git
   cd MCPDocSearch
   ```

3. **Install dependencies:**

   ```bash
   uv sync
   ```

   This command creates a virtual environment (usually `.venv`) and installs all dependencies listed in `pyproject.toml`.

## Usage

### 1. Crawling Documentation

Run the crawler using the `crawl.py` script or directly via `uv run`.

**Basic Example:**

```bash
uv run python crawl.py https://docs.example.com
```

This will crawl `https://docs.example.com` with default settings and save the output to `./storage/docs.example.com.md`.

**Example with Options:**

```bash
uv run python crawl.py https://docs.another.site --output ./storage/custom_name.md --max-depth 2 --keyword "API" --keyword "Reference" --exclude-pattern "*blog*"
```

**View all options:**

```bash
uv run python crawl.py --help
```

Key options include:

- `--output`/`-o`: Specify output file path.
- `--max-depth`/`-d`: Set crawl depth (must be between 1 and 5).
- `--include-pattern`/`--exclude-pattern`: Filter URLs to crawl.
- `--keyword`/`-k`: Keywords for relevance scoring during crawl.
- `--remove-links`/`--keep-links`: Control HTML cleaning.
- `--cache-mode`: Control `crawl4ai` caching (`DEFAULT`, `BYPASS`, `FORCE_REFRESH`).
- `--wait-for`: Wait for a specific time (seconds) or CSS selector before capturing content (e.g., `5` or `'css:.content'`). Useful for pages with delayed loading.
- `--js-code`: Execute custom JavaScript on the page before capturing content.
- `--page-load-timeout`: Set the maximum time (seconds) to wait for a page to load.
- `--wait-for-js-render`/`--no-wait-for-js-render`: Enable a specific script to better handle JavaScript-heavy Single Page Applications (SPAs) by scrolling and clicking potential "load more" buttons. Automatically sets a default wait time if `--wait-for` is not specified.

#### Refining Crawls with Patterns and Depth

Sometimes, you might want to crawl only a specific subsection of a documentation site. This often requires some trial and error with `--include-pattern` and `--max-depth`.

- **`--include-pattern`**: Restricts the crawler to only follow links whose URLs match the given pattern(s). Use wildcards (`*`) for flexibility.
- **`--max-depth`**: Controls how many "clicks" away from the starting URL the crawler will go. A depth of 1 means it only crawls pages directly linked from the start URL. A depth of 2 means it crawls those pages _and_ pages linked from them (if they also match include patterns), and so on.

**Example: Crawling only the Pulsar Admin API section**

Suppose you want only the content under `https://pulsar.apache.org/docs/4.0.x/admin-api-*`.

1. **Start URL:** You could start at the overview page: `https://pulsar.apache.org/docs/4.0.x/admin-api-overview/`.
2. **Include Pattern:** You only want links containing `admin-api`: `--include-pattern "*admin-api*"`.
3. **Max Depth:** You need to figure out how many levels deep the admin API links go from the starting page. Start with `2` and increase if needed.
4. **Verbose Mode:** Use `-v` to see which URLs are being visited or skipped, which helps debug the patterns and depth.

```bash
uv run python crawl.py https://pulsar.apache.org/docs/4.0.x/admin-api-overview/ -v --include-pattern "*admin-api*" --max-depth 2
```

Check the output file (`./storage/pulsar.apache.org.md` by default in this case). If pages are missing, try increasing `--max-depth` to `3`. If too many unrelated pages are included, make the `--include-pattern` more specific or add `--exclude-pattern` rules.

### 2. Running the MCP Server

The MCP server is designed to be run by an MCP client like Cursor via the `stdio` transport. The command to run the server is:

```bash
python -m mcp_server.main
```

However, it needs to be run from the project's root directory (`MCPDocSearch`) so that Python can find the `mcp_server` module.

## ⚠️ Caution: Embedding Time

The MCP server generates embeddings locally the first time it runs or whenever the source Markdown files in `./storage/` change. This process involves loading a machine learning model and processing all the text chunks.

- **Time Varies:** The time required for embedding generation can vary significantly based on:
  - **Hardware:** Systems with a compatible GPU (CUDA or Apple Silicon/MPS) will be much faster than CPU-only systems.
  - **Data Size:** The total number of Markdown files and their content length directly impacts processing time.
- **Be Patient:** For large documentation sets or on slower hardware, the initial startup (or startup after changes) might take several minutes. Subsequent startups using the cache will be much faster. ⏳


### 3. Configuring Cursor/Claude for Desktop

To use this server with Cursor, create a `.cursor/mcp.json` file in the root of this project (`MCPDocSearch/.cursor/mcp.json`) with the following content:

```json
{
  "mcpServers": {
    "doc-query-server": {
      "command": "uv",
      "args": [
        "--directory",
        // IMPORTANT: Replace with the ABSOLUTE path to this project directory on your machine
        "/path/to/your/MCPDocSearch",
        "run",
        "python",
        "-m",
        "mcp_server.main"
      ],
      "env": {}
    }
  }
}
```

**Explanation:**

- `"doc-query-server"`: A name for the server within Cursor.
- `"command": "uv"`: Specifies `uv` as the command runner.
- `"args"`:
  - `"--directory", "/path/to/your/MCPDocSearch"`: **Crucially**, tells `uv` to change its working directory to your project root before running the command. **Replace `/path/to/your/MCPDocSearch` with the actual absolute path on your system.**
  - `"run", "python", "-m", "mcp_server.main"`: The command `uv` will execute within the correct directory and virtual environment.

After saving this file and restarting Cursor, the "doc-query-server" should become available in Cursor's MCP settings and usable by the Agent (e.g., `@doc-query-server search documentation for "how to install"`).

For Claude for Desktop, you can use this [official documentation](https://modelcontextprotocol.io/quickstart/server#mac-os-linux) to set up the MCP server


## Dependencies

Key libraries used:

- `crawl4ai`: Core web crawling functionality.
- `fastmcp`: MCP server implementation.
- `sentence-transformers`: Generating text embeddings.
- `torch`: Required by `sentence-transformers`.
- `typer`: Building the crawler CLI.
- `uv`: Project and environment management.
- `beautifulsoup4` (via `crawl4ai`): HTML parsing.
- `rich`: Enhanced terminal output.

## Architecture

The project follows this basic flow:

1. **`crawler_cli`**: You run this tool, providing a starting URL and options.
2. **Crawling (`crawl4ai`)**: The tool uses `crawl4ai` to fetch web pages, following links based on configured rules (depth, patterns).
3. **Cleaning (`crawler_cli/markdown.py`)**: Optionally, HTML content is cleaned (removing navigation, links) using BeautifulSoup.
4. **Markdown Generation (`crawl4ai`)**: Cleaned HTML is converted to Markdown.
5. **Storage (`./storage/`)**: The generated Markdown content is saved to a file in the `./storage/` directory.
6. **`mcp_server` Startup**: When the MCP server starts (usually via Cursor's config), it runs `mcp_server/data_loader.py`.
7. **Loading & Caching**: The data loader checks for a cache file (`.pkl`). If valid, it loads chunks and embeddings from the cache. Otherwise, it reads `.md` files from `./storage/`.
8. **Chunking & Embedding**: Markdown files are parsed into chunks based on headings. Embeddings are generated for each chunk using `sentence-transformers` and stored in memory (and saved to cache).
9. **MCP Tools (`mcp_server/mcp_tools.py`)**: The server exposes tools (`list_documents`, `search_documentation`, etc.) via `fastmcp`.
10. **Querying (Cursor)**: An MCP client like Cursor can call these tools. `search_documentation` uses the pre-computed embeddings to find relevant chunks based on semantic similarity to the query.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## Security Notes

- **Pickle Cache:** This project uses Python's `pickle` module to cache processed data (`storage/document_chunks_cache.pkl`). Unpickling data from untrusted sources can be insecure. Ensure that the `./storage/` directory is only writable by trusted users/processes.
