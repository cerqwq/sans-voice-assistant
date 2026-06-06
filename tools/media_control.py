"""
Media Control Tool - Control media playback (Spotify, WMP, browser audio, etc.).
Requires: pynput (for media keys), keyboard (alternative), winsdk (for now-playing info)
"""

import time
import subprocess
import os
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
            GlobalSystemMediaTransportControlsSessionManager as SessionManager,
        )

        async def _get_info():
            manager = await SessionManager.request_async()
            session = manager.get_current_session()
            if session is None:
                return "No active media session"

            info = await session.try_get_media_properties_async()
            playback = session.get_playback_info()

            status_map = {4: "Playing", 5: "Paused", 1: "Stopped"}
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
# SPOTIFY CONTROL
# ============================================================

def spotify_control(action: str) -> str:
    """Control Spotify via Windows media commands."""
    try:
        import keyboard as kb

        key_map = {
            "play": "play/pause media",
            "pause": "play/pause media",
            "next": "next track media",
            "previous": "previous track media",
            "stop": "stop media",
        }

        if action not in key_map:
            return f"Unknown Spotify action: {action}"

        kb.press_and_release(key_map[action])
        return f"Spotify: {action}"

    except ImportError:
        return "Install keyboard: pip install keyboard"
    except Exception as e:
        return f"Spotify control error: {e}"


def open_spotify() -> str:
    """Launch Spotify application."""
    try:
        paths = [
            os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
            os.path.expandvars(
                r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"
            ),
        ]
        for path in paths:
            if os.path.exists(path):
                os.startfile(path)
                return "Spotify launched"

        # Fallback: try shell start
        subprocess.Popen(["cmd", "/c", "start", "", "spotify"], shell=False)
        return "Spotify launch requested"
    except Exception as e:
        return f"Spotify launch error: {e}"


def play_sound(file_path: str) -> str:
    """Play a WAV or MP3 sound file."""
    try:
        if file_path.endswith(".wav"):
            import winsound

            winsound.PlaySound(
                file_path, winsound.SND_FILENAME | winsound.SND_ASYNC
            )
            return f"Playing: {file_path}"
        else:
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
                    "play_pause",
                    "next",
                    "previous",
                    "stop",
                    "now_playing",
                    "open_spotify",
                ],
                "description": "Media action to perform",
            }
        },
        "required": ["action"],
    },
}
