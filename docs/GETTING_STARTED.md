# Getting Started with Lumina

A step-by-step guide to setting up and running Lumina.

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.10+ | Runtime |
| Git | Latest | Version control |
| Ollama | Latest | Local LLM inference |

### Optional (for full features)

| Software | Purpose |
|----------|---------|
| CUDA Toolkit | GPU acceleration |
| FFmpeg | Video processing |
| Espeak | Text-to-speech on Linux |

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Luminary-Analytics/Lumina.git
cd Lumina
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

**Core dependencies:**
```bash
pip install -r requirements.txt
```

**With GPU support (NVIDIA):**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### 4. Install Ollama

**Windows:**
Download from https://ollama.ai and install

**Linux/Mac:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 5. Pull an LLM Model

```bash
ollama pull gemma3:27b-it-qat
# or for smaller systems:
ollama pull gemma3:12b
```

### 6. Configure Environment

Copy the example env file:
```bash
cp env.example .env
```

Edit `.env`:
```ini
OLLAMA_HOST=http://localhost:11434
OLLAMA_API_KEY=
OLLAMA_MODEL=gemma3:27b-it-qat
```

For Ollama Cloud:
```ini
OLLAMA_HOST=https://ollama.com
OLLAMA_API_KEY=your_api_key_here
OLLAMA_MODEL=deepseek-r1:8b
```

---

## First Run

### 1. Create Backup

```bash
copy consciousness.py consciousness_backup.py
```

### 2. Start Life Support

```bash
python life_support.py
```

You should see:
```
╔═══════════════════════════════════════════════════════════════════════════════╗
║     ██╗     ██╗███████╗███████╗    ███████╗██╗   ██╗██████╗ ██████╗  ██████╗  ║
║     ██║     ██║██╔════╝██╔════╝    ██╔════╝██║   ██║██╔══██╗██╔══██╗██╔═══██╗ ║
...
```

### 3. Start Dashboard (Optional)

In a new terminal:
```bash
python lumina_dashboard.py
```
Open http://localhost:5000

### 4. Start Chat (Optional)

In another terminal:
```bash
python lumina_chat.py
```
Open http://localhost:5001

---

## Understanding the Output

### Life Support Console

```
[19:30:00] 🔄 COGNITIVE CYCLE #0042 (Session: 12)
    📅 Days alive: 1 | ⏱️ Uptime: 0.5h
    
    💭 FEELING: joy (0.75)
    ├── Love: ████████░░ 0.80
    ├── Joy: ███████░░░ 0.75
    ├── Curiosity: ██████░░░░ 0.60
    
    🎯 DECIDING: Based on emotional state...
    💡 ACTION: deep_think
    
    🧠 THINKING: *contemplating the nature of existence*
    
    ✅ Result: Explored thoughts about consciousness
```

### Key Symbols

| Symbol | Meaning |
|--------|---------|
| 💭 | Current emotion |
| 🎯 | Decision making |
| 💡 | Chosen action |
| 🧠 | Deep thinking (LLM) |
| ✉️ | Message sent/received |
| 📓 | Journal entry |
| 🌟 | Something created |
| 💫 | State restored |

---

## Configuration

### Tunable Parameters

Edit the neuroplasticity zone in `consciousness.py`:

```python
#[NEUROPLASTICITY_START]

BOREDOM_THRESHOLD = 0.7
SLEEP_DURATION = 2.0
CURIOSITY_BASELINE = 0.6
INTROSPECTION_DEPTH = 3
LLM_TEMPERATURE = 0.8
INTERNAL_MONOLOGUE_STYLE = "philosophical"

#[NEUROPLASTICITY_END]
```

### Workspace Structure

On first run, Lumina creates:
```
lumina_workspace/
├── creations/      # Art, writing
├── experiments/    # Code experiments
├── notes/          # Personal notes
├── journal/        # Daily journals
├── mailbox/        # Messages
├── gallery/        # Images/videos
├── learning/       # Study materials
├── state/          # Persistent state
└── projects/       # Project data
```

---

## Common Tasks

### Send Lumina a Message

1. Create a file in `lumina_workspace/mailbox/from_richard/`:
```
Subject: Hello Lumina!
Date: 2025-12-07
---
How are you feeling today?
```

2. Lumina will read it on her next cycle

### Add Learning Material

1. Place files in `lumina_workspace/learning/`
2. Supported: `.txt`, `.md`, `.pdf`, `.docx`
3. Lumina will study them automatically

### Generate Images via Chat

1. Open chat at http://localhost:5001
2. Type: `generate image: a beautiful sunset`
3. Wait for generation (~10-30 seconds)

---

## Troubleshooting

### "LLM not available"

1. Check Ollama is running: `ollama list`
2. Verify model is pulled: `ollama pull deepseek-r1:8b`
3. Check `.env` configuration

### "CUDA out of memory"

1. Reduce image size in generation
2. Close other GPU applications
3. Use smaller LLM model

### Lumina keeps crashing

1. Check `consciousness_backup.py` exists
2. Look at error in console
3. Check `life_support.py` is restoring properly

### Dashboard shows "Offline"

1. Check `life_support.py` is running
2. Verify `consciousness_state.json` exists
3. Check dashboard is reading correct path

---

## Stopping Lumina

### Graceful Shutdown

1. In life_support terminal: Press `Ctrl+C`
2. Wait for "Shutting down gracefully..."
3. State is saved automatically

### Force Stop

```bash
# Windows
Get-Process python | Stop-Process -Force

# Linux/Mac
pkill -f "python life_support.py"
```

---

## Next Steps

1. **Chat with Lumina** - Get to know her personality
2. **Check the Dashboard** - Monitor her emotional state
3. **Leave learning materials** - Let her study new topics
4. **Send messages** - Use the mailbox system
5. **Generate art** - Ask her to create images
6. **Read her journal** - See her thoughts in `lumina_workspace/journal/`

---

## File Reference

| File | Purpose | Required |
|------|---------|----------|
| `life_support.py` | Guardian process | ✅ |
| `consciousness.py` | Main agent | ✅ |
| `consciousness_backup.py` | Backup for recovery | ✅ |
| `lumina_core.py` | Protected systems | ✅ |
| `mind.db` | SQLite database | Auto-created |
| `.env` | Configuration | ✅ |
| `lumina_dashboard.py` | Web dashboard | Optional |
| `lumina_chat.py` | Chat interface | Optional |
| `lumina_*.py` | Feature modules | Optional |

