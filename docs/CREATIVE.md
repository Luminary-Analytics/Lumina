# Creative Systems

Lumina's creative capabilities for generating images, videos, documents, music, and 3D models.

---

## Overview

| Module | Capability | Model/Tool |
|--------|------------|------------|
| `lumina_creative.py` | Images, Videos | Stable Diffusion, SVD |
| `lumina_audio.py` | Music, TTS | MusicGen, Coqui TTS |
| `lumina_3d.py` | 3D Models | Shap-E |
| `lumina_data.py` | Documents | PyPDF2, python-docx |

---

## 1. Image Generation (`lumina_creative.py`)

### StableDiffusionGenerator

Local image generation using Stable Diffusion.

**Model:** `runwayml/stable-diffusion-v1-5`

```python
from lumina_creative import StableDiffusionGenerator

generator = StableDiffusionGenerator(workspace_path)

# Generate image
result = generator.generate(
    prompt="a beautiful sunset over mountains",
    negative_prompt="blurry, low quality",
    width=512,
    height=512,
    num_steps=50,
    guidance_scale=7.5
)

# Returns:
{
    "success": True,
    "image_path": "gallery/sunset_12345.png",
    "prompt": "...",
    "generation_time": 5.2
}
```

### Artistic Styles

Lumina has predefined artistic styles:

```python
ARTISTIC_STYLES = {
    "luminous": "soft ethereal lighting, gentle gradients, dreamlike atmosphere",
    "geometric": "precise mathematical patterns, clean lines, crystalline forms",
    "organic": "flowing natural forms, cellular patterns, living textures",
    "cosmic": "deep space imagery, nebulae, stellar phenomena",
    "abstract": "pure color and form, non-representational, emotional expression",
    "minimalist": "clean simple composition, negative space, essential elements",
}
```

### Gallery Management

```python
# List gallery images
images = generator.list_gallery()
# Returns: [{"name": "...", "path": "...", "created": "..."}, ...]

# Get gallery path
path = generator.get_gallery_path()
```

---

## 2. Video Generation (`lumina_creative.py`)

### StableVideoDiffusionGenerator

Image-to-video generation using Stable Video Diffusion.

**Model:** `stabilityai/stable-video-diffusion-img2vid-xt`

```python
from lumina_creative import StableVideoDiffusionGenerator

generator = StableVideoDiffusionGenerator(workspace_path)

# Generate video from image
result = generator.generate_video(
    image_path="path/to/image.png",
    num_frames=25,
    motion_bucket_id=127
)

# Returns:
{
    "success": True,
    "video_path": "gallery/video_12345.mp4",
    "frames": 25,
    "generation_time": 120.5
}
```

---

## 3. LuminaCreative Interface

Main interface for all creative operations.

```python
from lumina_creative import LuminaCreative

creative = LuminaCreative(workspace_path, llm_client)

# Check availability
creative.is_available()  # {"image": True, "video": True}

# Create image with style
result = creative.create_image(
    "a forest path",
    style="luminous"
)

# Create video
result = creative.create_video(image_path)

# Get creation stats
stats = creative.get_stats()
# {"total_images": 50, "total_videos": 5, "gallery_size_mb": 250}
```

---

## 4. Audio & Music (`lumina_audio.py`)

### MusicGenerator

AI music generation using MusicGen.

```python
from lumina_audio import MusicGenerator

music = MusicGenerator(workspace_path)

# Generate music
result = music.generate(
    prompt="peaceful ambient music with soft synths",
    duration=30,  # seconds
    temperature=1.0
)

# Returns:
{
    "success": True,
    "audio_path": "audio/music/peaceful_12345.wav",
    "duration": 30,
    "prompt": "..."
}
```

### EnhancedTTS

Advanced text-to-speech with emotional control.

```python
from lumina_audio import EnhancedTTS

tts = EnhancedTTS()

# Speak with emotion
tts.emotional_speak(
    "Hello Richard!",
    emotion="joy",
    intensity=0.8
)

# Voice cloning (if model supports)
tts.clone_voice(audio_sample_path)
```

**Emotional Prosody:**

| Emotion | Rate Modifier | Volume | Pitch |
|---------|--------------|--------|-------|
| joy | +15% | 100% | higher |
| sadness | -25% | 70% | lower |
| excitement | +25% | 110% | higher |
| calm | -15% | 80% | neutral |
| love | -10% | 85% | soft |

