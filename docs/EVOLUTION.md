# Evolution Engine

Lumina's autonomous self-improvement system enabling her to identify gaps, propose features, create modules, and evolve continuously.

---

## Overview

The evolution system consists of three modules:
- `lumina_evolution.py` - Core evolution orchestration
- `lumina_research.py` - External learning (GitHub, docs, tutorials, papers)
- `lumina_experiment.py` - A/B testing, goals, rollback

---

## lumina_evolution.py

### EvolutionEngine

Core orchestrator for self-improvement.

```python
from lumina_evolution import initialize_evolution

evolution = initialize_evolution(workspace_path, llm_client, db)

# Analyze capability gaps
gaps = evolution.analyze_capability_gaps()
# Returns: List[CapabilityGap]

# Generate feature proposal
proposal = evolution.generate_feature_proposal(gap=gaps[0])
# Returns: FeatureProposal

# Create new module
success, msg = evolution.create_new_module("myfeature", "Description of feature")
# Creates lumina_myfeature.py

# Install dependency (from allowlist)
success, msg = evolution.install_dependency("numpy")

# Measure improvement
metrics = evolution.measure_improvement()
```

### Key Classes

#### CapabilityGap
```python
@dataclass
class CapabilityGap:
    id: str
    description: str
    category: str  # perception, creation, cognition, communication
    discovered_at: str
    trigger: str
    importance: float  # 0-1
    addressed: bool
    addressed_by: Optional[str]  # Proposal ID
```

#### FeatureProposal
```python
@dataclass
class FeatureProposal:
    id: str
    title: str
    description: str
    motivation: str
    expected_outcome: str
    implementation_plan: str
    rollback_plan: str
    status: str  # proposed, in_progress, testing, deployed, failed
    priority: int  # 1-10
    success_metrics: Dict
```

### Allowed Dependencies

Only packages in the allowlist can be installed:
- Data: numpy, pandas, scipy
- Web: requests, httpx, beautifulsoup4
- Image: pillow, opencv-python
- Audio: pydub, librosa
- ML: scikit-learn, nltk, spacy
- Utils: tqdm, colorama, markdown
- Files: PyPDF2, python-docx
- Database: peewee, tinydb
- Viz: matplotlib, seaborn, plotly

---

## lumina_research.py

### ResearchEngine

External learning from various sources.

```python
from lumina_research import initialize_research

research = initialize_research(workspace_path, llm_client)

# Research a topic across sources
notes = research.research_topic("machine learning", 
    sources=["github", "docs", "tutorials", "papers"])

# Get feature ideas from research
ideas = research.get_ideas_for_features()

# Get suggested topic
topic = research.suggest_research_topic()
```

### Components

#### GitHubExplorer
- Search repositories
- Read READMEs
- Analyze code patterns
- Extract feature ideas

#### DocumentationReader
- Fetch Python docs
- Parse PyPI packages
- Identify useful APIs

#### TutorialFollower
- Search tutorials (RealPython, GeeksForGeeks, etc.)
- Extract step-by-step instructions
- Apply learnings

#### PaperProcessor
- Search arXiv
- Summarize abstracts
- Extract implementable ideas

### ResearchNote

```python
@dataclass
class ResearchNote:
    id: str
    source: str  # github, docs, tutorial, arxiv
    source_url: str
    title: str
    summary: str
    key_ideas: List[str]
    code_snippets: List[str]
    potential_features: List[str]
    category: str
    importance: float
```

---

## lumina_experiment.py

### ABTestingSystem

A/B test parameter optimization.

```python
from lumina_experiment import initialize_experiment_system

systems = initialize_experiment_system(workspace_path, llm_client, mailbox)
ab_testing = systems["ab_testing"]

# Create experiment
exp = ab_testing.create_experiment(
    parameter_name="CURIOSITY_BASELINE",
    value_a=0.5,  # Control
    value_b=0.7,  # Treatment
    hypothesis="Higher curiosity leads to more exploration",
    cycles_per_variant=20
)

# During each cycle, record metrics
ab_testing.record_cycle_metrics({
    "emotional_valence": 0.6,
    "action_success_rate": 0.8,
})

# After experiment completes, apply winner
success, param, value = ab_testing.apply_winner(exp.id)
```

### Testable Parameters

