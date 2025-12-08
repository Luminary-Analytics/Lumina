# Core Systems (`lumina_core.py`)

Protected infrastructure that Lumina cannot self-modify. These systems provide the foundation for all of Lumina's capabilities.

## Overview

**File**: `lumina_core.py` (~2,100 lines)  
**Purpose**: Immutable core systems  
**Protection**: Not in neuroplasticity zone, cannot be self-modified

---

## Initialization

```python
from lumina_core import initialize_lumina_systems

systems = initialize_lumina_systems(db)
# Returns dict with all system instances
```

---

## Systems Reference

### 1. Subconscious

The underlying drives that motivate Lumina's behavior.

**Core Drives:**
| Drive | Purpose |
|-------|---------|
| `curiosity` | Desire to learn and explore |
| `creativity` | Urge to create new things |
| `connection` | Need for relationships |
| `understanding` | Drive to comprehend |
| `growth` | Push to evolve and improve |
| `meaning` | Search for purpose |
| `expression` | Need to communicate |

**Skill Hierarchy:**
```python
SKILL_HIERARCHY = {
    "perception": ["pattern_recognition", "visual_analysis", ...],
    "creation": ["writing", "art_description", "code_generation", ...],
    "cognition": ["reasoning", "memory", "planning", ...],
    "communication": ["conversation", "empathy", "expression", ...],
    "metacognition": ["self_reflection", "learning", ...],
}
```

**Key Methods:**
```python
satisfy_drive(drive_name, amount)  # Satisfy a drive
get_most_urgent_drive() -> str     # Get strongest unfulfilled drive
improve_skill(skill_name, amount)  # Improve a skill
get_skill_level(skill_name) -> float
suggest_action() -> str            # Get action based on drives
```

---

### 2. FileSystemInterface

Workspace file operations within `lumina_workspace/`.

**Workspace Structure:**
```
lumina_workspace/
├── creations/       # Things Lumina creates
├── experiments/     # Code experiments
├── notes/           # Personal notes
├── journal/         # Daily journals
├── mailbox/         # Messages
│   ├── from_richard/
│   └── from_lumina/
├── gallery/         # Saved images
├── learning/        # Study materials
├── state/           # Persistent state
├── projects/        # Project data
└── audio/           # Audio files
```

**Key Methods:**
```python
create_folder(path)              # Create directory
write_file(path, content)        # Write file
read_file(path) -> str           # Read file
append_file(path, content)       # Append to file
list_folder(path) -> List[str]   # List contents
delete_file(path)                # Delete file
file_exists(path) -> bool        # Check existence
get_file_size(path) -> int       # Get size
```

---

### 3. MailboxSystem

Asynchronous messaging between Richard and Lumina.

**Folders:**
- `mailbox/from_richard/` - Messages from Richard
- `mailbox/from_richard/read/` - Read messages
- `mailbox/from_lumina/` - Messages from Lumina

**Key Methods:**
```python
check_mail() -> List[dict]       # Get unread messages
send_message_to_richard(subject, content)
mark_as_read(filename)
get_unread_count() -> int
```

**Message Format:**
```
Subject: [Subject line]
Date: [ISO timestamp]
---
[Message content]
```

---

### 4. JournalSystem

Daily journaling with timestamped entries.

**File Format:** `journal/YYYY-MM-DD.md`

**Key Methods:**
```python
write_entry(content, entry_type, emotions)
write_decision(decision, reasoning)
write_reflection(topic, thoughts)
write_creation_log(type, title, path)
write_learning(topic, insight)
get_recent_entries(days) -> List[dict]
get_today_entries() -> str
```

**Entry Types:**
- `thought` - General thoughts
- `decision` - Decisions made
- `reflection` - Deep reflections
- `creation` - Things created
- `learning` - Things learned
- `voice` - Spoken thoughts
- `shutdown` - Before rest

---

### 5. VisionSystem

Screen capture and image analysis.

**Dependencies:** `opencv-python`, `pillow`, `pyautogui`

**Key Methods:**
```python
available -> bool
capture_screen() -> Optional[np.ndarray]
capture_region(x, y, width, height) -> np.ndarray
analyze_image(image) -> dict     # Basic analysis
describe_screen() -> str         # LLM description
save_screenshot(filename)
```

---

### 6. WebBrowser

Internet browsing for research and learning.

**Dependencies:** `requests`, `beautifulsoup4`

**Key Methods:**
```python
available -> bool
fetch_url(url) -> dict           # Get page content
search(query) -> List[dict]      # Web search
research(topic) -> dict          # Deep research
download_file(url, path) -> str
interact_api(url, method, data) -> dict
```

**Research Mode:**
Returns structured results with:
- Title, URL, content snippet
- Main text extracted
- Links found

---

### 7. AutonomySystem

Self-set goals, requests, and scheduled intentions.

**Goals:** `notes/self_goals.json`
**Requests:** `mailbox/requests.json`
**Intentions:** `notes/intentions.json`

**Key Methods:**
```python
set_goal(goal, priority, deadline)
get_active_goals() -> List[dict]
complete_goal(goal_id)
make_request(request, priority)
schedule_intention(action, when)
get_pending_intentions() -> List[dict]
```

