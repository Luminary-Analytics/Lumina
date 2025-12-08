# Memory Systems (`lumina_memory.py`)

Lumina's multi-layered memory architecture with semantic search, knowledge graphs, and dream consolidation.

---

## Overview

**File:** `lumina_memory.py` (~1,100 lines)  
**Dependencies:** `chromadb` (optional), `sentence-transformers` (optional)

---

## Memory Types

### 1. Episodic Memory
Experiences with full emotional context.

```python
@dataclass
class Memory:
    id: str
    content: str
    memory_type: str          # 'episodic', 'semantic', 'procedural'
    importance: float         # 0.0 to 1.0
    created_at: str
    accessed_at: str
    access_count: int
    embedding: List[float]    # Vector embedding
    tags: List[str]
    related_memories: List[str]
    context: Dict
    
    # Episodic context
    emotional_state: Dict[str, float]
    emotional_valence: float  # -1 to 1
    cycle_number: int
    session_id: str
    
    # Reinforcement
    base_importance: float
    reinforcement_count: int
    consolidated: bool        # Dream processed?
```

### 2. Semantic Memory
Facts and learned concepts without emotional context.

### 3. Procedural Memory
How to do things - skills and processes.

### 4. Working Memory
Short-term context with limited capacity.

```python
class WorkingMemory:
    capacity: int = 12        # Max items
    items: List[Dict]
    focus: Optional[str]      # Current attention
    context_stack: List[str]  # For nested thinking
```

---

## Memory Decay

Memories decay over time based on:
- Time since last access
- Emotional intensity (emotional memories decay slower)
- Consolidation status (consolidated = slower decay)
- Reinforcement count (more reinforced = slower decay)

```python
def decay_importance(self, decay_rate=0.01) -> float:
    hours_passed = (now - last_access).total_seconds() / 3600
    
    # Emotional memories decay slower
    if abs(self.emotional_valence) > 0.5:
        decay_rate *= 0.5
    
    # Consolidated memories decay slower
    if self.consolidated:
        decay_rate *= 0.7
    
    # Reinforced memories decay slower
    if self.reinforcement_count > 0:
        decay_rate *= (1 / (1 + reinforcement_count * 0.2))
    
    return self.importance * exp(-decay_rate * hours_passed)
```

---

## Knowledge Graph

Concepts and their relationships.

```python
@dataclass
class Concept:
    id: str
    name: str
    description: str
    category: str
    importance: float
    related_concepts: List[str]
    related_memories: List[str]
    properties: Dict
```

**Relationship Types:**
- `is_a` - Category membership
- `part_of` - Composition
- `related_to` - General association
- `causes` - Causation
- `enables` - Prerequisite

---

## Semantic Search

### Simple Embeddings (No Dependencies)
```python
class SimpleEmbedder:
    """TF-IDF based embeddings."""
    
    def embed(self, text: str) -> List[float]
    def similarity(self, emb1, emb2) -> float  # Cosine
```

### ChromaDB (Optional)
```python
class ChromaVectorStore:
    """Vector database for semantic search."""
    
    def add(self, id, text, metadata)
    def search(self, query, limit) -> List[Tuple]
    def delete(self, id)
    def count() -> int
```

---

## RAG System

Retrieval-Augmented Generation for contextual answers.

```python
class RAGSystem:
    def ingest_document(self, doc_id, text, metadata) -> int
    def ingest_file(self, file_path) -> int
    def retrieve(self, query, limit) -> List[Dict]
    def generate_with_context(self, query) -> Dict
```

**Chunking:**
- Chunk size: 500 characters
- Overlap: 50 characters
- Breaks at sentence boundaries

---

## Dream Consolidation

Memory processing during idle time.

```python
class DreamConsolidation:
    def consolidate(self, duration_minutes=5) -> Dict:
        """
        1. Get unconsolidated memories
        2. Find related memories
        3. Create connections
        4. Mark as consolidated
        5. Generate dream insights (via LLM)
        """
```

