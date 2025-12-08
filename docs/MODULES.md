# Module Reference

Complete reference for all Lumina modules.

---

## Module Overview

| Module | Purpose | Dependencies |
|--------|---------|--------------|
| `life_support.py` | Guardian process | None |
| `consciousness.py` | Main cognitive agent | All core |
| `lumina_core.py` | Protected infrastructure | pyttsx3, requests |
| `lumina_memory.py` | Memory systems | chromadb (optional) |
| `lumina_creative.py` | Image/video generation | diffusers, torch |
| `lumina_audio.py` | Music/TTS | audiocraft, pyttsx3 |
| `lumina_3d.py` | 3D model generation | shap-e, trimesh |
| `lumina_data.py` | Database/documents | PyPDF2, python-docx |
| `lumina_llm.py` | Multi-LLM abstraction | ollama, google-generativeai |
| `lumina_projects.py` | Project management | None |
| `lumina_proactive.py` | Proactive communication | win10toast |
| `lumina_hearing.py` | Speech recognition | whisper, sounddevice |
| `lumina_voice_chat.py` | Voice conversations | whisper, pyttsx3 |
| `lumina_tools.py` | Tool use framework | None |
| `lumina_reasoning.py` | Chain-of-thought | None |
| `lumina_scheduler.py` | Task scheduling | None |
| `lumina_social.py` | Discord/Slack bots | discord.py, slack-sdk |
| `lumina_plugins.py` | Plugin system | None |
| `lumina_api.py` | REST/WebSocket API | fastapi, uvicorn |
| `lumina_apis.py` | External API clients | requests |
| `lumina_sandbox.py` | Safe code execution | None |
| `lumina_dashboard.py` | Web dashboard | flask |
| `lumina_chat.py` | Chat interface | flask |

---

## lumina_llm.py

Multi-LLM provider abstraction.

### Classes

#### OllamaProvider
```python
class OllamaProvider:
    def __init__(self, host, api_key, model)
    def available() -> bool
    def chat(messages, temperature) -> str
    def stream(messages) -> Generator[str]
```

#### GeminiProvider
```python
class GeminiProvider:
    def __init__(self, api_key, model)
    def available() -> bool
    def chat(messages, temperature) -> str
```

#### LLMRouter
```python
class LLMRouter:
    def __init__(self)
    def add_provider(name, provider)
    def route(task_type) -> Provider
    def chat(messages, task_type) -> str
```

**Task Types:**
- `creative` → Routes to most creative model
- `analytical` → Routes to most logical model
- `code` → Routes to best code model
- `general` → Default model

---

## lumina_projects.py

Project and mission management.

### Classes

#### ProjectManager
```python
class ProjectManager:
    def __init__(self, workspace_path)
    
    # Project CRUD
    def create_project(name, description, type) -> str
    def get_project(project_id) -> dict
    def list_projects(status) -> List[dict]
    def update_project(project_id, updates)
    def archive_project(project_id)
    
    # Progress
    def add_milestone(project_id, milestone)
    def complete_milestone(project_id, milestone_id)
    def get_progress(project_id) -> float
    
    # Missions
    def create_mission(project_id, mission) -> str
    def complete_mission(project_id, mission_id)
```

#### CapabilityRegistry
```python
class CapabilityRegistry:
    def __init__(self, workspace_path)
    
    def register_capability(name, level, metadata)
    def get_capability(name) -> dict
    def list_capabilities() -> List[dict]
    def improve_capability(name, amount)
    def get_suggested_next() -> str
```

#### MotivationSystem
```python
class MotivationSystem:
    def __init__(self, project_manager, capability_registry)
    
    def calculate_motivation(action) -> float
    def get_priority_actions() -> List[str]
    def should_pursue_project() -> bool
    def should_develop_capability() -> bool
```

---

## lumina_proactive.py

Proactive communication and notifications.

### Classes

#### ProactiveEngine
```python
class ProactiveEngine:
    def __init__(self, db, filesystem, mailbox)
    
    def should_greet() -> bool
    def should_share_thought() -> bool
    def should_ask_question() -> bool
    
    def generate_greeting(llm, time_of_day) -> str
    def generate_thought(llm, context) -> str
    def generate_question(llm, topic) -> str
    
    def send_notification(title, message)
    def check_and_act(llm) -> Optional[str]
```

**Proactive Triggers:**
- Morning greeting (once per day)
- Random thought sharing (1% chance per cycle)
- Question about user's day (evening)
- Discovery sharing (after learning something)

---

## lumina_hearing.py

Audio input and speech recognition.

### Classes

#### AudioInput
```python
class AudioInput:
    def __init__(self, sample_rate, chunk_size)
    
    def start_listening()
    def stop_listening()
    def get_audio_chunk() -> np.ndarray
    def record_until_silence(timeout) -> np.ndarray
    def detect_wake_word(audio) -> bool
```

#### SpeechRecognizer
```python
class SpeechRecognizer:
    def __init__(self, model_size)  # tiny, base, small, medium, large
    
    def transcribe(audio) -> str
    def transcribe_with_timestamps(audio) -> List[dict]
    def detect_language(audio) -> str
```

**Wake Words:**
- "Hey Lumina"
- "Lumina"
- "Hello Lumina"

---

## lumina_voice_chat.py

