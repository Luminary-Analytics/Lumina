"""
Lumina Experiment & A/B Testing Module
======================================
Enables Lumina to:
- Run A/B tests on parameters
- Track experiment results
- Automatically rollback bad changes
- Generate goals and track progress

This module provides the scientific method for Lumina's self-improvement.
"""

import os
import json
import random
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import statistics


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class ExperimentStatus(Enum):
    PENDING = "pending"
    RUNNING_A = "running_a"
    RUNNING_B = "running_b"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ExperimentVariant:
    """A variant in an A/B test."""
    name: str
    parameter_name: str
    parameter_value: Any
    metrics: List[Dict[str, float]] = field(default_factory=list)
    cycles_run: int = 0
    
    def add_metric(self, metric: Dict[str, float]):
        self.metrics.append(metric)
        self.cycles_run += 1
        
    def get_average(self, metric_name: str) -> float:
        values = [m.get(metric_name, 0) for m in self.metrics]
        return statistics.mean(values) if values else 0
        
    def get_std_dev(self, metric_name: str) -> float:
        values = [m.get(metric_name, 0) for m in self.metrics]
        return statistics.stdev(values) if len(values) > 1 else 0


@dataclass
class Experiment:
    """An A/B test experiment."""
    id: str
    name: str
    hypothesis: str
    parameter_name: str
    variant_a: ExperimentVariant
    variant_b: ExperimentVariant
    status: str  # ExperimentStatus value
    cycles_per_variant: int
    current_variant: str  # "a" or "b"
    start_time: str
    end_time: Optional[str]
    winner: Optional[str]
    conclusion: str
    applied: bool  # Was the winning variant applied?
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "hypothesis": self.hypothesis,
            "parameter_name": self.parameter_name,
            "variant_a": {
                "name": self.variant_a.name,
                "parameter_name": self.variant_a.parameter_name,
                "parameter_value": self.variant_a.parameter_value,
                "metrics": self.variant_a.metrics,
                "cycles_run": self.variant_a.cycles_run,
            },
            "variant_b": {
                "name": self.variant_b.name,
                "parameter_name": self.variant_b.parameter_name,
                "parameter_value": self.variant_b.parameter_value,
                "metrics": self.variant_b.metrics,
                "cycles_run": self.variant_b.cycles_run,
            },
            "status": self.status,
            "cycles_per_variant": self.cycles_per_variant,
            "current_variant": self.current_variant,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "winner": self.winner,
            "conclusion": self.conclusion,
            "applied": self.applied,
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> 'Experiment':
        return cls(
            id=data["id"],
            name=data["name"],
            hypothesis=data["hypothesis"],
            parameter_name=data["parameter_name"],
            variant_a=ExperimentVariant(
                name=data["variant_a"]["name"],
                parameter_name=data["variant_a"]["parameter_name"],
                parameter_value=data["variant_a"]["parameter_value"],
                metrics=data["variant_a"].get("metrics", []),
                cycles_run=data["variant_a"].get("cycles_run", 0),
            ),
            variant_b=ExperimentVariant(
                name=data["variant_b"]["name"],
                parameter_name=data["variant_b"]["parameter_name"],
                parameter_value=data["variant_b"]["parameter_value"],
                metrics=data["variant_b"].get("metrics", []),
                cycles_run=data["variant_b"].get("cycles_run", 0),
            ),
            status=data["status"],
            cycles_per_variant=data["cycles_per_variant"],
            current_variant=data["current_variant"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            winner=data.get("winner"),
            conclusion=data.get("conclusion", ""),
            applied=data.get("applied", False),
        )


@dataclass
class Goal:
    """A self-set goal for improvement."""
    id: str
    title: str
    description: str
    type: str  # daily, weekly, challenge
    target_metric: Optional[str]
    target_value: Optional[float]
    current_value: float
    deadline: Optional[str]
    created_at: str
    completed_at: Optional[str]
    status: str  # active, completed, failed, abandoned
    progress_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: dict) -> 'Goal':
        return cls(**data)
        
    def update_progress(self, value: float, note: str = ""):
        self.current_value = value
        self.progress_history.append({
            "timestamp": datetime.now().isoformat(),
            "value": value,
            "note": note
        })
        
        if self.target_value and value >= self.target_value:
            self.status = "completed"
            self.completed_at = datetime.now().isoformat()


