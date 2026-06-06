# RealtimeSTT + RealtimeTTS Technical Reference

Complete reference for building a voice assistant using KoljaB's RealtimeSTT and RealtimeTTS Python libraries, chained with the Claude API.

---

## Table of Contents

1. [Installation](#1-installation)
2. [RealtimeSTT - Speech-to-Text](#2-realtimestt---speech-to-text)
3. [Wake Word Detection](#3-wake-word-detection)
4. [VAD (Voice Activity Detection) Configuration](#4-vad-voice-activity-detection-configuration)
5. [RealtimeTTS - Text-to-Speech](#5-realtimetts---text-to-speech)
6. [TTS Engines Reference](#6-tts-engines-reference)
7. [Claude API Streaming Integration](#7-claude-api-streaming-integration)
8. [Complete Voice Assistant Examples](#8-complete-voice-assistant-examples)
9. [Gotchas and Troubleshooting](#9-gotchas-and-troubleshooting)

---

## 1. Installation

### Basic Install

```bash
pip install RealtimeSTT RealtimeTTS
```

### With Wake Word Support

```bash
# Option A: OpenWakeWord (free, local, no API key)
pip install RealtimeSTT openwakeword

# Option B: Picovoice Porcupine (higher quality, requires API key)
pip install RealtimeSTT pvporcupine
```

### With Claude API

```bash
pip install anthropic
```

### System Dependencies

- **Windows**: PyAudio/sounddevice usually work out of the box
- **Linux**: `sudo apt install libportaudio2 portaudio19-dev`
- **macOS**: `brew install portaudio`

### GPU Acceleration (Optional but Recommended)

```bash
# For CUDA-accelerated Whisper (faster transcription)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install ctranslate2  # Required by faster-whisper
```

### Key Dependencies

| Package | Purpose |
|---------|---------|
| `faster-whisper` | Optimized Whisper inference (STT backend) |
| `torch` / `torchaudio` | PyTorch for model inference |
| `sounddevice` | Audio I/O |
| `webrtcvad` | WebRTC Voice Activity Detection |
| `numpy`, `scipy` | Audio processing |
| `ctranslate2` | Fast C++ inference for Whisper |

---

## 2. RealtimeSTT - Speech-to-Text

### Basic Usage

```python
from RealtimeSTT import AudioToTextRecorder

# Simplest possible usage
if __name__ == '__main__':
    recorder = AudioToTextRecorder()
    print("Say something...")
    while True:
        text = recorder.text()  # Blocks until speech is detected and finalized
        print(f"You said: {text}")
```

### AudioToTextRecorder Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | str | `"base"` | Whisper model: `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3` |
| `language` | str | `""` | Language code (`"en"`, `"de"`, `"zh"`, etc.). Empty = auto-detect |
| `use_microphone` | bool | `True` | Use system microphone |
| `input_device_index` | int | `None` | PyAudio device index for specific microphone |
| `sample_rate` | int | `16000` | Audio sample rate |
| `spinner` | bool | `True` | Show spinner during processing |
| `level` | int | `logging.WARNING` | Logging level |
| `batch_size` | int | `50` | Batch size for faster-whisper inference |
| `compute_type` | str | `"default"` | Compute type: `default`, `float32`, `float16`, `int8` |
| `device` | str | `"auto"` | Device: `cpu`, `cuda`, `auto` |
| `gpu_device_index` | int | `0` | GPU device index |
| `beam_size` | int | `5` | Beam size for Whisper decoding |
| `initial_prompt` | str | `None` | Prompt to guide Whisper transcription style/vocabulary |
| `buffer_size` | int | `512` | Audio buffer size |

### Realtime Transcription Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_realtime_transcription` | bool | `False` | Show intermediate transcription while speaking |
| `realtime_processing_pause` | float | `0.02` | Pause between realtime processing chunks (seconds) |
| `realtime_model_type` | str | `"tiny"` | Model for realtime transcription (lighter = faster) |
| `use_main_model_for_realtime` | bool | `False` | Use main model instead of smaller realtime model |
| `on_realtime_transcription_update` | callable | `None` | Callback(text) for realtime transcription updates |

### Callback Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `on_recording_start` | callable | Called when recording begins (speech detected) |
| `on_recording_stop` | callable | Called when recording ends (silence detected) |
| `on_transcription_start` | callable | Called when transcription processing begins |
| `transcription_callback` | callable | Called with final transcription text |
| `on_wakeword_detected` | callable | Called when wake word is detected |

### Realtime Transcription Example

```python
from RealtimeSTT import AudioToTextRecorder

def on_realtime_update(text):
    print(f"\rRealtime: {text}", end="", flush=True)

def on_final(text):
    print(f"\nFinal: {text}")

recorder = AudioToTextRecorder(
    enable_realtime_transcription=True,
    realtime_model_type="tiny",
    on_realtime_transcription_update=on_realtime_update,
    transcription_callback=on_final,
    model="base",
    language="en"
)

while True:
    text = recorder.text()
    # Process final text...
```

---

## 3. Wake Word Detection

RealtimeSTT supports two wake word backends:

### Option A: OpenWakeWord (Free, Local)

No API key required. Runs locally.

```python
from RealtimeSTT import AudioToTextRecorder

def on_wake():
    print("Wake word detected! Listening...")

recorder = AudioToTextRecorder(
    wake_words="hey jarvis",
    wakeword_backend="oww",              # "oww" = OpenWakeWord
    on_wakeword_detected=on_wake,
    model="base",
    language="en"
)

while True:
    print("Waiting for wake word...")
    text = recorder.text()  # Blocks until wake word + speech
    print(f"Command: {text}")
```

Install: `pip install openwakeword`

### Option B: Picovoice Porcupine (Higher Quality)

Requires a free API key from [picovoice.ai](https://picovoice.ai/).

```python
from RealtimeSTT import AudioToTextRecorder

recorder = AudioToTextRecorder(
    wake_words="hey google",
    wakeword_backend="pv",               # "pv" = Picovoice Porcupine
    pv_access_key="YOUR_PICOVOICE_KEY",  # Or set PV_ACCESS_KEY env var
    model="base",
    language="en"
)

while True:
    text = recorder.text()
    print(f"Command: {text}")
```

Install: `pip install pvporcupine`

### Built-in Porcupine Wake Words

Porcupine supports these built-in keywords:
- `"porcupine"`, `"alexa"`, `"hey google"`, `"hey siri"`, `"jarvis"`, `"bumblebee"`, `"terminator"`, `"picovoice"`

### Wake Word Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `wake_words` | str | Wake word phrase to listen for |
| `wakeword_backend` | str | `"oww"` (OpenWakeWord) or `"pv"` (Porcupine) |
| `pv_access_key` | str | Picovoice API key (for `"pv"` backend) |
| `openwakeword_model_paths` | list | Custom model paths for OpenWakeWord |
| `wake_word_buffer_duration` | float | Audio buffer duration around wake word |
| `wake_word_sensitivity` | float | Detection sensitivity (0.0 - 1.0) |
| `on_wakeword_detected` | callable | Callback when wake word is detected |

---

## 4. VAD (Voice Activity Detection) Configuration

VAD controls when the system starts and stops recording. Proper tuning is critical for a good user experience.

### Dual VAD System

RealtimeSTT uses TWO VAD systems simultaneously:
1. **Silero VAD** - Neural network-based, more accurate
2. **WebRTC VAD** - Traditional, faster, less accurate

Both must agree for robust detection.

### Key VAD Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `silero_sensitivity` | float | `0.4` | Silero VAD threshold (0.0 - 1.0). Higher = more sensitive |
| `webrtc_sensitivity` | int | `3` | WebRTC VAD aggressiveness (0 - 3). 3 = most aggressive filtering |
| `post_speech_silence_duration` | float | `0.6` | Seconds of silence after speech to finalize recording |
| `min_length_of_recording` | float | `0.5` | Minimum recording length in seconds |
| `min_gap_between_recordings` | float | `0` | Minimum gap between consecutive recordings |
| `pre_recording_buffer_duration` | float | `0.2` | Audio buffer before speech detection starts |
| `speech_realization_sensitivity` | float | `0.8` | How quickly speech is realized (0.0 - 1.0) |
| `early_transcription_on_silence` | float | `0` | Start transcription before silence detected (seconds) |
| `faster_whisper_vad_filter` | bool | `True` | Use VAD filtering within faster-whisper |

### VAD Tuning Guide

```python
# For quiet environment, fast response
recorder = AudioToTextRecorder(
    silero_sensitivity=0.6,              # More sensitive
    webrtc_sensitivity=2,                # Less aggressive
    post_speech_silence_duration=0.4,    # Quick stop
    min_length_of_recording=0.3,         # Accept short utterances
)

# For noisy environment, conservative
recorder = AudioToTextRecorder(
    silero_sensitivity=0.2,              # Less sensitive
    webrtc_sensitivity=3,                # Most aggressive filtering
    post_speech_silence_duration=1.0,    # Wait longer for silence
    min_length_of_recording=1.0,         # Require longer utterances
)

# For natural conversation (balanced)
recorder = AudioToTextRecorder(
    silero_sensitivity=0.4,
    webrtc_sensitivity=3,
    post_speech_silence_duration=0.6,
    min_length_of_recording=0.5,
    pre_recording_buffer_duration=0.2,
)
```

### VAD Behavior Diagram

```
Silence -> [pre_recording_buffer] -> Speech Detected -> Recording...
    -> Silence Detected -> [post_speech_silence_duration] -> Finalize
    -> Transcription Complete -> Text Returned
```

---

## 5. RealtimeTTS - Text-to-Speech

### Basic Usage

```python
from RealtimeTTS import TextToAudioStream, OpenAIEngine

engine = OpenAIEngine()  # Uses OPENAI_API_KEY env var
stream = TextToAudioStream(engine)

# Simple playback
stream.feed("Hello, this is a test of realtime text to speech.")
stream.play()  # Blocks until complete

# Async playback (non-blocking)
stream.feed("This plays in the background.")
stream.play_async()
# Do other work...
stream.stop()  # Stop playback
```

### TextToAudioStream Key Methods

| Method | Description |
|--------|-------------|
| `feed(text)` | Feed text (string, list, or generator) into the stream |
| `play()` | Synchronous playback (blocks until complete) |
| `play_async()` | Asynchronous playback (non-blocking) |
| `stop()` | Stop current playback |
| `pause()` | Pause playback |
| `resume()` | Resume paused playback |
| `is_playing()` | Returns True if audio is currently playing |

### Feeding Text

```python
# Feed a string
stream.feed("Hello world")

# Feed a list of strings
stream.feed(["Hello ", "world", " how are you?"])

# Feed a generator (ideal for LLM streaming)
def text_generator():
    yield "Hello "
    yield "world "
    yield "how are you?"

stream.feed(text_generator())
stream.play_async()
```

---

## 6. TTS Engines Reference

### OpenAIEngine

Uses OpenAI's TTS API. Requires `OPENAI_API_KEY` env var or explicit `api_key`.

```python
from RealtimeTTS import TextToAudioStream, OpenAIEngine

engine = OpenAIEngine(
    model="tts-1",            # "tts-1" (fast) or "tts-1-hd" (quality)
    voice="alloy",            # alloy, echo, fable, onyx, nova, shimmer
    speed=1.0,                # 0.25 - 4.0
    api_key="sk-..."          # Or set OPENAI_API_KEY env var
)
```

| Parameter | Options | Description |
|-----------|---------|-------------|
| `model` | `tts-1`, `tts-1-hd` | Model. `tts-1` is faster, `tts-1-hd` is higher quality |
| `voice` | `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer` | Voice style |
| `speed` | `0.25` - `4.0` | Playback speed multiplier |
| `api_key` | str | OpenAI API key |

### ElevenLabsEngine

High-quality AI voices with voice cloning support.

```python
from RealtimeTTS import TextToAudioStream, ElevenLabsEngine

engine = ElevenLabsEngine(
    api_key="your_elevenlabs_key",    # Or set ELEVEN_API_KEY env var
    voice_id="21m00Tcm4TlvDq8ikWAM"   # Rachel (default). Get IDs from ElevenLabs dashboard
)
```

| Parameter | Description |
|-----------|-------------|
| `api_key` | ElevenLabs API key (or `ELEVEN_API_KEY` env var) |
| `voice_id` | Voice ID from your ElevenLabs account |

Popular voice IDs:
- `21m00Tcm4TlvDq8ikWAM` - Rachel
- `EXAVITQu4vr4xnSDxMaL` - Bella
- `ErXwobaYiN019PkySvjV` - Antoni

### AzureEngine

Microsoft Azure Cognitive Services Speech.

```python
from RealtimeTTS import TextToAudioStream, AzureEngine

engine = AzureEngine(
    subscription_key="your_azure_key",
    region="eastus",
    voice="en-US-JennyNeural",
    rate="+10%",              # Speech rate adjustment
    pitch="+5Hz",             # Pitch adjustment
    volume="+0%"              # Volume adjustment
)
```

| Parameter | Description |
|-----------|-------------|
| `subscription_key` | Azure Speech Services subscription key |
| `region` | Azure region (e.g., `eastus`, `westeurope`) |
| `voice` | Voice name (e.g., `en-US-JennyNeural`, `en-US-GuyNeural`) |
| `rate` | Speech rate (e.g., `"+10%"`, `"-5%"`) |
| `pitch` | Pitch adjustment (e.g., `"+5Hz"`) |
| `volume` | Volume adjustment |

### EdgeEngine (Free)

Free Microsoft Edge TTS. No API key required.

```python
from RealtimeTTS import TextToAudioStream, EdgeEngine

engine = EdgeEngine(
    voice="en-US-AriaNeural",
    rate="+0%",
    pitch="+0Hz",
    volume="+0%"
)
```

Edge voices include: `en-US-AriaNeural`, `en-US-JennyNeural`, `en-US-GuyNeural`, `en-GB-SoniaNeural`, and many more.

### CoquiEngine (Local, Offline)

Open-source, runs locally. Supports voice cloning.

```python
from RealtimeTTS import TextToAudioStream, CoquiEngine

engine = CoquiEngine(
    voice="en_US/ljspeech",
    language="en",
    speed=1.0
)
```

Note: Requires significant GPU VRAM (2-4+ GB). First load is slow.

### PiperEngine (Local, Lightweight)

Lightweight local TTS. Fast inference, lower quality.

```python
from RealtimeTTS import TextToAudioStream, PiperEngine

engine = PiperEngine(
    voice="en_US-lessac-medium"
)
```

### Engine Comparison

| Engine | API Key | Offline | Quality | Latency | VRAM |
|--------|---------|---------|---------|---------|------|
| OpenAI | Yes | No | High | Low | None |
| ElevenLabs | Yes | No | Very High | Low | None |
| Azure | Yes | No | High | Low | None |
| Edge | No | No | Good | Very Low | None |
| Coqui | No | Yes | High | Medium | 2-4 GB |
| Piper | No | Yes | Medium | Low | <1 GB |

---

## 7. Claude API Streaming Integration

### Anthropic Python SDK Streaming

```python
import anthropic

client = anthropic.Anthropic(api_key="your-key")

# Method 1: Using messages.stream() context manager (recommended)
with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system="You are a helpful voice assistant. Keep responses concise.",
    messages=[
        {"role": "user", "content": "What's the weather like on Mars?"}
    ],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

# Method 2: Event-based for more control
with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Tell me a joke"}],
) as stream:
    for event in stream:
        if event.type == "content_block_delta":
            print(event.delta.text, end="", flush=True)
```

### Streaming Generator for TTS Integration

```python
def claude_stream_generator(user_message, conversation_history=None):
    """Generator that yields text chunks from Claude's streaming response."""
    client = anthropic.Anthropic()

    messages = conversation_history or []
    messages.append({"role": "user", "content": user_message})

    with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system="You are a helpful voice assistant. Keep responses concise and natural for speech.",
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
```

---

## 8. Complete Voice Assistant Examples

### Example 1: Simple Voice Assistant (No Wake Word)

```python
"""
Simple voice assistant: STT -> Claude -> TTS
No wake word. Continuously listens, processes, speaks.
"""
import os
import anthropic
from RealtimeSTT import AudioToTextRecorder
from RealtimeTTS import TextToAudioStream, OpenAIEngine

# --- Configuration ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
SYSTEM_PROMPT = (
    "You are a helpful voice assistant. Keep responses concise and natural "
    "for spoken delivery. Avoid markdown formatting, lists, or special characters. "
    "Respond in 1-3 sentences unless asked for detail."
)

# --- Initialize Components ---
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
tts_engine = OpenAIEngine(api_key=OPENAI_API_KEY, voice="nova", model="tts-1")
tts_stream = TextToAudioStream(tts_engine)

# Conversation history
conversation = []


def get_claude_response(user_text):
    """Stream Claude response and yield text chunks for TTS."""
    conversation.append({"role": "user", "content": user_text})

    with claude_client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=conversation,
    ) as stream:
        full_response = ""
        for text in stream.text_stream:
            full_response += text
            yield text

    conversation.append({"role": "assistant", "content": full_response})


def process_text(text):
    """Process transcribed text: send to Claude, speak response."""
    print(f"\n[User] {text}")
    print("[Assistant] ", end="", flush=True)

    # Stream Claude response directly to TTS
    tts_stream.feed(get_claude_response(text))
    tts_stream.play()

    print()  # Newline after response


if __name__ == "__main__":
    print("Voice Assistant started. Speak to interact.")
    print("Press Ctrl+C to exit.\n")

    recorder = AudioToTextRecorder(
        model="base",
        language="en",
        silero_sensitivity=0.4,
        webrtc_sensitivity=3,
        post_speech_silence_duration=0.6,
        min_length_of_recording=0.5,
        spinner=True,
    )

    try:
        while True:
            text = recorder.text()
            if text and text.strip():
                process_text(text.strip())
    except KeyboardInterrupt:
        print("\nExiting...")
```

### Example 2: Wake Word Voice Assistant

```python
"""
Wake word voice assistant: Wake Word -> STT -> Claude -> TTS
Uses OpenWakeWord for wake word detection.
"""
import os
import anthropic
from RealtimeSTT import AudioToTextRecorder
from RealtimeTTS import TextToAudioStream, OpenAIEngine

# --- Configuration ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
SYSTEM_PROMPT = (
    "You are a helpful voice assistant named Jarvis. Keep responses concise "
    "and natural for spoken delivery. Be friendly but brief."
)

# --- Initialize ---
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
tts_engine = OpenAIEngine(api_key=OPENAI_API_KEY, voice="echo", model="tts-1")
tts_stream = TextToAudioStream(tts_engine)
conversation = []


def speak(text):
    """Speak text aloud."""
    tts_stream.feed(text)
    tts_stream.play()


def get_claude_response(user_text):
    """Stream Claude response and yield text chunks."""
    conversation.append({"role": "user", "content": user_text})

    with claude_client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=conversation,
    ) as stream:
        full_response = ""
        for text in stream.text_stream:
            full_response += text
            yield text

    conversation.append({"role": "assistant", "content": full_response})


def on_wake_word():
    print("\n[Wake word detected!] Listening for command...")


if __name__ == "__main__":
    print("Wake Word Voice Assistant")
    print("Say 'Hey Jarvis' to activate.\n")

    recorder = AudioToTextRecorder(
        wake_words="hey jarvis",
        wakeword_backend="oww",           # OpenWakeWord (free)
        on_wakeword_detected=on_wake_word,
        model="base",
        language="en",
        silero_sensitivity=0.4,
        webrtc_sensitivity=3,
        post_speech_silence_duration=0.8,  # Slightly longer for commands
        spinner=True,
    )

    speak("Hello, I am Jarvis. Say 'Hey Jarvis' to get my attention.")

    try:
        while True:
            # Blocks until wake word + speech detected
            text = recorder.text()
            if text and text.strip():
                print(f"[Command] {text.strip()}")
                print("[Jarvis] ", end="", flush=True)

                tts_stream.feed(get_claude_response(text.strip()))
                tts_stream.play()
                print()
    except KeyboardInterrupt:
        print("\nExiting...")
```

### Example 3: Advanced Voice Assistant with Realtime Transcription

```python
"""
Advanced voice assistant with:
- Realtime transcription display
- Wake word detection
- Conversation history with summary
- Error handling
- Graceful shutdown
"""
import os
import sys
import signal
import anthropic
from RealtimeSTT import AudioToTextRecorder
from RealtimeTTS import TextToAudioStream, OpenAIEngine

# --- Configuration ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_HISTORY = 20  # Keep last N message pairs

SYSTEM_PROMPT = """You are a helpful voice assistant.
Rules for voice responses:
- Keep responses under 3 sentences unless asked for more
- Never use markdown, bullet points, numbered lists, or special formatting
- Spell out numbers and abbreviations naturally
- Use conversational tone
- If you don't know something, say so briefly"""

# --- State ---
conversation = []
running = True


def signal_handler(sig, frame):
    global running
    print("\nShutting down gracefully...")
    running = False


signal.signal(signal.SIGINT, signal_handler)


class VoiceAssistant:
    def __init__(self):
        self.claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.tts_engine = OpenAIEngine(
            api_key=OPENAI_API_KEY,
            voice="nova",
            model="tts-1",
            speed=1.0,
        )
        self.tts_stream = TextToAudioStream(self.tts_engine)

        self.recorder = AudioToTextRecorder(
            wake_words="hey jarvis",
            wakeword_backend="oww",
            on_wakeword_detected=self._on_wake,
            model="base",
            language="en",
            enable_realtime_transcription=True,
            realtime_model_type="tiny",
            on_realtime_transcription_update=self._on_realtime,
            silero_sensitivity=0.4,
            webrtc_sensitivity=3,
            post_speech_silence_duration=0.8,
            min_length_of_recording=0.5,
            pre_recording_buffer_duration=0.2,
            spinner=False,
        )

    def _on_wake(self):
        sys.stdout.write("\r[!] Wake word detected! Listening...     \n")
        sys.stdout.flush()

    def _on_realtime(self, text):
        sys.stdout.write(f"\r>> {text}          ")
        sys.stdout.flush()

    def _trim_history(self):
        """Keep conversation history manageable."""
        global conversation
        if len(conversation) > MAX_HISTORY * 2:
            conversation = conversation[-(MAX_HISTORY * 2):]

    def _stream_claude(self, user_text):
        """Stream Claude response as a generator."""
        conversation.append({"role": "user", "content": user_text})

        try:
            with self.claude.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=conversation,
            ) as stream:
                full_response = ""
                for text in stream.text_stream:
                    full_response += text
                    yield text

            conversation.append({"role": "assistant", "content": full_response})
            self._trim_history()

        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            yield error_msg
            conversation.append({"role": "assistant", "content": error_msg})

    def speak(self, text):
        """Speak text with TTS."""
        self.tts_stream.feed(text)
        self.tts_stream.play()

    def listen(self):
        """Listen for wake word + speech. Returns transcribed text."""
        return self.recorder.text()

    def process(self, user_text):
        """Full pipeline: user text -> Claude -> TTS."""
        if not user_text or not user_text.strip():
            return

        user_text = user_text.strip()
        print(f"\n[You] {user_text}")
        print("[Assistant] ", end="", flush=True)

        # Stream Claude response directly to TTS
        self.tts_stream.feed(self._stream_claude(user_text))
        self.tts_stream.play()
        print()

    def run(self):
        """Main loop."""
        print("=" * 50)
        print("  Voice Assistant with Wake Word")
        print("  Say 'Hey Jarvis' to activate")
        print("  Press Ctrl+C to exit")
        print("=" * 50)

        self.speak("Hello! Say 'Hey Jarvis' to get my attention.")

        while running:
            try:
                text = self.listen()
                if text and text.strip() and running:
                    self.process(text)
            except Exception as e:
                print(f"\n[Error] {e}")
                continue


if __name__ == "__main__":
    assistant = VoiceAssistant()
    assistant.run()
```

### Example 4: Minimal Voice Loop (Starter Template)

```python
"""Minimal voice assistant - copy and customize."""
import os
import anthropic
from RealtimeSTT import AudioToTextRecorder
from RealtimeTTS import TextToAudioStream, OpenAIEngine

client = anthropic.Anthropic()
engine = OpenAIEngine(voice="alloy")
tts = TextToAudioStream(engine)
history = []

recorder = AudioToTextRecorder(model="tiny", language="en")

while True:
    user_text = recorder.text()
    history.append({"role": "user", "content": user_text})

    def stream_response():
        full = ""
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            system="Be a concise voice assistant.",
            messages=history,
        ) as s:
            for chunk in s.text_stream:
                full += chunk
                yield chunk
        history.append({"role": "assistant", "content": full})

    tts.feed(stream_response())
    tts.play()
```

---

## 9. Gotchas and Troubleshooting

### Installation Issues

1. **PortAudio not found (Linux/macOS)**
   ```
   # Linux
   sudo apt install libportaudio2 portaudio19-dev
   # macOS
   brew install portaudio
   ```

2. **CUDA out of memory**
   - Use smaller Whisper model: `model="tiny"` or `model="base"`
   - For CoquiEngine: use `model="tts-1"` (OpenAI) instead to avoid local VRAM usage
   - Set `device="cpu"` if GPU memory is limited

3. **torch is huge (~2GB)**
   - Install CPU-only if no GPU: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
   - For CUDA: match your CUDA version (`cu118`, `cu121`, etc.)

### STT Issues

4. **Transcription cuts off mid-sentence**
   - Increase `post_speech_silence_duration` (e.g., `1.0` or `1.5`)
   - Decrease `silero_sensitivity` to be less aggressive

5. **Too many false triggers (background noise detected as speech)**
   - Decrease `silero_sensitivity` (e.g., `0.2`)
   - Increase `webrtc_sensitivity` to `3`
   - Increase `min_length_of_recording`

6. **Wake word not detecting**
   - For OpenWakeWord: some wake words work better than others. "alexa" and "hey jarvis" tend to be reliable.
   - Increase `wake_word_sensitivity` (closer to 1.0)
   - Ensure microphone is clear and close

7. **High latency on first transcription**
   - First call loads the model. Subsequent calls are faster.
   - Use `model="tiny"` for lowest latency (at cost of accuracy)
   - Use GPU: `device="cuda"`

### TTS Issues

8. **Choppy audio playback**
   - Usually a network issue (for API-based engines)
   - Check internet connection
   - Use `model="tts-1"` instead of `"tts-1-hd"` for lower latency

9. **OpenAI TTS: "Invalid API key"**
   - Set `OPENAI_API_KEY` environment variable, or pass `api_key=` explicitly

10. **ElevenLabs rate limiting**
    - ElevenLabs has per-second character limits on lower tiers
    - Consider upgrading or using OpenAI/Edge TTS as fallback

### Threading / Callbacks

11. **Callbacks run in background thread**
    - `on_recording_start`, `on_recording_stop`, `on_wakeword_detected` all run in a background thread
    - Do NOT update GUI directly from callbacks (use `queue.Queue` or framework-specific thread-safe methods)
    - Avoid blocking operations in callbacks

12. **Race conditions with shared state**
    - Use `threading.Lock` if modifying shared variables from callbacks

### Claude API

13. **Long responses bore users**
    - System prompt should explicitly say "Keep responses under 2-3 sentences"
    - Set reasonable `max_tokens` (256-512 for voice)

14. **Conversation history grows unbounded**
    - Trim history to last N exchanges (see Example 3's `_trim_history`)

15. **Rate limits**
    - Claude API has rate limits. Handle `anthropic.RateLimitError` with retries.

### Architecture Tips

16. **Feed generators, not strings, to TTS**
    - Always use generators with `stream.feed()` for LLM responses
    - This enables true streaming: audio starts playing before the full response is generated
    - Dramatically reduces perceived latency

17. **Model size vs latency tradeoff**
    - `tiny`: fastest, least accurate
    - `base`: good balance for most use cases
    - `small`: better accuracy, noticeable latency
    - `medium`/`large`: best accuracy, significant latency (1-3s)

18. **Use separate models for realtime vs final transcription**
    - `realtime_model_type="tiny"` for live display (fast)
    - `model="base"` for final transcription (accurate)
    - This gives responsive UI + accurate results

---

## Sources

- [RealtimeSTT GitHub Repository](https://github.com/KoljaB/RealtimeSTT)
- [RealtimeTTS GitHub Repository](https://github.com/KoljaB/RealtimeTTS)
- [RealtimeSpeechToSpeech GitHub Repository](https://github.com/KoljaB/RealtimeSpeechToSpeech)
- [Anthropic Python SDK Documentation](https://docs.anthropic.com)
- [OpenAI TTS Documentation](https://platform.openai.com/docs/guides/text-to-speech)
- [ElevenLabs API Documentation](https://elevenlabs.io/docs)
- [Picovoice Porcupine Documentation](https://picovoice.ai/docs/porcupine/)
- [OpenWakeWord GitHub](https://github.com/dscripka/openWakeWord)
