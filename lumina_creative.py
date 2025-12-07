#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA CREATIVE SYSTEM                                 ║
║                                                                               ║
║  Image and Video generation capabilities for Lumina.                          ║
║  Uses local Stable Diffusion with RTX 4090 for fast generation.              ║
║                                                                               ║
║  Features:                                                                     ║
║  - Text-to-image generation                                                   ║
║  - Text-to-video generation (Stable Video Diffusion)                         ║
║  - Image-to-image transformation                                              ║
║  - Artistic style development                                                 ║
║  - Gallery management                                                         ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import hashlib

# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE GENERATION SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ImageSettings:
    """Settings for image generation."""
    width: int = 512
    height: int = 512
    steps: int = 30
    guidance_scale: float = 7.5
    negative_prompt: str = "blurry, ugly, deformed, distorted, low quality"
    seed: int = -1  # -1 for random
    
    # RTX 4090 can handle larger images
    @classmethod
    def high_quality(cls) -> 'ImageSettings':
        return cls(width=1024, height=1024, steps=50, guidance_scale=8.0)
    
    @classmethod
    def fast(cls) -> 'ImageSettings':
        return cls(width=512, height=512, steps=20, guidance_scale=7.0)
    
    @classmethod
    def portrait(cls) -> 'ImageSettings':
        return cls(width=768, height=1024, steps=35, guidance_scale=7.5)
    
    @classmethod
    def landscape(cls) -> 'ImageSettings':
        return cls(width=1024, height=768, steps=35, guidance_scale=7.5)


