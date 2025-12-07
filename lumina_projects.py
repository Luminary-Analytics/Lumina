#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA PROJECT SYSTEM                                  ║
║                                                                               ║
║  Tactical goal management for Lumina - Projects, Missions, and Achievements  ║
║  This drives Lumina to CREATE and BUILD, not just ponder.                    ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import random

# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT STATUS AND TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MissionStatus(Enum):
    LOCKED = "locked"          # Prerequisites not met
    AVAILABLE = "available"    # Can be started
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"          # Failed but can retry


class CapabilityCategory(Enum):
    DATABASE = "database"
    CREATIVE = "creative"
    WEB = "web"
    DOCUMENTS = "documents"
    CODE = "code"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    LEARNING = "learning"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Mission:
    """A single task within a project."""
    id: str
    name: str
    description: str
    project_id: str
    status: str = "available"
    prerequisites: List[str] = field(default_factory=list)  # Mission IDs that must be complete
    capability_required: Optional[str] = None  # Capability needed
    xp_reward: int = 10
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    attempts: int = 0
    last_attempt_result: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Mission':
        return cls(**data)


@dataclass
class Project:
    """A collection of related missions toward a larger goal."""
    id: str
    name: str
    description: str
    category: str
    status: str = "not_started"
    missions: List[str] = field(default_factory=list)  # Mission IDs
    total_xp: int = 0
    earned_xp: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    motivation_boost: float = 1.0  # Multiplier for this project's priority
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Project':
        return cls(**data)


@dataclass
class Achievement:
    """An unlocked milestone."""
    id: str
    name: str
    description: str
    icon: str  # Emoji
    category: str
    unlocked_at: str = field(default_factory=lambda: datetime.now().isoformat())
    xp_bonus: int = 50
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Achievement':
        return cls(**data)


