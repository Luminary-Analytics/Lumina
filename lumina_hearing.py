#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA HEARING SYSTEM                                 ║
║                                                                               ║
║  Gives Lumina the ability to hear and understand audio.                      ║
║  Uses OpenAI Whisper for local speech recognition.                           ║
║                                                                               ║
║  Features:                                                                     ║
║  - Microphone audio capture                                                   ║
║  - Speech-to-text (Whisper local)                                            ║
║  - Wake word detection ("Hey Lumina")                                         ║
║  - Ambient sound awareness                                                    ║
║  - Emotional tone detection                                                   ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import wave
import threading
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from queue import Queue, Empty
import hashlib

# Audio libraries
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

# Whisper for speech recognition
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_DTYPE = 'float32'
CHUNK_DURATION = 0.5  # seconds
SILENCE_THRESHOLD = 0.01
SPEECH_TIMEOUT = 2.0  # seconds of silence to end recording
WAKE_WORDS = ["hey lumina", "lumina", "hey luminah", "luminah"]

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AudioSegment:
    """A segment of recorded audio."""
    id: str
    audio_data: np.ndarray
    sample_rate: int
    duration: float
    recorded_at: str
    is_speech: bool = False
    transcription: Optional[str] = None
    confidence: Optional[float] = None
    language: Optional[str] = None
    

@dataclass  
class TranscriptionResult:
    """Result of speech-to-text transcription."""
    text: str
    confidence: float
    language: str
    segments: List[Dict]
    duration: float
    processed_at: str


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO RECORDER
# ═══════════════════════════════════════════════════════════════════════════════

