"""
Screenshot Tool - Capture screen or region.
Requires: mss (fast) or Pillow, pywin32 (for clipboard)
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

SCREENSHOT_DIR = Path.home() / "Screenshots"


def take_screenshot(
    save_path: Optional[str] = None,
    region: Optional[tuple] = None,
    method: str = "mss",
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
                monitor = {
                    "left": region[0],
                    "top": region[1],
                    "width": region[2],
                    "height": region[3],
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
            bbox = (
                region[0],
                region[1],
                region[0] + region[2],
                region[1] + region[3],
            )
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
                    "height": {"type": "integer", "description": "Region height in pixels"},
                },
                "description": "Region to capture (omit for full screen)",
            },
            "save_path": {
                "type": "string",
                "description": "Custom save path (default: ~/Screenshots/)",
            },
        },
        "required": [],
    },
}
