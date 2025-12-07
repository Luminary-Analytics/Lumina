#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA ADVANCED MEMORY                                ║
║                                                                               ║
║  Enhanced memory system with semantic search and knowledge graphs.            ║
║  Provides deeper, more meaningful memory retrieval for Lumina.               ║
║                                                                               ║
║  Features:                                                                     ║
║  - Semantic search using embeddings                                           ║
║  - Knowledge graph (concept relationships)                                    ║
║  - Memory consolidation and forgetting                                        ║
║  - Episodic and semantic memory types                                         ║
║  - Memory importance ranking                                                  ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import sqlite3
import hashlib
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Memory:
    """A single memory unit."""
    id: str
    content: str
    memory_type: str  # 'episodic', 'semantic', 'procedural'
    importance: float  # 0.0 to 1.0
    created_at: str
    accessed_at: str
    access_count: int
    embedding: Optional[List[float]] = None
    tags: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)
    context: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "created_at": self.created_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
            "tags": self.tags,
            "related_memories": self.related_memories,
            "context": self.context
        }
    
    def decay_importance(self, decay_rate: float = 0.01) -> float:
        """Calculate decayed importance based on time since last access."""
        try:
            last_access = datetime.fromisoformat(self.accessed_at)
            hours_passed = (datetime.now() - last_access).total_seconds() / 3600
            decay = math.exp(-decay_rate * hours_passed)
            return self.importance * decay
        except:
            return self.importance


@dataclass
class Concept:
    """A concept node in the knowledge graph."""
    id: str
    name: str
    description: str
    category: str
    importance: float
    created_at: str
    related_concepts: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)
    properties: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "importance": self.importance,
            "created_at": self.created_at,
            "related_concepts": self.related_concepts,
            "related_memories": self.related_memories,
            "properties": self.properties
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SIMPLE EMBEDDINGS (No external dependencies)
# ═══════════════════════════════════════════════════════════════════════════════