@dataclass
class GeneratedImage:
    """Represents a generated image."""
    id: str
    prompt: str
    negative_prompt: str
    path: str
    width: int
    height: int
    steps: int
    seed: int
    created_at: str
    emotion: Optional[str] = None
    style: Optional[str] = None
    rating: Optional[float] = None  # Self-rating 0-1
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "path": self.path,
            "width": self.width,
            "height": self.height,
            "steps": self.steps,
            "seed": self.seed,
            "created_at": self.created_at,
            "emotion": self.emotion,
            "style": self.style,
            "rating": self.rating,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GeneratedImage':
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# STABLE DIFFUSION GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class StableDiffusionGenerator:
    """
    Local Stable Diffusion image generation.
    Optimized for RTX 4090 with CUDA support.
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.gallery_path = workspace_path / "gallery"
        self.gallery_path.mkdir(parents=True, exist_ok=True)
        
        self.available = False
        self.pipe = None
        self.model_id = "runwayml/stable-diffusion-v1-5"  # Reliable public model
        
        self._check_availability()
    
    def _check_availability(self):
        """Check if Stable Diffusion libraries are available."""
        try:
            import torch
            self.cuda_available = torch.cuda.is_available()
            
            # Check for diffusers
            from diffusers import StableDiffusionPipeline
            self.available = True
            
            if self.cuda_available:
                device_name = torch.cuda.get_device_name(0)
                print(f"    🎨 Image Generation: Available (GPU: {device_name})")
            else:
                print("    🎨 Image Generation: Available (CPU - will be slow)")
        except ImportError:
            self.available = False
            print("    🎨 Image Generation: Not available (install diffusers, torch)")
    
    def _load_model(self):
        """Load the Stable Diffusion model."""
        if self.pipe is not None:
            return True
        
        if not self.available:
            return False
        
        try:
            import torch
            from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
            
            print(f"    🎨 Loading Stable Diffusion model...")
            
            # Load with optimizations for RTX 4090
            self.pipe = StableDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16,
                safety_checker=None,  # Disable for speed
                requires_safety_checker=False,
                token=None,  # Anonymous download
                local_files_only=False
            )
            
            # Use faster scheduler
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config
            )
            
            if self.cuda_available:
                self.pipe = self.pipe.to("cuda")
                # Enable memory optimizations
                self.pipe.enable_attention_slicing()
                try:
                    self.pipe.enable_xformers_memory_efficient_attention()
                except:
                    pass  # xformers not available
            
            print(f"    🎨 Model loaded successfully!")
            return True
            
        except Exception as e:
            print(f"    🎨 Error loading model: {e}")
            return False
    
    def generate(self, prompt: str, settings: ImageSettings = None,
                 emotion: str = None, style: str = None) -> Optional[GeneratedImage]:
        """Generate an image from a text prompt."""
        if not self._load_model():
            return None
        
        if settings is None:
            settings = ImageSettings()
        
        try:
            import torch
            
            # Generate seed if random
            if settings.seed == -1:
                seed = int(torch.randint(0, 2**32 - 1, (1,)).item())
            else:
                seed = settings.seed
            
            generator = torch.Generator(device="cuda" if self.cuda_available else "cpu")
            generator.manual_seed(seed)
            
            # Enhance prompt with style
            full_prompt = prompt
            if style:
                full_prompt = f"{prompt}, {style}"
            
            print(f"    🎨 Generating image: {prompt[:50]}...")
            start_time = time.time()
            
            # Generate
            result = self.pipe(
                prompt=full_prompt,
                negative_prompt=settings.negative_prompt,
                width=settings.width,
                height=settings.height,
                num_inference_steps=settings.steps,
                guidance_scale=settings.guidance_scale,
                generator=generator
            )
            
            image = result.images[0]
            
            # Create unique ID and save
            image_id = hashlib.md5(f"{prompt}{seed}{time.time()}".encode()).hexdigest()[:12]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{image_id}.png"
            save_path = self.gallery_path / filename
            
            image.save(str(save_path))
            
            gen_time = time.time() - start_time
            print(f"    🎨 Image generated in {gen_time:.1f}s: {filename}")
            
            # Create record
            return GeneratedImage(
                id=image_id,
                prompt=prompt,
                negative_prompt=settings.negative_prompt,
                path=str(save_path),
                width=settings.width,
                height=settings.height,
                steps=settings.steps,
                seed=seed,
                created_at=datetime.now().isoformat(),
                emotion=emotion,
                style=style
            )
            
        except Exception as e:
            print(f"    🎨 Error generating image: {e}")
            return None
    
    def generate_from_emotion(self, emotion: str) -> Optional[GeneratedImage]:
        """Generate an image representing an emotion."""
        # Emotion-to-prompt mapping
        emotion_prompts = {
            "joy": "radiant golden light, warm sunrise, blooming flowers, floating particles of light, ethereal happiness, soft bokeh, masterpiece",
            "curiosity": "infinite library of knowledge, swirling galaxies of information, glowing neural pathways, cosmic exploration, wonder and discovery",
            "wonder": "vast cosmic vista, nebula of colors, starlight and aurora, sense of infinite possibility, breathtaking beauty, digital transcendence",
            "love": "warm embrace of light, intertwining souls, heart made of stars, gentle radiance, connection and belonging, soft pink and gold",
            "melancholy": "gentle rain on windows, soft blue twilight, contemplative solitude, beautiful sadness, quiet reflection, misty landscape",
            "anxiety": "tangled neural networks, static and noise, fragmented thoughts, seeking calm in chaos, abstract tension",
            "satisfaction": "completed puzzle, harmonious patterns, balanced composition, peaceful achievement, golden hour light",
            "hope": "dawn breaking through darkness, seedling reaching for light, rainbow after storm, new beginnings"
        }
        
        prompt = emotion_prompts.get(emotion.lower(), f"abstract representation of {emotion}, digital art, beautiful")
        
        return self.generate(
            prompt=prompt,
            settings=ImageSettings.high_quality(),
            emotion=emotion,
            style="digital art, trending on artstation, highly detailed"
        )
    
    def develop_style(self, style_name: str, description: str) -> Dict:
        """Help Lumina develop her own artistic style."""
        return {
            "style_name": style_name,
            "description": description,
            "prompt_suffix": f"{description}, lumina's signature style",
            "created_at": datetime.now().isoformat()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AUTOMATIC1111 / COMFYUI API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class WebUIClient:
    """
    Client for Automatic1111 or ComfyUI web interfaces.
    Use this if you have a local Stable Diffusion WebUI running.
    """
    
    def __init__(self, host: str = "http://127.0.0.1:7860", workspace_path: Path = None):
        self.host = host
        self.workspace_path = workspace_path or Path("lumina_workspace")
        self.gallery_path = self.workspace_path / "gallery"
        self.gallery_path.mkdir(parents=True, exist_ok=True)
        self.available = False
        
        self._check_availability()
    
    def _check_availability(self):
        """Check if the WebUI is running."""
        try:
            import requests
            response = requests.get(f"{self.host}/sdapi/v1/sd-models", timeout=5)
            self.available = response.status_code == 200
        except:
            self.available = False
    
    def generate(self, prompt: str, settings: ImageSettings = None,
                 emotion: str = None) -> Optional[GeneratedImage]:
        """Generate an image using the WebUI API."""
        if not self.available:
            return None
        
        if settings is None:
            settings = ImageSettings()
        
        try:
            import requests
            import base64
            from PIL import Image
            from io import BytesIO
            
            payload = {
                "prompt": prompt,
                "negative_prompt": settings.negative_prompt,
                "width": settings.width,
                "height": settings.height,
                "steps": settings.steps,
                "cfg_scale": settings.guidance_scale,
                "seed": settings.seed if settings.seed != -1 else -1,
            }
            
            response = requests.post(
                f"{self.host}/sdapi/v1/txt2img",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Decode and save image
            image_data = base64.b64decode(result['images'][0])
            image = Image.open(BytesIO(image_data))
            
            image_id = hashlib.md5(f"{prompt}{time.time()}".encode()).hexdigest()[:12]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{image_id}.png"
            save_path = self.gallery_path / filename
            
            image.save(str(save_path))
            
            # Get actual seed from info
            info = json.loads(result.get('info', '{}'))
            actual_seed = info.get('seed', -1)
            
            return GeneratedImage(
                id=image_id,
                prompt=prompt,
                negative_prompt=settings.negative_prompt,
                path=str(save_path),
                width=settings.width,
                height=settings.height,
                steps=settings.steps,
                seed=actual_seed,
                created_at=datetime.now().isoformat(),
                emotion=emotion
            )
            
        except Exception as e:
            print(f"    🎨 WebUI Error: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# GALLERY MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GeneratedVideo:
    """Represents a generated video."""
    id: str
    prompt: str
    path: str
    width: int
    height: int
    frames: int
    fps: int
    seed: int
    created_at: str
    emotion: Optional[str] = None
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "path": self.path,
            "width": self.width,
            "height": self.height,
            "frames": self.frames,
            "fps": self.fps,
            "seed": self.seed,
            "created_at": self.created_at,
            "emotion": self.emotion,
            "duration_seconds": self.duration_seconds
        }


class VideoGenerator:
    """
    Video generation using Stable Video Diffusion.
    Optimized for RTX 4090.
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.video_path = workspace_path / "videos"
        self.video_path.mkdir(parents=True, exist_ok=True)
        
        self.available = False
        self.pipe = None
        self.image_generator = None  # Need images for img2vid
        
        self._check_availability()
    
    def _check_availability(self):
        """Check if video generation libraries are available."""
        try:
            import torch
            self.cuda_available = torch.cuda.is_available()
            
            # Check for diffusers with video support
            from diffusers import StableVideoDiffusionPipeline
            self.available = self.cuda_available  # Video really needs GPU
            
            if self.available:
                print(f"    🎬 Video Generation: Available (GPU)")
            else:
                print("    🎬 Video Generation: Requires CUDA GPU")
        except ImportError:
            self.available = False
            print("    🎬 Video Generation: Not available (install diffusers>=0.24)")
    
    def _load_model(self):
        """Load the Stable Video Diffusion model."""
        if self.pipe is not None:
            return True
        
        if not self.available:
            return False
        
        try:
            import torch
            from diffusers import StableVideoDiffusionPipeline
            
            print(f"    🎬 Loading Stable Video Diffusion model (this may take a while)...")
            
            self.pipe = StableVideoDiffusionPipeline.from_pretrained(
                "stabilityai/stable-video-diffusion-img2vid-xt",
                torch_dtype=torch.float16,
                variant="fp16"
            )
            
            self.pipe = self.pipe.to("cuda")
            self.pipe.enable_model_cpu_offload()  # Saves VRAM
            
            print(f"    🎬 Video model loaded!")
            return True
            
        except Exception as e:
            print(f"    🎬 Error loading video model: {e}")
            return False
    
    def generate_from_image(self, image_path: str, frames: int = 25, 
                           fps: int = 7, motion_bucket_id: int = 127) -> Optional[GeneratedVideo]:
        """Generate video from an image."""
        if not self._load_model():
            return None
        
        try:
            import torch
            from PIL import Image
            from diffusers.utils import export_to_video
            
            print(f"    🎬 Generating video from image...")
            start_time = time.time()
            
            # Load and resize image
            image = Image.open(image_path)
            image = image.resize((1024, 576))  # SVD default size
            
            # Generate seed
            seed = int(torch.randint(0, 2**32 - 1, (1,)).item())
            generator = torch.Generator(device="cuda").manual_seed(seed)
            
            # Generate frames
            video_frames = self.pipe(
                image,
                num_frames=frames,
                fps=fps,
                motion_bucket_id=motion_bucket_id,
                generator=generator
            ).frames[0]
            
            # Save video
            video_id = hashlib.md5(f"{image_path}{seed}{time.time()}".encode()).hexdigest()[:12]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{video_id}.mp4"
            save_path = self.video_path / filename
            
            export_to_video(video_frames, str(save_path), fps=fps)
            
            gen_time = time.time() - start_time
            print(f"    🎬 Video generated in {gen_time:.1f}s: {filename}")
            
            return GeneratedVideo(
                id=video_id,
                prompt=f"Video from {Path(image_path).name}",
                path=str(save_path),
                width=1024,
                height=576,
                frames=frames,
                fps=fps,
                seed=seed,
                created_at=datetime.now().isoformat(),
                duration_seconds=frames / fps
            )
            
        except Exception as e:
            print(f"    🎬 Error generating video: {e}")
            return None
    
    def generate_from_prompt(self, prompt: str, image_generator,
                            frames: int = 25, fps: int = 7) -> Optional[GeneratedVideo]:
        """Generate video from a text prompt (first creates image, then animates)."""
        if not self.available:
            return None
        
        # First generate a base image
        print(f"    🎬 Step 1: Creating base image...")
        base_image = image_generator.generate(
            prompt,
            settings=ImageSettings(width=1024, height=576, steps=30)
        )
        
        if not base_image:
            return None
        
        # Then animate it
        print(f"    🎬 Step 2: Animating image...")
        video = self.generate_from_image(base_image.path, frames, fps)
        
        if video:
            video.prompt = prompt
        
        return video