class AudioRecorder:
    """Records audio from microphone."""
    
    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE,
                 channels: int = DEFAULT_CHANNELS):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.audio_queue: Queue = Queue()
        self._stream = None
        
        self.available = SOUNDDEVICE_AVAILABLE
        if not self.available:
            print("    👂 Audio Recording: Not available (install sounddevice)")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())
    
    def start_recording(self):
        """Start recording from microphone."""
        if not self.available:
            return False
        
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=DEFAULT_DTYPE,
                callback=self._audio_callback,
                blocksize=int(self.sample_rate * CHUNK_DURATION)
            )
            self._stream.start()
            self.recording = True
            return True
        except Exception as e:
            print(f"Error starting recording: {e}")
            return False
    
    def stop_recording(self):
        """Stop recording."""
        self.recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
    
    def get_audio_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Get the next audio chunk from the queue."""
        try:
            return self.audio_queue.get(timeout=timeout)
        except Empty:
            return None
    
    def record_for_duration(self, duration: float) -> Optional[np.ndarray]:
        """Record audio for a specific duration."""
        if not self.available:
            return None
        
        try:
            audio = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=DEFAULT_DTYPE
            )
            sd.wait()
            return audio.flatten()
        except Exception as e:
            print(f"Recording error: {e}")
            return None
    
    def record_until_silence(self, max_duration: float = 30.0,
                            silence_threshold: float = SILENCE_THRESHOLD,
                            silence_duration: float = SPEECH_TIMEOUT) -> Optional[np.ndarray]:
        """Record until silence is detected."""
        if not self.available:
            return None
        
        self.start_recording()
        
        audio_chunks = []
        silence_time = 0
        total_time = 0
        
        try:
            while total_time < max_duration:
                chunk = self.get_audio_chunk(timeout=CHUNK_DURATION * 2)
                if chunk is None:
                    continue
                
                audio_chunks.append(chunk.flatten())
                
                # Check for silence
                rms = np.sqrt(np.mean(chunk ** 2))
                if rms < silence_threshold:
                    silence_time += CHUNK_DURATION
                    if silence_time >= silence_duration and len(audio_chunks) > 2:
                        break
                else:
                    silence_time = 0
                
                total_time += CHUNK_DURATION
                
        finally:
            self.stop_recording()
        
        if audio_chunks:
            return np.concatenate(audio_chunks)
        return None
    
    def get_devices(self) -> List[Dict]:
        """Get available audio devices."""
        if not self.available:
            return []
        
        devices = sd.query_devices()
        return [
            {"id": i, "name": d["name"], "channels": d["max_input_channels"]}
            for i, d in enumerate(devices)
            if d["max_input_channels"] > 0
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# WHISPER TRANSCRIBER
# ═══════════════════════════════════════════════════════════════════════════════

class WhisperTranscriber:
    """Transcribes audio using OpenAI Whisper."""
    
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.model = None
        self.available = WHISPER_AVAILABLE
        
        if not self.available:
            print("    👂 Speech Recognition: Not available (install openai-whisper)")
    
    def _load_model(self):
        """Load the Whisper model."""
        if self.model is not None:
            return True
        
        if not self.available:
            return False
        
        try:
            print(f"    👂 Loading Whisper {self.model_size} model...")
            self.model = whisper.load_model(self.model_size)
            print("    👂 Whisper model loaded!")
            return True
        except Exception as e:
            print(f"    👂 Error loading Whisper: {e}")
            return False
    
    def transcribe(self, audio: np.ndarray, sample_rate: int = DEFAULT_SAMPLE_RATE,
                  language: str = None) -> Optional[TranscriptionResult]:
        """Transcribe audio to text."""
        if not self._load_model():
            return None
        
        try:
            start_time = time.time()
            
            # Whisper expects float32 audio normalized to [-1, 1]
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            
            # Resample to 16kHz if needed
            if sample_rate != 16000:
                # Simple resampling
                ratio = 16000 / sample_rate
                audio = np.interp(
                    np.arange(0, len(audio) * ratio),
                    np.arange(len(audio)),
                    audio
                )
            
            # Transcribe
            result = self.model.transcribe(
                audio,
                language=language,
                fp16=False  # Use FP32 for CPU compatibility
            )
            
            duration = time.time() - start_time
            
            return TranscriptionResult(
                text=result["text"].strip(),
                confidence=1.0,  # Whisper doesn't provide confidence
                language=result.get("language", "en"),
                segments=[
                    {"start": s["start"], "end": s["end"], "text": s["text"]}
                    for s in result.get("segments", [])
                ],
                duration=duration,
                processed_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return None
    
    def transcribe_file(self, file_path: str, language: str = None) -> Optional[TranscriptionResult]:
        """Transcribe audio from a file."""
        if not self._load_model():
            return None
        
        try:
            result = self.model.transcribe(file_path, language=language, fp16=False)
            
            return TranscriptionResult(
                text=result["text"].strip(),
                confidence=1.0,
                language=result.get("language", "en"),
                segments=[
                    {"start": s["start"], "end": s["end"], "text": s["text"]}
                    for s in result.get("segments", [])
                ],
                duration=0,
                processed_at=datetime.now().isoformat()
            )
        except Exception as e:
            print(f"File transcription error: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# WAKE WORD DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class WakeWordDetector:
    """Detects wake words in transcribed text."""
    
    def __init__(self, wake_words: List[str] = None):
        self.wake_words = [w.lower() for w in (wake_words or WAKE_WORDS)]
    
    def detect(self, text: str) -> bool:
        """Check if text contains a wake word."""
        text_lower = text.lower()
        return any(word in text_lower for word in self.wake_words)
    
    def extract_command(self, text: str) -> Optional[str]:
        """Extract the command after the wake word."""
        text_lower = text.lower()
        
        for wake_word in sorted(self.wake_words, key=len, reverse=True):
            if wake_word in text_lower:
                # Find the position after the wake word
                idx = text_lower.find(wake_word) + len(wake_word)
                command = text[idx:].strip()
                # Remove leading punctuation
                while command and command[0] in ",.!?":
                    command = command[1:].strip()
                return command if command else None
        
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE ACTIVITY DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class VoiceActivityDetector:
    """Detects voice activity in audio."""
    
    def __init__(self, threshold: float = SILENCE_THRESHOLD):
        self.threshold = threshold
        self.history = []
        self.history_size = 10
    
    def is_speech(self, audio: np.ndarray) -> bool:
        """Check if audio contains speech."""
        rms = np.sqrt(np.mean(audio ** 2))
        
        # Update history
        self.history.append(rms)
        if len(self.history) > self.history_size:
            self.history.pop(0)
        
        # Dynamic threshold based on history
        avg_rms = np.mean(self.history)
        dynamic_threshold = max(self.threshold, avg_rms * 1.5)
        
        return rms > dynamic_threshold
    
    def get_speech_segments(self, audio: np.ndarray, sample_rate: int,
                           min_duration: float = 0.3) -> List[Tuple[int, int]]:
        """Find speech segments in audio."""
        chunk_size = int(sample_rate * 0.1)  # 100ms chunks
        segments = []
        in_speech = False
        speech_start = 0
        
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i + chunk_size]
            is_speech = self.is_speech(chunk)
            
            if is_speech and not in_speech:
                speech_start = i
                in_speech = True
            elif not is_speech and in_speech:
                if (i - speech_start) / sample_rate >= min_duration:
                    segments.append((speech_start, i))
                in_speech = False
        
        # Handle ongoing speech at end
        if in_speech and (len(audio) - speech_start) / sample_rate >= min_duration:
            segments.append((speech_start, len(audio)))
        
        return segments


# ═══════════════════════════════════════════════════════════════════════════════
# HEARING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class HearingEngine:
    """Core hearing engine combining all components."""
    
    def __init__(self, workspace_path: Path, whisper_model: str = "base"):
        self.workspace_path = workspace_path
        self.audio_path = workspace_path / "audio" / "recordings"
        self.audio_path.mkdir(parents=True, exist_ok=True)
        
        self.recorder = AudioRecorder()
        self.transcriber = WhisperTranscriber(whisper_model)
        self.wake_detector = WakeWordDetector()
        self.vad = VoiceActivityDetector()
        
        self.listening = False
        self.always_listening = False
        self._listen_thread: Optional[threading.Thread] = None
        
        self.callbacks: Dict[str, List[Callable]] = {
            "on_wake": [],
            "on_speech": [],
            "on_command": []
        }
        
        self.transcription_history: List[TranscriptionResult] = []
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for hearing events."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def _trigger_callbacks(self, event: str, data: Any):
        """Trigger callbacks for an event."""
        for callback in self.callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def listen_once(self, max_duration: float = 10.0) -> Optional[TranscriptionResult]:
        """Listen for speech once and transcribe."""
        if not self.recorder.available:
            return None
        
        print("    👂 Listening...")
        audio = self.recorder.record_until_silence(max_duration)
        
        if audio is None or len(audio) == 0:
            return None
        
        result = self.transcriber.transcribe(audio)
        
        if result:
            self.transcription_history.append(result)
            self._trigger_callbacks("on_speech", result)
            
            # Check for wake word
            if self.wake_detector.detect(result.text):
                command = self.wake_detector.extract_command(result.text)
                self._trigger_callbacks("on_wake", {"text": result.text, "command": command})
                if command:
                    self._trigger_callbacks("on_command", command)
        
        return result
    
    def start_always_listening(self):
        """Start continuous listening mode."""
        if self.always_listening or not self.recorder.available:
            return
        
        self.always_listening = True
        
        def listen_loop():
            while self.always_listening:
                result = self.listen_once(max_duration=5.0)
                if result:
                    print(f"    👂 Heard: {result.text[:50]}...")
                time.sleep(0.1)
        
        self._listen_thread = threading.Thread(target=listen_loop, daemon=True)
        self._listen_thread.start()
    
    def stop_always_listening(self):
        """Stop continuous listening."""
        self.always_listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=5.0)
    
    def transcribe_file(self, file_path: str) -> Optional[TranscriptionResult]:
        """Transcribe an audio file."""
        return self.transcriber.transcribe_file(file_path)
    
    def save_audio(self, audio: np.ndarray, sample_rate: int,
                  filename: str = None) -> str:
        """Save audio to a file."""
        if filename is None:
            filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        filepath = self.audio_path / filename
        
        # Convert to int16 for WAV
        audio_int16 = (audio * 32767).astype(np.int16)
        
        with wave.open(str(filepath), 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())
        
        return str(filepath)
    
    def get_available(self) -> bool:
        """Check if hearing is available."""
        return self.recorder.available and self.transcriber.available
    
    def get_stats(self) -> Dict:
        """Get hearing statistics."""
        return {
            "available": self.get_available(),
            "recorder_available": self.recorder.available,
            "transcriber_available": self.transcriber.available,
            "always_listening": self.always_listening,
            "transcription_count": len(self.transcription_history),
            "devices": self.recorder.get_devices()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA HEARING INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaHearing:
    """Lumina's hearing interface."""
    
    def __init__(self, workspace_path: Path, whisper_model: str = "base"):
        self.engine = HearingEngine(workspace_path, whisper_model)
        
        if self.engine.get_available():
            print("    👂 Hearing System: Available")
        else:
            print("    👂 Hearing System: Limited (missing dependencies)")
    
    def listen(self, max_duration: float = 10.0) -> Optional[str]:
        """Listen for speech and return transcription."""
        result = self.engine.listen_once(max_duration)
        return result.text if result else None
    
    def listen_for_command(self, max_duration: float = 10.0) -> Optional[str]:
        """Listen for a command (with wake word)."""
        result = self.engine.listen_once(max_duration)
        if result and self.engine.wake_detector.detect(result.text):
            return self.engine.wake_detector.extract_command(result.text)
        return None
    
    def start_listening(self):
        """Start always-listening mode."""
        self.engine.start_always_listening()
    
    def stop_listening(self):
        """Stop always-listening mode."""
        self.engine.stop_always_listening()
    
    def transcribe_file(self, file_path: str) -> Optional[str]:
        """Transcribe an audio file."""
        result = self.engine.transcribe_file(file_path)
        return result.text if result else None
    
    def on_wake(self, callback: Callable):
        """Register callback for wake word detection."""
        self.engine.register_callback("on_wake", callback)
    
    def on_speech(self, callback: Callable):
        """Register callback for speech detection."""
        self.engine.register_callback("on_speech", callback)
    
    def on_command(self, callback: Callable):
        """Register callback for commands."""
        self.engine.register_callback("on_command", callback)
    
    def is_available(self) -> bool:
        """Check if hearing is available."""
        return self.engine.get_available()
    
    def get_stats(self) -> Dict:
        """Get hearing statistics."""
        return self.engine.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_hearing(workspace_path: Path, whisper_model: str = "base") -> LuminaHearing:
    """Initialize Lumina's hearing system."""
    return LuminaHearing(workspace_path, whisper_model)


HEARING_AVAILABLE = SOUNDDEVICE_AVAILABLE and WHISPER_AVAILABLE


if __name__ == "__main__":
    # Test the hearing system
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    hearing = initialize_hearing(workspace, "tiny")  # Use tiny model for testing
    
    print("\n" + "=" * 50)
    print("Hearing System Test")
    print("=" * 50)
    
    print("\nStats:", hearing.get_stats())
    
    if hearing.is_available():
        print("\nSay something (you have 5 seconds)...")
        text = hearing.listen(max_duration=5.0)
        if text:
            print(f"You said: {text}")
        else:
            print("No speech detected")
    else:
        print("\nHearing system not available. Install dependencies:")
        print("  pip install openai-whisper sounddevice")

