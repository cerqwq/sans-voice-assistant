# Voice Assistant Toolkit Reference

Practical implementations for a Python voice assistant on Windows, integrated with Claude API tool calling.

## Table of Contents

1. [Claude API Tool Calling Architecture](#1-claude-api-tool-calling-architecture)
2. [App Launcher](#2-app-launcher)
3. [Weather](#3-weather)
4. [System Control](#4-system-control)
5. [Web Search](#5-web-search)
6. [File Search](#6-file-search)
7. [Clipboard](#7-clipboard)
8. [Screenshot](#8-screenshot)
9. [Music/Media Control](#9-musicmedia-control)
10. [Tool Registry & Error Handling](#10-tool-registry--error-handling)

---

## 1. Claude API Tool Calling Architecture

### Tool Definition Schema

Every tool registered with Claude follows this JSON schema format:

```json
{
  "name": "tool_name",
  "description": "Clear description of what the tool does and when to use it.",
  "input_schema": {
    "type": "object",
    "properties": {
      "param1": {
        "type": "string",
        "description": "What this parameter is for"
      },
      "param2": {
        "type": "integer",
        "description": "Another parameter",
        "default": 10
      }
    },
    "required": ["param1"]
  }
}
```

### Conversation Flow

```
User message --> Claude API (with tools) --> Claude returns tool_use block
                                              |
                         You execute the tool locally
                                              |
                         You send tool_result back --> Claude formulates final answer
```

### Complete Tool Use Loop (Python)

```python
import anthropic

client = anthropic.Anthropic()

# Step 1: Define tools
tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a city. Use when user asks about weather conditions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. 'Beijing' or 'New York'"}
            },
            "required": ["city"]
        }
    }
]

# Step 2: Send message with tools
messages = [{"role": "user", "content": "What's the weather in Tokyo?"}]
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=tools,
    messages=messages
)

# Step 3: Handle tool_use blocks
if response.stop_reason == "tool_use":
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            try:
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })
            except Exception as e:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"Error: {e}",
                    "is_error": True
                })

    # Step 4: Send results back
    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})
    final = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )
    print(final.content[0].text)
```

### Best Practices for Tool Descriptions

- State WHAT the tool does AND WHEN to use it
- Include examples of user queries that should trigger it
- Mention limitations or when NOT to use it
- Keep parameter descriptions specific with format examples
- Use enums to constrain value sets where possible

Good description example:
```
"Search the web for information. Use when the user asks about current events, 
facts you're unsure about, or anything requiring up-to-date information. 
Do NOT use for local file searches or app control."
```

---

## 2. App Launcher

### Implementation

```python
# tools/app_launcher.py

import subprocess
import os
import shutil
import webbrowser
from typing import Optional

# Common app paths on Windows
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
    "chrome": None,  # Found via shutil.which or registry
    "firefox": None,
    "edge": "msedge.exe",
    "vscode": "code.exe",
    "spotify": None,
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
    
    # Try with .exe extension
    if shutil.which(name_lower + ".exe"):
        return name_lower + ".exe"
    
    # Try os.startfile for registered apps
    return None


def launch_app(name: str, args: Optional[list] = None) -> str:
    """
    Launch an application by name.
    
    Args:
        name: Application name or path
        args: Optional command-line arguments
    
    Returns:
        Status message string
    """
    # Handle URLs
    if name.startswith(("http://", "https://", "www.")):
        webbrowser.open(name)
        return f"Opened URL: {name}"
    
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
```

### Required Packages

```
# All built-in - no extra packages needed
# subprocess, os, shutil, webbrowser are all stdlib
```

---

## 3. Weather

### Implementation (wttr.in - No API Key Required)

```python
# tools/weather.py

import requests
from typing import Optional

def get_weather(city: str, days: int = 1) -> str:
    """
    Get weather information for a city using wttr.in (free, no API key).
    
    Args:
        city: City name (e.g., 'Beijing', 'New York', 'Tokyo')
        days: Number of forecast days (1-3)
    
    Returns:
        Human-readable weather summary string
    """
    try:
        headers = {"User-Agent": "curl/8.0"}
        
        # Get JSON data
        url = f"https://wttr.in/{requests.utils.quote(city)}?format=j1"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Current conditions
        current = data["current_condition"][0]
        temp_c = current["temp_C"]
        temp_f = current["temp_F"]
        humidity = current["humidity"]
        wind_kmph = current["windspeedKmph"]
        desc = current["weatherDesc"][0]["value"]
        feels_c = current["FeelsLikeC"]
        
        result = (
            f"Weather in {city}:\n"
            f"  Condition: {desc}\n"
            f"  Temperature: {temp_c}C ({temp_f}F), feels like {feels_c}C\n"
            f"  Humidity: {humidity}%\n"
            f"  Wind: {wind_kmph} km/h\n"
        )
        
        # Forecast
        if days > 1:
            result += "\nForecast:\n"
            for day in data["weather"][:days]:
                date = day["date"]
                max_t = day["maxtempC"]
                min_t = day["mintempC"]
                day_desc = day["hourly"][4]["weatherDesc"][0]["value"]
                result += f"  {date}: {min_t}C - {max_t}C, {day_desc}\n"
        
        return result.strip()
    
    except requests.RequestException as e:
        return f"Weather service error: {e}"
    except (KeyError, IndexError) as e:
        return f"Failed to parse weather data: {e}"


def get_weather_compact(city: str) -> str:
    """Get a one-line weather summary."""
    try:
        headers = {"User-Agent": "curl/8.0"}
        resp = requests.get(
            f"https://wttr.in/{requests.utils.quote(city)}?format=3",
            headers=headers, timeout=10
        )
        return resp.text.strip()
    except Exception as e:
        return f"Weather error: {e}"


# Claude API tool definition
WEATHER_TOOL = {
    "name": "get_weather",
    "description": (
        "Get current weather and forecast for a city. Use when the user asks "
        "about weather, temperature, rain, forecast, or 'should I bring an umbrella'. "
        "Uses wttr.in service (free, no API key). Supports any city worldwide."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City name, e.g. 'Beijing', 'New York', 'Tokyo'"
            },
            "days": {
                "type": "integer",
                "description": "Forecast days (1-3, default 1)",
                "default": 1
            }
        },
        "required": ["city"]
    }
}
```

### Alternative: OpenWeatherMap API (Requires API Key)

```python
# tools/weather_owm.py

import requests
from typing import Optional

OPENWEATHER_API_KEY = "YOUR_API_KEY_HERE"  # Get from openweathermap.org

def get_weather_owm(city: str, units: str = "metric") -> str:
    """Get weather from OpenWeatherMap (requires free API key)."""
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": units  # metric, imperial, standard
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc = data["weather"][0]["description"]
        wind = data["wind"]["speed"]
        unit_sym = "C" if units == "metric" else "F"
        
        return (
            f"Weather in {city}: {desc}\n"
            f"Temperature: {temp}{unit_sym} (feels like {feels}{unit_sym})\n"
            f"Humidity: {humidity}%, Wind: {wind} m/s"
        )
    except Exception as e:
        return f"Weather error: {e}"
```

### Required Packages

```
pip install requests
```

---

## 4. System Control

### Implementation

```python
# tools/system_control.py

import subprocess
import ctypes
import os
from typing import Optional

# ============================================================
# VOLUME CONTROL (pycaw)
# ============================================================

def _get_volume_interface():
    """Get the Windows audio endpoint volume interface."""
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def get_volume() -> str:
    """Get current system volume (0-100)."""
    try:
        volume = _get_volume_interface()
        current = volume.GetMasterVolumeLevelScalar()  # 0.0 to 1.0
        percent = int(current * 100)
        muted = volume.GetMute()
        status = " (MUTED)" if muted else ""
        return f"Volume: {percent}%{status}"
    except Exception as e:
        return f"Volume error: {e}"


def set_volume(percent: int) -> str:
    """Set system volume (0-100)."""
    try:
        percent = max(0, min(100, percent))
        volume = _get_volume_interface()
        volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
        return f"Volume set to {percent}%"
    except Exception as e:
        return f"Volume error: {e}"


def mute_system() -> str:
    """Mute system audio."""
    try:
        volume = _get_volume_interface()
        volume.SetMute(1, None)
        return "System muted"
    except Exception as e:
        return f"Mute error: {e}"


def unmute_system() -> str:
    """Unmute system audio."""
    try:
        volume = _get_volume_interface()
        volume.SetMute(0, None)
        return "System unmuted"
    except Exception as e:
        return f"Unmute error: {e}"


# ============================================================
# BRIGHTNESS CONTROL
# ============================================================

def get_brightness() -> str:
    """Get current screen brightness percentage."""
    try:
        import screen_brightness_control as sbc
        brightness = sbc.get_brightness()
        # Returns list (one per display); use first
        current = brightness[0] if isinstance(brightness, list) else brightness
        return f"Brightness: {current}%"
    except ImportError:
        return "Install screen_brightness_control: pip install screen-brightness-control"
    except Exception as e:
        return f"Brightness error: {e}"


def set_brightness(percent: int) -> str:
    """Set screen brightness (0-100)."""
    try:
        import screen_brightness_control as sbc
        percent = max(0, min(100, percent))
        sbc.set_brightness(percent)
        return f"Brightness set to {percent}%"
    except ImportError:
        return "Install screen_brightness_control: pip install screen-brightness-control"
    except Exception as e:
        return f"Brightness error: {e}"


# ============================================================
# SYSTEM ACTIONS
# ============================================================

def lock_screen() -> str:
    """Lock the Windows workstation."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return "Screen locked"
    except Exception as e:
        return f"Lock error: {e}"


def shutdown_system(delay: int = 0, force: bool = True) -> str:
    """Shutdown the computer."""
    try:
        flags = f"/s /t {delay}"
        if force:
            flags += " /f"
        subprocess.run(["shutdown"] + flags.split(), check=True)
        return f"Shutdown initiated (delay: {delay}s)"
    except Exception as e:
        return f"Shutdown error: {e}"


def restart_system(delay: int = 0, force: bool = True) -> str:
    """Restart the computer."""
    try:
        flags = f"/r /t {delay}"
        if force:
            flags += " /f"
        subprocess.run(["shutdown"] + flags.split(), check=True)
        return f"Restart initiated (delay: {delay}s)"
    except Exception as e:
        return f"Restart error: {e}"


def cancel_shutdown() -> str:
    """Cancel a pending shutdown/restart."""
    try:
        subprocess.run(["shutdown", "/a"], check=True)
        return "Shutdown/restart cancelled"
    except Exception as e:
        return f"Cancel error: {e}"


def sleep_system() -> str:
    """Put the system to sleep."""
    try:
        subprocess.run(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            check=True
        )
        return "System going to sleep"
    except Exception as e:
        return f"Sleep error: {e}"


def empty_recycle_bin() -> str:
    """Empty the Recycle Bin."""
    try:
        import winshell
        winshell.recycle_bin().empty(confirm=False, show_progress=False)
        return "Recycle bin emptied"
    except ImportError:
        return "Install winshell: pip install winshell"
    except Exception as e:
        return f"Recycle bin error: {e}"


# Claude API tool definitions
VOLUME_TOOL = {
    "name": "system_volume",
    "description": (
        "Control system volume. Use when user says 'volume up/down', 'mute', "
        "'unmute', 'set volume to X', or asks 'what's the volume'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get", "set", "mute", "unmute"],
                "description": "Action to perform"
            },
            "level": {
                "type": "integer",
                "description": "Volume level 0-100 (only for 'set' action)"
            }
        },
        "required": ["action"]
    }
}

BRIGHTNESS_TOOL = {
    "name": "screen_brightness",
    "description": (
        "Control screen brightness. Use when user says 'brightness up/down', "
        "'dim the screen', 'set brightness to X%'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get", "set"],
                "description": "Action to perform"
            },
            "level": {
                "type": "integer",
                "description": "Brightness level 0-100 (only for 'set' action)"
            }
        },
        "required": ["action"]
    }
}

SYSTEM_CONTROL_TOOL = {
    "name": "system_control",
    "description": (
        "Control Windows system: lock screen, shutdown, restart, sleep, "
        "cancel shutdown, or empty recycle bin. Use when user says "
        "'lock screen', 'shut down', 'restart', 'sleep', etc. "
        "WARNING: shutdown/restart will close all applications!"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["lock", "shutdown", "restart", "sleep", "cancel_shutdown", "empty_recycle_bin"],
                "description": "System action to perform"
            },
            "delay": {
                "type": "integer",
                "description": "Delay in seconds before shutdown/restart (default 0 = immediate)",
                "default": 0
            }
        },
        "required": ["action"]
    }
}
```

### Required Packages

```
pip install pycaw comtypes screen-brightness-control winshell
```

---

## 5. Web Search

### Implementation (DuckDuckGo - No API Key Required)

```python
# tools/web_search.py

from typing import Optional

def search_web(query: str, max_results: int = 5, region: str = "wt-wt") -> str:
    """
    Search the web using DuckDuckGo (free, no API key).
    
    Args:
        query: Search query string
        max_results: Maximum number of results (1-20)
        region: Region code (e.g., 'wt-wt' for worldwide, 'cn-zh' for China)
    
    Returns:
        Formatted search results string
    """
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(
                keywords=query,
                region=region,
                safesearch="moderate",
                max_results=min(max_results, 20)
            ))
        
        if not results:
            return f"No results found for: {query}"
        
        output = f"Search results for '{query}':\n\n"
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            href = r.get("href", "")
            body = r.get("body", "No description")
            output += f"{i}. {title}\n   URL: {href}\n   {body}\n\n"
        
        return output.strip()
    
    except ImportError:
        return "Install duckduckgo-search: pip install duckduckgo-search"
    except Exception as e:
        return f"Search error: {e}"


def search_news(query: str, max_results: int = 5) -> str:
    """Search for recent news articles."""
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.news(
                keywords=query,
                safesearch="moderate",
                max_results=min(max_results, 10)
            ))
        
        if not results:
            return f"No news found for: {query}"
        
        output = f"News results for '{query}':\n\n"
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            source = r.get("source", "Unknown")
            date = r.get("date", "")
            body = r.get("body", "")
            output += f"{i}. [{source}] {title}\n   {date}\n   {url}\n   {body[:150]}...\n\n"
        
        return output.strip()
    
    except Exception as e:
        return f"News search error: {e}"


# Claude API tool definition
WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Search the web for information. Use when the user asks about current events, "
        "facts you're unsure about, recent news, or anything requiring up-to-date "
        "information. Also use for 'look up', 'search for', 'find information about'. "
        "Do NOT use for local file searches."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query, e.g. 'Python 3.12 new features'"
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results (1-20, default 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }
}
```

### Required Packages

```
pip install duckduckgo-search
```

---

## 6. File Search

### Implementation

```python
# tools/file_search.py

import os
import glob
from pathlib import Path
from typing import Optional
from datetime import datetime

def search_files(
    query: str,
    search_path: str = None,
    extensions: list = None,
    max_results: int = 50
) -> str:
    """
    Search for files on the local filesystem.
    
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
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                
                # Format size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024*1024):.1f} MB"
                
                matches.append({
                    "path": str(path),
                    "size": size_str,
                    "modified": modified
                })
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
        output += f"  {m['path']}\n    Size: {m['size']}, Modified: {m['modified']}\n"
    
    return output.strip()


def search_file_contents(
    query: str,
    search_path: str = None,
    extensions: list = None,
    max_results: int = 20
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
        extensions = [".txt", ".py", ".md", ".json", ".yaml", ".yml",
                      ".csv", ".log", ".ini", ".cfg", ".toml", ".xml",
                      ".html", ".css", ".js", ".ts"]
    
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
                        
                        matches.append({
                            "path": str(path),
                            "lines": lines
                        })
                        
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
        
        # Try to load Everything SDK
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
        
        # Search
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
                "description": "Filename pattern or text to search for, e.g. '*.py', 'report', 'TODO'"
            },
            "search_path": {
                "type": "string",
                "description": "Directory to search in (default: user home folder)"
            },
            "mode": {
                "type": "string",
                "enum": ["filename", "content"],
                "description": "Search by filename or file content (default: filename)"
            },
            "extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by extensions, e.g. ['.py', '.txt']"
            }
        },
        "required": ["query"]
    }
}
```

### Required Packages

```
# Core: all built-in (os, glob, pathlib, datetime)
# Optional: Everything SDK for instant search (requires Voidtools Everything installed)
```

---

## 7. Clipboard

### Implementation

```python
# tools/clipboard.py

import subprocess
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
                "description": "get=read clipboard, set=write to clipboard, append=add to existing"
            },
            "text": {
                "type": "string",
                "description": "Text to write (required for 'set' and 'append' actions)"
            }
        },
        "required": ["action"]
    }
}
```

### Required Packages

```
pip install pyperclip
```

### Note: pyperclip uses ctypes on Windows (no extra dependencies)

---

## 8. Screenshot

### Implementation

```python
# tools/screenshot.py

import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

SCREENSHOT_DIR = Path.home() / "Screenshots"


def take_screenshot(
    save_path: Optional[str] = None,
    region: Optional[tuple] = None,
    method: str = "mss"
) -> str:
    """
    Take a screenshot of the screen or a region.
    
    Args:
        save_path: Where to save (default: ~/Screenshots/timestamp.png)
        region: Optional (x, y, width, height) tuple for region capture
        method: 'mss' (fast) or 'pil' (Pillow)
    
    Returns:
        Path to saved screenshot
    """
    # Ensure save directory exists
    if save_path is None:
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = str(SCREENSHOT_DIR / f"screenshot_{timestamp}.png")
    
    try:
        if method == "mss":
            return _screenshot_mss(save_path, region)
        else:
            return _screenshot_pil(save_path, region)
    except Exception as e:
        return f"Screenshot error: {e}"


def _screenshot_mss(save_path: str, region: Optional[tuple] = None) -> str:
    """Fast screenshot using mss library."""
    try:
        import mss
        import mss.tools
        
        with mss.mss() as sct:
            if region:
                # mss uses dict format: {"left": x, "top": y, "width": w, "height": h}
                monitor = {
                    "left": region[0],
                    "top": region[1],
                    "width": region[2],
                    "height": region[3]
                }
            else:
                monitor = sct.monitors[0]  # Full screen (all monitors)
            
            screenshot = sct.grab(monitor)
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_path)
        
        return f"Screenshot saved: {save_path}"
    except ImportError:
        return "Install mss: pip install mss"


def _screenshot_pil(save_path: str, region: Optional[tuple] = None) -> str:
    """Screenshot using Pillow (ImageGrab)."""
    try:
        from PIL import ImageGrab
        
        if region:
            # PIL uses (left, top, right, bottom)
            bbox = (region[0], region[1],
                    region[0] + region[2], region[1] + region[3])
            img = ImageGrab.grab(bbox=bbox)
        else:
            img = ImageGrab.grab()
        
        img.save(save_path)
        return f"Screenshot saved: {save_path}"
    except ImportError:
        return "Install Pillow: pip install Pillow"


def take_screenshot_to_clipboard() -> str:
    """Take a screenshot and copy to clipboard."""
    try:
        from PIL import ImageGrab
        import win32clipboard
        from io import BytesIO
        
        img = ImageGrab.grab()
        
        # Copy to clipboard as bitmap
        output = BytesIO()
        img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]  # BMP header offset
        output.close()
        
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        
        return "Screenshot copied to clipboard"
    except ImportError:
        return "Install Pillow and pywin32: pip install Pillow pywin32"
    except Exception as e:
        return f"Clipboard screenshot error: {e}"


# Claude API tool definition
SCREENSHOT_TOOL = {
    "name": "take_screenshot",
    "description": (
        "Capture a screenshot of the screen. Use when user says 'screenshot', "
        "'capture screen', 'take a picture of the screen', or 'screen capture'. "
        "Can capture full screen or a specific region."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "region": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Left edge pixel coordinate"},
                    "y": {"type": "integer", "description": "Top edge pixel coordinate"},
                    "width": {"type": "integer", "description": "Region width in pixels"},
                    "height": {"type": "integer", "description": "Region height in pixels"}
                },
                "description": "Region to capture (omit for full screen)"
            },
            "save_path": {
                "type": "string",
                "description": "Custom save path (default: ~/Screenshots/)"
            }
        },
        "required": []
    }
}
```

### Required Packages

```
pip install mss Pillow pywin32
```

---

## 9. Music/Media Control

### Implementation

```python
# tools/media_control.py

import time
import subprocess
from typing import Optional

# ============================================================
# MEDIA KEY SIMULATION (works with any media player)
# ============================================================

def _press_media_key(key_name: str) -> str:
    """Simulate a media key press using pynput."""
    try:
        from pynput.keyboard import Key, Controller
        
        key_map = {
            "play_pause": Key.media_play_pause,
            "next": Key.media_next,
            "previous": Key.media_previous,
            "stop": Key.media_stop,
            "volume_up": Key.media_volume_up,
            "volume_down": Key.media_volume_down,
            "mute": Key.media_volume_mute,
        }
        
        if key_name not in key_map:
            return f"Unknown media key: {key_name}"
        
        keyboard = Controller()
        key = key_map[key_name]
        keyboard.press(key)
        time.sleep(0.05)
        keyboard.release(key)
        return f"Media key: {key_name}"
    
    except ImportError:
        return "Install pynput: pip install pynput"
    except Exception as e:
        return f"Media key error: {e}"


def play_pause() -> str:
    """Toggle play/pause for current media player."""
    return _press_media_key("play_pause")


def next_track() -> str:
    """Skip to next track."""
    return _press_media_key("next")


def previous_track() -> str:
    """Go to previous track."""
    return _press_media_key("previous")


def stop_media() -> str:
    """Stop media playback."""
    return _press_media_key("stop")


# ============================================================
# WINDOWS MEDIA SESSION (SMTC) - Get Now Playing info
# ============================================================

def get_now_playing() -> str:
    """
    Get information about currently playing media via Windows SMTC.
    Works with Spotify, Windows Media Player, Edge, Chrome, etc.
    """
    try:
        import asyncio
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as SessionManager
        )
        
        async def _get_info():
            manager = await SessionManager.request_async()
            session = manager.get_current_session()
            if session is None:
                return "No active media session"
            
            info = await session.try_get_media_properties_async()
            playback = session.get_playback_info()
            
            status_map = {
                4: "Playing",
                5: "Paused",
                1: "Stopped",
            }
            status_code = playback.playback_status
            status = status_map.get(status_code, f"Status {status_code}")
            
            return (
                f"Now Playing ({status}):\n"
                f"  Title: {info.title}\n"
                f"  Artist: {info.artist}\n"
                f"  Album: {info.album_title}"
            )
        
        return asyncio.run(_get_info())
    
    except ImportError:
        return "Install winsdk: pip install winsdk"
    except Exception as e:
        return f"Now playing error: {e}"


# ============================================================
# SPOTIFY CONTROL (via subprocess/CLI)
# ============================================================

def spotify_control(action: str) -> str:
    """
    Control Spotify via Windows media commands.
    Actions: play, pause, next, previous, mute, unmute
    """
    try:
        # Use keyboard library for media keys
        import keyboard
        
        key_map = {
            "play": "play/pause media",
            "pause": "play/pause media",
            "next": "next track media",
            "previous": "previous track media",
            "stop": "stop media",
        }
        
        if action not in key_map:
            return f"Unknown Spotify action: {action}"
        
        keyboard.press_and_release(key_map[action])
        return f"Spotify: {action}"
    
    except ImportError:
        return "Install keyboard: pip install keyboard"
    except Exception as e:
        return f"Spotify control error: {e}"


def open_spotify() -> str:
    """Launch Spotify application."""
    try:
        import os
        # Common Spotify paths
        paths = [
            os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
            r"C:\Users\{}\AppData\Roaming\Spotify\Spotify.exe".format(os.getenv("USERNAME")),
        ]
        for path in paths:
            if os.path.exists(path):
                os.startfile(path)
                return "Spotify launched"
        
        # Fallback: try to start via shell
        subprocess.Popen(["start", "spotify"], shell=True)
        return "Spotify launch requested"
    except Exception as e:
        return f"Spotify launch error: {e}"


# ============================================================
# PLAY SOUND FILE
# ============================================================

def play_sound(file_path: str) -> str:
    """Play a WAV or MP3 sound file."""
    try:
        if file_path.endswith(".wav"):
            import winsound
            winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return f"Playing: {file_path}"
        else:
            # For MP3 and other formats, use pygame or playsound
            try:
                from playsound import playsound
                playsound(file_path, block=False)
                return f"Playing: {file_path}"
            except ImportError:
                return "Install playsound: pip install playsound"
    except Exception as e:
        return f"Sound playback error: {e}"


# Claude API tool definition
MEDIA_CONTROL_TOOL = {
    "name": "media_control",
    "description": (
        "Control media playback (Spotify, Windows Media Player, browser audio, etc.). "
        "Use when user says 'play', 'pause', 'next song', 'previous song', 'stop music', "
        "'what's playing', 'open spotify', or other media-related commands. "
        "Works with any media player that supports Windows media keys."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "play_pause", "next", "previous", "stop",
                    "now_playing", "open_spotify"
                ],
                "description": "Media action to perform"
            }
        },
        "required": ["action"]
    }
}
```

### Required Packages

```
pip install pynput keyboard winsdk playsound
```

---

## 10. Tool Registry & Error Handling

### Unified Tool Registry

```python
# core/tool_registry.py

import json
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
                "is_error": True
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
                "is_error": True
            }
        except Exception as e:
            return {
                "type": "tool_result",
                "tool_use_id": "",
                "content": f"Tool error ({tool_name}): {type(e).__name__}: {e}",
                "is_error": True
            }


# ============================================================
# Initialize registry with all tools
# ============================================================

def create_default_registry() -> ToolRegistry:
    """Create a registry with all built-in tools."""
    from tools.app_launcher import launch_app, APP_LAUNCHER_TOOL
    from tools.weather import get_weather, WEATHER_TOOL
    from tools.system_control import (
        get_volume, set_volume, mute_system, unmute_system,
        get_brightness, set_brightness, lock_screen, shutdown_system,
        restart_system, cancel_shutdown, sleep_system, empty_recycle_bin,
        VOLUME_TOOL, BRIGHTNESS_TOOL, SYSTEM_CONTROL_TOOL
    )
    from tools.web_search import search_web, search_news, WEB_SEARCH_TOOL
    from tools.file_search import search_files, search_file_contents, FILE_SEARCH_TOOL
    from tools.clipboard import get_clipboard, set_clipboard, append_clipboard, CLIPBOARD_TOOL
    from tools.screenshot import take_screenshot, SCREENSHOT_TOOL
    from tools.media_control import (
        play_pause, next_track, previous_track, stop_media,
        get_now_playing, open_spotify, MEDIA_CONTROL_TOOL
    )
    
    registry = ToolRegistry()
    
    # App Launcher
    registry.register(APP_LAUNCHER_TOOL, launch_app)
    
    # Weather
    registry.register(WEATHER_TOOL, get_weather)
    
    # System Control
    registry.register(VOLUME_TOOL, lambda action, level=None: {
        "get": get_volume,
        "set": lambda: set_volume(level),
        "mute": mute_system,
        "unmute": unmute_system,
    }.get(action, lambda: "Unknown volume action")())
    
    registry.register(BRIGHTNESS_TOOL, lambda action, level=None: {
        "get": get_brightness,
        "set": lambda: set_brightness(level),
    }.get(action, lambda: "Unknown brightness action")())
    
    registry.register(SYSTEM_CONTROL_TOOL, lambda action, delay=0: {
        "lock": lock_screen,
        "shutdown": lambda: shutdown_system(delay),
        "restart": lambda: restart_system(delay),
        "sleep": sleep_system,
        "cancel_shutdown": cancel_shutdown,
        "empty_recycle_bin": empty_recycle_bin,
    }.get(action, lambda: "Unknown system action")())
    
    # Web Search
    registry.register(WEB_SEARCH_TOOL, search_web)
    
    # File Search
    registry.register(FILE_SEARCH_TOOL, lambda query, search_path=None, mode="filename", extensions=None: 
        search_file_contents(query, search_path, extensions) if mode == "content"
        else search_files(query, search_path, extensions))
    
    # Clipboard
    registry.register(CLIPBOARD_TOOL, lambda action, text=None: {
        "get": get_clipboard,
        "set": lambda: set_clipboard(text),
        "append": lambda: append_clipboard(text),
    }.get(action, lambda: "Unknown clipboard action")())
    
    # Screenshot
    registry.register(SCREENSHOT_TOOL, lambda save_path=None, region=None:
        take_screenshot(save_path, (region["x"], region["y"], region["width"], region["height"]) if region else None))
    
    # Media Control
    registry.register(MEDIA_CONTROL_TOOL, lambda action: {
        "play_pause": play_pause,
        "next": next_track,
        "previous": previous_track,
        "stop": stop_media,
        "now_playing": get_now_playing,
        "open_spotify": open_spotify,
    }.get(action, lambda: "Unknown media action")())
    
    return registry
```

### Complete Voice Assistant Loop

```python
# core/assistant.py

import anthropic
from core.tool_registry import create_default_registry

class VoiceAssistant:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic()
        self.model = model
        self.registry = create_default_registry()
        self.messages = []
        self.system_prompt = (
            "You are a helpful voice assistant running on Windows. "
            "You can control the computer, search the web, manage files, "
            "and control media. Be concise in your responses since they "
            "will be spoken aloud via text-to-speech."
        )
    
    def chat(self, user_message: str) -> str:
        """Send a message and handle any tool calls."""
        self.messages.append({"role": "user", "content": user_message})
        
        # First call - Claude may request tool use
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt,
            tools=self.registry.get_tool_definitions(),
            messages=self.messages
        )
        
        # Process tool calls in a loop (Claude may call multiple tools)
        while response.stop_reason == "tool_use":
            # Collect tool results
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self.registry.execute(block.name, block.input)
                    result["tool_use_id"] = block.id
                    tool_results.append(result)
            
            # Append assistant response and tool results
            self.messages.append({"role": "assistant", "content": response.content})
            self.messages.append({"role": "user", "content": tool_results})
            
            # Next call
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                tools=self.registry.get_tool_definitions(),
                messages=self.messages
            )
        
        # Extract final text response
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text
        
        self.messages.append({"role": "assistant", "content": response.content})
        return final_text


# Usage
if __name__ == "__main__":
    assistant = VoiceAssistant()
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ("quit", "exit", "bye"):
            break
        response = assistant.chat(user_input)
        print(f"Assistant: {response}")
```

---

## Package Installation Summary

```
pip install anthropic requests pyperclip mss Pillow pycaw comtypes pywin32 pynput keyboard duckduckgo-search screen-brightness-control winsdk playsound winshell
```

Breakdown by tool:

| Tool | Packages |
|------|----------|
| App Launcher | (none - stdlib only) |
| Weather | `requests` |
| Volume | `pycaw`, `comtypes` |
| Brightness | `screen-brightness-control` |
| System Control | (stdlib: `ctypes`, `subprocess`) |
| Web Search | `duckduckgo-search` |
| File Search | (stdlib: `pathlib`, `os`, `glob`) |
| Clipboard | `pyperclip` |
| Screenshot | `mss`, `Pillow`, `pywin32` |
| Media Control | `pynput`, `keyboard`, `winsdk` |

---

## Error Handling Patterns

### Pattern 1: Graceful Degradation

```python
def safe_tool(func):
    """Decorator that catches all errors and returns user-friendly messages."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ImportError as e:
            return f"Missing package. Run: pip install {e.name}"
        except PermissionError:
            return "Permission denied. Try running as administrator."
        except FileNotFoundError as e:
            return f"File not found: {e.filename}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"
    return wrapper
```

### Pattern 2: Tool Result with is_error

When sending results back to Claude, use `is_error: True` for failures:

```python
# Success
{
    "type": "tool_result",
    "tool_use_id": block.id,
    "content": "Volume set to 50%"
}

# Error
{
    "type": "tool_result",
    "tool_use_id": block.id,
    "content": "Error: Audio device not found",
    "is_error": True
}
```

Claude will interpret `is_error: True` and can:
- Apologize to the user
- Suggest alternatives
- Try a different tool
- Ask for clarification

### Pattern 3: Validation Before Execution

```python
def set_volume(percent: int) -> str:
    if not isinstance(percent, (int, float)):
        return "Error: Volume level must be a number"
    percent = max(0, min(100, int(percent)))
    # ... proceed
```

---

## Project File Structure

```
voice-assistant/
  core/
    __init__.py
    assistant.py          # Main assistant class
    tool_registry.py      # Tool registration system
  tools/
    __init__.py
    app_launcher.py       # Application launching
    weather.py            # Weather data (wttr.in + OpenWeatherMap)
    system_control.py     # Volume, brightness, lock, shutdown
    web_search.py         # DuckDuckGo search
    file_search.py        # Local file search
    clipboard.py          # Clipboard read/write
    screenshot.py         # Screenshot capture
    media_control.py      # Media playback control
  utils/
    __init__.py
    error_handling.py     # Shared error handling utilities
    config.py             # API keys, settings
  requirements.txt
  main.py               # Entry point
```
