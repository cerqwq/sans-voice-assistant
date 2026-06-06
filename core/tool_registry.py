"""
Tool Registry - Central registration and execution system for all voice assistant tools.
Handles tool discovery, execution, and error reporting to Claude API.
"""

import traceback
from typing import Callable, Any


class ToolRegistry:
    """Central registry for all voice assistant tools."""

    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, definition: dict, handler: Callable):
        """
        Register a tool with its Claude API definition and handler function.

        Args:
            definition: Claude API tool definition dict (name, description, input_schema)
            handler: Callable that executes the tool, takes **kwargs, returns string
        """
        name = definition["name"]
        self._tools[name] = definition
        self._handlers[name] = handler

    def get_tool_definitions(self) -> list[dict]:
        """Get all tool definitions for Claude API."""
        return list(self._tools.values())

    def execute(self, tool_name: str, tool_input: dict) -> dict:
        """
        Execute a tool and return a tool_result dict.

        Returns:
            dict with 'type', 'tool_use_id', 'content', and optionally 'is_error'
        """
        if tool_name not in self._handlers:
            return {
                "type": "tool_result",
                "tool_use_id": "",  # Filled by caller
                "content": f"Unknown tool: {tool_name}. Available: {list(self._handlers.keys())}",
                "is_error": True,
            }

        try:
            handler = self._handlers[tool_name]
            result = handler(**tool_input)
            return {
                "type": "tool_result",
                "tool_use_id": "",  # Filled by caller
                "content": str(result),
            }
        except TypeError as e:
            return {
                "type": "tool_result",
                "tool_use_id": "",
                "content": f"Invalid parameters for {tool_name}: {e}",
                "is_error": True,
            }
        except Exception as e:
            return {
                "type": "tool_result",
                "tool_use_id": "",
                "content": f"Tool error ({tool_name}): {type(e).__name__}: {e}",
                "is_error": True,
            }


def create_default_registry() -> ToolRegistry:
    """Create a registry with all built-in tools."""
    # Ensure tools package is importable
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    from tools.app_launcher import launch_app, APP_LAUNCHER_TOOL
    from tools.weather import get_weather, WEATHER_TOOL
    from tools.system_control import (
        get_volume, set_volume, mute_system, unmute_system,
        get_brightness, set_brightness, lock_screen, shutdown_system,
        restart_system, cancel_shutdown, sleep_system, empty_recycle_bin,
        VOLUME_TOOL, BRIGHTNESS_TOOL, SYSTEM_CONTROL_TOOL,
    )
    from tools.web_search import search_web, WEB_SEARCH_TOOL
    from tools.file_search import search_files, search_file_contents, FILE_SEARCH_TOOL
    from tools.clipboard import get_clipboard, set_clipboard, append_clipboard, CLIPBOARD_TOOL
    from tools.screenshot import take_screenshot, SCREENSHOT_TOOL
    from tools.media_control import (
        play_pause, next_track, previous_track, stop_media,
        get_now_playing, open_spotify, MEDIA_CONTROL_TOOL,
    )
    from tools.datetime_location import get_datetime_location, DATETIME_LOCATION_TOOL
    from tools.memory import TOOL_DEFINITIONS as MEMORY_TOOLS
    from tools.file_operations import (
        read_file, write_file, list_directory, search_files as search_files_op,
        execute_command, execute_python, get_file_info,
        READ_FILE_TOOL, WRITE_FILE_TOOL, LIST_DIRECTORY_TOOL, SEARCH_FILES_TOOL,
        EXECUTE_COMMAND_TOOL, EXECUTE_PYTHON_TOOL, GET_FILE_INFO_TOOL,
    )

    registry = ToolRegistry()

    # Datetime & Location
    registry.register(DATETIME_LOCATION_TOOL, get_datetime_location)

    # App Launcher
    registry.register(APP_LAUNCHER_TOOL, launch_app)

    # Weather
    registry.register(WEATHER_TOOL, get_weather)

    # Volume
    def handle_volume(action: str, level: int = None) -> str:
        if action == "get":
            return get_volume()
        elif action == "set":
            if level is None:
                return "Error: 'level' is required for 'set' action"
            return set_volume(level)
        elif action == "mute":
            return mute_system()
        elif action == "unmute":
            return unmute_system()
        return f"Unknown volume action: {action}"

    registry.register(VOLUME_TOOL, handle_volume)

    # Brightness
    def handle_brightness(action: str, level: int = None) -> str:
        if action == "get":
            return get_brightness()
        elif action == "set":
            if level is None:
                return "Error: 'level' is required for 'set' action"
            return set_brightness(level)
        return f"Unknown brightness action: {action}"

    registry.register(BRIGHTNESS_TOOL, handle_brightness)

    # System Control
    def handle_system(action: str, delay: int = 0) -> str:
        handlers = {
            "lock": lock_screen,
            "shutdown": lambda: shutdown_system(delay),
            "restart": lambda: restart_system(delay),
            "sleep": sleep_system,
            "cancel_shutdown": cancel_shutdown,
            "empty_recycle_bin": empty_recycle_bin,
        }
        handler = handlers.get(action)
        if handler:
            return handler()
        return f"Unknown system action: {action}"

    registry.register(SYSTEM_CONTROL_TOOL, handle_system)

    # Web Search
    registry.register(WEB_SEARCH_TOOL, search_web)

    # File Search
    def handle_file_search(
        query: str,
        search_path: str = None,
        mode: str = "filename",
        extensions: list = None,
    ) -> str:
        if mode == "content":
            return search_file_contents(query, search_path, extensions)
        return search_files(query, search_path, extensions)

    registry.register(FILE_SEARCH_TOOL, handle_file_search)

    # Clipboard
    def handle_clipboard(action: str, text: str = None) -> str:
        if action == "get":
            return get_clipboard()
        elif action == "set":
            if text is None:
                return "Error: 'text' is required for 'set' action"
            return set_clipboard(text)
        elif action == "append":
            if text is None:
                return "Error: 'text' is required for 'append' action"
            return append_clipboard(text)
        return f"Unknown clipboard action: {action}"

    registry.register(CLIPBOARD_TOOL, handle_clipboard)

    # Screenshot
    def handle_screenshot(save_path: str = None, region: dict = None) -> str:
        region_tuple = None
        if region:
            region_tuple = (region["x"], region["y"], region["width"], region["height"])
        return take_screenshot(save_path, region_tuple)

    registry.register(SCREENSHOT_TOOL, handle_screenshot)

    # Media Control
    def handle_media(action: str) -> str:
        handlers = {
            "play_pause": play_pause,
            "next": next_track,
            "previous": previous_track,
            "stop": stop_media,
            "now_playing": get_now_playing,
            "open_spotify": open_spotify,
        }
        handler = handlers.get(action)
        if handler:
            return handler()
        return f"Unknown media action: {action}"

    registry.register(MEDIA_CONTROL_TOOL, handle_media)

    # Memory tools
    for tool_def in MEMORY_TOOLS:
        registry.register(tool_def, tool_def["function"])

    # File Operations (Agent tools)
    registry.register(READ_FILE_TOOL, read_file)
    registry.register(WRITE_FILE_TOOL, write_file)
    registry.register(LIST_DIRECTORY_TOOL, list_directory)
    registry.register(SEARCH_FILES_TOOL, search_files_op)
    registry.register(EXECUTE_COMMAND_TOOL, execute_command)
    registry.register(EXECUTE_PYTHON_TOOL, execute_python)
    registry.register(GET_FILE_INFO_TOOL, get_file_info)

    return registry