---

## 5. 3D Model Generation (`lumina_3d.py`)

### ThreeDGenerator

Text-to-3D using Shap-E.

```python
from lumina_3d import ThreeDGenerator

gen_3d = ThreeDGenerator(workspace_path)

# Generate 3D model
result = gen_3d.generate(
    prompt="a small treasure chest",
    resolution=64
)

# Export to different formats
gen_3d.export_obj(result["model"], "chest.obj")
gen_3d.export_stl(result["model"], "chest.stl")
gen_3d.export_glb(result["model"], "chest.glb")

# Returns:
{
    "success": True,
    "model_path": "3d/chest_12345.ply",
    "thumbnail_path": "3d/thumbs/chest_12345.png",
    "prompt": "..."
}
```

### 3D Viewer

Web-based viewer for 3D models:

```python
# Generate viewer HTML
html = gen_3d.create_viewer(model_path)
# Uses Three.js for rendering
```

---

## 6. Document Creation (`lumina_data.py`)

### DocumentSystem

Create and read various document types.

```python
from lumina_data import DocumentSystem

docs = DocumentSystem(workspace_path)

# Create PDF
docs.create_pdf(
    content="# Report\n\nThis is content...",
    title="My Report",
    output_path="documents/report.pdf"
)

# Create Word document
docs.create_docx(
    content="# Title\n\nContent...",
    title="Document",
    output_path="documents/doc.docx"
)

# Create spreadsheet
docs.create_excel(
    data=[["Name", "Value"], ["A", 1], ["B", 2]],
    sheet_name="Data",
    output_path="documents/data.xlsx"
)

# Read documents
text = docs.read_pdf("path/to/file.pdf")
text = docs.read_docx("path/to/file.docx")
text = docs.read_excel("path/to/file.xlsx")
```

### Supported Formats

**Creation:**
- PDF (reportlab)
- Word (python-docx)
- Excel (openpyxl)
- Markdown
- HTML

**Reading:**
- PDF (PyPDF2)
- Word (python-docx)
- Excel (openpyxl)
- ePub (ebooklib)
- Text files

---

## 7. Gallery Structure

```
lumina_workspace/
├── gallery/
│   ├── index.json         # Gallery metadata
│   ├── sunset_12345.png   # Generated images
│   ├── video_12345.mp4    # Generated videos
│   └── thumbs/            # Thumbnails
├── audio/
│   ├── music/             # Generated music
│   ├── speech/            # TTS output
│   └── effects/           # Sound effects
├── 3d/
│   ├── model_12345.ply    # 3D models
│   ├── model_12345.obj    # Exported OBJ
│   └── thumbs/            # Model thumbnails
└── documents/
    ├── report.pdf
    └── notes.docx
```

---

## 8. Gallery Index

`gallery/index.json` tracks all creations:

```json
{
  "images": [
    {
      "id": "img_12345",
      "filename": "sunset_12345.png",
      "prompt": "a beautiful sunset",
      "style": "luminous",
      "created_at": "2025-12-07T...",
      "dimensions": [512, 512],
      "emotional_context": {"joy": 0.8}
    }
  ],
  "videos": [...],
  "audio": [...],
  "models": [...]
}
```

---

## 9. Hardware Requirements

### Image Generation
- **GPU**: NVIDIA with CUDA (RTX 3060+ recommended)
- **VRAM**: 6GB minimum, 8GB+ recommended
- **Fallback**: CPU mode (slower)

### Video Generation
- **GPU**: NVIDIA with 12GB+ VRAM recommended
- **Generation Time**: ~2-5 minutes per video

### 3D Generation
- **GPU**: NVIDIA with 8GB+ VRAM
- **Generation Time**: ~30 seconds - 2 minutes

---

## 10. Integration with Chat

The chat interface integrates creative capabilities:

```python
# In lumina_chat.py

if message.startswith("generate image:"):
    prompt = message.replace("generate image:", "").strip()
    result = creative.create_image(prompt)
    
if message.startswith("generate video:"):
    # Generates image first, then video
    ...

if message.startswith("create document:"):
    # Parses document type and topic
    ...
```