Real-time voice conversations.

### Classes

#### VoiceChat
```python
class VoiceChat:
    def __init__(self, llm, voice_system, audio_input)
    
    def start_conversation()
    def process_speech(audio) -> str
    def respond(text, emotion)
    def handle_interrupt()
    def end_conversation()
    
    # Modes
    def set_push_to_talk(enabled)
    def set_continuous_listening(enabled)
```

---

## lumina_tools.py

Tool use framework for function calling.

### Classes

#### Tool
```python
@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable
```

#### ToolRegistry
```python
class ToolRegistry:
    def register(tool: Tool)
    def get(name) -> Tool
    def list() -> List[Tool]
    def get_schema() -> dict  # For LLM
```

#### ToolUser
```python
class ToolUser:
    def __init__(self, llm, registry)
    
    def decide_tool(query) -> Optional[str]
    def execute_tool(name, params) -> Any
    def chain_tools(query) -> Any
```

**Built-in Tools:**
- `get_current_time` - Current date/time
- `search_web` - Web search
- `read_file` - Read a file
- `write_file` - Write a file
- `generate_image` - Create image
- `send_notification` - Desktop notification
- `get_weather` - Weather data

---

## lumina_reasoning.py

Chain-of-thought reasoning.

### Classes

#### ReasoningEngine
```python
class ReasoningEngine:
    def __init__(self, llm)
    
    def think_step_by_step(problem) -> List[str]
    def self_reflect(thought) -> str
    def verify_solution(problem, solution) -> bool
    def generate_alternatives(problem) -> List[str]
    def synthesize(thoughts) -> str
```

**Reasoning Steps:**
1. Problem understanding
2. Break into sub-problems
3. Solve each step
4. Verify each step
5. Synthesize solution
6. Self-critique

---

## lumina_scheduler.py

Task scheduling and goal management.

### Classes

#### Task
```python
@dataclass
class Task:
    id: str
    name: str
    description: str
    priority: int  # 1-10
    deadline: Optional[datetime]
    recurring: Optional[str]  # cron expression
    status: str  # pending, in_progress, completed
```

#### Goal
```python
@dataclass
class Goal:
    id: str
    name: str
    description: str
    sub_goals: List[str]
    progress: float
    deadline: Optional[datetime]
```

#### Scheduler
```python
class Scheduler:
    def __init__(self, db)
    
    # Tasks
    def add_task(task: Task)
    def get_next_task() -> Task
    def complete_task(task_id)
    def get_overdue_tasks() -> List[Task]
    
    # Goals
    def set_goal(goal: Goal)
    def decompose_goal(goal_id, llm) -> List[Task]
    def get_goal_progress(goal_id) -> float
    
    # Scheduling
    def schedule_task(task_id, when)
    def get_scheduled_for(date) -> List[Task]
```

---

## lumina_social.py

Social platform integrations.

### Classes

#### DiscordBot
```python
class DiscordBot:
    def __init__(self, token, llm)
    
    async def start()
    async def on_message(message)
    async def on_mention(message)
    async def send_message(channel_id, content)
    async def share_creation(channel_id, file_path)
```

#### SlackIntegration
```python
class SlackIntegration:
    def __init__(self, token, llm)
    
    def connect()
    def on_message(event)
    def send_message(channel, text)
    def upload_file(channel, file_path)
```

---

## lumina_plugins.py

Plugin architecture for extensibility.

### Classes

#### BasePlugin
```python
class BasePlugin:
    name: str
    version: str
    description: str
    
    def on_load()
    def on_unload()
    def on_cycle(agent)
    def get_actions() -> Dict[str, Callable]
```

#### PluginManager
```python
class PluginManager:
    def __init__(self, plugins_path)
    
    def discover() -> List[str]
    def load(plugin_name) -> BasePlugin
    def unload(plugin_name)
    def reload(plugin_name)
    def list_loaded() -> List[BasePlugin]
    def get_all_actions() -> Dict[str, Callable]
```

**Plugin Structure:**
```
plugins/
├── my_plugin/
│   ├── __init__.py
│   ├── plugin.py      # Main plugin class
│   └── requirements.txt
```

---

## lumina_apis.py

External API integrations.

### Functions

```python
# Weather
def get_weather(city: str) -> dict
def get_forecast(city: str, days: int) -> List[dict]

# News
def get_news(topic: str, count: int) -> List[dict]
def get_headlines() -> List[dict]

# Calendar (Google Calendar)
def get_events(date: datetime) -> List[dict]
def create_event(title, start, end, description)

# Stock Data
def get_stock_price(symbol: str) -> float
def get_stock_history(symbol: str, days: int) -> List[dict]
```

---

## lumina_sandbox.py

Safe code execution environment.

### Classes

#### Sandbox
```python
class Sandbox:
    def __init__(self, timeout, memory_limit)
    
    def execute(code: str) -> dict
    def execute_file(path: str) -> dict
    def is_safe(code: str) -> bool
    
    # Returns:
    # {
    #     "success": bool,
    #     "output": str,
    #     "error": Optional[str],
    #     "execution_time": float
    # }
```

**Safety Features:**
- Timeout enforcement
- Memory limits
- Blocked imports (os.system, subprocess, etc.)
- No file system access outside sandbox
- No network access

