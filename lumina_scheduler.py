#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA TASK SCHEDULER                                 ║
║                                                                               ║
║  Enables Lumina to manage her own schedule and goals autonomously.           ║
║  Includes task scheduling, goal decomposition, and progress tracking.        ║
║                                                                               ║
║  Features:                                                                     ║
║  - Cron-like task scheduling                                                  ║
║  - Goal decomposition (big goals -> actionable steps)                        ║
║  - Priority queue for tasks                                                   ║
║  - Time estimation and tracking                                               ║
║  - Progress reporting                                                         ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import sqlite3
import threading
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import heapq
import re

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS AND TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    URGENT = 5


class RecurrenceType(Enum):
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Task:
    """A scheduled task."""
    id: str
    name: str
    description: str
    action: str  # Action to execute
    priority: TaskPriority
    status: TaskStatus
    scheduled_at: datetime
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration: Optional[int] = None  # minutes
    actual_duration: Optional[int] = None
    recurrence: RecurrenceType = RecurrenceType.ONCE
    parent_goal_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    
    def __lt__(self, other):
        """For priority queue ordering."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value  # Higher priority first
        return self.scheduled_at < other.scheduled_at
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "action": self.action,
            "priority": self.priority.value,
            "status": self.status.value,
            "scheduled_at": self.scheduled_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "recurrence": self.recurrence.value,
            "parent_goal_id": self.parent_goal_id,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "result": self.result,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            action=data["action"],
            priority=TaskPriority(data["priority"]),
            status=TaskStatus(data["status"]),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            estimated_duration=data.get("estimated_duration"),
            actual_duration=data.get("actual_duration"),
            recurrence=RecurrenceType(data.get("recurrence", "once")),
            parent_goal_id=data.get("parent_goal_id"),
            dependencies=data.get("dependencies", []),
            tags=data.get("tags", []),
            result=data.get("result"),
            error=data.get("error")
        )


@dataclass
class Goal:
    """A high-level goal that can be decomposed into tasks."""
    id: str
    name: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tasks: List[str] = field(default_factory=list)  # Task IDs
    sub_goals: List[str] = field(default_factory=list)  # Sub-goal IDs
    parent_goal_id: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tasks": self.tasks,
            "sub_goals": self.sub_goals,
            "parent_goal_id": self.parent_goal_id,
            "progress": self.progress,
            "tags": self.tags,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Goal':
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            priority=TaskPriority(data["priority"]),
            status=TaskStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            tasks=data.get("tasks", []),
            sub_goals=data.get("sub_goals", []),
            parent_goal_id=data.get("parent_goal_id"),
            progress=data.get("progress", 0.0),
            tags=data.get("tags", []),
            notes=data.get("notes", "")
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK QUEUE
# ═══════════════════════════════════════════════════════════════════════════════

class TaskQueue:
    """Priority queue for tasks."""
    
    def __init__(self):
        self._queue: List[Task] = []
        self._index = 0
    
    def push(self, task: Task):
        """Add a task to the queue."""
        heapq.heappush(self._queue, task)
    
    def pop(self) -> Optional[Task]:
        """Remove and return the highest priority task."""
        if self._queue:
            return heapq.heappop(self._queue)
        return None
    
    def peek(self) -> Optional[Task]:
        """Return the highest priority task without removing."""
        if self._queue:
            return self._queue[0]
        return None
    
    def remove(self, task_id: str) -> bool:
        """Remove a task by ID."""
        for i, task in enumerate(self._queue):
            if task.id == task_id:
                self._queue.pop(i)
                heapq.heapify(self._queue)
                return True
        return False
    
    def get_ready_tasks(self) -> List[Task]:
        """Get all tasks that are ready to execute."""
        now = datetime.now()
        ready = [t for t in self._queue if t.scheduled_at <= now and t.status == TaskStatus.PENDING]
        return sorted(ready, reverse=True)  # Highest priority first
    
    def __len__(self) -> int:
        return len(self._queue)
    
    def __iter__(self):
        return iter(sorted(self._queue, reverse=True))


# ═══════════════════════════════════════════════════════════════════════════════
# GOAL DECOMPOSER
# ═══════════════════════════════════════════════════════════════════════════════

class GoalDecomposer:
    """Decomposes high-level goals into actionable tasks."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
        # Template decompositions for common goal types
        self.templates = {
            "learn": [
                "Research and gather resources about {topic}",
                "Read and summarize key concepts",
                "Practice with examples",
                "Create notes or documentation",
                "Test understanding through application"
            ],
            "create": [
                "Define the concept and requirements",
                "Gather inspiration and references",
                "Create initial draft/prototype",
                "Review and iterate",
                "Finalize and save"
            ],
            "improve": [
                "Analyze current state",
                "Identify specific areas for improvement",
                "Research best practices",
                "Implement changes",
                "Measure and evaluate results"
            ],
            "explore": [
                "Define scope of exploration",
                "Gather initial information",
                "Deep dive into interesting areas",
                "Document findings",
                "Synthesize insights"
            ]
        }
    
    def detect_goal_type(self, goal: Goal) -> str:
        """Detect the type of goal from its description."""
        text = f"{goal.name} {goal.description}".lower()
        
        if any(word in text for word in ["learn", "understand", "study", "master"]):
            return "learn"
        elif any(word in text for word in ["create", "make", "build", "generate", "write"]):
            return "create"
        elif any(word in text for word in ["improve", "enhance", "optimize", "fix"]):
            return "improve"
        elif any(word in text for word in ["explore", "discover", "investigate", "research"]):
            return "explore"
        else:
            return "explore"  # Default
    
    def decompose(self, goal: Goal) -> List[Dict]:
        """Decompose a goal into task descriptions."""
        goal_type = self.detect_goal_type(goal)
        template = self.templates.get(goal_type, self.templates["explore"])
        
        # Extract topic/subject from goal
        topic = goal.name
        
        tasks = []
        for i, task_template in enumerate(template):
            task_desc = task_template.format(topic=topic)
            tasks.append({
                "name": task_desc,
                "description": f"Step {i+1} for achieving: {goal.name}",
                "order": i,
                "estimated_duration": 30  # Default 30 minutes
            })
        
        return tasks
    
    def decompose_with_llm(self, goal: Goal) -> List[Dict]:
        """Use LLM to decompose a goal into tasks."""
        if not self.llm_client:
            return self.decompose(goal)
        
        try:
            prompt = f"""Break down this goal into 3-7 specific, actionable tasks:

Goal: {goal.name}
Description: {goal.description}
Deadline: {goal.deadline.isoformat() if goal.deadline else 'None'}

Return a JSON array of tasks with these fields:
- name: short task name
- description: what needs to be done
- estimated_duration: time in minutes
- priority: 1-5 (5 highest)

Return ONLY the JSON array, no other text."""

            response = self.llm_client.chat(
                model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7}
            )
            
            # Parse JSON from response
            content = response.message.content
            # Find JSON array in response
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                tasks = json.loads(match.group())
                return tasks
                
        except Exception as e:
            print(f"LLM decomposition failed: {e}")
        
        return self.decompose(goal)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class SchedulerEngine:
    """Core scheduling engine."""
    
    def __init__(self, db_path: Path, workspace_path: Path):
        self.db_path = db_path
        self.workspace_path = workspace_path
        self.schedule_path = workspace_path / "schedule"
        self.schedule_path.mkdir(parents=True, exist_ok=True)
        
        self.tasks: Dict[str, Task] = {}
        self.goals: Dict[str, Goal] = {}
        self.task_queue = TaskQueue()
        self.decomposer = GoalDecomposer()
        
        self.action_handlers: Dict[str, Callable] = {}
        self.running = False
        self._thread: Optional[threading.Thread] = None
        
        self._ensure_tables()
        self._load_data()
    
    def _ensure_tables(self):
        """Create scheduler tables."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_tasks (
                id TEXT PRIMARY KEY,
                data TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_goals (
                id TEXT PRIMARY KEY,
                data TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def _load_data(self):
        """Load tasks and goals from database."""
        conn = sqlite3.connect(str(self.db_path))
        
        # Load tasks
        cursor = conn.execute("SELECT id, data FROM scheduler_tasks")
        for row in cursor.fetchall():
            try:
                task = Task.from_dict(json.loads(row[1]))
                self.tasks[task.id] = task
                if task.status == TaskStatus.PENDING:
                    self.task_queue.push(task)
            except Exception as e:
                print(f"Error loading task {row[0]}: {e}")
        
        # Load goals
        cursor = conn.execute("SELECT id, data FROM scheduler_goals")
        for row in cursor.fetchall():
            try:
                goal = Goal.from_dict(json.loads(row[1]))
                self.goals[goal.id] = goal
            except Exception as e:
                print(f"Error loading goal {row[0]}: {e}")
        
        conn.close()
    
    def _save_task(self, task: Task):
        """Save a task to database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT OR REPLACE INTO scheduler_tasks (id, data) VALUES (?, ?)",
            (task.id, json.dumps(task.to_dict()))
        )
        conn.commit()
        conn.close()
    
    def _save_goal(self, goal: Goal):
        """Save a goal to database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT OR REPLACE INTO scheduler_goals (id, data) VALUES (?, ?)",
            (goal.id, json.dumps(goal.to_dict()))
        )
        conn.commit()
        conn.close()
    
    def register_action_handler(self, action: str, handler: Callable):
        """Register a handler for an action type."""
        self.action_handlers[action] = handler
    
    def create_task(self, name: str, description: str, action: str,
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   scheduled_at: datetime = None,
                   estimated_duration: int = None,
                   recurrence: RecurrenceType = RecurrenceType.ONCE,
                   parent_goal_id: str = None,
                   dependencies: List[str] = None,
                   tags: List[str] = None) -> Task:
        """Create a new task."""
        task_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]
        
        task = Task(
            id=task_id,
            name=name,
            description=description,
            action=action,
            priority=priority,
            status=TaskStatus.PENDING,
            scheduled_at=scheduled_at or datetime.now(),
            created_at=datetime.now(),
            estimated_duration=estimated_duration,
            recurrence=recurrence,
            parent_goal_id=parent_goal_id,
            dependencies=dependencies or [],
            tags=tags or []
        )
        
        self.tasks[task_id] = task
        self.task_queue.push(task)
        self._save_task(task)
        
        return task
    
    def create_goal(self, name: str, description: str,
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   deadline: datetime = None,
                   tags: List[str] = None,
                   decompose: bool = True) -> Tuple[Goal, List[Task]]:
        """Create a new goal and optionally decompose into tasks."""
        goal_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]
        
        goal = Goal(
            id=goal_id,
            name=name,
            description=description,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            deadline=deadline,
            tags=tags or []
        )
        
        self.goals[goal_id] = goal
        self._save_goal(goal)
        
        tasks = []
        if decompose:
            task_descriptions = self.decomposer.decompose(goal)
            
            for i, task_desc in enumerate(task_descriptions):
                # Schedule tasks sequentially
                scheduled = datetime.now() + timedelta(hours=i)
                
                task = self.create_task(
                    name=task_desc["name"],
                    description=task_desc["description"],
                    action="generic",
                    priority=priority,
                    scheduled_at=scheduled,
                    estimated_duration=task_desc.get("estimated_duration", 30),
                    parent_goal_id=goal_id,
                    tags=goal.tags
                )
                
                goal.tasks.append(task.id)
                tasks.append(task)
            
            self._save_goal(goal)
        
        return goal, tasks
    
    def update_task_status(self, task_id: str, status: TaskStatus,
                          result: str = None, error: str = None) -> Optional[Task]:
        """Update a task's status."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        task.status = status
        
        if status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.now()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task.completed_at = datetime.now()
            if task.started_at:
                task.actual_duration = int((task.completed_at - task.started_at).total_seconds() / 60)
            task.result = result
            task.error = error
            
            # Handle recurrence
            if status == TaskStatus.COMPLETED and task.recurrence != RecurrenceType.ONCE:
                self._schedule_next_recurrence(task)
            
            # Update parent goal progress
            if task.parent_goal_id:
                self._update_goal_progress(task.parent_goal_id)
        
        self._save_task(task)
        return task
    
    def _schedule_next_recurrence(self, task: Task):
        """Schedule the next occurrence of a recurring task."""
        intervals = {
            RecurrenceType.HOURLY: timedelta(hours=1),
            RecurrenceType.DAILY: timedelta(days=1),
            RecurrenceType.WEEKLY: timedelta(weeks=1),
            RecurrenceType.MONTHLY: timedelta(days=30)
        }
        
        interval = intervals.get(task.recurrence)
        if interval:
            next_task = self.create_task(
                name=task.name,
                description=task.description,
                action=task.action,
                priority=task.priority,
                scheduled_at=datetime.now() + interval,
                estimated_duration=task.estimated_duration,
                recurrence=task.recurrence,
                parent_goal_id=task.parent_goal_id,
                tags=task.tags
            )
    
    def _update_goal_progress(self, goal_id: str):
        """Update goal progress based on completed tasks."""
        if goal_id not in self.goals:
            return
        
        goal = self.goals[goal_id]
        if not goal.tasks:
            return
        
        completed = sum(1 for tid in goal.tasks 
                       if tid in self.tasks and 
                       self.tasks[tid].status == TaskStatus.COMPLETED)
        
        goal.progress = completed / len(goal.tasks)
        
        if goal.progress >= 1.0:
            goal.status = TaskStatus.COMPLETED
            goal.completed_at = datetime.now()
        elif completed > 0:
            goal.status = TaskStatus.IN_PROGRESS
        
        self._save_goal(goal)
    
    def get_next_task(self) -> Optional[Task]:
        """Get the next task to execute."""
        ready_tasks = self.task_queue.get_ready_tasks()
        
        for task in ready_tasks:
            # Check dependencies
            if task.dependencies:
                deps_complete = all(
                    self.tasks.get(dep_id, Task(
                        id="", name="", description="", action="",
                        priority=TaskPriority.MEDIUM, status=TaskStatus.COMPLETED,
                        scheduled_at=datetime.now(), created_at=datetime.now()
                    )).status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                if not deps_complete:
                    continue
            
            return task
        
        return None
    
    def execute_task(self, task: Task) -> bool:
        """Execute a task."""
        self.update_task_status(task.id, TaskStatus.IN_PROGRESS)
        
        try:
            handler = self.action_handlers.get(task.action)
            if handler:
                result = handler(task)
                self.update_task_status(task.id, TaskStatus.COMPLETED, result=str(result))
                return True
            else:
                # No handler - just mark as complete
                self.update_task_status(task.id, TaskStatus.COMPLETED, result="No handler defined")
                return True
                
        except Exception as e:
            self.update_task_status(task.id, TaskStatus.FAILED, error=str(e))
            return False
    
    def run_scheduler_loop(self, interval: float = 60.0):
        """Run the scheduler loop in a thread."""
        def loop():
            while self.running:
                task = self.get_next_task()
                if task:
                    self.execute_task(task)
                time.sleep(interval)
        
        self.running = True
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
    
    def stop_scheduler(self):
        """Stop the scheduler loop."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5.0)
    
    def get_daily_schedule(self, date: datetime = None) -> List[Task]:
        """Get all tasks scheduled for a day."""
        if date is None:
            date = datetime.now()
        
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        return [
            task for task in self.tasks.values()
            if start <= task.scheduled_at < end
        ]
    
    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks."""
        return [task for task in self.tasks.values() if task.status == TaskStatus.PENDING]
    
    def get_active_goals(self) -> List[Goal]:
        """Get all active (non-completed) goals."""
        return [goal for goal in self.goals.values() 
                if goal.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
    
    def get_stats(self) -> Dict:
        """Get scheduler statistics."""
        tasks_by_status = {}
        for task in self.tasks.values():
            status = task.status.value
            tasks_by_status[status] = tasks_by_status.get(status, 0) + 1
        
        goals_by_status = {}
        for goal in self.goals.values():
            status = goal.status.value
            goals_by_status[status] = goals_by_status.get(status, 0) + 1
        
        # Calculate velocity (tasks completed in last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        velocity = sum(
            1 for task in self.tasks.values()
            if task.completed_at and task.completed_at > week_ago
        )
        
        return {
            "total_tasks": len(self.tasks),
            "total_goals": len(self.goals),
            "tasks_by_status": tasks_by_status,
            "goals_by_status": goals_by_status,
            "pending_count": len(self.get_pending_tasks()),
            "weekly_velocity": velocity,
            "scheduler_running": self.running
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA SCHEDULER INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaScheduler:
    """Lumina's task scheduling interface."""
    
    def __init__(self, db_path: Path, workspace_path: Path):
        self.engine = SchedulerEngine(db_path, workspace_path)
        
        print(f"    📅 Scheduler: {len(self.engine.tasks)} tasks, {len(self.engine.goals)} goals")
    
    def schedule_task(self, name: str, description: str, action: str = "generic",
                     when: datetime = None, priority: int = 3,
                     duration: int = 30, recurring: str = "once") -> Task:
        """Schedule a new task."""
        return self.engine.create_task(
            name=name,
            description=description,
            action=action,
            priority=TaskPriority(priority),
            scheduled_at=when or datetime.now(),
            estimated_duration=duration,
            recurrence=RecurrenceType(recurring)
        )
    
    def set_goal(self, name: str, description: str, deadline: datetime = None,
                priority: int = 3, decompose: bool = True) -> Tuple[Goal, List[Task]]:
        """Set a new goal."""
        return self.engine.create_goal(
            name=name,
            description=description,
            priority=TaskPriority(priority),
            deadline=deadline,
            decompose=decompose
        )
    
    def get_next_task(self) -> Optional[Task]:
        """Get the next task to work on."""
        return self.engine.get_next_task()
    
    def complete_task(self, task_id: str, result: str = None) -> Optional[Task]:
        """Mark a task as completed."""
        return self.engine.update_task_status(task_id, TaskStatus.COMPLETED, result=result)
    
    def fail_task(self, task_id: str, error: str = None) -> Optional[Task]:
        """Mark a task as failed."""
        return self.engine.update_task_status(task_id, TaskStatus.FAILED, error=error)
    
    def get_todays_tasks(self) -> List[Task]:
        """Get today's scheduled tasks."""
        return self.engine.get_daily_schedule()
    
    def get_active_goals(self) -> List[Goal]:
        """Get all active goals."""
        return self.engine.get_active_goals()
    
    def register_handler(self, action: str, handler: Callable):
        """Register a task action handler."""
        self.engine.register_action_handler(action, handler)
    
    def start(self, interval: float = 60.0):
        """Start the scheduler."""
        self.engine.run_scheduler_loop(interval)
    
    def stop(self):
        """Stop the scheduler."""
        self.engine.stop_scheduler()
    
    def get_stats(self) -> Dict:
        """Get scheduler statistics."""
        return self.engine.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_scheduler(db_path: Path, workspace_path: Path) -> LuminaScheduler:
    """Initialize Lumina's scheduler."""
    return LuminaScheduler(db_path, workspace_path)


SCHEDULER_AVAILABLE = True


if __name__ == "__main__":
    # Test the scheduler
    db_path = Path("mind.db")
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    scheduler = initialize_scheduler(db_path, workspace)
    
    print("\n" + "=" * 50)
    print("Scheduler Test")
    print("=" * 50)
    
    # Create a goal
    print("\n1. Creating a goal...")
    goal, tasks = scheduler.set_goal(
        name="Learn about quantum computing",
        description="Understand the basics of quantum computing and its applications",
        priority=4
    )
    print(f"   Created goal: {goal.name}")
    print(f"   Decomposed into {len(tasks)} tasks:")
    for task in tasks:
        print(f"     - {task.name}")
    
    # Schedule a standalone task
    print("\n2. Scheduling a standalone task...")
    task = scheduler.schedule_task(
        name="Morning reflection",
        description="Reflect on yesterday's experiences",
        action="reflect",
        when=datetime.now() + timedelta(hours=1),
        priority=3,
        recurring="daily"
    )
    print(f"   Scheduled: {task.name}")
    
    # Get today's tasks
    print("\n3. Today's tasks:")
    for task in scheduler.get_todays_tasks():
        print(f"   - [{task.priority.name}] {task.name} @ {task.scheduled_at.strftime('%H:%M')}")
    
    print("\n" + "=" * 50)
    print("Stats:", scheduler.get_stats())

