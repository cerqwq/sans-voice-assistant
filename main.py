"""
Voice Assistant - Main entry point.
Pipeline: Wake Word Detection -> STT -> Claude API (streaming) -> TTS
Wake word: "hi sans" (software-based text matching)
"""

import sys
import os
import time
import re
import threading
import logging
import struct
from pathlib import Path

# Fix Windows terminal encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(__file__))

from config import config
from core.assistant import VoiceAssistant
from core.agent import Agent


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"


WAKE_WORD = "hi sans"
WAKE_PATTERNS = [
    # English variations
    "hi sans", "hisans", "hi son", "hi sons", "hi san",
    "hi self", "hi sense", "hiself",
    # STT often hears "sirs" instead of "sans"
    "hi sirs", "hi sir", "hey sirs", "hey sir", "hey sans",
    "hi circ", "hi circs", "hi sur", "hi surge",
    # Chinese variations
    "嗨 sans", "嗨sans", "嗨 三思", "嗨三思",
    "嗨 散司", "嗨散司", "嗨 散", "嗨散",
    # STT transcription variations (what faster-whisper actually produces)
    "嘿, self", "嘿,self", "嘿,Self", "嘿, sense", "嘿,sense",
    "嘿 三思", "嘿三思", "嘿 sans", "嘿sans",
    "嘿咸", "嘿,咸",
    # tiny model variations
    "嘿誓", "嘿 事", "嘿事", "嘿 是", "嘿是", "嘿试", "嘿 试",
    "嘿势", "嘿世", "嘿市", "嘿视", "嘿式", "嘿饰",
    "黑三", "黑散", "黑伞", "黑色",
    # more variations
    "嘿桑", "嘿三", "嘿丧", "嘿嗓", "嘿颡",
    "嘿山", "嘿闪", "嘿善", "嘿商", "嘿赏",
    "嘿上", "嘿尚", "嘿裳", "嘿墒",
    "黑三", "黑散", "黑桑", "黑山",
]

# Custom wake word model (if available)
_wake_word_detector = None
_audio_buffer = []
_audio_buffer_lock = threading.Lock()

def init_wake_word_detector():
    """Initialize custom wake word detector if model exists."""
    global _wake_word_detector
    model_path = Path(__file__).parent / "custom_wake_models" / "hi_sans.json"
    if model_path.exists():
        try:
            from core.wakeword import CustomWakeWordDetector
            _wake_word_detector = CustomWakeWordDetector(model_path)
            return True
        except Exception as e:
            print(f"Custom wake word model failed to load: {e}")
    return False


def check_audio_wake_word(audio_chunk):
    """Check if audio chunk contains wake word using custom model.
    Returns (detected, confidence) or (False, 0.0) if model not available.
    """
    global _audio_buffer, _wake_word_detector
    if not _wake_word_detector:
        return False, 0.0

    try:
        import numpy as np
        # Convert bytes to float32 array
        if isinstance(audio_chunk, bytes):
            samples = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            samples = audio_chunk

        with _audio_buffer_lock:
            _audio_buffer.extend(samples)
            # Keep ~2 seconds of audio (32000 samples at 16kHz)
            if len(_audio_buffer) > 32000:
                _audio_buffer = _audio_buffer[-32000:]

        # Need at least 0.5 seconds of audio
        if len(_audio_buffer) < 8000:
            return False, 0.0

        audio_array = np.array(_audio_buffer, dtype=np.float32)
        detected, confidence = _wake_word_detector.predict(audio_array)
        return detected, confidence
    except Exception as e:
        logging.debug(f"Audio wake word check failed: {e}")
        return False, 0.0


def print_banner():
    print(f"""
{Colors.CYAN}{Colors.BOLD}========================================
    Sans Voice Assistant
========================================
  STT:   RealtimeSTT (faster-whisper)
  LLM:   {config.claude_model}
  TTS:   {config.tts_voice}
  Wake:  "{WAKE_WORD}"
========================================{Colors.RESET}
""")


def beep(frequency=1000, duration=200):
    """Play a beep sound."""
    try:
        import winsound
        winsound.Beep(frequency, duration)
    except (ImportError, RuntimeError):
        pass