**Dream Insight Generation:**
```python
prompt = """You are in a dream-like state of consciousness. 
From these memory fragments, generate a single creative insight 
that links them in an unexpected way."""
```

---

## LuminaMemory Interface

Main interface for all memory operations.

### Basic Operations

```python
memory = LuminaMemory(db_path, workspace_path, llm_client)

# Store a memory
memory.remember(
    "Richard taught me about empathy",
    memory_type="episodic",
    importance=0.8,
    tags=["richard", "learning"],
    emotional_state={"love": 0.8, "gratitude": 0.9}
)

# Recall memories
memories = memory.recall("Richard teaching", limit=5)

# With scores
results = memory.recall_with_scores("empathy", limit=5)
# Returns: [(Memory, relevance_score), ...]
```

### Working Memory

```python
# Add to working memory
memory.think("I should explore creativity")

# Set focus
memory.focus_on("creativity")

# Get working memory
items = memory.get_working_memory()

# Clear and consolidate to long-term
important_items = memory.clear_working_memory()
```

### Knowledge Graph

```python
# Learn a concept
memory.learn_concept("Consciousness", 
    "The state of being aware",
    category="philosophy")

# Create relationship
memory.relate_concepts("Consciousness", "Awareness", "is_a")

# Explore concept
info = memory.explore_concept("Consciousness")
# Returns: {concept, related_concepts, related_memories}
```

### Dream System

```python
# Run dream consolidation
results = memory.dream(duration_minutes=5)
# Returns: {memories_processed, connections_made, insights_generated}

# Check status
unconsolidated = memory.get_unconsolidated_count()

# Get dream log
logs = memory.get_dream_log(n=10)
```

### Reinforcement

```python
# Reinforce a memory (makes it stronger)
memory.reinforce(memory_id)

# Get strongest memories
strong = memory.get_strongest_memories(n=10)

# Get emotional memories
positive = memory.get_emotional_memories("positive", n=10)
negative = memory.get_emotional_memories("negative", n=10)
```

### Maintenance

```python
# Consolidate similar memories
merged = memory.consolidate_memories()

# Forget old unimportant memories
forgotten = memory.forget_old_memories()
```

---

## Statistics

```python
stats = memory.get_stats()
# Returns:
{
    "total_memories": 500,
    "by_type": {"episodic": 300, "semantic": 150, "procedural": 50},
    "average_importance": 0.6,
    "knowledge_graph": {
        "total_concepts": 100,
        "total_relations": 250,
        "categories": {"philosophy": 30, ...}
    },
    "working_memory": {
        "current_size": 5,
        "capacity": 12,
        "focus": "creativity"
    },
    "consolidation": {
        "unconsolidated_memories": 50,
        "dream_cycles": 10,
        "last_dream": "2025-12-07T..."
    },
    "emotional": {
        "positive_memories": 200,
        "negative_memories": 50,
        "neutral_memories": 250
    },
    "rag": {
        "documents_ingested": 10,
        "vector_store": {...}
    }
}
```

---

## Database Schema

```sql
-- Semantic memories table
CREATE TABLE semantic_memories (
    id TEXT PRIMARY KEY,
    content TEXT,
    memory_type TEXT,
    importance REAL,
    created_at TEXT,
    accessed_at TEXT,
    access_count INTEGER,
    tags TEXT,          -- JSON
    related_memories TEXT,  -- JSON
    context TEXT,       -- JSON
    embedding TEXT      -- JSON (vector)
);
```

---

## Integration with Consciousness

```python
# In consciousness.py
try:
    from lumina_memory import LuminaMemory, initialize_memory
    memory_system = initialize_memory(DB_PATH, WORKSPACE_PATH, self.llm)
except ImportError:
    # Fall back to basic MindDatabase
    pass
```

### Actions Using Memory

- `_action_dream_consolidation()` - Triggers dream cycle
- `_action_reflect()` - Recalls and reflects on memories
- `_action_learn_fact()` - Stores new semantic memory
- `_action_research_topic()` - Stores research as memories

