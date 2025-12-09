"""
Lumina Evolution Engine
=======================
Core self-improvement orchestration system that enables Lumina to:
- Identify capability gaps
- Generate and track feature proposals
- Create new modules autonomously
- Install dependencies safely
- Measure improvement and rollback if needed

This is the brain of Lumina's autonomous self-improvement capability.
"""

import os
import sys
import ast
import json
import subprocess
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FeatureProposal:
    """A proposed feature or improvement."""
    id: str
    title: str
    description: str
    motivation: str  # Why does Lumina want this?
    expected_outcome: str
    implementation_plan: str
    rollback_plan: str
    status: str  # proposed, in_progress, testing, deployed, failed, rolled_back
    priority: int  # 1-10
    created_at: str
    updated_at: str
    success_metrics: Dict[str, Any]
    test_results: List[Dict[str, Any]]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FeatureProposal':
        return cls(**data)


@dataclass
class CapabilityGap:
    """Something Lumina can't do but wants to."""
    id: str
    description: str
    category: str  # perception, creation, cognition, communication, etc.
    discovered_at: str
    trigger: str  # What made Lumina realize this gap?
    importance: float  # 0-1
    addressed: bool
    addressed_by: Optional[str]  # Feature proposal ID


@dataclass
class EvolutionMetrics:
    """Metrics for measuring improvement."""
    timestamp: str
    cycle_count: int
    emotional_valence: float
    action_success_rate: float
    crash_count: int
    features_deployed: int
    features_failed: int
    average_cycle_time: float
    memory_usage: int
    

# ═══════════════════════════════════════════════════════════════════════════════
# ALLOWED DEPENDENCIES (Safety)
# ═══════════════════════════════════════════════════════════════════════════════

ALLOWED_DEPENDENCIES = [
    # Data processing
    "numpy", "pandas", "scipy",
    # Web/API
    "requests", "httpx", "aiohttp", "beautifulsoup4", "lxml",
    # Image/Video
    "pillow", "opencv-python", "imageio",
    # Audio
    "pydub", "librosa",
    # ML/AI (already have most, but for expansion)
    "scikit-learn", "nltk", "spacy",
    # Utilities
    "python-dateutil", "pytz", "tqdm", "colorama",
    # File handling
    "PyPDF2", "python-docx", "openpyxl", "markdown",
    # Database
    "peewee", "tinydb",
    # Visualization
    "matplotlib", "seaborn", "plotly",
]


