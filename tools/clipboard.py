"""
Clipboard Tool - Read and write system clipboard.
Requires: pyperclip
"""

from typing import Optional


def get_clipboard() -> str:
    """Read current clipboard text content."""
    try:
        import pyperclip

        text = pyperclip.paste()
        if not text:
            return "Clipboard is empty"
        # Truncate very long content
        if len(text) > 2000:
            text = text[:2000] + f"\n... (truncated, {len(text)} chars total)"
        return f"Clipboard content:\n{text}"
    except ImportError:
        return "Install pyperclip: pip install pyperclip"
    except Exception as e:
        return f"Clipboard read error: {e}"


def set_clipboard(text: str) -> str:
    """Copy text to the clipboard."""
    try:
        import pyperclip

        pyperclip.copy(text)
        preview = text[:100] + "..." if len(text) > 100 else text
        return f"Copied to clipboard: {preview}"
    except ImportError:
        return "Install pyperclip: pip install pyperclip"
    except Exception as e:
        return f"Clipboard write error: {e}"


def append_clipboard(text: str) -> str:
    """Append text to existing clipboard content."""
    try:
        import pyperclip

        existing = pyperclip.paste()
        new_content = existing + text if existing else text
        pyperclip.copy(new_content)
        return f"Appended to clipboard ({len(text)} chars)"
    except ImportError:
        return "Install pyperclip: pip install pyperclip"
    except Exception as e:
        return f"Clipboard append error: {e}"


# Claude API tool definition
CLIPBOARD_TOOL = {
    "name": "clipboard",
    "description": (
        "Read from or write to the system clipboard. Use when user says "
        "'copy this', 'what's in my clipboard', 'paste', 'remember this', "
        "or when you need to save text for the user to paste elsewhere."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get", "set", "append"],
                "description": "get=read clipboard, set=write to clipboard, append=add to existing",
            },
            "text": {
                "type": "string",
                "description": "Text to write (required for 'set' and 'append' actions)",
            },
        },
        "required": ["action"],
    },
}
