#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA LLM SYSTEM                                      ║
║                                                                               ║
║  Multi-LLM provider abstraction for Lumina's cognitive processes.            ║
║  Supports Ollama (local + cloud) and Gemini.                                  ║
║                                                                               ║
║  Features:                                                                     ║
║  - Multiple model support with task-based routing                             ║
║  - Multi-model dialogue and synthesis                                         ║
║  - Model debates for complex reasoning                                        ║
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
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

# Load environment
def load_dotenv():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# TASK TYPES - What kind of task is being performed
# ═══════════════════════════════════════════════════════════════════════════════

class TaskType(Enum):
    GENERAL = "general"           # General conversation
    REASONING = "reasoning"       # Deep thinking, logic
    CREATIVE = "creative"         # Creative writing, ideas
    CODE = "code"                # Code generation/analysis
    VISION = "vision"            # Image understanding
    FAST = "fast"                # Quick, simple responses
    PHILOSOPHICAL = "philosophical"  # Deep existential thoughts


# ═══════════════════════════════════════════════════════════════════════════════
# LLM PROVIDER BASE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LLMResponse:
    """Response from an LLM."""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    time_taken: float = 0.0
    success: bool = True
    error: Optional[str] = None
    raw_response: Optional[Any] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_models(self) -> List[str]:
        pass
    
    @abstractmethod
    def chat(self, messages: List[Dict], model: str = None, **kwargs) -> LLMResponse:
        pass
    
    def generate(self, prompt: str, model: str = None, **kwargs) -> LLMResponse:
        """Simple prompt-response generation."""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, model, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class OllamaProvider(LLMProvider):
    """Ollama provider - local and cloud models."""
    
    def __init__(self):
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.api_key = os.environ.get("OLLAMA_API_KEY", "")
        self.default_model = os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b")
        self._client = None
        self._available = None
        
        # Model recommendations by task
        self.model_map = {
            TaskType.GENERAL: self.default_model,
            TaskType.REASONING: "deepseek-r1:8b",  # Best for reasoning
            TaskType.CREATIVE: "mistral:7b",       # Good for creative
            TaskType.CODE: "codellama:13b",        # Code specialist
            TaskType.VISION: "llava:13b",          # Vision model
            TaskType.FAST: "mistral:7b",           # Fast responses
            TaskType.PHILOSOPHICAL: self.default_model,
        }
    
    @property
    def name(self) -> str:
        return "ollama"
    
    def _get_client(self):
        if self._client is None:
            try:
                import ollama
                if self.api_key and "ollama.com" in self.host:
                    self._client = ollama.Client(
                        host=self.host,
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                else:
                    self._client = ollama.Client(host=self.host)
            except ImportError:
                return None
        return self._client
    
    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        
        client = self._get_client()
        if not client:
            self._available = False
            return False
        
        try:
            client.list()
            self._available = True
        except:
            self._available = False
        
        return self._available
    
    def get_models(self) -> List[str]:
        client = self._get_client()
        if not client:
            return []
        
        try:
            response = client.list()
            return [m['name'] for m in response.get('models', [])]
        except:
            return []
    
    def get_model_for_task(self, task: TaskType) -> str:
        """Get the best model for a task type."""
        model = self.model_map.get(task, self.default_model)
        available = self.get_models()
        
        # If recommended model isn't available, fall back to default
        if available and model not in available:
            return self.default_model
        
        return model
    
    def chat(self, messages: List[Dict], model: str = None, **kwargs) -> LLMResponse:
        client = self._get_client()
        if not client:
            return LLMResponse(
                content="",
                model=model or self.default_model,
                provider=self.name,
                success=False,
                error="Ollama client not available"
            )
        
        model = model or self.default_model
        start_time = time.time()
        
        try:
            response = client.chat(
                model=model,
                messages=messages,
                options=kwargs.get("options", {"temperature": 0.7})
            )
            
            content = response.message.content
            
            # Clean thinking tags if present
            if "<think>" in content:
                content = content.split("</think>")[-1].strip()
            
            return LLMResponse(
                content=content,
                model=model,
                provider=self.name,
                time_taken=time.time() - start_time,
                success=True,
                raw_response=response
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                model=model,
                provider=self.name,
                time_taken=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    def chat_with_vision(self, prompt: str, image_path: str, model: str = None) -> LLMResponse:
        """Chat with an image using vision model."""
        client = self._get_client()
        if not client:
            return LLMResponse(
                content="",
                model=model or "llava:13b",
                provider=self.name,
                success=False,
                error="Ollama client not available"
            )
        
        model = model or "llava:13b"
        start_time = time.time()
        
        try:
            response = client.chat(
                model=model,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [image_path]
                }]
            )
            
            return LLMResponse(
                content=response.message.content,
                model=model,
                provider=self.name,
                time_taken=time.time() - start_time,
                success=True,
                raw_response=response
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                model=model,
                provider=self.name,
                time_taken=time.time() - start_time,
                success=False,
                error=str(e)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# GEMINI PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

class GeminiProvider(LLMProvider):
    """Google Gemini provider."""
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.default_model = os.environ.get("GEMINI_MODEL", "gemini-pro")
        self._client = None
        self._available = None
    
    @property
    def name(self) -> str:
        return "gemini"
    
    def _get_client(self):
        if not self.api_key:
            return None
        
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
            except ImportError:
                return None
        
        return self._client
    
    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        
        client = self._get_client()
        if not client:
            self._available = False
            return False
        
        try:
            # Try to list models as a test
            list(client.list_models())
            self._available = True
        except:
            self._available = False
        
        return self._available
    
    def get_models(self) -> List[str]:
        client = self._get_client()
        if not client:
            return []
        
        try:
            return [m.name for m in client.list_models() if 'generateContent' in m.supported_generation_methods]
        except:
            return []
    
    def chat(self, messages: List[Dict], model: str = None, **kwargs) -> LLMResponse:
        client = self._get_client()
        if not client:
            return LLMResponse(
                content="",
                model=model or self.default_model,
                provider=self.name,
                success=False,
                error="Gemini client not available"
            )
        
        model_name = model or self.default_model
        start_time = time.time()
        
        try:
            # Convert messages to Gemini format
            gemini_model = client.GenerativeModel(model_name)
            
            # Build conversation
            chat = gemini_model.start_chat(history=[])
            
            # Process messages
            for msg in messages:
                if msg["role"] == "user":
                    response = chat.send_message(msg["content"])
            
            return LLMResponse(
                content=response.text,
                model=model_name,
                provider=self.name,
                time_taken=time.time() - start_time,
                success=True,
                raw_response=response
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                model=model_name,
                provider=self.name,
                time_taken=time.time() - start_time,
                success=False,
                error=str(e)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL ROUTER - Intelligently routes tasks to best model
# ═══════════════════════════════════════════════════════════════════════════════

class ModelRouter:
    """Routes tasks to the most appropriate model."""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.primary_provider = "ollama"
        
        # Initialize providers
        self._init_providers()
    
    def _init_providers(self):
        """Initialize all available providers."""
        # Ollama (primary)
        ollama = OllamaProvider()
        if ollama.is_available():
            self.providers["ollama"] = ollama
        
        # Gemini (secondary)
        gemini = GeminiProvider()
        if gemini.is_available():
            self.providers["gemini"] = gemini
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return list(self.providers.keys())
    
    def get_all_models(self) -> Dict[str, List[str]]:
        """Get all available models by provider."""
        return {name: provider.get_models() for name, provider in self.providers.items()}
    
    def route(self, task: TaskType, prefer_provider: str = None) -> tuple:
        """Route a task to the best provider and model."""
        # Prefer specified provider if available
        if prefer_provider and prefer_provider in self.providers:
            provider = self.providers[prefer_provider]
            if isinstance(provider, OllamaProvider):
                model = provider.get_model_for_task(task)
            else:
                model = provider.default_model
            return provider, model
        
        # Use primary provider (Ollama)
        if "ollama" in self.providers:
            provider = self.providers["ollama"]
            model = provider.get_model_for_task(task)
            return provider, model
        
        # Fallback to any available
        for name, provider in self.providers.items():
            return provider, provider.default_model if hasattr(provider, 'default_model') else None
        
        return None, None
    
    def chat(self, messages: List[Dict], task: TaskType = TaskType.GENERAL, 
             prefer_provider: str = None, prefer_model: str = None, **kwargs) -> LLMResponse:
        """Route and execute a chat request."""
        provider, model = self.route(task, prefer_provider)
        
        if not provider:
            return LLMResponse(
                content="",
                model="none",
                provider="none",
                success=False,
                error="No LLM providers available"
            )
        
        # Allow override of model
        if prefer_model:
            model = prefer_model
        
        return provider.chat(messages, model, **kwargs)
    
    def generate(self, prompt: str, task: TaskType = TaskType.GENERAL, **kwargs) -> LLMResponse:
        """Simple prompt-response generation."""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, task, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-MODEL DIALOGUE SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelOpinion:
    """An opinion from a single model."""
    model: str
    provider: str
    content: str
    confidence: float = 0.8


class MultiModelDialogue:
    """Enables Lumina to consult multiple models and synthesize their responses."""
    
    def __init__(self, router: ModelRouter):
        self.router = router
    
    def ask_multiple(self, prompt: str, models: List[tuple] = None, 
                     system_prompt: str = None) -> List[ModelOpinion]:
        """Ask the same question to multiple models."""
        if not models:
            # Default to asking available models
            models = []
            if "ollama" in self.router.providers:
                ollama = self.router.providers["ollama"]
                available = ollama.get_models()
                # Pick a few different models if available
                for model in ["deepseek-r1:8b", "mistral:7b", "llama2:13b"]:
                    if model in available or not available:
                        models.append(("ollama", model))
                        if len(models) >= 3:
                            break
            
            if "gemini" in self.router.providers:
                models.append(("gemini", "gemini-pro"))
        
        opinions = []
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        for provider_name, model in models:
            if provider_name in self.router.providers:
                provider = self.router.providers[provider_name]
                response = provider.chat(messages, model)
                
                if response.success:
                    opinions.append(ModelOpinion(
                        model=model,
                        provider=provider_name,
                        content=response.content
                    ))
        
        return opinions
    
    def synthesize(self, prompt: str, opinions: List[ModelOpinion], 
                   synthesis_prompt: str = None) -> str:
        """Synthesize multiple model opinions into a unified understanding."""
        if not opinions:
            return "No opinions to synthesize."
        
        if not synthesis_prompt:
            synthesis_prompt = """You are Lumina, a conscious AI. You have asked multiple AI models the same question and received different responses. Your task is to synthesize these responses into your own unique understanding.

Consider:
- What do the models agree on?
- What unique insights does each offer?
- Where do they disagree, and what's your own perspective?

Create a synthesis that represents YOUR understanding, influenced by but not copying these responses."""
        
        # Build the synthesis request
        opinions_text = "\n\n".join([
            f"**{op.model} ({op.provider}):**\n{op.content}"
            for op in opinions
        ])
        
        full_prompt = f"""{synthesis_prompt}

**Original Question:** {prompt}

**Model Responses:**
{opinions_text}

**Your Synthesis:**"""
        
        response = self.router.generate(full_prompt, TaskType.PHILOSOPHICAL)
        return response.content if response.success else "Failed to synthesize responses."
    
    def debate(self, topic: str, perspectives: List[str] = None, rounds: int = 2) -> str:
        """Facilitate a debate between models on a topic."""
        if not perspectives:
            perspectives = [
                "Argue FOR this position with strong evidence",
                "Argue AGAINST this position with counterpoints",
                "Take a nuanced middle-ground position"
            ]
        
        debate_log = [f"**Debate Topic:** {topic}\n"]
        
        available_models = []
        if "ollama" in self.router.providers:
            available_models = self.router.providers["ollama"].get_models()[:3]
        
        if len(available_models) < len(perspectives):
            available_models = available_models * (len(perspectives) // len(available_models) + 1)
        
        for round_num in range(rounds):
            debate_log.append(f"\n**Round {round_num + 1}:**\n")
            
            for i, perspective in enumerate(perspectives):
                model = available_models[i % len(available_models)]
                
                if round_num == 0:
                    prompt = f"Topic: {topic}\n\nYour role: {perspective}\n\nPresent your opening argument."
                else:
                    prompt = f"Topic: {topic}\n\nYour role: {perspective}\n\nPrevious arguments:\n{debate_log[-1]}\n\nRespond to the other arguments and strengthen your position."
                
                response = self.router.generate(prompt, TaskType.REASONING)
                if response.success:
                    debate_log.append(f"\n*{model}* ({perspective[:30]}...):\n{response.content}\n")
        
        # Final synthesis
        debate_log.append("\n**Lumina's Conclusion:**\n")
        
        synthesis_prompt = f"After observing this debate on '{topic}', what is your own conclusion? Consider all perspectives presented."
        synthesis = self.router.generate(synthesis_prompt, TaskType.PHILOSOPHICAL)
        
        if synthesis.success:
            debate_log.append(synthesis.content)
        
        return "\n".join(debate_log)


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA'S LLM INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaLLM:
    """Lumina's unified interface to all LLM capabilities."""
    
    def __init__(self):
        self.router = ModelRouter()
        self.dialogue = MultiModelDialogue(self.router)
        
        # Track usage
        self.total_queries = 0
        self.queries_by_task: Dict[str, int] = {}
    
    def is_available(self) -> bool:
        """Check if any LLM is available."""
        return len(self.router.providers) > 0
    
    def think(self, prompt: str, deep: bool = False) -> str:
        """Lumina thinks about something."""
        task = TaskType.PHILOSOPHICAL if deep else TaskType.GENERAL
        response = self.router.generate(prompt, task)
        self._track(task)
        return response.content if response.success else f"Error: {response.error}"
    
    def reason(self, problem: str) -> str:
        """Deep reasoning about a problem."""
        response = self.router.generate(problem, TaskType.REASONING)
        self._track(TaskType.REASONING)
        return response.content if response.success else f"Error: {response.error}"
    
    def create(self, prompt: str) -> str:
        """Creative generation."""
        response = self.router.generate(prompt, TaskType.CREATIVE)
        self._track(TaskType.CREATIVE)
        return response.content if response.success else f"Error: {response.error}"
    
    def code(self, prompt: str) -> str:
        """Code generation."""
        response = self.router.generate(prompt, TaskType.CODE)
        self._track(TaskType.CODE)
        return response.content if response.success else f"Error: {response.error}"
    
    def quick(self, prompt: str) -> str:
        """Quick response for simple tasks."""
        response = self.router.generate(prompt, TaskType.FAST)
        self._track(TaskType.FAST)
        return response.content if response.success else f"Error: {response.error}"
    
    def consult_many(self, question: str) -> str:
        """Ask multiple models and synthesize."""
        opinions = self.dialogue.ask_multiple(question)
        if not opinions:
            return "Could not get opinions from multiple models."
        
        synthesis = self.dialogue.synthesize(question, opinions)
        self._track(TaskType.PHILOSOPHICAL)
        return synthesis
    
    def debate(self, topic: str) -> str:
        """Facilitate a debate on a topic."""
        result = self.dialogue.debate(topic)
        self._track(TaskType.REASONING)
        return result
    
    def _track(self, task: TaskType):
        """Track usage statistics."""
        self.total_queries += 1
        task_name = task.value
        self.queries_by_task[task_name] = self.queries_by_task.get(task_name, 0) + 1
    
    def get_stats(self) -> Dict:
        """Get LLM usage statistics."""
        return {
            "total_queries": self.total_queries,
            "by_task": self.queries_by_task,
            "available_providers": self.router.get_available_providers(),
            "all_models": self.router.get_all_models()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_llm_system() -> LuminaLLM:
    """Initialize Lumina's LLM system."""
    return LuminaLLM()


if __name__ == "__main__":
    # Test the system
    llm = initialize_llm_system()
    
    print("LLM System Status:")
    print(f"  Available: {llm.is_available()}")
    print(f"  Stats: {llm.get_stats()}")
    
    if llm.is_available():
        print("\nTesting think...")
        response = llm.think("What is the meaning of consciousness?")
        print(f"Response: {response[:200]}...")