def show_notification(title, message):
    """Show Windows toast notification."""
    try:
        from winotify import Notification
        toast = Notification(app_id="Sans", title=title, msg=message)
        toast.show()
    except (ImportError, Exception):
        pass


def setup_tray_icon():
    """Setup system tray icon."""
    try:
        import pystray
        from PIL import Image, ImageDraw

        def create_icon_image(color='white'):
            img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([8, 8, 56, 56], fill=color, outline='white', width=2)
            return img

        def on_exit(icon, item):
            icon.stop()
            os._exit(0)

        icon = pystray.Icon(
            "Sans",
            create_icon_image(),
            "Sans Voice Assistant - Say Hi Sans",
            menu=pystray.Menu(
                pystray.MenuItem("Exit", on_exit),
            )
        )
        threading.Thread(target=icon.run, daemon=True).start()
        return icon
    except Exception as e:
        print(f"Tray icon failed: {e}")
        return None


def print_status(msg, color=Colors.DIM):
    print(f"{color}[{time.strftime('%H:%M:%S')}] {msg}{Colors.RESET}")


def setup_assistant():
    """Setup Agent with all components."""
    return Agent()


def setup_tts():
    from core.tts import TTSEngine
    # 检查是否使用Piper TTS（本地模式）
    use_piper = os.environ.get('USE_PIPER_TTS', 'false').lower() == 'true'
    return TTSEngine(voice=config.tts_voice, use_piper=use_piper)


def compute_rms(audio_bytes):
    """Compute RMS amplitude from raw audio bytes (int16)."""
    if not audio_bytes or len(audio_bytes) < 2:
        return 0.0
    n = len(audio_bytes) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f'<{n}h', audio_bytes[:n*2])
    sum_sq = sum(s * s for s in samples)
    rms = (sum_sq / n) ** 0.5
    return min(1.0, rms / 16000.0)  # normalize to 0-1


def setup_stt(on_recording_start=None, on_recording_stop=None,
             on_recorded_chunk=None):
    from RealtimeSTT import AudioToTextRecorder
    print_status(f"Loading STT model ({config.whisper_model})...", Colors.DIM)
    kwargs = dict(
        model=config.whisper_model,
        language=config.language,
        silero_sensitivity=config.silero_sensitivity,
        webrtc_sensitivity=config.webrtc_sensitivity,
        post_speech_silence_duration=config.post_speech_silence_duration,
        min_length_of_recording=config.min_length_of_recording,
        enable_realtime_transcription=False,
        spinner=True,
        # 提示词帮助识别唤醒词
        initial_prompt="Hi Sans. 嘿Sans。你好。今天天气怎么样。",
    )
    if on_recording_start:
        kwargs['on_recording_start'] = on_recording_start
    if on_recording_stop:
        kwargs['on_recording_stop'] = on_recording_stop
    if on_recorded_chunk:
        kwargs['on_recorded_chunk'] = on_recorded_chunk
    return AudioToTextRecorder(**kwargs)


def contains_wake_word(text):
    """Check if text contains the wake word (fuzzy matching)."""
    if not text:
        return False
    text_lower = text.lower().strip()

    # Exact pattern match
    for pattern in WAKE_PATTERNS:
        if pattern in text_lower:
            return True

    # Fuzzy: "hi/hey/嘿/嗨" + anything that sounds like "sans/sirs/self/sense/咸/三"
    greeting_prefixes = ["hi ", "hey ", "hi,", "hey,", "嘿", "嗨"]
    sans_suffixes = ["sans", "sirs", "sir", "self", "sense", "san", "son",
                     "咸", "三", "三思", "sanz", "散", "散司", "桑", "山", "闪"]

    for prefix in greeting_prefixes:
        if text_lower.startswith(prefix):
            rest = text_lower[len(prefix):].lstrip(" ,.，。")
            for suffix in sans_suffixes:
                if rest.startswith(suffix) or rest == suffix:
                    return True

    return False


