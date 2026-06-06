"""
System Control Tool - Volume, brightness, lock, shutdown, restart, sleep.
Requires: pycaw, comtypes, screen-brightness-control (optional: winshell)
"""

import subprocess
import ctypes
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
        cmd = ["shutdown", "/s", "/t", str(delay)]
        if force:
            cmd.append("/f")
        subprocess.run(cmd, check=True)
        return f"Shutdown initiated (delay: {delay}s)"
    except Exception as e:
        return f"Shutdown error: {e}"


def restart_system(delay: int = 0, force: bool = True) -> str:
    """Restart the computer."""
    try:
        cmd = ["shutdown", "/r", "/t", str(delay)]
        if force:
            cmd.append("/f")
        subprocess.run(cmd, check=True)
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
            check=True,
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
                "description": "Action to perform",
            },
            "level": {
                "type": "integer",
                "description": "Volume level 0-100 (only for 'set' action)",
            },
        },
        "required": ["action"],
    },
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
                "description": "Action to perform",
            },
            "level": {
                "type": "integer",
                "description": "Brightness level 0-100 (only for 'set' action)",
            },
        },
        "required": ["action"],
    },
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
                "enum": [
                    "lock",
                    "shutdown",
                    "restart",
                    "sleep",
                    "cancel_shutdown",
                    "empty_recycle_bin",
                ],
                "description": "System action to perform",
            },
            "delay": {
                "type": "integer",
                "description": "Delay in seconds before shutdown/restart (default 0)",
                "default": 0,
            },
        },
        "required": ["action"],
    },
}