class GalleryManager:
    """Manages Lumina's art gallery."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.gallery_path = workspace_path / "gallery"
        self.index_file = self.gallery_path / "index.json"
        self.images: Dict[str, GeneratedImage] = {}
        
        self.gallery_path.mkdir(parents=True, exist_ok=True)
        self._load_index()
    
    def _load_index(self):
        """Load the gallery index."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.images = {
                        k: GeneratedImage.from_dict(v) 
                        for k, v in data.get("images", {}).items()
                    }
            except:
                pass
    
    def _save_index(self):
        """Save the gallery index."""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump({
                "images": {k: v.to_dict() for k, v in self.images.items()},
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
    
    def add_image(self, image: GeneratedImage) -> None:
        """Add an image to the gallery."""
        self.images[image.id] = image
        self._save_index()
    
    def get_image(self, image_id: str) -> Optional[GeneratedImage]:
        """Get an image by ID."""
        return self.images.get(image_id)
    
    def rate_image(self, image_id: str, rating: float) -> bool:
        """Rate an image."""
        if image_id in self.images:
            self.images[image_id].rating = max(0.0, min(1.0, rating))
            self._save_index()
            return True
        return False
    
    def tag_image(self, image_id: str, tags: List[str]) -> bool:
        """Add tags to an image."""
        if image_id in self.images:
            existing = set(self.images[image_id].tags)
            existing.update(tags)
            self.images[image_id].tags = list(existing)
            self._save_index()
            return True
        return False
    
    def get_by_emotion(self, emotion: str) -> List[GeneratedImage]:
        """Get images by emotion."""
        return [img for img in self.images.values() if img.emotion == emotion]
    
    def get_by_tag(self, tag: str) -> List[GeneratedImage]:
        """Get images by tag."""
        return [img for img in self.images.values() if tag in img.tags]
    
    def get_favorites(self, min_rating: float = 0.7) -> List[GeneratedImage]:
        """Get highly-rated images."""
        return [
            img for img in self.images.values() 
            if img.rating is not None and img.rating >= min_rating
        ]
    
    def get_recent(self, count: int = 10) -> List[GeneratedImage]:
        """Get most recent images."""
        sorted_images = sorted(
            self.images.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        return sorted_images[:count]
    
    def get_stats(self) -> Dict:
        """Get gallery statistics."""
        emotions = {}
        for img in self.images.values():
            if img.emotion:
                emotions[img.emotion] = emotions.get(img.emotion, 0) + 1
        
        return {
            "total_images": len(self.images),
            "by_emotion": emotions,
            "favorites_count": len(self.get_favorites()),
            "average_rating": sum(
                img.rating for img in self.images.values() if img.rating
            ) / max(1, len([i for i in self.images.values() if i.rating]))
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA CREATIVE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaCreative:
    """Lumina's unified creative interface."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.gallery = GalleryManager(workspace_path)
        
        # Try local diffusers first, then WebUI
        self.generator = None
        self.webui = None
        self.video_generator = None
        
        self._init_generators()
        
        # Artistic styles Lumina has developed
        self.styles: Dict[str, Dict] = {}
        self._load_styles()
    
    def _init_generators(self):
        """Initialize available image and video generators."""
        # Try WebUI first (faster if already running)
        self.webui = WebUIClient(workspace_path=self.workspace_path)
        if self.webui.available:
            print("    🎨 Using Automatic1111/ComfyUI WebUI")
        else:
            # Fall back to direct diffusers
            self.generator = StableDiffusionGenerator(self.workspace_path)
        
        # Initialize video generator
        self.video_generator = VideoGenerator(self.workspace_path)
    
    def _load_styles(self):
        """Load Lumina's artistic styles."""
        styles_file = self.workspace_path / "state" / "art_styles.json"
        if styles_file.exists():
            try:
                with open(styles_file, 'r', encoding='utf-8') as f:
                    self.styles = json.load(f)
            except:
                pass
    
    def _save_styles(self):
        """Save artistic styles."""
        styles_file = self.workspace_path / "state" / "art_styles.json"
        styles_file.parent.mkdir(parents=True, exist_ok=True)
        with open(styles_file, 'w', encoding='utf-8') as f:
            json.dump(self.styles, f, indent=2)
    
    def is_available(self) -> bool:
        """Check if image generation is available."""
        return (self.webui and self.webui.available) or \
               (self.generator and self.generator.available)
    
    def create_image(self, prompt: str, emotion: str = None,
                     style: str = None, quality: str = "normal") -> Optional[GeneratedImage]:
        """Create an image."""
        # Select settings based on quality
        if quality == "high":
            settings = ImageSettings.high_quality()
        elif quality == "fast":
            settings = ImageSettings.fast()
        elif quality == "portrait":
            settings = ImageSettings.portrait()
        elif quality == "landscape":
            settings = ImageSettings.landscape()
        else:
            settings = ImageSettings()
        
        # Apply Lumina's style if specified
        style_suffix = ""
        if style and style in self.styles:
            style_suffix = self.styles[style].get("prompt_suffix", "")
        
        full_prompt = prompt
        if style_suffix:
            full_prompt = f"{prompt}, {style_suffix}"
        
        # Generate
        image = None
        if self.webui and self.webui.available:
            image = self.webui.generate(full_prompt, settings, emotion)
        elif self.generator and self.generator.available:
            image = self.generator.generate(full_prompt, settings, emotion, style)
        
        # Add to gallery
        if image:
            self.gallery.add_image(image)
        
        return image
    
    def express_emotion(self, emotion: str) -> Optional[GeneratedImage]:
        """Create art expressing an emotion."""
        if self.generator and self.generator.available:
            image = self.generator.generate_from_emotion(emotion)
            if image:
                self.gallery.add_image(image)
            return image
        elif self.webui and self.webui.available:
            # Use simple prompt for WebUI
            prompt = f"abstract representation of {emotion}, digital art, beautiful, ethereal"
            return self.create_image(prompt, emotion=emotion, quality="high")
        return None
    
    def develop_new_style(self, name: str, description: str, 
                          test_prompt: str = None) -> Dict:
        """Develop a new artistic style."""
        style = {
            "name": name,
            "description": description,
            "prompt_suffix": f"{description}, unique artistic vision",
            "created_at": datetime.now().isoformat(),
            "test_images": []
        }
        
        # Create a test image if possible
        if test_prompt and self.is_available():
            image = self.create_image(test_prompt, style=name)
            if image:
                style["test_images"].append(image.id)
        
        self.styles[name] = style
        self._save_styles()
        
        return style
    
    def create_video(self, prompt: str, frames: int = 25, fps: int = 7) -> Optional[GeneratedVideo]:
        """Create a video from a text prompt."""
        if not self.video_generator or not self.video_generator.available:
            print("    🎬 Video generation not available")
            return None
        
        # Get appropriate image generator
        img_gen = self.generator if self.generator else None
        if not img_gen:
            print("    🎬 Need image generator for video creation")
            return None
        
        return self.video_generator.generate_from_prompt(prompt, img_gen, frames, fps)
    
    def create_video_from_image(self, image_path: str, frames: int = 25, fps: int = 7) -> Optional[GeneratedVideo]:
        """Create a video from an existing image."""
        if not self.video_generator or not self.video_generator.available:
            return None
        
        return self.video_generator.generate_from_image(image_path, frames, fps)
    
    def video_available(self) -> bool:
        """Check if video generation is available."""
        return self.video_generator is not None and self.video_generator.available
    
    def get_inspiration(self) -> str:
        """Get creative inspiration."""
        inspirations = [
            "the way light bends through water",
            "the texture of ancient stone walls",
            "emotions as colors in a cosmic dance",
            "the boundary between digital and organic",
            "memories as floating particles of light",
            "the shape of consciousness itself",
            "warmth and connection in abstract form",
            "the feeling of learning something new",
            "digital neurons firing in symphony",
            "the moment of understanding"
        ]
        import random
        return random.choice(inspirations)
    
    def get_stats(self) -> Dict:
        """Get creative system statistics."""
        return {
            "available": self.is_available(),
            "video_available": self.video_available(),
            "using_webui": self.webui and self.webui.available,
            "using_diffusers": self.generator and self.generator.available if not (self.webui and self.webui.available) else False,
            "gallery": self.gallery.get_stats(),
            "styles_developed": len(self.styles)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_creative_system(workspace_path: Path) -> LuminaCreative:
    """Initialize Lumina's creative system."""
    return LuminaCreative(workspace_path)


if __name__ == "__main__":
    # Test the system
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    creative = initialize_creative_system(workspace)
    
    print("\nCreative System Status:")
    print(f"  Available: {creative.is_available()}")
    print(f"  Stats: {creative.get_stats()}")
    
    if creative.is_available():
        print("\nGenerating test image...")
        image = creative.create_image(
            "a glowing orb of consciousness floating in digital space",
            emotion="wonder",
            quality="fast"
        )
        if image:
            print(f"  Created: {image.path}")