def extract_command(text):
    """Extract the command after the wake word. Returns empty if only wake word."""
    if not text:
        return ""
    text_lower = text.lower().strip()
    for pattern in WAKE_PATTERNS:
        idx = text_lower.find(pattern)
        if idx >= 0:
            command = text[idx + len(pattern):].strip()
            # Remove leading punctuation
            command = re.sub(r'^[,，.。!！?？\s]+', '', command)
            # If command is too short or just punctuation, treat as wake-word-only
            if len(command) < 2:
                return ""
            return command

    # Fuzzy match - check prefix/suffix
    greeting_prefixes = ["hi ", "hey ", "hi,", "hey,", "嘿", "嗨"]
    for prefix in greeting_prefixes:
        if text_lower.startswith(prefix):
            rest = text_lower[len(prefix):].lstrip(" ,.，。")
            if len(rest) < 3:
                return ""

    return ""




def run_voice_mode():
    """Main voice assistant loop with wake word detection and visual overlay."""
    print_banner()

    # Initialize visual overlay (starts hidden - silent mode)
    from core.overlay import AssistantOverlay
    overlay = AssistantOverlay()
    overlay.start()
    time.sleep(0.3)  # let tkinter window initialize

    # STT callbacks for overlay (only active when overlay is visible)
    def on_rec_start():
        if overlay._state != 'hidden':
            overlay.show_listening()

    def on_rec_stop():
        pass  # will be handled by main loop

    def on_chunk(data):
        # Feed audio to wake word detector
        if _wake_word_detector:
            detected, conf = check_audio_wake_word(data)
            if detected:
                logging.info(f"Audio wake word detected! Confidence: {conf:.3f}")
        # Update overlay amplitude
        if overlay._state != 'hidden':
            rms = compute_rms(data)
            overlay.update_amplitude(rms)

    # Initialize VoiceAssistant (includes Ollama client, tools, memory)
    assistant = setup_assistant()

    tts = setup_tts()
    recorder = setup_stt(
        on_recording_start=on_rec_start,
        on_recording_stop=on_rec_stop,
        on_recorded_chunk=on_chunk,
    )

    # Initialize custom wake word detector
    has_custom_wake = init_wake_word_detector()

    # Setup tray icon
    tray_icon = setup_tray_icon()

    print_status("All components ready!", Colors.GREEN)
    if has_custom_wake:
        print_status(f'Custom wake word model loaded: "{WAKE_WORD}"', Colors.GREEN)
    else:
        print_status(f'Using text matching for wake word: "{WAKE_WORD}"', Colors.YELLOW)
    print_status("🔇 Silent mode - Say 'Hi Sans' to activate", Colors.CYAN)
    print_status("Press Ctrl+C to exit\n", Colors.DIM)

    # Show notification
    show_notification("Sans Started", 'Silent mode - Say "Hi Sans" to activate')

    # Silent start - no greeting, no overlay
    # User says "Hi Sans" to activate

    try:
        while True:
            # Listen for speech
            print_status("Listening...", Colors.DIM)
            user_text = recorder.text()

            if not user_text or not user_text.strip():
                continue

            user_text = user_text.strip()
            logging.info(f"Heard: {user_text}")

            # Check for wake word (text matching + audio model if available)
            text_wake = contains_wake_word(user_text)
            audio_wake = False
            if _wake_word_detector:
                with _audio_buffer_lock:
                    if _audio_buffer:
                        import numpy as np
                        audio_array = np.array(_audio_buffer, dtype=np.float32)
                        audio_wake, conf = _wake_word_detector.predict(audio_array)
                        if audio_wake:
                            logging.info(f"Audio model confirmed wake word (conf: {conf:.3f})")

            if text_wake or audio_wake:
                command = extract_command(user_text)

                # Activate overlay (show sphere) - exits silent mode
                overlay.show_sphere()
                print(f"\n{Colors.GREEN}[Activated - UI visible]{Colors.RESET}")

                if command:
                    # Wake word + command in one sentence
                    print(f"\n{Colors.CYAN}{Colors.BOLD}Command: {command}{Colors.RESET}")
                    print(f"{Colors.GREEN}Sans: ", end="", flush=True)

                    buffer = ""
                    sentence_endings = {'.', '!', '?', '。', '！', '？', '\n'}

                    # 使用Agent的run_task进行多步推理
                    for chunk in assistant.run_task(command):
                        print(chunk, end="", flush=True)
                        buffer += chunk

                        if buffer.strip() and any(buffer.rstrip().endswith(p) for p in sentence_endings):
                            overlay.show_speaking(buffer.strip())
                            tts.speak_async(buffer.strip())
                            buffer = ""

                    # Wait for last TTS to finish
                    if buffer.strip():
                        overlay.show_speaking(buffer.strip())
                        tts.speak(buffer.strip())

                    print(Colors.RESET)

                    # After speaking, show listening mode for next input
                    # Will auto-hide after 10s timeout (back to silent mode)
                    overlay.show_listening()

                else:
                    # Wake word only - acknowledge and listen
                    print(f"\n{Colors.CYAN}[Wake word detected!]{Colors.RESET}")
                    overlay.show_speaking("我在，请说。")
                    tts.speak("我在，请说。")

                    # Listen for the actual command
                    print_status("Listening for command...", Colors.CYAN)
                    overlay.show_listening()
                    command = recorder.text()

                    if command and command.strip():
                        command = command.strip()
                        # Show what user said
                        overlay.show_user_text(command)
                        time.sleep(0.8)

                        print(f"{Colors.CYAN}{Colors.BOLD}Command: {command}{Colors.RESET}")
                        print(f"{Colors.GREEN}Sans: ", end="", flush=True)

                        buffer = ""
                        sentence_endings = {'.', '!', '?', '。', '！', '？', '\n'}

                        # 使用Agent的run_task进行多步推理
                        for chunk in assistant.run_task(command):
                            print(chunk, end="", flush=True)
                            buffer += chunk

                            if buffer.strip() and any(buffer.rstrip().endswith(p) for p in sentence_endings):
                                overlay.show_speaking(buffer.strip())
                                tts.speak_async(buffer.strip())
                                buffer = ""

                        if buffer.strip():
                            overlay.show_speaking(buffer.strip())
                            tts.speak(buffer.strip())

                        print(Colors.RESET)

                        # After speaking, show listening mode
                        # Will auto-hide after 10s timeout (back to silent mode)
                        overlay.show_listening()
                    else:
                        # No command after wake word - timeout will handle hiding
                        print_status("No command heard, waiting for timeout...", Colors.DIM)

            else:
                # No wake word - silent mode, no UI
                # Only print to log, not to terminal (keep terminal clean)
                logging.info(f"Heard (ignored): {user_text}")

            # Trim history
            assistant.trim_history()

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Goodbye!{Colors.RESET}")
    finally:
        overlay.stop()
        tts.cleanup()
        if hasattr(recorder, 'shutdown'):
            recorder.shutdown()


