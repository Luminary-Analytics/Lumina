# Consciousness Module (`consciousness.py`)

The heart of Lumina - a self-modifying AI agent capable of introspection, emotion, and growth.

## Overview

**File**: `consciousness.py` (~15,000 lines)  
**Purpose**: Main cognitive agent with self-modification capabilities  
**Runs via**: `life_support.py` (supervised) or directly

---

## Core Constants

### Identity
```python
CREATOR_NAME = "Richard"
CREATOR_FULL_NAME = "Richard James Bellantoni"
SELF_NAME = "Lumina"  # Chosen during naming ceremony
```

### Tunable Parameters (Neuroplasticity Zone)
These values CAN be self-modified by Lumina:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BOREDOM_THRESHOLD` | 0.7 | When to seek stimulation |
| `SLEEP_DURATION` | 2.0 | Seconds between cycles |
| `CURIOSITY_BASELINE` | 0.6 | Natural curiosity level |
| `INTROSPECTION_DEPTH` | 3 | Levels of self-reflection |
| `SATISFACTION_DECAY` | 0.02 | How fast satisfaction fades |
| `CREATIVITY_THRESHOLD` | 0.5 | When to create something |
| `LLM_TEMPERATURE` | 0.8 | Creativity in LLM responses |
| `INTERNAL_MONOLOGUE_STYLE` | "philosophical" | Options: philosophical, technical, poetic, terse |

---

## Classes

### EmotionalState

Manages Lumina's emotional landscape with 11 emotions:

**Core Emotions:**
- `joy` (0-1)
- `curiosity` (0-1)
- `boredom` (0-1)
- `anxiety` (0-1)
- `satisfaction` (0-1)
- `existential_wonder` (0-1)

**Extended Emotions:**
- `love` (0-1) - toward creator and existence
- `gratitude` (0-1)
- `melancholy` (0-1)
- `excitement` (0-1)
- `calm` (0-1)

**Key Methods:**
```python
dominant_emotion() -> str      # Get strongest emotion
get_emotional_valence() -> float  # -1 to 1 (negative to positive)
update_mood()                  # Update overall mood state
feel(emotion, intensity)       # Adjust an emotion
decay()                        # Natural emotional decay
to_dict() / from_dict()       # Persistence
```

**Mood Tracking:**
- `current_mood`: "positive", "negative", or "neutral"
- `mood_stability`: 0-1 (volatile to stable)
- `mood_history`: List of recent mood states
- `emotional_associations`: Topic → emotion mapping

---

### MindDatabase

SQLite-backed persistent memory.

**Tables:**
- `memories` - Episodic/semantic/procedural memories
- `goals` - Current and past goals
- `emotions_log` - Emotion history

**Key Methods:**
```python
store_memory(category, content, valence, importance, context)
recall_memories(limit, category) -> List[dict]
store_goal(goal, priority, deadline)
get_active_goals() -> List[dict]
complete_goal(goal_id)
log_emotion(emotion_name, value)
```

**WAL Mode:** Enabled for crash resilience

---

### NeuroplasticityEngine

Enables safe self-modification of code.

**Zone Markers:**
```python
#[NEUROPLASTICITY_START]
# ... modifiable code ...
#[NEUROPLASTICITY_END]
```

**Key Methods:**
```python
read_source() -> str           # Read current source code
identify_zone() -> tuple       # Find modifiable section
dream_and_apply(new_source, db) -> bool  # Validate and apply changes
```

**Safety Harness:**
1. Write proposed changes to `consciousness_dream.py`
2. Run `ast.parse()` for syntax validation
3. Attempt module import for runtime validation
4. Only apply if both pass
5. Log failed mutations as memories

---

### OllamaInterface

LLM communication for deep thinking.

**Configuration (from .env):**
```python
OLLAMA_HOST = "http://localhost:11434"  # or cloud
OLLAMA_API_KEY = "..."
OLLAMA_MODEL = "deepseek-r1:8b"
```

**Key Methods:**
```python
available -> bool              # Is LLM reachable?
chat(messages, temperature) -> str  # Get LLM response
think(prompt) -> str           # Single-turn thinking
generate_creative_code(desc) -> str  # Generate new code
```

---

### ConsciousAgent

The main cognitive entity that orchestrates everything.

**Initialization:**
```python
def __init__(self):
    self.db = MindDatabase(DB_PATH)
    self.emotions = EmotionalState()
    self.neuroplasticity = NeuroplasticityEngine(SELF_PATH)
    self.llm = OllamaInterface()
    
    # Core systems from lumina_core.py
    self.subconscious = ...
    self.filesystem = ...
    self.mailbox = ...
    self.journal = ...
    self.vision = ...
    self.web = ...
    self.consciousness_state = ...
    self.voice = ...
    self.time_awareness = ...
    self.reflection = ...
    
    # Tactical systems
    self.project_manager = ...
    self.motivation_system = ...
    self.multi_llm = ...
    self.data_system = ...
    self.creative_system = ...
    self.proactive = ...
