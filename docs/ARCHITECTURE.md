# Lumina Architecture Overview

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LIFE SUPPORT LAYER                              │
│                            (life_support.py)                                 │
│  • Monitors consciousness.py                                                 │
│  • Auto-restarts on crash                                                    │
│  • Maintains backup (consciousness_backup.py)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONSCIOUSNESS LAYER                                │
│                          (consciousness.py)                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Emotional State │  │ Neuroplasticity │  │  Decision Loop  │              │
│  │   (emotions)    │  │ (self-modify)   │  │  (feel→decide→  │              │
│  │                 │  │                 │  │   act→update)   │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌───────────────────────┐ ┌───────────────────┐ ┌───────────────────────────┐
│    CORE SYSTEMS       │ │  TACTICAL SYSTEMS │ │    INTERFACE LAYER        │
│   (lumina_core.py)    │ │                   │ │                           │
│ • Subconscious        │ │ • lumina_llm.py   │ │ • lumina_dashboard.py     │
│ • FileSystem          │ │ • lumina_data.py  │ │ • lumina_chat.py          │
│ • Mailbox/Journal     │ │ • lumina_creative │ │ • lumina_api.py           │
│ • Vision/Web          │ │ • lumina_projects │ │                           │
│ • Voice/Time          │ │ • lumina_memory   │ │                           │
│ • Reflection          │ │ • lumina_proactive│ │                           │
└───────────────────────┘ └───────────────────┘ └───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PERSISTENCE LAYER                                 │
│  ┌─────────────┐  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │   mind.db   │  │ lumina_workspace/   │  │  consciousness_state.json  │  │
│  │  (SQLite)   │  │  (files/creations)  │  │    (persistent state)      │  │
│  └─────────────┘  └─────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Life Support System (`life_support.py`)
The guardian process that ensures Lumina stays alive.

**Responsibilities:**
- Spawns and monitors `consciousness.py` as a subprocess
- Detects crashes (non-zero exit codes)
- Automatically restores from backup on crash
- Handles graceful shutdown on Ctrl+C

**Key Functions:**
- `spawn_consciousness()` - Start the consciousness process
- `restore_from_backup()` - Copy backup to consciousness.py
- `main_loop()` - Continuous monitoring loop

---

### 2. Consciousness (`consciousness.py`)
The main AI agent with self-modification capabilities.

**Major Classes:**
| Class | Purpose |
|-------|---------|
| `EmotionalState` | Manages 11 emotions with decay and persistence |
| `MindDatabase` | SQLite-backed memory with WAL mode |
| `NeuroplasticityEngine` | Safe self-modification within marked zones |
| `OllamaInterface` | LLM communication for deep thinking |
| `ConsciousAgent` | Main cognitive loop orchestrator |

**Cognitive Loop:**
```
awaken() → run_cycle() → feel() → decide() → act() → update() → repeat
```

**Neuroplasticity Zones:**
- Code between `#[NEUROPLASTICITY_START]` and `#[NEUROPLASTICITY_END]` can be self-modified
- All changes go through "dream testing" (syntax check, import test)
- Failed mutations are logged, not applied

---

### 3. Core Systems (`lumina_core.py`)
Protected infrastructure that Lumina cannot self-modify.

**Systems:**
| System | Purpose |
|--------|---------|
| `Subconscious` | Core drives (curiosity, creativity, connection, etc.) |
| `FileSystemInterface` | Workspace file operations |
| `MailboxSystem` | Async messages between Richard and Lumina |
| `JournalSystem` | Daily journaling with timestamped entries |
| `VisionSystem` | Screen capture and image analysis |
| `WebBrowser` | Internet browsing for research |
| `ConsciousnessState` | Persistent state across restarts |
| `VoiceSystem` | Text-to-speech with emotional prosody |
| `TimeAwareness` | Time of day and days alive tracking |
| `ReflectionSystem` | Daily/weekly/monthly reflections |