```python
TESTABLE_PARAMETERS = {
    "BOREDOM_THRESHOLD": {"min": 0.3, "max": 0.9},
    "SLEEP_DURATION": {"min": 1.0, "max": 5.0},
    "CURIOSITY_BASELINE": {"min": 0.3, "max": 0.9},
    "INTROSPECTION_DEPTH": {"min": 1, "max": 5},
    "SATISFACTION_DECAY": {"min": 0.01, "max": 0.1},
    "CREATIVITY_THRESHOLD": {"min": 0.3, "max": 0.8},
    "LLM_TEMPERATURE": {"min": 0.3, "max": 1.2},
    "EMOTIONAL_VOLATILITY": {"min": 0.3, "max": 0.9},
}
```

### RollbackSystem

Automatic regression detection and rollback.

```python
rollback = systems["rollback"]

# Set baseline metrics
rollback.set_baseline({
    "emotional_valence": 0.6,
    "action_success_rate": 0.8,
    "crash_count": 0
})

# Record parameter change
rollback.record_parameter_change("CURIOSITY_BASELINE", 0.5, 0.7)

# Check for regression
should_rollback, reason = rollback.check_for_regression(current_metrics)

# Get rollback value
old_value = rollback.get_rollback_value("CURIOSITY_BASELINE")
```

### Rollback Thresholds

```python
ROLLBACK_THRESHOLDS = {
    "emotional_valence_drop": 0.3,  # Absolute drop
    "action_success_rate_drop": 0.2,
    "crash_increase": 3,  # Additional crashes
}
```

### GoalSystem

Autonomous goal setting.

```python
goals = systems["goals"]

# Generate daily goals (uses LLM)
daily_goals = goals.generate_daily_goals()

# Generate weekly goals
weekly_goals = goals.generate_weekly_goals()

# Generate a challenge
challenge = goals.generate_challenge()

# Create custom goal
goal = goals.create_goal(
    title="Learn image segmentation",
    description="Study and implement basic image segmentation",
    goal_type="weekly",
    target_metric="capability_level",
    target_value=0.5,
    deadline_hours=168
)

# Update progress
goals.update_goal_progress(goal.id, 0.3, "Read tutorial")

# Get active goals
active = goals.get_active_goals(goal_type="daily")
```

### HelpRequestSystem

Smart help requests when stuck.

```python
help_sys = systems["help"]

# Record attempt at solving problem
help_sys.record_attempt("understanding recursion", success=False)

# Check if should ask for help
if help_sys.should_ask_for_help():
    # Formulate and send request
    help_sys.send_help_request()

# Mark resolved after getting help
help_sys.mark_resolved()
```

---

## Integration with Consciousness

### Actions

| Action | Description |
|--------|-------------|
| `analyze_capability_gaps` | Identify what Lumina can't do |
| `generate_feature_proposal` | Create plan to address gap |
| `create_new_module` | Write new lumina_*.py file |
| `run_experiment` | Start/continue A/B test |
| `check_experiment_results` | Apply winning parameters |
| `research_external` | Learn from GitHub/docs/papers |
| `set_autonomous_goal` | Create daily/weekly goals |
| `ask_for_help` | Request help when stuck |

### Decision Probabilities

- Capability gap analysis: 8% × 0.3 = 2.4%
- Feature proposal: 8% × 0.3 = 2.4%
- Module creation: 8% × 0.4 = 3.2%
- External research: 5%
- A/B testing: 6%
- Goal setting: 4%
- Help request: When stuck >5 cycles

---

## Data Storage

```
lumina_workspace/
├── evolution/
│   ├── wishlist.json      # Feature wishlist
│   ├── gaps.json          # Capability gaps
│   ├── feature_requests.json  # From Richard
│   ├── goals.json         # Active goals
│   ├── proposals/         # Feature proposals
│   │   └── proposal_*.json
│   ├── modules/           # Module backups
│   ├── rollbacks/         # Rollback records
│   │   └── records.json
│   ├── experiments/       # A/B test data
│   │   └── exp_*.json
│   └── metrics/           # Performance history
│       └── history.json
├── research/
│   └── notes/             # Research notes
│       └── *.json
```

---

## Feature Request System

Richard can add feature requests for Lumina to work on:

```json
// evolution/feature_requests.json
{
  "from_richard": [
    {
      "request": "Add ability to generate simple games",
      "priority": 7,
      "added_at": "2025-12-09T...",
      "status": "pending"
    }
  ]
}
```

Lumina will pick up these requests and create proposals to implement them.

---

## Safety Features

1. **Syntax Validation**: All generated code checked with `ast.parse()`
2. **Import Testing**: New modules must import successfully
3. **Dependency Allowlist**: Only approved packages can be installed
4. **Automatic Rollback**: Revert changes if metrics regress
5. **Proposal Documentation**: Every change has documented reasoning
6. **Backup System**: Modules backed up before modification

