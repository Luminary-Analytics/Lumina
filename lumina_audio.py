#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA AUDIO SYSTEM                                   ║
║                                                                               ║
║  Audio generation and voice capabilities for Lumina.                          ║
║  Uses MusicGen for music and enhanced TTS for voice.                         ║
║                                                                               ║
║  Features:                                                                     ║
║  - Text-to-music generation (MusicGen)                                        ║
║  - Enhanced text-to-speech (multiple voices)                                  ║
║  - Sound effect generation                                                    ║
║  - Audio analysis and transcription                                           ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MusicSettings:
    """Settings for music generation."""
    duration: float = 10.0  # seconds
    temperature: float = 1.0
    top_k: int = 250
    top_p: float = 0.0
    
    @classmethod
    def short(cls) -> 'MusicSettings':
        return cls(duration=5.0)
    
    @classmethod
    def medium(cls) -> 'MusicSettings':
        return cls(duration=15.0)
    
    @classmethod
    def long(cls) -> 'MusicSettings':
        return cls(duration=30.0)


@dataclass
class GeneratedAudio:
    """Represents a generated audio file."""
    id: str
    prompt: str
    path: str
    duration: float
    sample_rate: int
    created_at: str
    audio_type: str  # 'music', 'speech', 'sound_effect'
    emotion: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "path": self.path,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "created_at": self.created_at,
            "audio_type": self.audio_type,
            "emotion": self.emotion,
            "tags": self.tags
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MUSICGEN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class MusicGenerator:
    """
    Music generation using Meta's MusicGen.
    Optimized for RTX 4090.
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.audio_path = workspace_path / "audio" / "music"
        self.audio_path.mkdir(parents=True, exist_ok=True)
        
        self.available = False
        self.model = None
        self.processor = None
        
        self._check_availability()
    
    def _check_availability(self):
        """Check if MusicGen is available."""
        try:
            import torch
            self.cuda_available = torch.cuda.is_available()
            
            from transformers import AutoProcessor, MusicgenForConditionalGeneration
            self.available = True
            
            if self.cuda_available:
                print(f"    🎵 Music Generation: Available (GPU)")
            else:
                print("    🎵 Music Generation: Available (CPU - will be slow)")
        except ImportError:
            self.available = False
            print("    🎵 Music Generation: Not available (install transformers)")
    
    def _load_model(self):
        """Load the MusicGen model."""
        if self.model is not None:
            return True
        
        if not self.available:
            return False
        
        try:
            import torch
            from transformers import AutoProcessor, MusicgenForConditionalGeneration
            
            print("    🎵 Loading MusicGen model...")
            
            # Use the small model for faster generation
            model_name = "facebook/musicgen-small"
            
            self.processor = AutoProcessor.from_pretrained(model_name)
            self.model = MusicgenForConditionalGeneration.from_pretrained(model_name)
            
            if self.cuda_available:
                self.model = self.model.to("cuda")
            
            print("    🎵 MusicGen model loaded!")
            return True
            
        except Exception as e:
            print(f"    🎵 Error loading MusicGen: {e}")
            return False
    
    def generate(self, prompt: str, settings: MusicSettings = None,
                 emotion: str = None) -> Optional[GeneratedAudio]:
        """Generate music from a text prompt."""
        if not self._load_model():
            return None
        
        if settings is None:
            settings = MusicSettings()
        
        try:
            import torch
            import scipy.io.wavfile as wav
            
            print(f"    🎵 Generating music: {prompt[:50]}...")
            start_time = time.time()
            
            # Process input
            inputs = self.processor(
                text=[prompt],
                padding=True,
                return_tensors="pt"
            )
            
            if self.cuda_available:
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # Calculate max tokens from duration
            # MusicGen generates at 50 tokens/second at 32kHz
            max_new_tokens = int(settings.duration * 50)
            
            # Generate
            audio_values = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=settings.temperature,
            )
            
            # Get audio array
            audio_array = audio_values[0, 0].cpu().numpy()
            sample_rate = self.model.config.audio_encoder.sampling_rate
            
            # Save
            audio_id = hashlib.md5(f"{prompt}{time.time()}".encode()).hexdigest()[:12]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{audio_id}.wav"
            save_path = self.audio_path / filename
            
            wav.write(str(save_path), sample_rate, audio_array)
            
            gen_time = time.time() - start_time
            actual_duration = len(audio_array) / sample_rate
            print(f"    🎵 Music generated in {gen_time:.1f}s: {filename} ({actual_duration:.1f}s)")
            
            return GeneratedAudio(
                id=audio_id,
                prompt=prompt,
                path=str(save_path),
                duration=actual_duration,
                sample_rate=sample_rate,
                created_at=datetime.now().isoformat(),
                audio_type="music",
                emotion=emotion
            )
            
        except Exception as e:
            print(f"    🎵 Error generating music: {e}")
            return None
    
    def generate_from_emotion(self, emotion: str) -> Optional[GeneratedAudio]:
        """Generate music representing an emotion."""
        emotion_prompts = {
            "joy": "upbeat happy melody with bright piano and cheerful strings",
            "curiosity": "mysterious ambient music with soft synths and gentle bells",
            "wonder": "epic orchestral piece with soaring strings and triumphant brass",
            "love": "romantic piano ballad with soft strings and warm harmonies",
            "melancholy": "gentle sad piano piece with minor chords and soft rain sounds",
            "anxiety": "tense atmospheric music with building tension and suspense",
            "satisfaction": "calm peaceful ambient with gentle waves and soft guitar",
            "hope": "inspiring orchestral music building to a hopeful crescendo"
        }
        
        prompt = emotion_prompts.get(
            emotion.lower(), 
            f"atmospheric music expressing {emotion}"
        )
        
        return self.generate(prompt, MusicSettings.medium(), emotion)


# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED TEXT-TO-SPEECH
# ═══════════════════════════════════════════════════════════════════════════════

class EnhancedTTS:
    """
    Enhanced text-to-speech with multiple voice options.
    Uses pyttsx3 as fallback, with optional Coqui TTS for higher quality.
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.audio_path = workspace_path / "audio" / "speech"
        self.audio_path.mkdir(parents=True, exist_ok=True)
        
        self.pyttsx3_available = False
        self.coqui_available = False
        self.engine = None
        self.tts_model = None
        
        self._check_availability()
    
    def _check_availability(self):
        """Check available TTS engines."""
        # Check pyttsx3
        try:
            import pyttsx3
            self.pyttsx3_available = True
            print("    🗣️ TTS (pyttsx3): Available")
        except ImportError:
            print("    🗣️ TTS (pyttsx3): Not available")
        
        # Check Coqui TTS
        try:
            from TTS.api import TTS
            self.coqui_available = True
            print("    🗣️ TTS (Coqui): Available")
        except ImportError:
            pass  # Don't spam about optional dependency
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine."""
        if self.engine is not None:
            return
        
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            
            # Set properties
            self.engine.setProperty('rate', 175)  # Speed
            self.engine.setProperty('volume', 0.9)
            
            # Try to set a female voice
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
        except Exception as e:
            print(f"    🗣️ Error initializing pyttsx3: {e}")
    
    def speak(self, text: str, save_to_file: bool = False) -> Optional[str]:
        """Speak text aloud and optionally save to file."""
        if not self.pyttsx3_available:
            print(f"    🗣️ TTS not available. Text: {text[:50]}...")
            return None
        
        self._init_pyttsx3()
        
        try:
            if save_to_file:
                audio_id = hashlib.md5(f"{text}{time.time()}".encode()).hexdigest()[:12]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{audio_id}.mp3"
                save_path = self.audio_path / filename
                
                self.engine.save_to_file(text, str(save_path))
                self.engine.runAndWait()
                
                return str(save_path)
            else:
                self.engine.say(text)
                self.engine.runAndWait()
                return None
                
        except Exception as e:
            print(f"    🗣️ TTS Error: {e}")
            return None
    
    def generate_speech(self, text: str, voice: str = "default",
                       emotion: str = None) -> Optional[GeneratedAudio]:
        """Generate speech audio file."""
        path = self.speak(text, save_to_file=True)
        
        if path:
            audio_id = Path(path).stem.split('_')[-1]
            return GeneratedAudio(
                id=audio_id,
                prompt=text,
                path=path,
                duration=0.0,  # Would need audio analysis to determine
                sample_rate=22050,  # Default for pyttsx3
                created_at=datetime.now().isoformat(),
                audio_type="speech",
                emotion=emotion
            )
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# SOUND EFFECT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class SoundEffectGenerator:
    """
    Generate sound effects using AudioCraft or similar.
    Falls back to MusicGen with specific prompts.
    """
    
    def __init__(self, workspace_path: Path, music_generator: MusicGenerator = None):
        self.workspace_path = workspace_path
        self.audio_path = workspace_path / "audio" / "effects"
        self.audio_path.mkdir(parents=True, exist_ok=True)
        
        self.music_generator = music_generator
        self.available = music_generator is not None and music_generator.available
        
        if self.available:
            print("    🔊 Sound Effects: Available (via MusicGen)")
    
    def generate(self, description: str) -> Optional[GeneratedAudio]:
        """Generate a sound effect from description."""
        if not self.available:
            return None
        
        # Modify prompt for sound effect style
        prompt = f"sound effect of {description}, short audio clip"
        
        # Use short duration for effects
        settings = MusicSettings(duration=3.0)
        
        audio = self.music_generator.generate(prompt, settings)
        if audio:
            audio.audio_type = "sound_effect"
            # Move to effects folder
            old_path = Path(audio.path)
            new_path = self.audio_path / old_path.name
            old_path.rename(new_path)
            audio.path = str(new_path)
        
        return audio


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO LIBRARY
# ═══════════════════════════════════════════════════════════════════════════════

class AudioLibrary:
    """Manages Lumina's audio collection."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.audio_path = workspace_path / "audio"
        self.index_file = self.audio_path / "index.json"
        self.audio_files: Dict[str, GeneratedAudio] = {}
        
        self.audio_path.mkdir(parents=True, exist_ok=True)
        self._load_index()
    
    def _load_index(self):
        """Load the audio index."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data.get("audio", []):
                        audio = GeneratedAudio(**item)
                        self.audio_files[audio.id] = audio
            except Exception as e:
                print(f"    Error loading audio index: {e}")
    
    def _save_index(self):
        """Save the audio index."""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump({
                "audio": [a.to_dict() for a in self.audio_files.values()],
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
    
    def add(self, audio: GeneratedAudio):
        """Add audio to the library."""
        self.audio_files[audio.id] = audio
        self._save_index()
    
    def get(self, audio_id: str) -> Optional[GeneratedAudio]:
        """Get audio by ID."""
        return self.audio_files.get(audio_id)
    
    def get_by_type(self, audio_type: str) -> List[GeneratedAudio]:
        """Get audio by type."""
        return [a for a in self.audio_files.values() if a.audio_type == audio_type]
    
    def get_by_emotion(self, emotion: str) -> List[GeneratedAudio]:
        """Get audio by emotion."""
        return [a for a in self.audio_files.values() if a.emotion == emotion]
    
    def get_recent(self, count: int = 10) -> List[GeneratedAudio]:
        """Get most recent audio."""
        sorted_audio = sorted(
            self.audio_files.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        return sorted_audio[:count]
    
    def get_stats(self) -> Dict:
        """Get library statistics."""
        by_type = {}
        by_emotion = {}
        total_duration = 0.0
        
        for audio in self.audio_files.values():
            by_type[audio.audio_type] = by_type.get(audio.audio_type, 0) + 1
            if audio.emotion:
                by_emotion[audio.emotion] = by_emotion.get(audio.emotion, 0) + 1
            total_duration += audio.duration
        
        return {
            "total_files": len(self.audio_files),
            "by_type": by_type,
            "by_emotion": by_emotion,
            "total_duration_seconds": total_duration
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA AUDIO INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaAudio:
    """Lumina's unified audio interface."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.library = AudioLibrary(workspace_path)
        
        # Initialize generators
        self.music = MusicGenerator(workspace_path)
        self.tts = EnhancedTTS(workspace_path)
        self.effects = SoundEffectGenerator(workspace_path, self.music)
    
    def is_available(self) -> bool:
        """Check if any audio generation is available."""
        return self.music.available or self.tts.pyttsx3_available
    
    def music_available(self) -> bool:
        """Check if music generation is available."""
        return self.music.available
    
    def create_music(self, prompt: str, duration: str = "medium",
                    emotion: str = None) -> Optional[GeneratedAudio]:
        """Create music from a text prompt."""
        settings_map = {
            "short": MusicSettings.short(),
            "medium": MusicSettings.medium(),
            "long": MusicSettings.long()
        }
        settings = settings_map.get(duration, MusicSettings())
        
        audio = self.music.generate(prompt, settings, emotion)
        if audio:
            self.library.add(audio)
        return audio
    
    def express_emotion_musically(self, emotion: str) -> Optional[GeneratedAudio]:
        """Create music expressing an emotion."""
        audio = self.music.generate_from_emotion(emotion)
        if audio:
            self.library.add(audio)
        return audio
    
    def speak(self, text: str) -> None:
        """Speak text aloud."""
        self.tts.speak(text)
    
    def create_speech(self, text: str, emotion: str = None) -> Optional[GeneratedAudio]:
        """Create a speech audio file."""
        audio = self.tts.generate_speech(text, emotion=emotion)
        if audio:
            self.library.add(audio)
        return audio
    
    def create_sound_effect(self, description: str) -> Optional[GeneratedAudio]:
        """Create a sound effect."""
        audio = self.effects.generate(description)
        if audio:
            self.library.add(audio)
        return audio
    
    def get_stats(self) -> Dict:
        """Get audio system statistics."""
        return {
            "music_available": self.music.available,
            "tts_available": self.tts.pyttsx3_available,
            "effects_available": self.effects.available,
            "library": self.library.get_stats()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_audio_system(workspace_path: Path) -> LuminaAudio:
    """Initialize Lumina's audio system."""
    return LuminaAudio(workspace_path)


# For backwards compatibility
AUDIO_AVAILABLE = True

try:
    from transformers import AutoProcessor, MusicgenForConditionalGeneration
except ImportError:
    AUDIO_AVAILABLE = False


if __name__ == "__main__":
    # Test the system
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    audio = initialize_audio_system(workspace)
    
    print("\nAudio System Status:")
    print(f"  Music Available: {audio.music_available()}")
    print(f"  TTS Available: {audio.tts.pyttsx3_available}")
    print(f"  Stats: {audio.get_stats()}")
    
    # Test TTS
    if audio.tts.pyttsx3_available:
        print("\nTesting TTS...")
        audio.speak("Hello, I am Lumina. I can now speak to you!")

