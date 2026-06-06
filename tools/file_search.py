"""
File Search Tool - Search local files by name or content.
Uses pathlib/os.walk for standard search, optional Everything SDK for instant search.
No external dependencies for basic search (stdlib only).
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional


def search_files(
    query: str,
    search_path: Optional[str] = None,
    extensions: Optional[list] = None,
    max_results: int = 50,
) -> str:
    """
    Search for files on the local filesystem by name pattern.

    Args:
        query: Filename pattern or partial name (supports * and ? wildcards)
        search_path: Root directory to search (default: user home)
        extensions: Filter by file extensions (e.g., ['.py', '.txt'])
        max_results: Maximum results to return

    Returns:
        Formatted list of matching files
    """
    if search_path is None:
        search_path = str(Path.home())

    # Build glob pattern
    if not any(c in query for c in "*?"):
        query = f"*{query}*"

    matches = []
    search_root = Path(search_path)

    if not search_root.exists():
        return f"Path does not exist: {search_path}"

    try:
        for path in search_root.rglob(query):
            if not path.is_file():
                continue

            # Filter by extension
            if extensions and path.suffix.lower() not in extensions:
                continue

            try:
                stat = path.stat()
                size = stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                )

                # Format size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"

                matches.append(
                    {"path": str(path), "size": size_str, "modified": modified}
                )
            except (PermissionError, OSError):
                continue

            if len(matches) >= max_results:
                break

    except PermissionError:
        return f"Permission denied accessing: {search_path}"
    except Exception as e:
        return f"Search error: {e}"

    if not matches:
        return f"No files matching '{query}' found in {search_path}"

    output = f"Found {len(matches)} file(s) matching '{query}':\n\n"
    for m in matches:
        output += (
            f"  {m['path']}\n"
            f"    Size: {m['size']}, Modified: {m['modified']}\n"
        )

    return output.strip()


def search_file_contents(
    query: str,
    search_path: Optional[str] = None,
    extensions: Optional[list] = None,
    max_results: int = 20,
) -> str:
    """
    Search for text inside files.

    Args:
        query: Text to search for (case-insensitive)
        search_path: Root directory to search
        extensions: File extensions to search in (default: common text files)
        max_results: Maximum number of matching files

    Returns:
        Formatted results with file paths and matching lines
    """
    if search_path is None:
        search_path = str(Path.home())

    if extensions is None:
        extensions = [
            ".txt", ".py", ".md", ".json", ".yaml", ".yml",
            ".csv", ".log", ".ini", ".cfg", ".toml", ".xml",
            ".html", ".css", ".js", ".ts",
        ]

    matches = []
    query_lower = query.lower()

    try:
        for ext in extensions:
            for path in Path(search_path).rglob(f"*{ext}"):
                if not path.is_file():
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    if query_lower in text.lower():
                        # Find matching lines
                        lines = []
                        for i, line in enumerate(text.splitlines(), 1):
                            if query_lower in line.lower():
                                lines.append(f"    L{i}: {line.strip()[:120]}")
                                if len(lines) >= 3:
                                    break

                        matches.append({"path": str(path), "lines": lines})

                        if len(matches) >= max_results:
                            break
                except (PermissionError, UnicodeDecodeError, OSError):
                    continue

            if len(matches) >= max_results:
                break

    except Exception as e:
        return f"Content search error: {e}"

    if not matches:
        return f"No files containing '{query}' found in {search_path}"

    output = f"Found '{query}' in {len(matches)} file(s):\n\n"
    for m in matches:
        output += f"  {m['path']}\n"
        for line in m["lines"]:
            output += f"  {line}\n"
        output += "\n"

    return output.strip()


def search_with_everything(query: str, max_results: int = 20) -> str:
    """
    Search using Voidtools Everything (instant, requires Everything running).

    Requires:
        - Voidtools Everything installed and running
        - Everything SDK DLL (Everything64.dll) in PATH or script directory
    """
    try:
        import ctypes

        dll_paths = [
            "Everything64.dll",
            os.path.join(os.path.dirname(__file__), "Everything64.dll"),
            r"C:\Program Files\Everything\Everything64.dll",
        ]

        dll = None
        for p in dll_paths:
            try:
                dll = ctypes.WinDLL(p)
                break
            except OSError:
                continue

        if dll is None:
            return (
                "Everything SDK not found. Install Voidtools Everything and "
                "place Everything64.dll in the script directory."
            )

        dll.Everything_SetSearchW(query)
        dll.Everything_SetMax(max_results)
        dll.Everything_QueryW(1)

        num_results = dll.Everything_GetNumResults()
        if num_results == 0:
            return f"No results for '{query}' in Everything"

        output = f"Everything found {num_results} result(s) for '{query}':\n\n"

        buf = ctypes.create_unicode_buffer(260)
        for i in range(min(num_results, max_results)):
            dll.Everything_GetResultFullPathNameW(i, buf, 260)
            output += f"  {buf.value}\n"

        return output.strip()

    except Exception as e:
        return f"Everything search error: {e}"


# Claude API tool definition
FILE_SEARCH_TOOL = {
    "name": "search_files",
    "description": (
        "Search for files on the computer by name or content. Use when user says "
        "'find file', 'search for', 'where is my file', 'locate', or 'find text in files'. "
        "Supports wildcard patterns (* and ?). Searches recursively from a starting directory."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Filename pattern or text to search for, e.g. '*.py', 'report', 'TODO'",
            },
            "search_path": {
                "type": "string",
                "description": "Directory to search in (default: user home folder)",
            },
            "mode": {
                "type": "string",
                "enum": ["filename", "content"],
                "description": "Search by filename or file content (default: filename)",
            },
            "extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by extensions, e.g. ['.py', '.txt']",
            },
        },
        "required": ["query"],
    },
}