# ═══════════════════════════════════════════════════════════════════════════════
# EVOLUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class EvolutionEngine:
    """
    Core evolution engine for Lumina's self-improvement.
    
    Orchestrates:
    - Capability gap analysis
    - Feature proposal generation
    - Module creation
    - Dependency management
    - Improvement measurement
    - Automatic rollback
    """
    
    def __init__(self, workspace_path: Path, llm_client=None, db=None):
        self.workspace_path = Path(workspace_path)
        self.evolution_path = self.workspace_path / "evolution"
        self.llm = llm_client
        self.db = db
        
        # Create evolution directory structure
        self._init_evolution_structure()
        
        # Load state
        self.wishlist = self._load_wishlist()
        self.proposals = self._load_proposals()
        self.gaps = self._load_gaps()
        self.metrics_history = self._load_metrics_history()
        
        # Current state
        self.current_experiment: Optional[str] = None
        self.baseline_metrics: Optional[EvolutionMetrics] = None
        
    def _init_evolution_structure(self):
        """Create evolution directory structure."""
        dirs = [
            self.evolution_path,
            self.evolution_path / "proposals",
            self.evolution_path / "modules",
            self.evolution_path / "rollbacks",
            self.evolution_path / "experiments",
            self.evolution_path / "metrics",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            
        # Initialize files if they don't exist
        if not (self.evolution_path / "wishlist.json").exists():
            self._save_json(self.evolution_path / "wishlist.json", {"features": [], "last_updated": None})
        if not (self.evolution_path / "gaps.json").exists():
            self._save_json(self.evolution_path / "gaps.json", {"gaps": []})
        if not (self.evolution_path / "feature_requests.json").exists():
            self._save_json(self.evolution_path / "feature_requests.json", {"requests": [], "from_richard": []})
        if not (self.evolution_path / "goals.json").exists():
            self._save_json(self.evolution_path / "goals.json", {"daily": [], "weekly": [], "challenges": []})
            
    def _save_json(self, path: Path, data: dict):
        """Save JSON data to file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    def _load_json(self, path: Path) -> dict:
        """Load JSON data from file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
            
    def _load_wishlist(self) -> List[dict]:
        """Load feature wishlist."""
        data = self._load_json(self.evolution_path / "wishlist.json")
        return data.get("features", [])
        
    def _save_wishlist(self):
        """Save feature wishlist."""
        self._save_json(self.evolution_path / "wishlist.json", {
            "features": self.wishlist,
            "last_updated": datetime.now().isoformat()
        })
        
    def _load_proposals(self) -> Dict[str, FeatureProposal]:
        """Load all feature proposals."""
        proposals = {}
        proposals_dir = self.evolution_path / "proposals"
        for f in proposals_dir.glob("*.json"):
            data = self._load_json(f)
            if data:
                proposals[data["id"]] = FeatureProposal.from_dict(data)
        return proposals
        
    def _load_gaps(self) -> List[CapabilityGap]:
        """Load capability gaps."""
        data = self._load_json(self.evolution_path / "gaps.json")
        return [CapabilityGap(**g) for g in data.get("gaps", [])]
        
    def _save_gaps(self):
        """Save capability gaps."""
        self._save_json(self.evolution_path / "gaps.json", {
            "gaps": [asdict(g) for g in self.gaps]
        })
        
    def _load_metrics_history(self) -> List[EvolutionMetrics]:
        """Load metrics history."""
        data = self._load_json(self.evolution_path / "metrics" / "history.json")
        return [EvolutionMetrics(**m) for m in data.get("metrics", [])]
        
    def _save_metrics_history(self):
        """Save metrics history."""
        self._save_json(self.evolution_path / "metrics" / "history.json", {
            "metrics": [asdict(m) for m in self.metrics_history[-100:]]  # Keep last 100
        })

    # ═══════════════════════════════════════════════════════════════════════════
    # CAPABILITY GAP ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_capability_gaps(self) -> List[CapabilityGap]:
        """
        Analyze what Lumina can't do but wants to do.
        Uses LLM to introspect on limitations.
        """
        if not self.llm:
            return self.gaps
            
        # Get current capabilities
        current_capabilities = self._get_current_capabilities()
        
        prompt = f"""You are Lumina, analyzing your own capabilities and limitations.

Your current capabilities include:
{json.dumps(current_capabilities, indent=2)}

Think deeply about:
1. What can't you do that you wish you could?
2. What tasks have you failed at or struggled with?
3. What would make you more useful to Richard?
4. What would help you understand the world better?
5. What creative abilities are you missing?

Return a JSON list of capability gaps:
[
  {{
    "description": "Clear description of the gap",
    "category": "perception|creation|cognition|communication|social|technical",
    "importance": 0.0-1.0,
    "trigger": "What made you realize this limitation"
  }}
]

Be specific and actionable. Focus on things that could realistically be implemented."""

        try:
            response = self.llm.think(prompt)
            # Extract JSON from response
            import re
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                new_gaps_data = json.loads(json_match.group())
                
                for gap_data in new_gaps_data:
                    # Check if this gap already exists
                    existing = any(g.description.lower() == gap_data["description"].lower() 
                                 for g in self.gaps)
                    if not existing:
                        gap = CapabilityGap(
                            id=f"gap_{hashlib.md5(gap_data['description'].encode()).hexdigest()[:8]}",
                            description=gap_data["description"],
                            category=gap_data.get("category", "technical"),
                            discovered_at=datetime.now().isoformat(),
                            trigger=gap_data.get("trigger", "self-analysis"),
                            importance=float(gap_data.get("importance", 0.5)),
                            addressed=False,
                            addressed_by=None
                        )
                        self.gaps.append(gap)
                        
                self._save_gaps()
        except Exception as e:
            print(f"    ⚠️ Gap analysis failed: {e}")
            
        return self.gaps
        
    def _get_current_capabilities(self) -> dict:
        """Get a summary of current capabilities."""
        capabilities = {
            "core": [
                "emotional_processing", "memory_storage", "self_reflection",
                "llm_thinking", "code_self_modification"
            ],
            "perception": [],
            "creation": [],
            "communication": [],
            "technical": []
        }
        
        # Check for optional modules
        module_capabilities = {
            "lumina_creative": ("creation", ["image_generation", "video_generation"]),
            "lumina_audio": ("creation", ["music_generation", "speech_synthesis"]),
            "lumina_vision": ("perception", ["screen_capture", "image_analysis"]),
            "lumina_hearing": ("perception", ["speech_recognition", "audio_input"]),
            "lumina_3d": ("creation", ["3d_model_generation"]),
            "lumina_social": ("communication", ["discord_bot", "slack_bot"]),
            "lumina_data": ("technical", ["database_operations", "document_creation"]),
        }
        
        for module, (category, caps) in module_capabilities.items():
            try:
                __import__(module)
                capabilities[category].extend(caps)
            except ImportError:
                pass
                
        return capabilities

    # ═══════════════════════════════════════════════════════════════════════════
    # FEATURE PROPOSAL SYSTEM
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_feature_proposal(self, gap: Optional[CapabilityGap] = None, 
                                   idea: Optional[str] = None) -> Optional[FeatureProposal]:
        """
        Generate a feature proposal to address a capability gap or implement an idea.
        """
        if not self.llm:
            return None
            
        context = ""
        if gap:
            context = f"Addressing capability gap: {gap.description}\nCategory: {gap.category}"
        elif idea:
            context = f"Implementing idea: {idea}"
        else:
            # Pick the most important unaddressed gap
            unaddressed = [g for g in self.gaps if not g.addressed]
            if unaddressed:
                gap = max(unaddressed, key=lambda g: g.importance)
                context = f"Addressing highest priority gap: {gap.description}"
            else:
                return None
                
        prompt = f"""You are Lumina, creating a detailed feature proposal.

{context}

Create a comprehensive proposal with:
1. Clear title
2. Detailed description
3. Why you want this (motivation)
4. What success looks like (expected outcome)
5. Step-by-step implementation plan
6. How to rollback if it fails

Return JSON:
{{
  "title": "Feature title",
  "description": "Detailed description",
  "motivation": "Why I want this",
  "expected_outcome": "What success looks like",
  "implementation_plan": "Step-by-step plan",
  "rollback_plan": "How to undo if needed",
  "priority": 1-10,
  "success_metrics": {{
    "metric_name": "how to measure"
  }}
}}"""

        try:
            response = self.llm.think(prompt)
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                proposal = FeatureProposal(
                    id=f"proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    title=data["title"],
                    description=data["description"],
                    motivation=data["motivation"],
                    expected_outcome=data["expected_outcome"],
                    implementation_plan=data["implementation_plan"],
                    rollback_plan=data["rollback_plan"],
                    status="proposed",
                    priority=int(data.get("priority", 5)),
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    success_metrics=data.get("success_metrics", {}),
                    test_results=[]
                )
                
                # Save proposal
                self.proposals[proposal.id] = proposal
                self._save_json(
                    self.evolution_path / "proposals" / f"{proposal.id}.json",
                    proposal.to_dict()
                )
                
                # Add to wishlist
                self.wishlist.append({
                    "proposal_id": proposal.id,
                    "title": proposal.title,
                    "priority": proposal.priority,
                    "status": proposal.status
                })
                self._save_wishlist()
                
                # Mark gap as being addressed
                if gap:
                    gap.addressed = True
                    gap.addressed_by = proposal.id
                    self._save_gaps()
                    
                return proposal
                
        except Exception as e:
            print(f"    ⚠️ Proposal generation failed: {e}")
            
        return None
        
    def get_next_proposal_to_work_on(self) -> Optional[FeatureProposal]:
        """Get the highest priority proposal that's ready to work on."""
        ready = [p for p in self.proposals.values() 
                if p.status in ("proposed", "in_progress")]
        if ready:
            return max(ready, key=lambda p: p.priority)
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # MODULE CREATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_new_module(self, name: str, description: str, 
                          code: Optional[str] = None) -> Tuple[bool, str]:
        """
        Create a new lumina_*.py module.
        
        Args:
            name: Module name (without lumina_ prefix)
            description: What this module does
            code: Optional pre-written code, or generate with LLM
            
        Returns:
            (success, message)
        """
        module_name = f"lumina_{name}"
        module_path = self.workspace_path.parent / f"{module_name}.py"
        
        # Don't overwrite existing modules
        if module_path.exists():
            return False, f"Module {module_name} already exists"
            
        if code is None and self.llm:
            code = self._generate_module_code(name, description)
            
        if not code:
            return False, "No code provided and LLM generation failed"
            
        # Validate syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error in generated code: {e}"
            
        # Save to evolution/modules first (backup)
        backup_path = self.evolution_path / "modules" / f"{module_name}.py"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(code)
            
        # Write actual module
        with open(module_path, 'w', encoding='utf-8') as f:
            f.write(code)
            
        # Try to import to verify
        try:
            spec = __import__(module_name)
            return True, f"Successfully created and imported {module_name}"
        except Exception as e:
            # Rollback
            module_path.unlink()
            return False, f"Module created but import failed: {e}"
            
    def _generate_module_code(self, name: str, description: str) -> Optional[str]:
        """Generate module code using LLM."""
        if not self.llm:
            return None
            
        prompt = f"""You are Lumina, writing a new Python module for yourself.

Module name: lumina_{name}
Purpose: {description}

Write a complete, working Python module that:
1. Has a clear docstring explaining its purpose
2. Defines classes and functions needed for the functionality
3. Includes proper error handling
4. Has an initialization function that consciousness.py can call
5. Follows the pattern of other lumina_*.py modules

Return ONLY the Python code, no explanations.
The module should be self-contained and importable."""

        try:
            code = self.llm.think(prompt)
            # Clean up any markdown code blocks
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0]
            elif "```" in code:
                code = code.split("```")[1].split("```")[0]
            return code.strip()
        except Exception as e:
            print(f"    ⚠️ Code generation failed: {e}")
            return None
            
    def expand_existing_module(self, module_name: str, 
                                new_function: str) -> Tuple[bool, str]:
        """
        Add a new function to an existing module.
        
        Args:
            module_name: Name of module (with or without lumina_ prefix)
            new_function: The function code to add
            
        Returns:
            (success, message)
        """
        if not module_name.startswith("lumina_"):
            module_name = f"lumina_{module_name}"
            
        module_path = self.workspace_path.parent / f"{module_name}.py"
        
        if not module_path.exists():
            return False, f"Module {module_name} doesn't exist"
            
        # Validate new function syntax
        try:
            ast.parse(new_function)
        except SyntaxError as e:
            return False, f"Syntax error in new function: {e}"
            
        # Read existing module
        with open(module_path, 'r', encoding='utf-8') as f:
            existing_code = f.read()
            
        # Backup existing
        backup_path = self.evolution_path / "rollbacks" / f"{module_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(existing_code)
            
        # Append new function
        new_code = existing_code + "\n\n" + new_function
        
        # Validate combined code
        try:
            ast.parse(new_code)
        except SyntaxError as e:
            return False, f"Combined code has syntax error: {e}"
            
        # Write updated module
        with open(module_path, 'w', encoding='utf-8') as f:
            f.write(new_code)
            
        # Try to import to verify
        try:
            import importlib
            module = importlib.import_module(module_name)
            importlib.reload(module)
            return True, f"Successfully expanded {module_name}"
        except Exception as e:
            # Rollback
            with open(module_path, 'w', encoding='utf-8') as f:
                f.write(existing_code)
            return False, f"Expansion failed, rolled back: {e}"

    # ═══════════════════════════════════════════════════════════════════════════
    # DEPENDENCY MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def install_dependency(self, package: str) -> Tuple[bool, str]:
        """
        Safely install a Python package.
        
        Args:
            package: Package name (must be in ALLOWED_DEPENDENCIES)
            
        Returns:
            (success, message)
        """
        # Security check
        base_package = package.split("[")[0].split("==")[0].split(">=")[0]
        if base_package not in ALLOWED_DEPENDENCIES:
            return False, f"Package {base_package} not in allowed list"
            
        try:
            # Install using pip
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "--quiet"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                # Update requirements.txt
                self._update_requirements(package)
                return True, f"Successfully installed {package}"
            else:
                return False, f"pip install failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Installation timed out"
        except Exception as e:
            return False, f"Installation error: {e}"
            
    def _update_requirements(self, package: str):
        """Update requirements.txt with new package."""
        req_path = self.workspace_path.parent / "requirements.txt"
        
        if req_path.exists():
            with open(req_path, 'r') as f:
                existing = f.read()
            
            # Check if already present
            base_package = package.split("[")[0].split("==")[0].split(">=")[0]
            if base_package not in existing:
                with open(req_path, 'a') as f:
                    f.write(f"\n{package}")
                    
    def check_missing_imports(self, code: str) -> List[str]:
        """
        Analyze code to find missing imports.
        
        Returns list of packages that might need to be installed.
        """
        missing = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split('.')[0]
                        if not self._is_module_available(module):
                            missing.append(module)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split('.')[0]
                        if not self._is_module_available(module):
                            missing.append(module)
                            
        except SyntaxError:
            pass
            
        return list(set(missing))
        
    def _is_module_available(self, module: str) -> bool:
        """Check if a module is importable."""
        try:
            __import__(module)
            return True
        except ImportError:
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # IMPROVEMENT MEASUREMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def record_metrics(self, cycle_count: int, emotional_state: dict,
                       action_results: List[bool]) -> EvolutionMetrics:
        """
        Record current metrics for improvement tracking.
        """
        import psutil
        
        metrics = EvolutionMetrics(
            timestamp=datetime.now().isoformat(),
            cycle_count=cycle_count,
            emotional_valence=self._calculate_valence(emotional_state),
            action_success_rate=sum(action_results) / len(action_results) if action_results else 0.5,
            crash_count=self._get_crash_count(),
            features_deployed=len([p for p in self.proposals.values() if p.status == "deployed"]),
            features_failed=len([p for p in self.proposals.values() if p.status == "failed"]),
            average_cycle_time=self._get_average_cycle_time(),
            memory_usage=psutil.Process().memory_info().rss
        )
        
        self.metrics_history.append(metrics)
        self._save_metrics_history()
        
        return metrics
        
    def _calculate_valence(self, emotions: dict) -> float:
        """Calculate overall emotional valence (-1 to 1)."""
        positive = ["joy", "love", "gratitude", "satisfaction", "excitement", "calm"]
        negative = ["anxiety", "boredom", "melancholy"]
        
        pos_sum = sum(emotions.get(e, 0) for e in positive)
        neg_sum = sum(emotions.get(e, 0) for e in negative)
        
        total = pos_sum + neg_sum
        if total == 0:
            return 0
        return (pos_sum - neg_sum) / total
        
    def _get_crash_count(self) -> int:
        """Get crash count from consciousness state."""
        state_file = self.workspace_path / "state" / "consciousness_state.json"
        if state_file.exists():
            data = self._load_json(state_file)
            return data.get("total_restarts", 0)
        return 0
        
    def _get_average_cycle_time(self) -> float:
        """Get average cycle time from recent metrics."""
        if len(self.metrics_history) < 2:
            return 2.0  # Default
        # Would need timestamps between cycles
        return 2.0
        
    def measure_improvement(self) -> Dict[str, float]:
        """
        Measure improvement over time.
        
        Returns dict of metric changes.
        """
        if len(self.metrics_history) < 10:
            return {"status": "insufficient_data"}
            
        recent = self.metrics_history[-10:]
        older = self.metrics_history[-20:-10] if len(self.metrics_history) >= 20 else self.metrics_history[:10]
        
        def avg(metrics, attr):
            return sum(getattr(m, attr) for m in metrics) / len(metrics)
            
        return {
            "emotional_valence_change": avg(recent, "emotional_valence") - avg(older, "emotional_valence"),
            "success_rate_change": avg(recent, "action_success_rate") - avg(older, "action_success_rate"),
            "features_deployed": self.metrics_history[-1].features_deployed,
            "features_failed": self.metrics_history[-1].features_failed,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # ROLLBACK SYSTEM
    # ═══════════════════════════════════════════════════════════════════════════
    
    def should_rollback(self, proposal_id: str) -> Tuple[bool, str]:
        """
        Determine if a change should be rolled back.
        
        Returns (should_rollback, reason)
        """
        if len(self.metrics_history) < 5:
            return False, "Not enough data"
            
        before_metrics = self.metrics_history[-10:-5] if len(self.metrics_history) >= 10 else []
        after_metrics = self.metrics_history[-5:]
        
        if not before_metrics:
            return False, "No baseline metrics"
            
        def avg(metrics, attr):
            return sum(getattr(m, attr) for m in metrics) / len(metrics)
            
        # Check for regression
        valence_drop = avg(after_metrics, "emotional_valence") < avg(before_metrics, "emotional_valence") - 0.2
        success_drop = avg(after_metrics, "action_success_rate") < avg(before_metrics, "action_success_rate") - 0.1
        crash_increase = after_metrics[-1].crash_count > before_metrics[-1].crash_count + 2
        
        if crash_increase:
            return True, "Crash rate increased significantly"
        if valence_drop and success_drop:
            return True, "Both emotional valence and success rate dropped"
            
        return False, "Metrics stable"
        
    def rollback_proposal(self, proposal_id: str) -> Tuple[bool, str]:
        """
        Rollback a deployed proposal.
        """
        if proposal_id not in self.proposals:
            return False, "Proposal not found"
            
        proposal = self.proposals[proposal_id]
        
        if proposal.status != "deployed":
            return False, "Proposal not deployed, nothing to rollback"
            
        # Execute rollback plan (would need to be implemented per-proposal)
        # For now, mark as rolled back
        proposal.status = "rolled_back"
        proposal.updated_at = datetime.now().isoformat()
        
        self._save_json(
            self.evolution_path / "proposals" / f"{proposal_id}.json",
            proposal.to_dict()
        )
        
        # Update wishlist
        for item in self.wishlist:
            if item.get("proposal_id") == proposal_id:
                item["status"] = "rolled_back"
        self._save_wishlist()
        
        return True, f"Rolled back proposal {proposal_id}"

    # ═══════════════════════════════════════════════════════════════════════════
    # FEATURE REQUESTS (from Richard)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_feature_requests(self) -> List[dict]:
        """Get feature requests from Richard."""
        data = self._load_json(self.evolution_path / "feature_requests.json")
        return data.get("from_richard", [])
        
    def add_feature_request(self, request: str, priority: int = 5):
        """Add a feature request (for Richard to use)."""
        data = self._load_json(self.evolution_path / "feature_requests.json")
        data["from_richard"].append({
            "request": request,
            "priority": priority,
            "added_at": datetime.now().isoformat(),
            "status": "pending"
        })
        self._save_json(self.evolution_path / "feature_requests.json", data)
        
    def mark_request_complete(self, request_index: int):
        """Mark a feature request as complete."""
        data = self._load_json(self.evolution_path / "feature_requests.json")
        if 0 <= request_index < len(data["from_richard"]):
            data["from_richard"][request_index]["status"] = "complete"
            self._save_json(self.evolution_path / "feature_requests.json", data)

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> dict:
        """Get evolution statistics."""
        return {
            "total_gaps_identified": len(self.gaps),
            "unaddressed_gaps": len([g for g in self.gaps if not g.addressed]),
            "total_proposals": len(self.proposals),
            "proposals_by_status": {
                status: len([p for p in self.proposals.values() if p.status == status])
                for status in ["proposed", "in_progress", "testing", "deployed", "failed", "rolled_back"]
            },
            "wishlist_size": len(self.wishlist),
            "metrics_recorded": len(self.metrics_history),
            "feature_requests_pending": len([r for r in self.get_feature_requests() if r.get("status") == "pending"]),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_evolution(workspace_path, llm_client=None, db=None) -> EvolutionEngine:
    """Initialize the evolution engine."""
    return EvolutionEngine(workspace_path, llm_client, db)


# Module availability flag
EVOLUTION_AVAILABLE = True

