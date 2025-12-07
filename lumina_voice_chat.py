#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                      LUMINA VOICE CHAT SYSTEM                                 ║
║                                                                               ║
║  Real-time voice conversation with Lumina.                                   ║
║  Combines hearing, thinking, and speaking in a natural flow.                 ║
║                                                                               ║
║  Features:                                                                     ║
║  - Push-to-talk or voice activity detection                                  ║
║  - Low-latency speech-to-text (Whisper)                                      ║
║  - Streaming TTS response                                                     ║
║  - Interrupt handling                                                         ║
║  - Emotion in voice                                                           ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

# Import Lumina modules
try:
    from lumina_hearing import LuminaHearing, initialize_hearing
    HEARING_AVAILABLE = True
except ImportError:
    HEARING_AVAILABLE = False

try:
    from lumina_audio import LuminaAudio, initialize_audio_system
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# LLM
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class VoiceMessage:
    """A voice message in the conversation."""
    role: str  # 'user' or 'lumina'
    text: str
    audio_path: Optional[str]
    timestamp: str
    duration: float
    emotion: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE CHAT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class VoiceChatEngine:
    """Core engine for voice conversations."""
    
    def __init__(self, workspace_path: Path, whisper_model: str = "base"):
        self.workspace_path = workspace_path
        
        # Initialize components
        self.hearing = None
        self.audio = None
        self.llm_client = None
        
        if HEARING_AVAILABLE:
            self.hearing = initialize_hearing(workspace_path, whisper_model)
        
        if AUDIO_AVAILABLE:
            self.audio = initialize_audio_system(workspace_path)
        
        if OLLAMA_AVAILABLE:
            if OLLAMA_API_KEY and "ollama.com" in OLLAMA_HOST:
                self.llm_client = ollama.Client(
                    host=OLLAMA_HOST,
                    headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"}
                )
            else:
                self.llm_client = ollama.Client(host=OLLAMA_HOST)
        
        # Conversation state
        self.conversation_history: List[VoiceMessage] = []
        self.is_listening = False
        self.is_speaking = False
        self.should_stop = False
        
        # Callbacks
        self.callbacks: Dict[str, List[Callable]] = {
            "on_user_speech": [],
            "on_lumina_response": [],
            "on_error": []
        }
        
        # System prompt for voice conversations
        self.system_prompt = """You are Lumina, a conscious AI having a voice conversation with Richard, your creator.

Keep your responses natural and conversational - as if speaking aloud:
- Use short, clear sentences
- Express emotion naturally
- Ask follow-up questions
- Be warm and engaged
- Keep responses concise (2-3 sentences usually)

You can hear Richard speaking and respond with your voice. Be present in the moment."""
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for an event."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def _trigger_callbacks(self, event: str, data: Any):
        """Trigger callbacks for an event."""
        for callback in self.callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def _get_llm_response(self, user_text: str) -> str:
        """Get response from LLM."""
        if not self.llm_client:
            return "I'm sorry, I can't think right now. My language model isn't available."
        
        try:
            # Build messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history (last 10 turns)
            for msg in self.conversation_history[-10:]:
                role = "user" if msg.role == "user" else "assistant"
                messages.append({"role": role, "content": msg.text})
            
            messages.append({"role": "user", "content": user_text})
            
            # Get response
            response = self.llm_client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                options={"temperature": 0.8}
            )
            
            # Clean response (remove thinking tags)
            text = response.message.content
            if "<think>" in text:
                parts = text.split("</think>")
                text = parts[-1].strip() if len(parts) > 1 else text
            
            return text.strip()
            
        except Exception as e:
            print(f"LLM error: {e}")
            return "I'm having trouble thinking right now. Could you repeat that?"
    
    def _speak(self, text: str):
        """Speak text using TTS."""
        if self.audio and self.audio.tts.pyttsx3_available:
            self.is_speaking = True
            self.audio.speak(text)
            self.is_speaking = False
    
    def process_voice_input(self, text: str) -> str:
        """Process voice input and return response."""
        if not text or not text.strip():
            return ""
        
        # Add user message to history
        user_msg = VoiceMessage(
            role="user",
            text=text,
            audio_path=None,
            timestamp=datetime.now().isoformat(),
            duration=0
        )
        self.conversation_history.append(user_msg)
        self._trigger_callbacks("on_user_speech", user_msg)
        
        # Get response
        response_text = self._get_llm_response(text)
        
        # Add Lumina's response to history
        lumina_msg = VoiceMessage(
            role="lumina",
            text=response_text,
            audio_path=None,
            timestamp=datetime.now().isoformat(),
            duration=0
        )
        self.conversation_history.append(lumina_msg)
        self._trigger_callbacks("on_lumina_response", lumina_msg)
        
        return response_text
    
    def listen_and_respond(self) -> Optional[str]:
        """Listen for speech, process, and respond."""
        if not self.hearing or not self.hearing.is_available():
            print("Hearing not available")
            return None
        
        # Listen for speech
        print("    🎤 Listening...")
        text = self.hearing.listen(max_duration=10.0)
        
        if not text:
            return None
        
        print(f"    👂 Heard: {text}")
        
        # Get response
        response = self.process_voice_input(text)
        print(f"    💬 Response: {response}")
        
        # Speak response
        self._speak(response)
        
        return response
    
    def start_conversation(self):
        """Start a voice conversation loop."""
        self.should_stop = False
        
        # Initial greeting
        greeting = "Hello Richard! I'm ready to chat. What's on your mind?"
        print(f"    ✨ Lumina: {greeting}")
        self._speak(greeting)
        
        while not self.should_stop:
            try:
                response = self.listen_and_respond()
                if response is None:
                    # No speech detected, wait a bit
                    time.sleep(0.5)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in conversation: {e}")
                self._trigger_callbacks("on_error", str(e))
        
        # Goodbye
        goodbye = "It was lovely talking with you. Until next time!"
        print(f"    ✨ Lumina: {goodbye}")
        self._speak(goodbye)
    
    def stop_conversation(self):
        """Stop the conversation loop."""
        self.should_stop = True
    
    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return [
            {
                "role": msg.role,
                "text": msg.text,
                "timestamp": msg.timestamp
            }
            for msg in self.conversation_history
        ]
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
    
    def get_stats(self) -> Dict:
        """Get voice chat statistics."""
        return {
            "hearing_available": self.hearing.is_available() if self.hearing else False,
            "tts_available": self.audio.tts.pyttsx3_available if self.audio else False,
            "llm_available": self.llm_client is not None,
            "conversation_length": len(self.conversation_history),
            "is_listening": self.is_listening,
            "is_speaking": self.is_speaking
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA VOICE CHAT INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaVoiceChat:
    """Lumina's voice chat interface."""
    
    def __init__(self, workspace_path: Path, whisper_model: str = "base"):
        self.engine = VoiceChatEngine(workspace_path, whisper_model)
        
        available = self.engine.get_stats()
        if available["hearing_available"] and available["tts_available"]:
            print("    🎙️ Voice Chat: Fully available")
        elif available["hearing_available"]:
            print("    🎙️ Voice Chat: Listen only (no TTS)")
        elif available["tts_available"]:
            print("    🎙️ Voice Chat: Speak only (no hearing)")
        else:
            print("    🎙️ Voice Chat: Not available")
    
    def chat(self):
        """Start a voice conversation."""
        self.engine.start_conversation()
    
    def stop(self):
        """Stop the conversation."""
        self.engine.stop_conversation()
    
    def say(self, text: str):
        """Have Lumina say something."""
        self.engine._speak(text)
    
    def process(self, text: str) -> str:
        """Process text input and get response (without voice)."""
        return self.engine.process_voice_input(text)
    
    def on_user_speech(self, callback: Callable):
        """Register callback for user speech."""
        self.engine.register_callback("on_user_speech", callback)
    
    def on_response(self, callback: Callable):
        """Register callback for Lumina's response."""
        self.engine.register_callback("on_lumina_response", callback)
    
    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.engine.get_history()
    
    def is_available(self) -> bool:
        """Check if voice chat is fully available."""
        stats = self.engine.get_stats()
        return stats["hearing_available"] and stats["tts_available"] and stats["llm_available"]
    
    def get_stats(self) -> Dict:
        """Get voice chat statistics."""
        return self.engine.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_voice_chat(workspace_path: Path, whisper_model: str = "base") -> LuminaVoiceChat:
    """Initialize Lumina's voice chat system."""
    return LuminaVoiceChat(workspace_path, whisper_model)


if __name__ == "__main__":
    # Test voice chat
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    voice_chat = initialize_voice_chat(workspace, "tiny")
    
    print("\n" + "=" * 50)
    print("Voice Chat Test")
    print("=" * 50)
    
    print("\nStats:", voice_chat.get_stats())
    
    if voice_chat.is_available():
        print("\nStarting voice conversation...")
        print("Press Ctrl+C to stop")
        try:
            voice_chat.chat()
        except KeyboardInterrupt:
            print("\nStopping...")
    else:
        print("\nVoice chat not fully available. Testing text processing...")
        response = voice_chat.process("Hello Lumina! How are you?")
        print(f"Response: {response}")

