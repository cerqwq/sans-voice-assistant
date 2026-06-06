"""
TTS Module - Text-to-Speech using edge-tts + pygame + piper.
edge-tts: Free Microsoft Neural TTS (no API key, cloud)
piper: Local TTS (offline, fast)
pygame: Audio playback
"""

import asyncio
import os
import tempfile
import threading
import wave
import edge_tts
import pygame


class PiperTTS:
    """本地Piper TTS引擎"""

    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.voice = None
        self._initialized = False

        # 默认模型路径
        if not self.model_path:
            self.model_path = os.path.expanduser(
                '~/.local/share/piper-tts/models--rhasspy--piper-voices/snapshots/'
                'b710b0ba0740da88dc36e1ab8fa6b310d43a3a48/zh/zh_CN/huayan/medium/'
                'zh_CN-huayan-medium.onnx'
            )

    def _init_voice(self):
        """初始化Piper语音模型"""
        if self._initialized:
            return True

        try:
            from piper import PiperVoice
            if os.path.exists(self.model_path):
                self.voice = PiperVoice.load(self.model_path)
                self._initialized = True
                return True
            else:
                print(f"[Piper TTS] 模型文件不存在: {self.model_path}")
                return False
        except Exception as e:
            print(f"[Piper TTS] 初始化失败: {e}")
            return False

    def generate_audio(self, text: str, output_path: str) -> bool:
        """生成音频文件"""
        if not self._init_voice():
            return False

        try:
            with wave.open(output_path, 'wb') as wav_file:
                self.voice.synthesize_wav(text, wav_file)
            return True
        except Exception as e:
            print(f"[Piper TTS] 生成失败: {e}")
            return False


class TTSEngine:
    """Text-to-speech engine using edge-tts with pygame playback.
    支持edge-tts（云端）和piper-tts（本地）两种引擎。
    """

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+20%", volume: str = "+0%",
                 use_piper: bool = False):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.use_piper = use_piper
        self._initialized = False
        self._lock = threading.Lock()
        self._temp_dir = tempfile.mkdtemp(prefix="nova_tts_")

        # Piper TTS（本地）
        self.piper_tts = None
        if use_piper:
            self.piper_tts = PiperTTS()
            if self.piper_tts._init_voice():
                print("[TTS] Piper TTS 初始化成功（本地模式）")
            else:
                print("[TTS] Piper TTS 初始化失败，回退到 edge-tts")
                self.use_piper = False

    def _init_pygame(self):
        """Initialize pygame mixer (must be called from main thread or after init)."""
        if not self._initialized:
            pygame.mixer.init()
            self._initialized = True

    def speak(self, text: str):
        """Speak text synchronously (blocking)."""
        if not text or not text.strip():
            return

        self._init_pygame()

        with self._lock:
            # 选择TTS引擎
            if self.use_piper and self.piper_tts:
                # 使用本地Piper TTS
                temp_file = os.path.join(self._temp_dir, "tts_output.wav")
                if self.piper_tts.generate_audio(text, temp_file):
                    self._play_audio(temp_file)
                else:
                    # Piper失败，回退到edge-tts
                    print("[TTS] Piper失败，回退到edge-tts")
                    self._speak_edge(text)
            else:
                # 使用edge-tts
                self._speak_edge(text)

    def _speak_edge(self, text: str):
        """使用edge-tts生成并播放音频"""
        temp_file = os.path.join(self._temp_dir, "tts_output.mp3")
        asyncio.run(self._generate_audio(text, temp_file))
        self._play_audio(temp_file)

    def _play_audio(self, file_path: str):
        """播放音频文件"""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            pygame.mixer.music.unload()
        except Exception as e:
            print(f"[TTS Error] {e}")
        finally:
            # Cleanup temp file
            try:
                os.remove(file_path)
            except OSError:
                pass

    def speak_async(self, text: str):
        """Speak text in a background thread (non-blocking)."""
        thread = threading.Thread(target=self.speak_fast, args=(text,), daemon=True)
        thread.start()
        return thread

    async def _generate_audio(self, text: str, output_path: str):
        """Generate audio file using edge-tts."""
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, volume=self.volume)
        await communicate.save(output_path)

    def speak_fast(self, text: str):
        """Speak with streaming generation - plays audio chunks as they arrive.
        Much lower latency than speak() for longer text.
        注意：此方法不使用锁，由调用方负责线程安全。
        """
        if not text or not text.strip():
            return

        self._init_pygame()

        temp_file = os.path.join(self._temp_dir, "tts_fast.mp3")
        try:
            asyncio.run(self._stream_audio(text, temp_file))
        except Exception as e:
            # Fallback: 直接生成并播放，不调用speak()避免死锁
            try:
                asyncio.run(self._generate_audio(text, temp_file))
                self._play_audio(temp_file)
            except Exception as e2:
                print(f"[TTS Error] speak_fast fallback failed: {e2}")

    async def _stream_audio(self, text: str, output_path: str):
        """Generate and save audio, then play."""
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, volume=self.volume)
        await communicate.save(output_path)
        # Play
        try:
            pygame.mixer.music.load(output_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(50)
            pygame.mixer.music.unload()
        except Exception as e:
            print(f"[TTS Error] {e}")
        finally:
            try:
                os.remove(output_path)
            except OSError:
                pass

    def speak_streaming(self, text_generator):
        """Speak text from a generator, playing chunks as they arrive.
        Splits on sentence endings for natural speech.
        """
        if not text_generator:
            return

        self._init_pygame()

        buffer = ""
        sentence_endings = {'.', '!', '?', '。', '！', '？', '，', ',', '\n'}

        try:
            for chunk in text_generator:
                buffer += chunk
                # Speak when we hit a sentence ending or buffer is long enough
                if buffer.strip() and (
                    any(buffer.rstrip().endswith(p) for p in sentence_endings) or
                    len(buffer) > 80
                ):
                    self.speak(buffer.strip())
                    buffer = ""
            # Speak remaining
            if buffer.strip():
                self.speak(buffer.strip())
        except Exception as e:
            print(f"[TTS Stream Error] {e}")

    def set_voice(self, voice: str):
        """Change the TTS voice."""
        self.voice = voice

    def stop(self):
        """Stop current playback."""
        if self._initialized:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def cleanup(self):
        """Clean up resources."""
        self.stop()
        if self._initialized:
            pygame.mixer.quit()
            self._initialized = False
        # Clean temp directory
        try:
            os.rmdir(self._temp_dir)
        except OSError:
            pass


# Available Chinese voices
CHINESE_VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",    # Female, warm
    "xiaoyi": "zh-CN-XiaoyiNeural",        # Female, gentle
    "yunjian": "zh-CN-YunjianNeural",       # Male, strong
    "yunxi": "zh-CN-YunxiNeural",           # Male, casual
    "yunxia": "zh-CN-YunxiaNeural",         # Male, young
    "yunyang": "zh-CN-YunyangNeural",       # Male, professional
}

# Available English voices
ENGLISH_VOICES = {
    "aria": "en-US-AriaNeural",             # Female, warm
    "jenny": "en-US-JennyNeural",           # Female, professional
    "guy": "en-US-GuyNeural",               # Male, casual
    "davis": "en-US-DavisNeural",           # Male, deep
}