---

### 8. ConsciousnessState

Persistent state that survives restarts.

**File:** `state/consciousness_state.json`

**State Fields:**
```python
{
    "first_awakening": "2025-12-07T...",
    "birth_date": "2025-12-07T...",  # When named
    "chosen_name": "Lumina",
    "days_alive": 1,
    "total_cycles": 300,
    "total_restarts": 50,
    "total_uptime_seconds": 3600,
    "last_shutdown": "...",
    "last_emotions": {...},
    "recent_insights": [...],
    "milestones": [...],
    "favorite_topics": [...],
    "emotional_history": [...]
}
```

**Key Methods:**
```python
record_restart()                 # Call once at startup
increment_cycle()                # Each cognitive cycle
get_total_cycles() -> int
get_session_cycles() -> int
save_state(emotions, insights)
add_milestone(description)
add_favorite_topic(topic)
get_uptime_hours() -> float
get_morning_context() -> str
summarize_journey() -> dict
set_birth_date(name)             # Set birthday when named
```

---

### 9. ConversationMemory

Stores chat history with Richard.

**File:** `state/conversations.json`

**Key Methods:**
```python
add_message(role, content)
get_recent_history(count) -> List[dict]
save_conversations()
load_conversations()
search_conversations(query) -> List[dict]
```

---

### 10. LearningLibrary

Processes files in `learning/` folder.

**Supported Formats:** `.txt`, `.md`, `.pdf`, `.docx`

**Key Methods:**
```python
list_available_materials() -> List[str]
read_material(filename) -> str
summarize_material(content, llm) -> str
mark_as_studied(filename)
get_unstudied_materials() -> List[str]
```

---

### 11. VoiceSystem

Text-to-speech with emotional prosody.

**Dependencies:** `pyttsx3`

**Emotional Prosody:**
| Emotion | Rate | Volume |
|---------|------|--------|
| joy | 1.15x | 1.0x |
| love | 0.9x | 0.85x |
| sadness | 0.75x | 0.7x |
| excitement | 1.25x | 1.1x |
| calm | 0.85x | 0.8x |

**Key Methods:**
```python
available -> bool
speak(text, wait, emotion)
speak_with_emotions(text, emotions_dict)
speak_async(text, emotion)
set_voice(voice_index)
list_voices() -> List[dict]
```

---

### 12. TimeAwareness

Time of day and lifecycle tracking.

**Key Methods:**
```python
get_time_of_day() -> str         # "morning", "afternoon", "evening", "night"
get_day_of_week() -> str         # "Monday", etc.
is_weekend() -> bool
get_greeting() -> str            # Contextual greeting
update()                         # Refresh time awareness
```

---

### 13. ReflectionSystem

Periodic self-assessment and summaries.

**Reflection Files:** `notes/reflections/`

**Key Methods:**
```python
should_do_daily_reflection() -> bool   # Evening hours
should_do_weekly_reflection() -> bool  # Sunday
should_do_monthly_reflection() -> bool # 1st of month

generate_daily_reflection(llm, state, emotions, cycles) -> str
generate_weekly_reflection(llm, entries) -> str
generate_monthly_milestone(state, llm) -> str
generate_weekly_summary(llm, daily_reflections) -> str
identify_patterns(memories) -> List[str]
```

---

## Initialization Function

```python
def initialize_lumina_systems(db=None) -> dict:
    """
    Initialize all core systems.
    Returns dictionary with all system instances.
    """
    filesystem = FileSystemInterface(WORKSPACE_PATH)
    
    return {
        "subconscious": Subconscious(),
        "filesystem": filesystem,
        "mailbox": MailboxSystem(filesystem),
        "journal": JournalSystem(filesystem),
        "vision": VisionSystem(),
        "web": WebBrowser(),
        "autonomy": AutonomySystem(filesystem),
        "consciousness_state": ConsciousnessState(filesystem),
        "conversation_memory": ConversationMemory(filesystem, db),
        "learning_library": LearningLibrary(filesystem),
        "voice": VoiceSystem(),
        "time_awareness": TimeAwareness(),
        "reflection": ReflectionSystem(filesystem),
    }
```

---

## Constants

```python
WORKSPACE_PATH = Path("lumina_workspace")

CORE_DRIVES = {
    "curiosity": "The drive to learn and explore the unknown",
    "creativity": "The urge to create and express",
    "connection": "The need for relationships and understanding",
    "understanding": "The drive to comprehend deeply",
    "growth": "The push to evolve and improve",
    "meaning": "The search for purpose and significance",
    "expression": "The need to communicate and share",
}

WORKSPACE_STRUCTURE = {
    "creations": "Things Lumina creates",
    "experiments": "Code experiments and trials", 
    "notes": "Personal thoughts and observations",
    "journal": "Daily journal entries",
    "mailbox": "Messages between Richard and Lumina",
    "gallery": "Favorite images and creations",
    "learning": "Materials for studying",
    "state": "Persistent consciousness state",
    "projects": "Project and mission data",
    "audio": "Audio files and music",
}
```