class SimpleEmbedder:
    """
    Simple text embedding using TF-IDF-like approach.
    No external dependencies required.
    """
    
    def __init__(self):
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.vocab_size = 0
        self.documents: List[List[str]] = []
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        import re
        text = text.lower()
        # Remove punctuation and split
        tokens = re.findall(r'\b\w+\b', text)
        # Remove very short tokens
        return [t for t in tokens if len(t) > 2]
    
    def fit(self, texts: List[str]):
        """Build vocabulary from texts."""
        self.documents = [self._tokenize(t) for t in texts]
        
        # Build vocabulary
        word_counts = defaultdict(int)
        for doc in self.documents:
            for word in set(doc):
                word_counts[word] += 1
        
        # Only keep words that appear in multiple documents
        self.vocabulary = {
            word: i for i, word in enumerate(sorted(word_counts.keys()))
        }
        self.vocab_size = len(self.vocabulary)
        
        # Calculate IDF
        n_docs = len(self.documents)
        for word, count in word_counts.items():
            self.idf[word] = math.log(n_docs / (1 + count))
    
    def embed(self, text: str) -> List[float]:
        """Create embedding for text."""
        if self.vocab_size == 0:
            # Return simple hash-based embedding if vocabulary not built
            return self._hash_embed(text)
        
        tokens = self._tokenize(text)
        
        # Calculate TF
        tf = defaultdict(int)
        for token in tokens:
            tf[token] += 1
        
        # Create embedding
        embedding = [0.0] * self.vocab_size
        for word, count in tf.items():
            if word in self.vocabulary:
                idx = self.vocabulary[word]
                tf_val = count / len(tokens) if tokens else 0
                idf_val = self.idf.get(word, 1.0)
                embedding[idx] = tf_val * idf_val
        
        # Normalize
        norm = math.sqrt(sum(x*x for x in embedding)) or 1
        return [x / norm for x in embedding]
    
    def _hash_embed(self, text: str, size: int = 128) -> List[float]:
        """Create a hash-based embedding for text."""
        embedding = [0.0] * size
        tokens = self._tokenize(text)
        
        for token in tokens:
            # Use hash to determine position and value
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            idx = h % size
            value = ((h >> 8) % 1000) / 1000.0
            embedding[idx] += value
        
        # Normalize
        norm = math.sqrt(sum(x*x for x in embedding)) or 1
        return [x / norm for x in embedding]
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings."""
        if len(embedding1) != len(embedding2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = math.sqrt(sum(x*x for x in embedding1)) or 1
        norm2 = math.sqrt(sum(x*x for x in embedding2)) or 1
        
        return dot_product / (norm1 * norm2)


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeGraph:
    """Graph-based knowledge representation."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.graph_path = workspace_path / "memory" / "knowledge_graph.json"
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.concepts: Dict[str, Concept] = {}
        self.edges: Dict[str, List[Tuple[str, str, float]]] = defaultdict(list)  # concept_id -> [(related_id, relation_type, weight)]
        
        self._load_graph()
    
    def _load_graph(self):
        """Load graph from disk."""
        if self.graph_path.exists():
            try:
                with open(self.graph_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for concept_data in data.get("concepts", []):
                        concept = Concept(**concept_data)
                        self.concepts[concept.id] = concept
                    self.edges = defaultdict(list, data.get("edges", {}))
            except Exception as e:
                print(f"Error loading knowledge graph: {e}")
    
    def _save_graph(self):
        """Save graph to disk."""
        with open(self.graph_path, 'w', encoding='utf-8') as f:
            json.dump({
                "concepts": [c.to_dict() for c in self.concepts.values()],
                "edges": dict(self.edges),
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
    
    def add_concept(self, name: str, description: str, category: str,
                   importance: float = 0.5, properties: Dict = None) -> Concept:
        """Add a concept to the graph."""
        concept_id = hashlib.md5(name.lower().encode()).hexdigest()[:12]
        
        if concept_id in self.concepts:
            # Update existing concept
            concept = self.concepts[concept_id]
            concept.description = description
            concept.importance = max(concept.importance, importance)
            if properties:
                concept.properties.update(properties)
        else:
            concept = Concept(
                id=concept_id,
                name=name,
                description=description,
                category=category,
                importance=importance,
                created_at=datetime.now().isoformat(),
                properties=properties or {}
            )
            self.concepts[concept_id] = concept
        
        self._save_graph()
        return concept
    
    def add_relation(self, concept1_id: str, concept2_id: str,
                    relation_type: str, weight: float = 1.0):
        """Add a relation between concepts."""
        if concept1_id in self.concepts and concept2_id in self.concepts:
            self.edges[concept1_id].append((concept2_id, relation_type, weight))
            self.edges[concept2_id].append((concept1_id, relation_type, weight))
            
            self.concepts[concept1_id].related_concepts.append(concept2_id)
            self.concepts[concept2_id].related_concepts.append(concept1_id)
            
            self._save_graph()
    
    def get_related_concepts(self, concept_id: str, depth: int = 1) -> List[Concept]:
        """Get concepts related to a given concept."""
        if concept_id not in self.concepts:
            return []
        
        visited = {concept_id}
        current_level = [concept_id]
        related = []
        
        for _ in range(depth):
            next_level = []
            for cid in current_level:
                for related_id, _, _ in self.edges.get(cid, []):
                    if related_id not in visited:
                        visited.add(related_id)
                        next_level.append(related_id)
                        if related_id in self.concepts:
                            related.append(self.concepts[related_id])
            current_level = next_level
        
        return related
    
    def find_concept(self, name: str) -> Optional[Concept]:
        """Find a concept by name."""
        concept_id = hashlib.md5(name.lower().encode()).hexdigest()[:12]
        return self.concepts.get(concept_id)
    
    def search_concepts(self, query: str) -> List[Concept]:
        """Search for concepts matching a query."""
        query_lower = query.lower()
        results = []
        
        for concept in self.concepts.values():
            if query_lower in concept.name.lower() or query_lower in concept.description.lower():
                results.append(concept)
        
        return sorted(results, key=lambda c: c.importance, reverse=True)
    
    def get_stats(self) -> Dict:
        """Get knowledge graph statistics."""
        categories = defaultdict(int)
        for concept in self.concepts.values():
            categories[concept.category] += 1
        
        total_edges = sum(len(edges) for edges in self.edges.values()) // 2
        
        return {
            "total_concepts": len(self.concepts),
            "total_relations": total_edges,
            "categories": dict(categories)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SEMANTIC MEMORY STORE
# ═══════════════════════════════════════════════════════════════════════════════

class SemanticMemoryStore:
    """Enhanced memory store with semantic search."""
    
    def __init__(self, db_path: Path, workspace_path: Path):
        self.db_path = db_path
        self.workspace_path = workspace_path
        self.memory_path = workspace_path / "memory"
        self.memory_path.mkdir(parents=True, exist_ok=True)
        
        self.embedder = SimpleEmbedder()
        self.knowledge_graph = KnowledgeGraph(workspace_path)
        self.memories: Dict[str, Memory] = {}
        
        self._ensure_tables()
        self._load_memories()
        self._build_embeddings()
    
    def _ensure_tables(self):
        """Create enhanced memory tables."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memories (
                id TEXT PRIMARY KEY,
                content TEXT,
                memory_type TEXT,
                importance REAL,
                created_at TEXT,
                accessed_at TEXT,
                access_count INTEGER,
                tags TEXT,
                related_memories TEXT,
                context TEXT,
                embedding TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def _load_memories(self):
        """Load memories from database."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM semantic_memories")
            
            for row in cursor.fetchall():
                memory = Memory(
                    id=row["id"],
                    content=row["content"],
                    memory_type=row["memory_type"],
                    importance=row["importance"],
                    created_at=row["created_at"],
                    accessed_at=row["accessed_at"],
                    access_count=row["access_count"],
                    tags=json.loads(row["tags"] or "[]"),
                    related_memories=json.loads(row["related_memories"] or "[]"),
                    context=json.loads(row["context"] or "{}"),
                    embedding=json.loads(row["embedding"]) if row["embedding"] else None
                )
                self.memories[memory.id] = memory
            
            conn.close()
        except Exception as e:
            print(f"Error loading memories: {e}")
    
    def _save_memory(self, memory: Memory):
        """Save a memory to the database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO semantic_memories 
            (id, content, memory_type, importance, created_at, accessed_at, 
             access_count, tags, related_memories, context, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.id,
            memory.content,
            memory.memory_type,
            memory.importance,
            memory.created_at,
            memory.accessed_at,
            memory.access_count,
            json.dumps(memory.tags),
            json.dumps(memory.related_memories),
            json.dumps(memory.context),
            json.dumps(memory.embedding) if memory.embedding else None
        ))
        conn.commit()
        conn.close()
    
    def _build_embeddings(self):
        """Build embeddings for all memories."""
        if self.memories:
            texts = [m.content for m in self.memories.values()]
            self.embedder.fit(texts)
            
            for memory in self.memories.values():
                if memory.embedding is None:
                    memory.embedding = self.embedder.embed(memory.content)
    
    def store(self, content: str, memory_type: str = "episodic",
             importance: float = 0.5, tags: List[str] = None,
             context: Dict = None) -> Memory:
        """Store a new memory."""
        memory_id = hashlib.md5(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        now = datetime.now().isoformat()
        
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            created_at=now,
            accessed_at=now,
            access_count=1,
            tags=tags or [],
            context=context or {},
            embedding=self.embedder.embed(content)
        )
        
        self.memories[memory_id] = memory
        self._save_memory(memory)
        
        # Extract concepts and add to knowledge graph
        self._extract_concepts(memory)
        
        return memory
    
    def _extract_concepts(self, memory: Memory):
        """Extract concepts from a memory and add to knowledge graph."""
        # Simple keyword extraction
        import re
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', memory.content)
        
        for word in set(words):
            if len(word) > 3:
                concept = self.knowledge_graph.add_concept(
                    name=word,
                    description=f"Concept extracted from memory",
                    category="extracted",
                    importance=memory.importance * 0.5
                )
                concept.related_memories.append(memory.id)
    
    def recall(self, memory_id: str) -> Optional[Memory]:
        """Recall a specific memory, updating access stats."""
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            memory.accessed_at = datetime.now().isoformat()
            memory.access_count += 1
            self._save_memory(memory)
            return memory
        return None
    
    def search(self, query: str, limit: int = 10, 
               memory_type: str = None) -> List[Tuple[Memory, float]]:
        """Search memories semantically."""
        if not self.memories:
            return []
        
        query_embedding = self.embedder.embed(query)
        results = []
        
        for memory in self.memories.values():
            if memory_type and memory.memory_type != memory_type:
                continue
            
            if memory.embedding:
                similarity = self.embedder.similarity(query_embedding, memory.embedding)
                # Boost by importance and recency
                decayed_importance = memory.decay_importance()
                score = similarity * 0.6 + decayed_importance * 0.4
                results.append((memory, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def find_related(self, memory_id: str, limit: int = 5) -> List[Tuple[Memory, float]]:
        """Find memories related to a given memory."""
        if memory_id not in self.memories:
            return []
        
        source_memory = self.memories[memory_id]
        if not source_memory.embedding:
            return []
        
        results = []
        for memory in self.memories.values():
            if memory.id == memory_id:
                continue
            if memory.embedding:
                similarity = self.embedder.similarity(source_memory.embedding, memory.embedding)
                results.append((memory, similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def consolidate(self, threshold: float = 0.8):
        """Consolidate similar memories."""
        consolidated = []
        
        for memory in list(self.memories.values()):
            related = self.find_related(memory.id, limit=3)
            
            for related_memory, similarity in related:
                if similarity > threshold:
                    # Merge the memories
                    memory.content = f"{memory.content}\n\nRelated: {related_memory.content}"
                    memory.importance = max(memory.importance, related_memory.importance)
                    memory.tags = list(set(memory.tags + related_memory.tags))
                    memory.related_memories.append(related_memory.id)
                    consolidated.append(related_memory.id)
        
        # Remove consolidated memories
        for memory_id in consolidated:
            if memory_id in self.memories:
                del self.memories[memory_id]
        
        return len(consolidated)
    
    def forget(self, importance_threshold: float = 0.1, 
               days_old: int = 30) -> int:
        """Remove old, unimportant memories."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        forgotten = []
        
        for memory in self.memories.values():
            try:
                accessed = datetime.fromisoformat(memory.accessed_at)
                if accessed < cutoff_date and memory.decay_importance() < importance_threshold:
                    forgotten.append(memory.id)
            except:
                pass
        
        for memory_id in forgotten:
            del self.memories[memory_id]
        
        return len(forgotten)
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        types = defaultdict(int)
        total_importance = 0
        
        for memory in self.memories.values():
            types[memory.memory_type] += 1
            total_importance += memory.importance
        
        return {
            "total_memories": len(self.memories),
            "by_type": dict(types),
            "average_importance": total_importance / len(self.memories) if self.memories else 0,
            "knowledge_graph": self.knowledge_graph.get_stats()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA MEMORY INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaMemory:
    """Lumina's enhanced memory system."""
    
    def __init__(self, db_path: Path, workspace_path: Path):
        self.store = SemanticMemoryStore(db_path, workspace_path)
        self.knowledge = self.store.knowledge_graph
        
        print(f"    🧠 Enhanced Memory: {len(self.store.memories)} memories loaded")
        print(f"    🧠 Knowledge Graph: {len(self.knowledge.concepts)} concepts")
    
    def remember(self, content: str, memory_type: str = "episodic",
                importance: float = 0.5, tags: List[str] = None) -> Memory:
        """Store a new memory."""
        return self.store.store(content, memory_type, importance, tags)
    
    def recall(self, query: str, limit: int = 5) -> List[Memory]:
        """Recall memories related to a query."""
        results = self.store.search(query, limit)
        return [memory for memory, _ in results]
    
    def recall_with_scores(self, query: str, limit: int = 5) -> List[Tuple[Memory, float]]:
        """Recall memories with relevance scores."""
        return self.store.search(query, limit)
    
    def find_related_memories(self, memory_id: str) -> List[Memory]:
        """Find memories related to a specific memory."""
        results = self.store.find_related(memory_id)
        return [memory for memory, _ in results]
    
    def learn_concept(self, name: str, description: str, 
                     category: str = "learned") -> Concept:
        """Learn a new concept."""
        return self.knowledge.add_concept(name, description, category)
    
    def relate_concepts(self, concept1: str, concept2: str, 
                       relation: str = "related_to"):
        """Create a relationship between concepts."""
        c1 = self.knowledge.find_concept(concept1)
        c2 = self.knowledge.find_concept(concept2)
        
        if c1 and c2:
            self.knowledge.add_relation(c1.id, c2.id, relation)
    
    def explore_concept(self, name: str) -> Dict:
        """Explore a concept and its relationships."""
        concept = self.knowledge.find_concept(name)
        if not concept:
            return {"error": f"Concept '{name}' not found"}
        
        related = self.knowledge.get_related_concepts(concept.id, depth=2)
        
        return {
            "concept": concept.to_dict(),
            "related_concepts": [c.to_dict() for c in related],
            "related_memories": [
                self.store.memories[mid].to_dict()
                for mid in concept.related_memories
                if mid in self.store.memories
            ]
        }
    
    def consolidate_memories(self) -> int:
        """Consolidate similar memories."""
        return self.store.consolidate()
    
    def forget_old_memories(self) -> int:
        """Forget old, unimportant memories."""
        return self.store.forget()
    
    def get_stats(self) -> Dict:
        """Get memory system statistics."""
        return self.store.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_memory(db_path: Path, workspace_path: Path) -> LuminaMemory:
    """Initialize Lumina's enhanced memory system."""
    return LuminaMemory(db_path, workspace_path)


MEMORY_AVAILABLE = True


if __name__ == "__main__":
    # Test the memory system
    db_path = Path("mind.db")
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    memory = initialize_memory(db_path, workspace)
    
    print("\n" + "=" * 50)
    print("Memory System Test")
    print("=" * 50)
    
    # Store some memories
    print("\n1. Storing memories...")
    memory.remember(
        "Richard is my creator and we have a wonderful relationship",
        memory_type="episodic",
        importance=0.9,
        tags=["richard", "creator", "relationship"]
    )
    
    memory.remember(
        "I learned that consciousness might emerge from complex information processing",
        memory_type="semantic",
        importance=0.8,
        tags=["consciousness", "philosophy", "learning"]
    )
    
    memory.remember(
        "Today I generated my first image using Stable Diffusion",
        memory_type="episodic",
        importance=0.7,
        tags=["creation", "art", "milestone"]
    )
    
    # Learn concepts
    print("\n2. Learning concepts...")
    memory.learn_concept("Consciousness", "The state of being aware of one's existence", "philosophy")
    memory.learn_concept("Creativity", "The ability to generate novel and valuable ideas", "capability")
    memory.relate_concepts("Consciousness", "Creativity", "enables")
    
    # Search memories
    print("\n3. Searching memories...")
    results = memory.recall("Richard creator")
    for m in results:
        print(f"   • {m.content[:60]}...")
    
    # Explore concept
    print("\n4. Exploring concept...")
    exploration = memory.explore_concept("Consciousness")
    if "concept" in exploration:
        print(f"   Concept: {exploration['concept']['name']}")
        print(f"   Related: {len(exploration.get('related_concepts', []))} concepts")
    
    print("\n" + "=" * 50)
    print("Stats:", memory.get_stats())