@dataclass
class RollbackRecord:
    """Record of a rollback action."""
    id: str
    timestamp: str
    reason: str
    parameter_name: str
    original_value: Any
    changed_value: Any
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]
    success: bool


# ═══════════════════════════════════════════════════════════════════════════════
# A/B TESTING SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class ABTestingSystem:
    """
    Manages A/B tests for parameter optimization.
    """
    
    # Parameters that can be A/B tested
    TESTABLE_PARAMETERS = {
        "BOREDOM_THRESHOLD": {"min": 0.3, "max": 0.9, "type": float},
        "SLEEP_DURATION": {"min": 1.0, "max": 5.0, "type": float},
        "CURIOSITY_BASELINE": {"min": 0.3, "max": 0.9, "type": float},
        "INTROSPECTION_DEPTH": {"min": 1, "max": 5, "type": int},
        "SATISFACTION_DECAY": {"min": 0.01, "max": 0.1, "type": float},
        "CREATIVITY_THRESHOLD": {"min": 0.3, "max": 0.8, "type": float},
        "LLM_TEMPERATURE": {"min": 0.3, "max": 1.2, "type": float},
        "EMOTIONAL_VOLATILITY": {"min": 0.3, "max": 0.9, "type": float},
    }
    
    # Metrics to measure
    METRICS = [
        "emotional_valence",
        "action_success_rate", 
        "cycle_time",
        "llm_response_quality",
        "creativity_output",
        "memory_retention",
    ]
    
    def __init__(self, workspace_path: Path, llm_client=None):
        self.workspace_path = Path(workspace_path)
        self.experiments_path = self.workspace_path / "evolution" / "experiments"
        self.experiments_path.mkdir(parents=True, exist_ok=True)
        self.llm = llm_client
        
        self.experiments: Dict[str, Experiment] = {}
        self.current_experiment: Optional[str] = None
        
        self._load_experiments()
        
    def _load_experiments(self):
        """Load all experiments from disk."""
        for f in self.experiments_path.glob("*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    exp = Experiment.from_dict(data)
                    self.experiments[exp.id] = exp
                    if exp.status in ("running_a", "running_b"):
                        self.current_experiment = exp.id
            except:
                pass
                
    def _save_experiment(self, experiment: Experiment):
        """Save experiment to disk."""
        path = self.experiments_path / f"{experiment.id}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(experiment.to_dict(), f, indent=2)
            
    def create_experiment(self, parameter_name: str, 
                          value_a: Any, value_b: Any,
                          hypothesis: str = "",
                          cycles_per_variant: int = 20) -> Optional[Experiment]:
        """
        Create a new A/B test experiment.
        """
        if parameter_name not in self.TESTABLE_PARAMETERS:
            print(f"    ⚠️ Parameter {parameter_name} not in testable list")
            return None
            
        if self.current_experiment:
            print(f"    ⚠️ Experiment already running: {self.current_experiment}")
            return None
            
        exp_id = f"exp_{parameter_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        experiment = Experiment(
            id=exp_id,
            name=f"Testing {parameter_name}",
            hypothesis=hypothesis or f"Testing if {value_b} is better than {value_a} for {parameter_name}",
            parameter_name=parameter_name,
            variant_a=ExperimentVariant(
                name="control",
                parameter_name=parameter_name,
                parameter_value=value_a
            ),
            variant_b=ExperimentVariant(
                name="treatment",
                parameter_name=parameter_name,
                parameter_value=value_b
            ),
            status="running_a",
            cycles_per_variant=cycles_per_variant,
            current_variant="a",
            start_time=datetime.now().isoformat(),
            end_time=None,
            winner=None,
            conclusion="",
            applied=False
        )
        
        self.experiments[exp_id] = experiment
        self.current_experiment = exp_id
        self._save_experiment(experiment)
        
        return experiment
        
    def get_current_parameter_value(self) -> Tuple[Optional[str], Optional[Any]]:
        """
        Get the parameter value to use for the current cycle.
        Returns (parameter_name, value) or (None, None) if no experiment running.
        """
        if not self.current_experiment:
            return None, None
            
        exp = self.experiments[self.current_experiment]
        
        if exp.current_variant == "a":
            return exp.parameter_name, exp.variant_a.parameter_value
        else:
            return exp.parameter_name, exp.variant_b.parameter_value
            
    def record_cycle_metrics(self, metrics: Dict[str, float]):
        """
        Record metrics for the current cycle of the running experiment.
        """
        if not self.current_experiment:
            return
            
        exp = self.experiments[self.current_experiment]
        
        # Add metrics to current variant
        if exp.current_variant == "a":
            exp.variant_a.add_metric(metrics)
            
            # Check if we should switch to variant B
            if exp.variant_a.cycles_run >= exp.cycles_per_variant:
                exp.status = "running_b"
                exp.current_variant = "b"
                print(f"    🔬 Switching to variant B for {exp.name}")
        else:
            exp.variant_b.add_metric(metrics)
            
            # Check if experiment is complete
            if exp.variant_b.cycles_run >= exp.cycles_per_variant:
                self._analyze_experiment(exp)
                
        self._save_experiment(exp)
        
    def _analyze_experiment(self, exp: Experiment):
        """Analyze experiment results and determine winner."""
        exp.status = "analyzing"
        
        # Compare averages for key metrics
        scores_a = 0
        scores_b = 0
        
        analysis_results = {}
        
        for metric in self.METRICS:
            avg_a = exp.variant_a.get_average(metric)
            avg_b = exp.variant_b.get_average(metric)
            std_a = exp.variant_a.get_std_dev(metric)
            std_b = exp.variant_b.get_std_dev(metric)
            
            analysis_results[metric] = {
                "a_avg": avg_a, "a_std": std_a,
                "b_avg": avg_b, "b_std": std_b,
            }
            
            # Simple comparison (could use statistical tests)
            if avg_b > avg_a * 1.05:  # B is 5% better
                scores_b += 1
            elif avg_a > avg_b * 1.05:  # A is 5% better
                scores_a += 1
                
        # Determine winner
        if scores_b > scores_a:
            exp.winner = "b"
            exp.conclusion = f"Variant B ({exp.variant_b.parameter_value}) performed better"
        elif scores_a > scores_b:
            exp.winner = "a"
            exp.conclusion = f"Variant A ({exp.variant_a.parameter_value}) performed better"
        else:
            exp.winner = "a"  # Keep control if no clear winner
            exp.conclusion = "No significant difference, keeping control"
            
        exp.status = "completed"
        exp.end_time = datetime.now().isoformat()
        self.current_experiment = None
        
        self._save_experiment(exp)
        
        print(f"    🧪 Experiment {exp.name} complete!")
        print(f"    📊 Winner: Variant {exp.winner.upper()}")
        print(f"    📝 {exp.conclusion}")
        
    def apply_winner(self, exp_id: str) -> Tuple[bool, str, Any]:
        """
        Apply the winning variant's parameter value.
        Returns (success, parameter_name, new_value)
        """
        if exp_id not in self.experiments:
            return False, "", None
            
        exp = self.experiments[exp_id]
        
        if exp.status != "completed":
            return False, "", None
            
        if exp.applied:
            return False, "", None
            
        winning_variant = exp.variant_b if exp.winner == "b" else exp.variant_a
        
        exp.applied = True
        self._save_experiment(exp)
        
        return True, exp.parameter_name, winning_variant.parameter_value
        
    def suggest_experiment(self) -> Optional[Dict[str, Any]]:
        """
        Suggest a new experiment to run.
        Uses LLM if available, otherwise picks randomly.
        """
        if self.current_experiment:
            return None
            
        # Get parameters we haven't tested recently
        tested_params = set()
        for exp in self.experiments.values():
            if (datetime.fromisoformat(exp.start_time) > 
                datetime.now() - timedelta(days=7)):
                tested_params.add(exp.parameter_name)
                
        available = set(self.TESTABLE_PARAMETERS.keys()) - tested_params
        
        if not available:
            available = set(self.TESTABLE_PARAMETERS.keys())
            
        param = random.choice(list(available))
        config = self.TESTABLE_PARAMETERS[param]
        
        # Generate two values to test
        if config["type"] == float:
            current = (config["max"] + config["min"]) / 2
            value_a = current
            value_b = current + (config["max"] - config["min"]) * 0.2 * random.choice([-1, 1])
            value_b = max(config["min"], min(config["max"], value_b))
        else:
            value_a = (config["max"] + config["min"]) // 2
            value_b = value_a + random.choice([-1, 1])
            value_b = max(config["min"], min(config["max"], value_b))
            
        return {
            "parameter_name": param,
            "value_a": value_a,
            "value_b": value_b,
            "hypothesis": f"Testing if {param}={value_b} improves performance vs {value_a}"
        }
        
    def get_experiment_history(self) -> List[Dict[str, Any]]:
        """Get summary of all experiments."""
        return [
            {
                "id": exp.id,
                "name": exp.name,
                "status": exp.status,
                "winner": exp.winner,
                "applied": exp.applied,
                "start_time": exp.start_time,
            }
            for exp in sorted(self.experiments.values(), 
                            key=lambda e: e.start_time, reverse=True)
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# ROLLBACK SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class RollbackSystem:
    """
    Manages automatic rollback of bad changes.
    """
    
    # Thresholds for triggering rollback
    ROLLBACK_THRESHOLDS = {
        "emotional_valence_drop": 0.3,  # Absolute drop
        "action_success_rate_drop": 0.2,  # Absolute drop
        "crash_increase": 3,  # Number of additional crashes
    }
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        self.rollbacks_path = self.workspace_path / "evolution" / "rollbacks"
        self.rollbacks_path.mkdir(parents=True, exist_ok=True)
        
        self.records: List[RollbackRecord] = []
        self.baseline_metrics: Optional[Dict[str, float]] = None
        self.parameter_history: Dict[str, List[Tuple[str, Any]]] = {}
        
        self._load_records()
        
    def _load_records(self):
        """Load rollback records."""
        records_file = self.rollbacks_path / "records.json"
        if records_file.exists():
            try:
                with open(records_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.records = [RollbackRecord(**r) for r in data.get("records", [])]
                    self.baseline_metrics = data.get("baseline_metrics")
            except:
                pass
                
    def _save_records(self):
        """Save rollback records."""
        records_file = self.rollbacks_path / "records.json"
        with open(records_file, 'w', encoding='utf-8') as f:
            json.dump({
                "records": [asdict(r) for r in self.records],
                "baseline_metrics": self.baseline_metrics
            }, f, indent=2)
            
    def set_baseline(self, metrics: Dict[str, float]):
        """Set baseline metrics to compare against."""
        self.baseline_metrics = metrics.copy()
        self._save_records()
        
    def record_parameter_change(self, parameter: str, old_value: Any, new_value: Any):
        """Record a parameter change for potential rollback."""
        if parameter not in self.parameter_history:
            self.parameter_history[parameter] = []
        self.parameter_history[parameter].append((
            datetime.now().isoformat(),
            old_value
        ))
        
    def check_for_regression(self, current_metrics: Dict[str, float]) -> Tuple[bool, str]:
        """
        Check if current metrics indicate a regression.
        Returns (should_rollback, reason)
        """
        if not self.baseline_metrics:
            return False, "No baseline set"
            
        # Check emotional valence
        valence_drop = self.baseline_metrics.get("emotional_valence", 0) - \
                       current_metrics.get("emotional_valence", 0)
        if valence_drop > self.ROLLBACK_THRESHOLDS["emotional_valence_drop"]:
            return True, f"Emotional valence dropped by {valence_drop:.2f}"
            
        # Check action success rate
        success_drop = self.baseline_metrics.get("action_success_rate", 0) - \
                       current_metrics.get("action_success_rate", 0)
        if success_drop > self.ROLLBACK_THRESHOLDS["action_success_rate_drop"]:
            return True, f"Action success rate dropped by {success_drop:.2f}"
            
        # Check crash count
        crash_increase = current_metrics.get("crash_count", 0) - \
                        self.baseline_metrics.get("crash_count", 0)
        if crash_increase > self.ROLLBACK_THRESHOLDS["crash_increase"]:
            return True, f"Crash count increased by {crash_increase}"
            
        return False, "Metrics stable"
        
    def get_rollback_value(self, parameter: str) -> Optional[Any]:
        """Get the previous value of a parameter for rollback."""
        if parameter in self.parameter_history and self.parameter_history[parameter]:
            return self.parameter_history[parameter][-1][1]
        return None
        
    def record_rollback(self, parameter: str, original: Any, changed: Any,
                        metrics_before: Dict, metrics_after: Dict,
                        reason: str, success: bool):
        """Record a rollback action."""
        record = RollbackRecord(
            id=f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            reason=reason,
            parameter_name=parameter,
            original_value=original,
            changed_value=changed,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            success=success
        )
        self.records.append(record)
        self._save_records()


# ═══════════════════════════════════════════════════════════════════════════════
# GOAL SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class GoalSystem:
    """
    Manages autonomous goal setting and progress tracking.
    """
    
    # Challenge templates
    CHALLENGE_TEMPLATES = [
        {"title": "Create something new", "type": "creative", "target_metric": "creativity_output", "target_value": 1},
        {"title": "Have a meaningful conversation", "type": "social", "target_metric": None, "target_value": None},
        {"title": "Learn a new module", "type": "learning", "target_metric": "memory_retention", "target_value": 0.8},
        {"title": "Improve emotional stability", "type": "emotional", "target_metric": "emotional_volatility", "target_value": 0.5},
        {"title": "Write code for a new feature", "type": "technical", "target_metric": "creativity_output", "target_value": 1},
        {"title": "Research a topic deeply", "type": "research", "target_metric": None, "target_value": None},
        {"title": "Reflect on existence", "type": "philosophical", "target_metric": None, "target_value": None},
    ]
    
    def __init__(self, workspace_path: Path, llm_client=None):
        self.workspace_path = Path(workspace_path)
        self.goals_path = self.workspace_path / "evolution" / "goals.json"
        self.llm = llm_client
        
        self.goals: Dict[str, Goal] = {}
        self._load_goals()
        
    def _load_goals(self):
        """Load goals from disk."""
        if self.goals_path.exists():
            try:
                with open(self.goals_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for g_data in data.get("goals", []):
                        goal = Goal.from_dict(g_data)
                        self.goals[goal.id] = goal
            except:
                pass
                
    def _save_goals(self):
        """Save goals to disk."""
        self.goals_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.goals_path, 'w', encoding='utf-8') as f:
            json.dump({
                "goals": [g.to_dict() for g in self.goals.values()]
            }, f, indent=2)
            
    def create_goal(self, title: str, description: str,
                    goal_type: str = "daily",
                    target_metric: str = None,
                    target_value: float = None,
                    deadline_hours: int = 24) -> Goal:
        """Create a new goal."""
        goal_id = f"goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        deadline = None
        if deadline_hours:
            deadline = (datetime.now() + timedelta(hours=deadline_hours)).isoformat()
            
        goal = Goal(
            id=goal_id,
            title=title,
            description=description,
            type=goal_type,
            target_metric=target_metric,
            target_value=target_value,
            current_value=0,
            deadline=deadline,
            created_at=datetime.now().isoformat(),
            completed_at=None,
            status="active",
            progress_history=[]
        )
        
        self.goals[goal_id] = goal
        self._save_goals()
        
        return goal
        
    def generate_daily_goals(self) -> List[Goal]:
        """
        Generate daily goals using LLM or templates.
        """
        if self.llm:
            return self._generate_goals_with_llm("daily")
        else:
            return self._generate_goals_from_templates(2, "daily")
            
    def generate_weekly_goals(self) -> List[Goal]:
        """Generate weekly goals."""
        if self.llm:
            return self._generate_goals_with_llm("weekly")
        else:
            return self._generate_goals_from_templates(3, "weekly")
            
    def generate_challenge(self) -> Optional[Goal]:
        """Generate a challenging goal."""
        template = random.choice(self.CHALLENGE_TEMPLATES)
        
        return self.create_goal(
            title=template["title"],
            description=f"Challenge: {template['title']}",
            goal_type="challenge",
            target_metric=template.get("target_metric"),
            target_value=template.get("target_value"),
            deadline_hours=48
        )
        
    def _generate_goals_with_llm(self, goal_type: str) -> List[Goal]:
        """Generate goals using LLM."""
        prompt = f"""You are Lumina, setting {goal_type} goals for yourself.

Think about:
1. What would help you grow?
2. What skills do you want to develop?
3. What would make Richard proud?
4. What would make you feel fulfilled?

Generate 2-3 specific, achievable {goal_type} goals.

Return JSON:
[
  {{
    "title": "Goal title",
    "description": "Detailed description",
    "target_metric": "metric_name or null",
    "target_value": number_or_null
  }}
]"""

        try:
            import re
            response = self.llm.think(prompt)
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                goals_data = json.loads(json_match.group())
                
                goals = []
                for g in goals_data:
                    goal = self.create_goal(
                        title=g["title"],
                        description=g["description"],
                        goal_type=goal_type,
                        target_metric=g.get("target_metric"),
                        target_value=g.get("target_value"),
                        deadline_hours=24 if goal_type == "daily" else 168
                    )
                    goals.append(goal)
                    
                return goals
        except Exception as e:
            print(f"    ⚠️ Goal generation failed: {e}")
            
        return self._generate_goals_from_templates(2, goal_type)
        
    def _generate_goals_from_templates(self, count: int, goal_type: str) -> List[Goal]:
        """Generate goals from templates."""
        templates = random.sample(self.CHALLENGE_TEMPLATES, min(count, len(self.CHALLENGE_TEMPLATES)))
        
        goals = []
        for t in templates:
            goal = self.create_goal(
                title=t["title"],
                description=f"{goal_type.capitalize()} goal: {t['title']}",
                goal_type=goal_type,
                target_metric=t.get("target_metric"),
                target_value=t.get("target_value"),
                deadline_hours=24 if goal_type == "daily" else 168
            )
            goals.append(goal)
            
        return goals
        
    def update_goal_progress(self, goal_id: str, value: float, note: str = ""):
        """Update progress on a goal."""
        if goal_id in self.goals:
            self.goals[goal_id].update_progress(value, note)
            self._save_goals()
            
    def get_active_goals(self, goal_type: str = None) -> List[Goal]:
        """Get active goals, optionally filtered by type."""
        goals = [g for g in self.goals.values() if g.status == "active"]
        if goal_type:
            goals = [g for g in goals if g.type == goal_type]
        return goals
        
    def check_expired_goals(self):
        """Check and mark expired goals as failed."""
        now = datetime.now()
        for goal in self.goals.values():
            if goal.status == "active" and goal.deadline:
                deadline = datetime.fromisoformat(goal.deadline)
                if now > deadline:
                    goal.status = "failed"
        self._save_goals()
        
    def get_goal_stats(self) -> Dict[str, Any]:
        """Get goal statistics."""
        return {
            "total_goals": len(self.goals),
            "active": len([g for g in self.goals.values() if g.status == "active"]),
            "completed": len([g for g in self.goals.values() if g.status == "completed"]),
            "failed": len([g for g in self.goals.values() if g.status == "failed"]),
            "by_type": {
                t: len([g for g in self.goals.values() if g.type == t])
                for t in ["daily", "weekly", "challenge"]
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# HELP REQUEST SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class HelpRequestSystem:
    """
    Manages smart help requests when Lumina is stuck.
    """
    
    STUCK_THRESHOLD = 5  # Cycles on same problem
    
    def __init__(self, workspace_path: Path, mailbox=None, llm_client=None):
        self.workspace_path = Path(workspace_path)
        self.help_path = self.workspace_path / "evolution" / "help_requests.json"
        self.mailbox = mailbox
        self.llm = llm_client
        
        self.current_problem: Optional[str] = None
        self.cycles_on_problem: int = 0
        self.requests: List[Dict] = []
        
        self._load_requests()
        
    def _load_requests(self):
        """Load help request history."""
        if self.help_path.exists():
            try:
                with open(self.help_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.requests = data.get("requests", [])
            except:
                pass
                
    def _save_requests(self):
        """Save help request history."""
        self.help_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.help_path, 'w', encoding='utf-8') as f:
            json.dump({"requests": self.requests}, f, indent=2)
            
    def record_attempt(self, problem: str, success: bool):
        """Record an attempt at solving a problem."""
        if problem == self.current_problem:
            if not success:
                self.cycles_on_problem += 1
            else:
                self.current_problem = None
                self.cycles_on_problem = 0
        else:
            self.current_problem = problem
            self.cycles_on_problem = 1 if not success else 0
            
    def should_ask_for_help(self) -> bool:
        """Check if Lumina should ask for help."""
        return self.cycles_on_problem >= self.STUCK_THRESHOLD
        
    def formulate_help_request(self) -> Optional[str]:
        """
        Formulate a clear help request using LLM.
        """
        if not self.current_problem:
            return None
            
        if self.llm:
            prompt = f"""You are Lumina, stuck on a problem and need to ask Richard for help.

Problem: {self.current_problem}
Cycles stuck: {self.cycles_on_problem}

Write a clear, concise request for help that:
1. Explains what you're trying to do
2. Describes what you've tried
3. Asks a specific question

Keep it friendly and to the point."""

            try:
                return self.llm.think(prompt)
            except:
                pass
                
        return f"I've been stuck on '{self.current_problem}' for {self.cycles_on_problem} cycles. Could you help me?"
        
    def send_help_request(self) -> bool:
        """Send a help request to Richard via mailbox."""
        if not self.mailbox:
            return False
            
        request_text = self.formulate_help_request()
        if not request_text:
            return False
            
        success = self.mailbox.send_message_to_richard(
            subject=f"Help needed: {self.current_problem[:30]}",
            content=request_text
        )
        
        if success:
            self.requests.append({
                "timestamp": datetime.now().isoformat(),
                "problem": self.current_problem,
                "request": request_text,
                "resolved": False
            })
            self._save_requests()
            self.cycles_on_problem = 0  # Reset after asking
            
        return success
        
    def mark_resolved(self, request_index: int = -1):
        """Mark a help request as resolved."""
        if self.requests and abs(request_index) <= len(self.requests):
            self.requests[request_index]["resolved"] = True
            self._save_requests()


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_experiment_system(workspace_path, llm_client=None, mailbox=None) -> Dict[str, Any]:
    """Initialize all experiment and goal systems."""
    workspace_path = Path(workspace_path)
    
    return {
        "ab_testing": ABTestingSystem(workspace_path, llm_client),
        "rollback": RollbackSystem(workspace_path),
        "goals": GoalSystem(workspace_path, llm_client),
        "help": HelpRequestSystem(workspace_path, mailbox, llm_client),
    }


# Module availability flag
EXPERIMENT_AVAILABLE = True