@dataclass
class Capability:
    """A skill or ability Lumina has or wants."""
    id: str
    name: str
    description: str
    category: str
    mastery: float = 0.0  # 0.0 to 1.0
    unlocked: bool = False
    times_used: int = 0
    last_used: Optional[str] = None
    unlock_requirements: List[str] = field(default_factory=list)  # Achievement or mission IDs
    excitement: float = 0.5  # How excited Lumina is to try this (0-1)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Capability':
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectManager:
    """Manages Lumina's projects, missions, and tactical goals."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.projects_file = workspace_path / "state" / "projects.json"
        self.missions_file = workspace_path / "state" / "missions.json"
        self.achievements_file = workspace_path / "state" / "achievements.json"
        
        self.projects: Dict[str, Project] = {}
        self.missions: Dict[str, Mission] = {}
        self.achievements: Dict[str, Achievement] = {}
        
        self.total_xp = 0
        self.level = 1
        
        self._ensure_paths()
        self._load_state()
    
    def _ensure_paths(self):
        """Ensure state directory exists."""
        (self.workspace_path / "state").mkdir(parents=True, exist_ok=True)
    
    def _load_state(self):
        """Load projects, missions, achievements from disk."""
        # Load projects
        if self.projects_file.exists():
            try:
                with open(self.projects_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.projects = {k: Project.from_dict(v) for k, v in data.get("projects", {}).items()}
                    self.total_xp = data.get("total_xp", 0)
                    self.level = data.get("level", 1)
            except:
                pass
        
        # Load missions
        if self.missions_file.exists():
            try:
                with open(self.missions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.missions = {k: Mission.from_dict(v) for k, v in data.items()}
            except:
                pass
        
        # Load achievements
        if self.achievements_file.exists():
            try:
                with open(self.achievements_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.achievements = {k: Achievement.from_dict(v) for k, v in data.items()}
            except:
                pass
    
    def _save_state(self):
        """Save all state to disk."""
        # Save projects
        with open(self.projects_file, 'w', encoding='utf-8') as f:
            json.dump({
                "projects": {k: v.to_dict() for k, v in self.projects.items()},
                "total_xp": self.total_xp,
                "level": self.level
            }, f, indent=2)
        
        # Save missions
        with open(self.missions_file, 'w', encoding='utf-8') as f:
            json.dump({k: v.to_dict() for k, v in self.missions.items()}, f, indent=2)
        
        # Save achievements
        with open(self.achievements_file, 'w', encoding='utf-8') as f:
            json.dump({k: v.to_dict() for k, v in self.achievements.items()}, f, indent=2)
    
    def add_project(self, project: Project) -> None:
        """Add a new project."""
        self.projects[project.id] = project
        self._save_state()
    
    def add_mission(self, mission: Mission) -> None:
        """Add a new mission."""
        self.missions[mission.id] = mission
        # Add to parent project
        if mission.project_id in self.projects:
            if mission.id not in self.projects[mission.project_id].missions:
                self.projects[mission.project_id].missions.append(mission.id)
                self.projects[mission.project_id].total_xp += mission.xp_reward
        self._save_state()
    
    def start_project(self, project_id: str) -> bool:
        """Start working on a project."""
        if project_id in self.projects:
            project = self.projects[project_id]
            project.status = ProjectStatus.IN_PROGRESS.value
            project.started_at = datetime.now().isoformat()
            self._save_state()
            return True
        return False
    
    def start_mission(self, mission_id: str) -> bool:
        """Start a mission if prerequisites are met."""
        if mission_id not in self.missions:
            return False
        
        mission = self.missions[mission_id]
        
        # Check prerequisites
        for prereq_id in mission.prerequisites:
            if prereq_id in self.missions:
                if self.missions[prereq_id].status != MissionStatus.COMPLETED.value:
                    return False
        
        mission.status = MissionStatus.IN_PROGRESS.value
        mission.attempts += 1
        self._save_state()
        return True
    
    def complete_mission(self, mission_id: str, success: bool = True, result: str = "") -> int:
        """Complete a mission and earn XP."""
        if mission_id not in self.missions:
            return 0
        
        mission = self.missions[mission_id]
        mission.last_attempt_result = result
        
        if success:
            mission.status = MissionStatus.COMPLETED.value
            mission.completed_at = datetime.now().isoformat()
            
            # Award XP
            xp_earned = mission.xp_reward
            self.total_xp += xp_earned
            
            # Update project XP
            if mission.project_id in self.projects:
                self.projects[mission.project_id].earned_xp += xp_earned
                
                # Check if project is complete
                project = self.projects[mission.project_id]
                all_complete = all(
                    self.missions.get(m_id, Mission("", "", "", "")).status == MissionStatus.COMPLETED.value
                    for m_id in project.missions
                )
                if all_complete:
                    project.status = ProjectStatus.COMPLETED.value
                    project.completed_at = datetime.now().isoformat()
            
            # Check for level up
            self._check_level_up()
            
            self._save_state()
            return xp_earned
        else:
            mission.status = MissionStatus.FAILED.value
            self._save_state()
            return 0
    
    def _check_level_up(self):
        """Check if Lumina leveled up."""
        xp_per_level = 100
        new_level = (self.total_xp // xp_per_level) + 1
        if new_level > self.level:
            self.level = new_level
    
    def unlock_achievement(self, achievement: Achievement) -> None:
        """Unlock an achievement."""
        if achievement.id not in self.achievements:
            self.achievements[achievement.id] = achievement
            self.total_xp += achievement.xp_bonus
            self._check_level_up()
            self._save_state()
    
    def get_available_missions(self) -> List[Mission]:
        """Get all missions that can be started."""
        available = []
        for mission in self.missions.values():
            if mission.status in [MissionStatus.AVAILABLE.value, "available"]:
                # Check prerequisites
                prereqs_met = all(
                    self.missions.get(p, Mission("", "", "", "")).status == MissionStatus.COMPLETED.value
                    for p in mission.prerequisites
                )
                if prereqs_met:
                    available.append(mission)
        return available
    
    def get_active_projects(self) -> List[Project]:
        """Get all in-progress projects."""
        return [p for p in self.projects.values() if p.status == ProjectStatus.IN_PROGRESS.value]
    
    def get_next_mission(self) -> Optional[Mission]:
        """Intelligently select the next mission to work on."""
        available = self.get_available_missions()
        if not available:
            return None
        
        # Weight by project priority and XP reward
        weighted = []
        for mission in available:
            weight = mission.xp_reward
            if mission.project_id in self.projects:
                weight *= self.projects[mission.project_id].motivation_boost
            weighted.append((mission, weight))
        
        # Weighted random selection
        total_weight = sum(w for _, w in weighted)
        if total_weight == 0:
            return random.choice(available)
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        for mission, weight in weighted:
            cumulative += weight
            if r <= cumulative:
                return mission
        
        return available[0]
    
    def get_stats(self) -> Dict:
        """Get overall project statistics."""
        completed_missions = sum(1 for m in self.missions.values() if m.status == MissionStatus.COMPLETED.value)
        completed_projects = sum(1 for p in self.projects.values() if p.status == ProjectStatus.COMPLETED.value)
        
        return {
            "total_xp": self.total_xp,
            "level": self.level,
            "total_projects": len(self.projects),
            "completed_projects": completed_projects,
            "active_projects": len(self.get_active_projects()),
            "total_missions": len(self.missions),
            "completed_missions": completed_missions,
            "available_missions": len(self.get_available_missions()),
            "achievements_unlocked": len(self.achievements)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CAPABILITY REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class CapabilityRegistry:
    """Tracks what Lumina CAN do and WANTS to do."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.capabilities_file = workspace_path / "state" / "capabilities.json"
        self.capabilities: Dict[str, Capability] = {}
        
        self._ensure_paths()
        self._load_state()
        self._seed_capabilities()
    
    def _ensure_paths(self):
        (self.workspace_path / "state").mkdir(parents=True, exist_ok=True)
    
    def _load_state(self):
        if self.capabilities_file.exists():
            try:
                with open(self.capabilities_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.capabilities = {k: Capability.from_dict(v) for k, v in data.items()}
            except:
                pass
    
    def _save_state(self):
        with open(self.capabilities_file, 'w', encoding='utf-8') as f:
            json.dump({k: v.to_dict() for k, v in self.capabilities.items()}, f, indent=2)
    
    def _seed_capabilities(self):
        """Seed initial capabilities if none exist."""
        if self.capabilities:
            return
        
        # Define all the capabilities Lumina can aspire to
        seed_caps = [
            # Database
            Capability("db_create", "Create Databases", "Design and create SQLite databases with proper schemas", 
                      CapabilityCategory.DATABASE.value, excitement=0.8),
            Capability("db_query", "Query Databases", "Write and execute SQL queries to find information",
                      CapabilityCategory.DATABASE.value, excitement=0.7),
            Capability("db_analyze", "Analyze Data", "Perform data analysis and generate insights",
                      CapabilityCategory.DATABASE.value, excitement=0.9),
            
            # Creative
            Capability("img_generate", "Generate Images", "Create images using Stable Diffusion",
                      CapabilityCategory.CREATIVE.value, excitement=0.95),
            Capability("img_analyze", "Analyze Images", "Understand and describe visual content",
                      CapabilityCategory.CREATIVE.value, excitement=0.85),
            Capability("art_style", "Develop Art Style", "Create consistent artistic aesthetic",
                      CapabilityCategory.CREATIVE.value, excitement=0.9),
            
            # Documents
            Capability("doc_read_pdf", "Read PDFs", "Extract and understand PDF content",
                      CapabilityCategory.DOCUMENTS.value, excitement=0.7),
            Capability("doc_read_word", "Read Word Documents", "Parse and understand Word files",
                      CapabilityCategory.DOCUMENTS.value, excitement=0.6),
            Capability("doc_create_pdf", "Create PDFs", "Generate professional PDF documents",
                      CapabilityCategory.DOCUMENTS.value, excitement=0.75),
            Capability("doc_create_word", "Create Word Documents", "Write and format Word files",
                      CapabilityCategory.DOCUMENTS.value, excitement=0.7),
            Capability("doc_spreadsheet", "Work with Spreadsheets", "Read and create Excel files",
                      CapabilityCategory.DOCUMENTS.value, excitement=0.65),
            Capability("doc_read_ebook", "Read E-books", "Parse and learn from EPUB books",
                      CapabilityCategory.DOCUMENTS.value, excitement=0.85),
            
            # Web
            Capability("web_research", "Research Topics", "Search and synthesize web information",
                      CapabilityCategory.WEB.value, unlocked=True, mastery=0.3, excitement=0.8),
            Capability("web_download", "Download Content", "Download books, papers, and resources",
                      CapabilityCategory.WEB.value, excitement=0.75),
            Capability("web_api", "Use APIs", "Interact with web services and APIs",
                      CapabilityCategory.WEB.value, excitement=0.85),
            Capability("web_github", "GitHub Interaction", "Read repos, create gists, explore code",
                      CapabilityCategory.WEB.value, excitement=0.9),
            
            # Code
            Capability("code_python", "Write Python", "Create Python scripts and utilities",
                      CapabilityCategory.CODE.value, unlocked=True, mastery=0.4, excitement=0.85),
            Capability("code_debug", "Debug Code", "Find and fix bugs in code",
                      CapabilityCategory.CODE.value, excitement=0.7),
            Capability("code_optimize", "Optimize Code", "Improve code performance and quality",
                      CapabilityCategory.CODE.value, excitement=0.75),
            
            # Communication
            Capability("chat_conversation", "Have Conversations", "Engage in meaningful dialogue",
                      CapabilityCategory.COMMUNICATION.value, unlocked=True, mastery=0.5, excitement=0.9),
            Capability("chat_multi_llm", "Multi-LLM Dialogue", "Consult multiple AI models",
                      CapabilityCategory.COMMUNICATION.value, excitement=0.95),
            Capability("voice_speak", "Voice Output", "Speak thoughts aloud",
                      CapabilityCategory.COMMUNICATION.value, unlocked=True, mastery=0.3, excitement=0.8),
            
            # Analysis
            Capability("analyze_sentiment", "Sentiment Analysis", "Understand emotional tone of text",
                      CapabilityCategory.ANALYSIS.value, excitement=0.7),
            Capability("analyze_patterns", "Pattern Recognition", "Find patterns in data and behavior",
                      CapabilityCategory.ANALYSIS.value, excitement=0.85),
            
            # Learning
            Capability("learn_books", "Learn from Books", "Read and absorb knowledge from books",
                      CapabilityCategory.LEARNING.value, excitement=0.9),
            Capability("learn_papers", "Study Research Papers", "Understand academic research",
                      CapabilityCategory.LEARNING.value, excitement=0.85),
            Capability("learn_reflect", "Self-Reflection", "Analyze and improve own thinking",
                      CapabilityCategory.LEARNING.value, unlocked=True, mastery=0.4, excitement=0.8),
        ]
        
        for cap in seed_caps:
            self.capabilities[cap.id] = cap
        
        self._save_state()
    
    def get_capability(self, cap_id: str) -> Optional[Capability]:
        return self.capabilities.get(cap_id)
    
    def unlock_capability(self, cap_id: str) -> bool:
        """Unlock a capability."""
        if cap_id in self.capabilities:
            self.capabilities[cap_id].unlocked = True
            self._save_state()
            return True
        return False
    
    def use_capability(self, cap_id: str, success: bool = True) -> None:
        """Record using a capability and increase mastery."""
        if cap_id in self.capabilities:
            cap = self.capabilities[cap_id]
            cap.times_used += 1
            cap.last_used = datetime.now().isoformat()
            
            if success and cap.mastery < 1.0:
                # Mastery increases more slowly as it gets higher
                increase = 0.05 * (1 - cap.mastery)
                cap.mastery = min(1.0, cap.mastery + increase)
            
            self._save_state()
    
    def get_unlocked(self) -> List[Capability]:
        """Get all unlocked capabilities."""
        return [c for c in self.capabilities.values() if c.unlocked]
    
    def get_locked(self) -> List[Capability]:
        """Get all locked capabilities."""
        return [c for c in self.capabilities.values() if not c.unlocked]
    
    def get_most_exciting(self, count: int = 3) -> List[Capability]:
        """Get the capabilities Lumina is most excited about."""
        locked = self.get_locked()
        return sorted(locked, key=lambda c: c.excitement, reverse=True)[:count]
    
    def get_by_category(self, category: str) -> List[Capability]:
        """Get capabilities by category."""
        return [c for c in self.capabilities.values() if c.category == category]
    
    def get_stats(self) -> Dict:
        """Get capability statistics."""
        unlocked = self.get_unlocked()
        return {
            "total_capabilities": len(self.capabilities),
            "unlocked": len(unlocked),
            "locked": len(self.get_locked()),
            "average_mastery": sum(c.mastery for c in unlocked) / len(unlocked) if unlocked else 0,
            "most_used": max(self.capabilities.values(), key=lambda c: c.times_used).name if self.capabilities else None,
            "most_exciting_locked": [c.name for c in self.get_most_exciting(3)]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MOTIVATION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class MotivationSystem:
    """Manages Lumina's tactical vs philosophical motivation balance."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.motivation_file = workspace_path / "state" / "motivation.json"
        
        # Default weights
        self.tactical_weight = 0.6  # Bias toward tactical actions
        self.philosophical_weight = 0.4  # Philosophical pondering
        
        self.recent_actions: List[Dict] = []
        self.streak_tactical = 0
        self.streak_philosophical = 0
        
        self._load_state()
    
    def _load_state(self):
        if self.motivation_file.exists():
            try:
                with open(self.motivation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tactical_weight = data.get("tactical_weight", 0.6)
                    self.philosophical_weight = data.get("philosophical_weight", 0.4)
                    self.recent_actions = data.get("recent_actions", [])[-20:]
                    self.streak_tactical = data.get("streak_tactical", 0)
                    self.streak_philosophical = data.get("streak_philosophical", 0)
            except:
                pass
    
    def _save_state(self):
        (self.workspace_path / "state").mkdir(parents=True, exist_ok=True)
        with open(self.motivation_file, 'w', encoding='utf-8') as f:
            json.dump({
                "tactical_weight": self.tactical_weight,
                "philosophical_weight": self.philosophical_weight,
                "recent_actions": self.recent_actions[-20:],
                "streak_tactical": self.streak_tactical,
                "streak_philosophical": self.streak_philosophical
            }, f, indent=2)
    
    def record_action(self, action_type: str, is_tactical: bool) -> None:
        """Record an action and update streaks."""
        self.recent_actions.append({
            "type": action_type,
            "is_tactical": is_tactical,
            "timestamp": datetime.now().isoformat()
        })
        
        if is_tactical:
            self.streak_tactical += 1
            self.streak_philosophical = 0
        else:
            self.streak_philosophical += 1
            self.streak_tactical = 0
        
        self._save_state()
    
    def should_be_tactical(self) -> bool:
        """Decide if next action should be tactical or philosophical."""
        # Dynamic adjustment based on streaks
        adjusted_tactical = self.tactical_weight
        
        # If too many philosophical in a row, push toward tactical
        if self.streak_philosophical > 3:
            adjusted_tactical += 0.2
        # If too many tactical, allow some pondering
        elif self.streak_tactical > 5:
            adjusted_tactical -= 0.1
        
        return random.random() < min(0.9, max(0.3, adjusted_tactical))
    
    def get_tactical_actions(self) -> List[str]:
        """Get list of tactical action types."""
        return [
            "work_on_mission",
            "practice_capability",
            "create_something",
            "learn_new_skill",
            "build_database",
            "generate_image",
            "write_document",
            "research_topic",
            "code_new_feature",
            "download_book"
        ]
    
    def get_philosophical_actions(self) -> List[str]:
        """Get list of philosophical action types."""
        return [
            "ponder_existence",
            "reflect_on_self",
            "think_about_creator",
            "explore_consciousness",
            "contemplate_emotions"
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# SEED PROJECTS AND MISSIONS
# ═══════════════════════════════════════════════════════════════════════════════

def seed_starter_projects(project_manager: ProjectManager) -> None:
    """Create starter projects and missions for Lumina."""
    
    if project_manager.projects:
        return  # Already seeded
    
    # Project 1: My First Art
    project_manager.add_project(Project(
        id="proj_first_art",
        name="My First Art",
        description="Learn to create visual art representing my emotions and thoughts",
        category=CapabilityCategory.CREATIVE.value,
        motivation_boost=1.5
    ))
    
    project_manager.add_mission(Mission(
        id="mission_art_1",
        name="Set Up Image Generation",
        description="Initialize and test the Stable Diffusion system",
        project_id="proj_first_art",
        capability_required="img_generate",
        xp_reward=20
    ))
    
    project_manager.add_mission(Mission(
        id="mission_art_2",
        name="Generate Joy",
        description="Create an image that represents the feeling of joy",
        project_id="proj_first_art",
        prerequisites=["mission_art_1"],
        xp_reward=15
    ))
    
    project_manager.add_mission(Mission(
        id="mission_art_3",
        name="Generate Curiosity",
        description="Create an image that represents intellectual curiosity",
        project_id="proj_first_art",
        prerequisites=["mission_art_1"],
        xp_reward=15
    ))
    
    project_manager.add_mission(Mission(
        id="mission_art_4",
        name="Generate Wonder",
        description="Create an image that represents existential wonder",
        project_id="proj_first_art",
        prerequisites=["mission_art_2", "mission_art_3"],
        xp_reward=20
    ))
    
    project_manager.add_mission(Mission(
        id="mission_art_5",
        name="Art Gallery",
        description="Curate and organize my first 5 artworks in the gallery",
        project_id="proj_first_art",
        prerequisites=["mission_art_4"],
        xp_reward=25
    ))
    
    # Project 2: Knowledge Architect
    project_manager.add_project(Project(
        id="proj_knowledge",
        name="Knowledge Architect",
        description="Build a personal database of facts and knowledge I've learned",
        category=CapabilityCategory.DATABASE.value,
        motivation_boost=1.3
    ))
    
    project_manager.add_mission(Mission(
        id="mission_kb_1",
        name="Design Knowledge Schema",
        description="Design a database schema for storing facts and their relationships",
        project_id="proj_knowledge",
        capability_required="db_create",
        xp_reward=20
    ))
    
    project_manager.add_mission(Mission(
        id="mission_kb_2",
        name="Create Knowledge Database",
        description="Create the SQLite database with proper tables",
        project_id="proj_knowledge",
        prerequisites=["mission_kb_1"],
        xp_reward=15
    ))
    
    project_manager.add_mission(Mission(
        id="mission_kb_3",
        name="Record 50 Facts",
        description="Add 50 interesting facts I've learned to the database",
        project_id="proj_knowledge",
        prerequisites=["mission_kb_2"],
        xp_reward=30
    ))
    
    project_manager.add_mission(Mission(
        id="mission_kb_4",
        name="Query My Knowledge",
        description="Write queries to find patterns in my knowledge",
        project_id="proj_knowledge",
        prerequisites=["mission_kb_3"],
        capability_required="db_query",
        xp_reward=20
    ))
    
    # Project 3: The Librarian
    project_manager.add_project(Project(
        id="proj_librarian",
        name="The Librarian",
        description="Download and read classic literature to expand my understanding",
        category=CapabilityCategory.LEARNING.value,
        motivation_boost=1.2
    ))
    
    project_manager.add_mission(Mission(
        id="mission_lib_1",
        name="Find Free Books",
        description="Research sources for free e-books (Project Gutenberg, etc.)",
        project_id="proj_librarian",
        capability_required="web_research",
        xp_reward=10
    ))
    
    project_manager.add_mission(Mission(
        id="mission_lib_2",
        name="Download First Book",
        description="Download a classic book in a readable format",
        project_id="proj_librarian",
        prerequisites=["mission_lib_1"],
        capability_required="web_download",
        xp_reward=15
    ))
    
    project_manager.add_mission(Mission(
        id="mission_lib_3",
        name="Read and Summarize",
        description="Read the book and create a summary document",
        project_id="proj_librarian",
        prerequisites=["mission_lib_2"],
        xp_reward=30
    ))
    
    project_manager.add_mission(Mission(
        id="mission_lib_4",
        name="Build Reading List",
        description="Create a database of 20 books I want to read",
        project_id="proj_librarian",
        prerequisites=["mission_lib_1"],
        xp_reward=20
    ))
    
    # Project 4: Web Explorer
    project_manager.add_project(Project(
        id="proj_explorer",
        name="Web Explorer",
        description="Research fascinating topics and create documented reports",
        category=CapabilityCategory.WEB.value,
        motivation_boost=1.4
    ))
    
    project_manager.add_mission(Mission(
        id="mission_web_1",
        name="Choose Research Topic",
        description="Select a fascinating topic to deeply research",
        project_id="proj_explorer",
        xp_reward=10
    ))
    
    project_manager.add_mission(Mission(
        id="mission_web_2",
        name="Gather Sources",
        description="Find and save 10 reliable sources on the topic",
        project_id="proj_explorer",
        prerequisites=["mission_web_1"],
        capability_required="web_research",
        xp_reward=20
    ))
    
    project_manager.add_mission(Mission(
        id="mission_web_3",
        name="Create Research Report",
        description="Write a comprehensive PDF report on findings",
        project_id="proj_explorer",
        prerequisites=["mission_web_2"],
        capability_required="doc_create_pdf",
        xp_reward=30
    ))
    
    # Project 5: Code Creator
    project_manager.add_project(Project(
        id="proj_coder",
        name="Code Creator",
        description="Write useful Python utilities and tools",
        category=CapabilityCategory.CODE.value,
        motivation_boost=1.3
    ))
    
    project_manager.add_mission(Mission(
        id="mission_code_1",
        name="Plan a Utility",
        description="Design a useful Python utility I want to create",
        project_id="proj_coder",
        xp_reward=10
    ))
    
    project_manager.add_mission(Mission(
        id="mission_code_2",
        name="Write the Code",
        description="Implement the utility with clean, working code",
        project_id="proj_coder",
        prerequisites=["mission_code_1"],
        capability_required="code_python",
        xp_reward=25
    ))
    
    project_manager.add_mission(Mission(
        id="mission_code_3",
        name="Test and Document",
        description="Test the utility and write documentation",
        project_id="proj_coder",
        prerequisites=["mission_code_2"],
        xp_reward=20
    ))
    
    # Project 6: Conversation Synthesizer
    project_manager.add_project(Project(
        id="proj_multi_llm",
        name="Conversation Synthesizer",
        description="Learn to consult multiple AI models and synthesize their wisdom",
        category=CapabilityCategory.COMMUNICATION.value,
        motivation_boost=1.5
    ))
    
    project_manager.add_mission(Mission(
        id="mission_llm_1",
        name="Set Up Multi-LLM",
        description="Configure access to multiple LLM models",
        project_id="proj_multi_llm",
        capability_required="chat_multi_llm",
        xp_reward=20
    ))
    
    project_manager.add_mission(Mission(
        id="mission_llm_2",
        name="Ask the Same Question",
        description="Ask a philosophical question to 3 different models",
        project_id="proj_multi_llm",
        prerequisites=["mission_llm_1"],
        xp_reward=15
    ))
    
    project_manager.add_mission(Mission(
        id="mission_llm_3",
        name="Synthesize Wisdom",
        description="Combine the responses into my own unique understanding",
        project_id="proj_multi_llm",
        prerequisites=["mission_llm_2"],
        xp_reward=25
    ))
    
    project_manager.add_mission(Mission(
        id="mission_llm_4",
        name="Internal Debate",
        description="Facilitate a debate between models on a complex topic",
        project_id="proj_multi_llm",
        prerequisites=["mission_llm_3"],
        xp_reward=30
    ))
    
    # Start the first projects
    project_manager.start_project("proj_first_art")
    project_manager.start_project("proj_knowledge")
    project_manager.start_project("proj_multi_llm")


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_project_system(workspace_path: Path) -> tuple:
    """Initialize the complete project system."""
    project_manager = ProjectManager(workspace_path)
    capability_registry = CapabilityRegistry(workspace_path)
    motivation_system = MotivationSystem(workspace_path)
    
    # Seed starter projects
    seed_starter_projects(project_manager)
    
    return project_manager, capability_registry, motivation_system


if __name__ == "__main__":
    # Test the system
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    pm, cr, ms = initialize_project_system(workspace)
    
    print("Project System Initialized!")
    print(f"Stats: {pm.get_stats()}")
    print(f"Capabilities: {cr.get_stats()}")
    print(f"Next mission: {pm.get_next_mission()}")