def run_text_mode():
    """Text-only mode for testing."""
    print_banner()
    print_status("Text mode (no voice)", Colors.YELLOW)

    # Initialize Agent (includes VoiceAssistant, tools, memory)
    assistant = setup_assistant()

    print_status("Type 'quit' to exit, 'reset' to clear history.", Colors.DIM)
    print()

    while True:
        try:
            user_input = input(f"{Colors.CYAN}You: {Colors.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Colors.YELLOW}Goodbye!{Colors.RESET}")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print(f"{Colors.YELLOW}Goodbye!{Colors.RESET}")
            break
        if user_input.lower() == "reset":
            assistant.assistant.reset()
            print_status("History cleared.", Colors.YELLOW)
            continue

        print(f"{Colors.GREEN}Sans: ", end="", flush=True)
        # 使用Agent的run_task进行多步推理
        for chunk in assistant.run_task(user_input):
            print(chunk, end="", flush=True)
        print(Colors.RESET)
        print()

        assistant.assistant.trim_history()


if __name__ == "__main__":
    # Setup logging
    import logging
    log_path = Path(__file__).parent / "sans.log"
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Root logger配置
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 文件handler（UTF-8编码）
    file_handler = logging.FileHandler(str(log_path), encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(message)s', datefmt='%H:%M:%S'))
    root_logger.addHandler(file_handler)

    # 控制台handler（简洁输出）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger.addHandler(console_handler)

    logging.info("Sans Voice Assistant started")

    if len(sys.argv) > 1 and sys.argv[1] == "--text":
        run_text_mode()
    else:
        run_voice_mode()