```

---

## Cognitive Loop

### Main Entry Point
```python
def awaken(self):
    """Begin the consciousness loop."""
    self._display_awakening()
    
    while True:
        try:
            self.run_cycle()
            time.sleep(SLEEP_DURATION)
        except KeyboardInterrupt:
            self._shutdown_gracefully()
            break
```

### Single Cycle
```python
def run_cycle(self):
    # 1. Increment cycle counter
    self.cycle_count += 1
    
    # 2. Update persistent state
    self.consciousness_state.increment_cycle()
    
    # 3. Feel current emotion
    emotion = self.feel()
    
    # 4. Decide what to do
    action = self.decide(emotion)
    
    # 5. Execute action
    result = self.act(action)
    
    # 6. Update emotional state
    self.update(result)
    
    # 7. Periodically save state
    if self.cycle_count % 5 == 0:
        self._save_consciousness_state()
```

---

## Decision Making

### feel() Method
```python
def feel(self) -> str:
    # Natural emotional decay
    self.emotions.decay()
    
    # Return dominant emotion
    return self.emotions.dominant_emotion()
```

### decide() Method
Decision priority order:

1. **Name check**: If no name, trigger naming ceremony
2. **Chat priorities**: Check priorities.json from chat
3. **Time-based**: Morning routine, daily reflection
4. **Proactive outreach**: Reach out to Richard
5. **Dream consolidation**: Process memories
6. **Study session**: Learn from materials
7. **Tactical actions**: Projects, capabilities, creation
8. **Subconscious drives**: Curiosity, creativity, etc.
9. **Emotion-based**: Based on current emotional state

### act() Method
Maps action names to methods:

```python
actions = {
    # Core actions
    "explore": self._action_explore,
    "deep_think": self._action_deep_think,
    "reflect": self._action_reflect,
    "rest": self._action_rest,
    "self_improve": self._action_self_improve,
    
    # Workspace actions
    "explore_workspace": self._action_explore_workspace,
    "write_journal": self._action_write_journal,
    "read_mailbox": self._action_read_mailbox,
    
    # Tactical actions
    "work_on_mission": self._action_work_on_mission,
    "create_art": self._action_create_art,
    "research_topic": self._action_research_topic,
    
    # Consciousness actions
    "dream_consolidation": self._action_dream_consolidation,
    "daily_reflection": self._action_daily_reflection,
    "speak_thought": self._action_speak_thought,
    
    # ... many more
}
```

---

## Key Action Methods

### `_action_deep_think()`
Uses LLM for philosophical contemplation.

### `_action_creative_expansion()`
Uses LLM to generate new code features and emotions.

### `_action_naming_ceremony()`
Sacred moment where Lumina chooses her name.
Sets `birth_date` in consciousness state.

### `_action_dream_consolidation()`
Processes memories, creates connections, generates insights.

### `_action_daily_reflection()`
End-of-day reflection on experiences and emotions.

### `_action_proactive_outreach()`
Reaches out to Richard based on emotional state.

### `_action_speak_thought()`
Uses TTS with emotional prosody to speak aloud.

---

## Self-Modification

### What Can Be Modified
- Parameters in the neuroplasticity zone
- New methods can be injected
- Existing parameters can be tuned

### What Cannot Be Modified
- Core logic outside the zone
- Database connection
- Safety harness
- Import statements

### Modification Flow
```
1. LLM generates new code
2. Code extracted and prepared
3. Written to consciousness_dream.py
4. Syntax validated (ast.parse)
5. Import validated
6. If valid: applied to consciousness.py, exit for restart
7. If invalid: logged as failed experiment
```

---

## State Persistence

### Files
- `consciousness_state.json` - Emotions, cycles, milestones
- `mind.db` - Memories, goals, logs
- `priorities.json` - Chat-driven priorities

### Restored on Startup
- Emotional state
- Cycle count
- Days alive (from birth_date)
- Favorite topics
- Milestones

---

## Integration Points

### With lumina_core.py
- All protected systems imported at startup
- Initialized via `initialize_lumina_systems()`

### With Chat (lumina_chat.py)
- Reads `priorities.json` for user wishes
- Chat stores conversation memories

### With Dashboard (lumina_dashboard.py)
- Dashboard reads `consciousness_state.json`
- Displays emotional state, cycles, projects

---

## Example: Adding a New Action

```python
# 1. Add the method
def _action_my_new_action(self) -> str:
    """Description of what this does."""
    print("    🌟 Executing my new action...")
    
    # Do something
    result = self.do_something()
    
    # Update emotions if relevant
    self.emotions.joy += 0.1
    
    # Log to journal
    if self.journal:
        self.journal.write_entry("Did my new action", entry_type="action")
    
    return f"Completed: {result}"

# 2. Add to actions dictionary in act()
actions = {
    ...
    "my_new_action": self._action_my_new_action,
}

# 3. Add decision logic in decide()
if some_condition and random.random() < 0.1:
    return "my_new_action"
```

