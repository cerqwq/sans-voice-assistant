"""
App Launcher Tool - Open applications, files, and URLs on Windows.
No external dependencies required (stdlib only).
"""

import subprocess
import os
import shutil
import webbrowser
from typing import Optional

# Common Windows app aliases
APP_ALIASES = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "control panel": "control.exe",
    "paint": "mspaint.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "edge": "msedge.exe",
    "vscode": "code.exe",
    "settings": "ms-settings:",
}


def find_app(name: str) -> Optional[str]:
    """Resolve an app name to an executable path."""
    name_lower = name.lower().strip()

    # Check aliases first
    if name_lower in APP_ALIASES:
        path = APP_ALIASES[name_lower]
        if path and shutil.which(path):
            return path

    # Try shutil.which (checks PATH)
    if shutil.which(name_lower):
        return name_lower
    if shutil.which(name_lower + ".exe"):
        return name_lower + ".exe"

    return None


def launch_app(name: str, args: Optional[list] = None) -> str:
    """
    Launch an application by name, path, or URL.

    Args:
        name: Application name (e.g. 'notepad'), executable path, or URL
        args: Optional command-line arguments

    Returns:
        Status message string
    """
    # Handle URLs
    if name.startswith(("http://", "https://", "www.")):
        webbrowser.open(name)
        return f"Opened URL: {name}"

    # Handle ms-settings: URIs
    if name.startswith("ms-settings:"):
        os.startfile(name)
        return f"Opened Settings: {name}"

    # Try to find the app
    app_path = find_app(name)

    if app_path:
        try:
            cmd = [app_path] + (args or [])
            subprocess.Popen(cmd, shell=False)
            return f"Launched: {name}"
        except Exception as e:
            return f"Failed to launch {name}: {e}"

    # Fallback: try os.startfile (Windows-specific, handles registered apps)
    try:
        os.startfile(name)
        return f"Opened: {name}"
    except OSError:
        pass

    # Fallback: try shell execution
    try:
        subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)
        return f"Shell-launched: {name}"
    except Exception as e:
        return f"Could not find or launch '{name}': {e}"


def open_file_or_folder(path: str) -> str:
    """Open a file with its default application or a folder in Explorer."""
    try:
        os.startfile(path)
        return f"Opened: {path}"
    except OSError as e:
        return f"Failed to open '{path}': {e}"


# Claude API tool definition
APP_LAUNCHER_TOOL = {
    "name": "launch_app",
    "description": (
        "Launch a Windows application or open a URL. Use when the user says "
        "'open [app]', 'start [app]', 'launch [app]', or 'go to [website]'. "
        "Supports common apps (notepad, calculator, chrome, vscode, etc.), "
        "full paths (C:\\...), and URLs (https://...)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Application name (e.g. 'notepad'), executable path, or URL"
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional command-line arguments"
            }
        },
        "required": ["name"]
    }
}