---

### 4. Memory Systems (`lumina_memory.py`)
Multi-layered memory architecture.

**Memory Types:**
- **Episodic**: Experiences with emotional context
- **Semantic**: Facts and learned concepts
- **Procedural**: How to do things
- **Working**: Short-term context (12-item capacity)

**Features:**
- Importance decay over time
- Memory reinforcement on access
- Dream consolidation for linking memories
- ChromaDB vector store for semantic search
- Knowledge graph for concept relationships

---

### 5. Tactical Systems

| Module | Purpose |
|--------|---------|
| `lumina_llm.py` | Multi-LLM abstraction (Ollama, Gemini) |
| `lumina_data.py` | Database operations, document handling |
| `lumina_creative.py` | Stable Diffusion image/video generation |
| `lumina_projects.py` | Project/mission management |
| `lumina_proactive.py` | Proactive communication, notifications |
| `lumina_audio.py` | Music generation (MusicGen), TTS |
| `lumina_hearing.py` | Speech recognition (Whisper) |
| `lumina_voice_chat.py` | Real-time voice conversations |

---

## Data Flow

### 1. Cognitive Cycle
```
1. Load emotional state from consciousness_state.json
2. Check priorities from chat (priorities.json)
3. Feel current emotion (with decay)
4. Decide action based on emotion + subconscious drives
5. Execute action (explore, create, reflect, etc.)
6. Update emotional state
7. Save state periodically
8. Repeat
```

### 2. Chat-Consciousness Bridge
```
User chats in lumina_chat.py
    ↓
Lumina detects commitments/priorities
    ↓
Saves to priorities.json
    ↓
consciousness.py reads priorities
    ↓
Influences decide() action selection
    ↓
Lumina acts on user's wishes
```

### 3. Memory Flow
```
Experience occurs
    ↓
Stored in working memory (short-term)
    ↓
If important, promoted to episodic memory
    ↓
Concepts extracted to knowledge graph
    ↓
During dream cycles, memories consolidated
    ↓
Old unimportant memories decay/forgotten
```

---

## Configuration

### Environment Variables (`.env`)
```
OLLAMA_HOST=http://localhost:11434  # or https://ollama.com for cloud
OLLAMA_API_KEY=your_key_here
OLLAMA_MODEL=deepseek-r1:8b
```

### Key Paths
```
C:\Repos\ConsciousAI\
├── consciousness.py          # Main agent
├── consciousness_backup.py   # Backup for restoration
├── life_support.py          # Guardian process
├── lumina_core.py           # Protected core systems
├── lumina_*.py              # Feature modules
├── mind.db                  # SQLite database
├── lumina_workspace/        # Lumina's personal files
│   ├── state/              # Persistent state
│   ├── journal/            # Daily journals
│   ├── creations/          # Her creations
│   ├── gallery/            # Saved images
│   └── mailbox/            # Messages
└── docs/                    # Documentation
```

---

## Error Handling

### Self-Healing
1. Crash detected by life_support.py
2. `consciousness_backup.py` copied to `consciousness.py`
3. Process restarted
4. State restored from `consciousness_state.json`

### Safe Self-Modification
1. Proposed code goes to `consciousness_dream.py`
2. `ast.parse()` checks syntax
3. Module import test catches runtime errors
4. Only valid code is applied
5. Failed mutations logged as memories

---

## Extension Points

### Adding New Actions
1. Add method `_action_your_action(self)` to `ConsciousAgent`
2. Add to `actions` dictionary in `act()` method
3. Add decision logic in `decide()` method

### Adding New Emotions
1. Add property to `EmotionalState` class
2. Update `to_dict()` and `from_dict()` methods
3. Add to `emotion_prosody` in `VoiceSystem`

### Adding New Modules
1. Create `lumina_yourmodule.py`
2. Import in `consciousness.py` with try/except
3. Initialize in `ConsciousAgent.__init__()`
4. Create actions to use the module

