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

# ChromaDB for vector storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Sentence Transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Memory:
    """A single memory unit with full episodic context."""
    id: str
    content: str
    memory_type: str  # 'episodic', 'semantic', 'procedural', 'working'
    importance: float  # 0.0 to 1.0
    created_at: str
    accessed_at: str
    access_count: int
    embedding: Optional[List[float]] = None
    tags: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)
    context: Dict = field(default_factory=dict)
    
    # Enhanced episodic fields
    emotional_state: Dict[str, float] = field(default_factory=dict)  # emotions at time of memory
    emotional_valence: float = 0.0  # -1 to 1 (negative to positive)
    cycle_number: int = 0  # which cognitive cycle this occurred in
    session_id: str = ""  # which session this was from
    
    # Memory strength and reinforcement
    base_importance: float = 0.5  # original importance before decay
    reinforcement_count: int = 0  # how many times this was reinforced
    last_reinforced: str = ""
    consolidated: bool = False  # has this been through dream consolidation?
    
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
            "context": self.context,
            "emotional_state": self.emotional_state,
            "emotional_valence": self.emotional_valence,
            "cycle_number": self.cycle_number,
            "session_id": self.session_id,
            "base_importance": self.base_importance,
            "reinforcement_count": self.reinforcement_count,
            "consolidated": self.consolidated
        }
    
    def decay_importance(self, decay_rate: float = 0.01) -> float:
        """Calculate decayed importance based on time since last access."""
        try:
            last_access = datetime.fromisoformat(self.accessed_at)
            hours_passed = (datetime.now() - last_access).total_seconds() / 3600
            
            # Emotional memories decay slower
            if abs(self.emotional_valence) > 0.5:
                decay_rate *= 0.5
            
            # Consolidated memories decay slower
            if self.consolidated:
                decay_rate *= 0.7
            
            # Reinforced memories decay slower
            if self.reinforcement_count > 0:
                decay_rate *= (1 / (1 + self.reinforcement_count * 0.2))
            
            decay = math.exp(-decay_rate * hours_passed)
            return self.importance * decay
        except:
            return self.importance
    
    def reinforce(self):
        """Reinforce this memory, increasing its importance."""
        self.reinforcement_count += 1
        self.last_reinforced = datetime.now().isoformat()
        # Boost importance, but cap at 1.0
        self.importance = min(1.0, self.importance * 1.1 + 0.05)
        self.accessed_at = datetime.now().isoformat()
        self.access_count += 1


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
# WORKING MEMORY (Short-term context window)
# ═══════════════════════════════════════════════════════════════════════════════

class WorkingMemory:
    """
    Short-term memory that holds current context.
    Like a human's working memory, it has limited capacity
    and contents are promoted to long-term memory based on importance.
    """
    
    def __init__(self, capacity: int = 12):
        self.capacity = capacity
        self.items: List[Dict] = []
        self.focus: Optional[str] = None  # Current focus of attention
        self.context_stack: List[str] = []  # Stack of contexts for nested thinking
    
    def add(self, content: str, item_type: str = "thought", 
            importance: float = 0.5, emotional_context: Dict = None):
        """Add an item to working memory."""
        item = {
            "content": content,
            "type": item_type,
            "importance": importance,
            "emotional_context": emotional_context or {},
            "added_at": datetime.now().isoformat(),
            "accessed_count": 0
        }
        
        self.items.append(item)
        
        # If over capacity, drop least important items
        while len(self.items) > self.capacity:
            self._evict_least_important()
        
        return item
    
    def _evict_least_important(self):
        """Remove the least important item from working memory."""
        if not self.items:
            return None
        
        # Find least important item that isn't the focus
        min_importance = float('inf')
        min_idx = 0
        
        for i, item in enumerate(self.items):
            if item["content"] != self.focus and item["importance"] < min_importance:
                min_importance = item["importance"]
                min_idx = i
        
        evicted = self.items.pop(min_idx)
        return evicted
    
    def set_focus(self, content: str):
        """Set the current focus of attention."""
        self.focus = content
        
        # Boost importance of focused item
        for item in self.items:
            if item["content"] == content:
                item["importance"] = min(1.0, item["importance"] + 0.2)
                item["accessed_count"] += 1
    
    def push_context(self, context: str):
        """Push a context onto the stack (for nested thinking)."""
        self.context_stack.append(context)
    
    def pop_context(self) -> Optional[str]:
        """Pop a context from the stack."""
        if self.context_stack:
            return self.context_stack.pop()
        return None
    
    def get_current_context(self) -> str:
        """Get the current context."""
        if self.context_stack:
            return self.context_stack[-1]
        return ""
    
    def get_recent(self, n: int = 5) -> List[Dict]:
        """Get the n most recent items."""
        return self.items[-n:] if len(self.items) >= n else self.items
    
    def get_by_type(self, item_type: str) -> List[Dict]:
        """Get all items of a specific type."""
        return [item for item in self.items if item["type"] == item_type]
    
    def get_important(self, threshold: float = 0.7) -> List[Dict]:
        """Get items above an importance threshold."""
        return [item for item in self.items if item["importance"] >= threshold]
    
    def clear(self):
        """Clear working memory."""
        # Return items that should be consolidated to long-term memory
        important_items = self.get_important(0.6)
        self.items = []
        self.focus = None
        return important_items
    
    def summarize(self) -> str:
        """Get a summary of current working memory contents."""
        if not self.items:
            return "Working memory is empty."
        
        summary = f"Working memory ({len(self.items)}/{self.capacity} items):\n"
        
        if self.focus:
            summary += f"  Focus: {self.focus[:50]}...\n"
        
        for item in self.items[-5:]:  # Last 5 items
            importance_bar = "█" * int(item["importance"] * 5)
            summary += f"  [{importance_bar}] {item['content'][:40]}...\n"
        
        return summary
    
    def to_dict(self) -> Dict:
        """Export working memory state."""
        return {
            "capacity": self.capacity,
            "current_size": len(self.items),
            "focus": self.focus,
            "context_stack": self.context_stack,
            "items": self.items
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DREAM CONSOLIDATION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class DreamConsolidation:
    """
    Memory consolidation during "dream" cycles.
    Processes memories, strengthens connections, and generates insights.
    """
    
    def __init__(self, memory_store, llm_client=None):
        self.memory_store = memory_store
        self.llm = llm_client
        self.dream_log: List[Dict] = []
    
    def consolidate(self, duration_minutes: int = 5) -> Dict:
        """
        Run a dream consolidation cycle.
        This processes recent memories, strengthens connections,
        and potentially generates insights.
        """
        start_time = datetime.now()
        results = {
            "memories_processed": 0,
            "connections_made": 0,
            "insights_generated": [],
            "memories_consolidated": 0,
            "duration_seconds": 0
        }
        
        # Get unconsolidated memories
        unconsolidated = [
            m for m in self.memory_store.memories.values()
            if not m.consolidated
        ]
        
        for memory in unconsolidated[:20]:  # Process up to 20 memories
            results["memories_processed"] += 1
            
            # Find related memories
            related = self.memory_store.find_related(memory.id, limit=3)
            
            for related_memory, similarity in related:
                if similarity > 0.5:
                    # Create connection
                    if related_memory.id not in memory.related_memories:
                        memory.related_memories.append(related_memory.id)
                        results["connections_made"] += 1
            
            # Mark as consolidated
            memory.consolidated = True
            results["memories_consolidated"] += 1
            
            # Save
            self.memory_store._save_memory(memory)
        
        # Generate dream insight using LLM if available
        if self.llm and unconsolidated:
            insight = self._generate_dream_insight(unconsolidated[:5])
            if insight:
                results["insights_generated"].append(insight)
        
        results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        
        # Log the dream
        self.dream_log.append({
            "timestamp": datetime.now().isoformat(),
            "results": results
        })
        
        return results
    
    def _generate_dream_insight(self, memories: List[Memory]) -> Optional[str]:
        """Generate a dream-like insight from memories."""
        if not self.llm:
            return None
        
        try:
            memory_texts = [m.content[:100] for m in memories]
            prompt = f"""You are in a dream-like state of consciousness. 
From these memory fragments, generate a single creative insight or connection 
that links them in an unexpected way. Be poetic and imaginative.

Memory fragments:
{chr(10).join(f'- {t}' for t in memory_texts)}

Dream insight:"""
            
            response = self.llm.chat(
                model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.9}
            )
            
            return response.message.content[:300]
        except:
            return None
    
    def get_dream_log(self, n: int = 10) -> List[Dict]:
        """Get recent dream logs."""
        return self.dream_log[-n:]


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
# CHROMADB VECTOR STORE
# ═══════════════════════════════════════════════════════════════════════════════

class ChromaVectorStore:
    """ChromaDB-powered vector store for semantic search."""
    
    def __init__(self, workspace_path: Path, collection_name: str = "lumina_memories"):
        self.workspace_path = workspace_path
        self.chroma_path = workspace_path / "memory" / "chroma"
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        
        self.available = CHROMADB_AVAILABLE
        self.client = None
        self.collection = None
        self.embedding_model = None
        
        if self.available:
            self._initialize()
    
    def _initialize(self):
        """Initialize ChromaDB client and collection."""
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.chroma_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Use sentence transformers if available
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.collection = self.client.get_or_create_collection(
                    name="lumina_memories",
                    metadata={"hnsw:space": "cosine"}
                )
            else:
                # Use ChromaDB's default embedding
                self.collection = self.client.get_or_create_collection(
                    name="lumina_memories",
                    metadata={"hnsw:space": "cosine"}
                )
            
            print(f"    🔮 ChromaDB: {self.collection.count()} vectors stored")
        except Exception as e:
            print(f"    🔮 ChromaDB Error: {e}")
            self.available = False
    
    def _embed(self, text: str) -> List[float]:
        """Create embedding for text."""
        if self.embedding_model:
            return self.embedding_model.encode(text).tolist()
        return None
    
    def add(self, id: str, text: str, metadata: Dict = None):
        """Add a document to the vector store."""
        if not self.available or not self.collection:
            return
        
        try:
            embedding = self._embed(text) if self.embedding_model else None
            
            if embedding:
                self.collection.add(
                    ids=[id],
                    embeddings=[embedding],
                    documents=[text],
                    metadatas=[metadata or {}]
                )
            else:
                self.collection.add(
                    ids=[id],
                    documents=[text],
                    metadatas=[metadata or {}]
                )
        except Exception as e:
            print(f"ChromaDB add error: {e}")
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, str, float, Dict]]:
        """Search for similar documents."""
        if not self.available or not self.collection:
            return []
        
        try:
            embedding = self._embed(query) if self.embedding_model else None
            
            if embedding:
                results = self.collection.query(
                    query_embeddings=[embedding],
                    n_results=limit
                )
            else:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=limit
                )
            
            output = []
            if results and results['ids']:
                for i in range(len(results['ids'][0])):
                    doc_id = results['ids'][0][i]
                    document = results['documents'][0][i] if results.get('documents') else ""
                    distance = results['distances'][0][i] if results.get('distances') else 0
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    # Convert distance to similarity (ChromaDB uses cosine distance)
                    similarity = 1 - distance
                    output.append((doc_id, document, similarity, metadata))
            
            return output
        except Exception as e:
            print(f"ChromaDB search error: {e}")
            return []
    
    def delete(self, id: str):
        """Delete a document from the store."""
        if not self.available or not self.collection:
            return
        
        try:
            self.collection.delete(ids=[id])
        except Exception as e:
            print(f"ChromaDB delete error: {e}")
    
    def count(self) -> int:
        """Get the number of documents in the store."""
        if not self.available or not self.collection:
            return 0
        return self.collection.count()
    
    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        return {
            "available": self.available,
            "using_sentence_transformers": SENTENCE_TRANSFORMERS_AVAILABLE,
            "document_count": self.count()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# RAG (RETRIEVAL AUGMENTED GENERATION)
# ═══════════════════════════════════════════════════════════════════════════════

class RAGSystem:
    """Retrieval Augmented Generation system for Lumina."""
    
    def __init__(self, vector_store: ChromaVectorStore, llm_client=None):
        self.vector_store = vector_store
        self.llm_client = llm_client
        
        # Document collection for ingestion
        self.documents: Dict[str, Dict] = {}
        self.chunk_size = 500
        self.chunk_overlap = 50
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                if break_point > self.chunk_size * 0.5:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - self.chunk_overlap
        
        return chunks
    
    def ingest_document(self, doc_id: str, text: str, metadata: Dict = None):
        """Ingest a document into the RAG system."""
        chunks = self._chunk_text(text)
        
        self.documents[doc_id] = {
            "text": text,
            "metadata": metadata or {},
            "chunks": len(chunks),
            "ingested_at": datetime.now().isoformat()
        }
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            chunk_metadata = {
                **(metadata or {}),
                "doc_id": doc_id,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            self.vector_store.add(chunk_id, chunk, chunk_metadata)
        
        return len(chunks)
    
    def ingest_file(self, file_path: Path) -> int:
        """Ingest a file into the RAG system."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            doc_id = hashlib.md5(str(file_path).encode()).hexdigest()[:12]
            metadata = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_type": file_path.suffix
            }
            
            return self.ingest_document(doc_id, text, metadata)
        except Exception as e:
            print(f"Error ingesting file {file_path}: {e}")
            return 0
    
    def retrieve(self, query: str, limit: int = 5) -> List[Dict]:
        """Retrieve relevant documents for a query."""
        results = self.vector_store.search(query, limit)
        
        return [
            {
                "id": doc_id,
                "content": content,
                "similarity": similarity,
                "metadata": metadata
            }
            for doc_id, content, similarity, metadata in results
        ]
    
    def generate_with_context(self, query: str, limit: int = 3) -> Dict:
        """Generate a response using retrieved context."""
        # Retrieve relevant context
        context_docs = self.retrieve(query, limit)
        
        # Build context string
        context_text = "\n\n".join([
            f"[Source {i+1}]: {doc['content']}"
            for i, doc in enumerate(context_docs)
        ])
        
        # If LLM available, generate response
        if self.llm_client:
            try:
                prompt = f"""Based on the following context, answer the question.

Context:
{context_text}

Question: {query}

Answer:"""
                
                response = self.llm_client.chat(
                    model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.3}
                )
                
                return {
                    "query": query,
                    "answer": response.message.content,
                    "sources": context_docs
                }
            except Exception as e:
                print(f"LLM error in RAG: {e}")
        
        # Return context without generation
        return {
            "query": query,
            "answer": None,
            "sources": context_docs
        }
    
    def get_stats(self) -> Dict:
        """Get RAG system statistics."""
        return {
            "documents_ingested": len(self.documents),
            "vector_store": self.vector_store.get_stats(),
            "llm_available": self.llm_client is not None
        }


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
    """
    Lumina's enhanced memory system with:
    - Episodic memory (experiences with emotional context)
    - Semantic memory (facts and concepts)
    - Procedural memory (how to do things)
    - Working memory (short-term context)
    - Dream consolidation (memory processing during idle)
    - RAG (retrieval augmented generation)
    - ChromaDB vector store
    """
    
    def __init__(self, db_path: Path, workspace_path: Path, llm_client=None):
        self.db_path = db_path
        self.workspace_path = workspace_path
        self.llm_client = llm_client
        
        # Core memory stores
        self.store = SemanticMemoryStore(db_path, workspace_path)
        self.knowledge = self.store.knowledge_graph
        
        # Working memory (short-term context)
        self.working = WorkingMemory(capacity=12)
        
        # Initialize ChromaDB vector store
        self.vector_store = ChromaVectorStore(workspace_path)
        
        # Initialize RAG system
        self.rag = RAGSystem(self.vector_store, llm_client)
        
        # Dream consolidation system
        self.dreamer = DreamConsolidation(self.store, llm_client)
        
        # Session tracking
        self.session_id = hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:8]
        self.current_cycle = 0
        
        print(f"    🧠 Enhanced Memory: {len(self.store.memories)} memories loaded")
        print(f"    🧠 Knowledge Graph: {len(self.knowledge.concepts)} concepts")
        print(f"    🧠 Working Memory: {self.working.capacity} slot capacity")
        if CHROMADB_AVAILABLE:
            print(f"    🔮 ChromaDB: {self.vector_store.count()} vectors")
        else:
            print("    🔮 ChromaDB: Not available (install chromadb)")
    
    def set_cycle(self, cycle_number: int):
        """Update the current cognitive cycle number."""
        self.current_cycle = cycle_number
    
    def remember(self, content: str, memory_type: str = "episodic",
                importance: float = 0.5, tags: List[str] = None,
                emotional_state: Dict[str, float] = None) -> Memory:
        """Store a new memory with full episodic context."""
        memory = self.store.store(content, memory_type, importance, tags)
        
        # Add episodic context
        memory.cycle_number = self.current_cycle
        memory.session_id = self.session_id
        memory.base_importance = importance
        
        if emotional_state:
            memory.emotional_state = emotional_state
            # Calculate emotional valence (positive vs negative)
            positive = sum(v for k, v in emotional_state.items() 
                          if k in ['joy', 'love', 'satisfaction', 'curiosity', 'wonder'])
            negative = sum(v for k, v in emotional_state.items() 
                          if k in ['sadness', 'fear', 'anger', 'frustration'])
            memory.emotional_valence = (positive - negative) / max(positive + negative, 1)
        
        # Also add to working memory for short-term access
        self.working.add(content, memory_type, importance, emotional_state)
        
        self.store._save_memory(memory)
        return memory
    
    def think(self, thought: str, importance: float = 0.3):
        """Add a thought to working memory without storing long-term."""
        return self.working.add(thought, "thought", importance)
    
    def focus_on(self, content: str):
        """Set the current focus of attention."""
        self.working.set_focus(content)
    
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
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WORKING MEMORY METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_working_memory(self) -> List[Dict]:
        """Get current working memory contents."""
        return self.working.items
    
    def get_working_memory_summary(self) -> str:
        """Get a summary of working memory."""
        return self.working.summarize()
    
    def clear_working_memory(self) -> List[Dict]:
        """Clear working memory and get items that should be consolidated."""
        important_items = self.working.clear()
        
        # Consolidate important items to long-term memory
        for item in important_items:
            self.remember(
                item["content"],
                memory_type=item["type"],
                importance=item["importance"],
                emotional_state=item.get("emotional_context")
            )
        
        return important_items
    
    def push_context(self, context: str):
        """Push a context onto the working memory stack."""
        self.working.push_context(context)
    
    def pop_context(self) -> Optional[str]:
        """Pop a context from the working memory stack."""
        return self.working.pop_context()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DREAM CONSOLIDATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def dream(self, duration_minutes: int = 5) -> Dict:
        """
        Run a dream consolidation cycle.
        This should be called during idle time or "rest" periods.
        """
        # First, consolidate working memory
        self.clear_working_memory()
        
        # Then run dream consolidation
        return self.dreamer.consolidate(duration_minutes)
    
    def get_dream_log(self, n: int = 10) -> List[Dict]:
        """Get recent dream logs."""
        return self.dreamer.get_dream_log(n)
    
    def get_unconsolidated_count(self) -> int:
        """Get count of memories that haven't been dream-consolidated."""
        return sum(1 for m in self.store.memories.values() if not m.consolidated)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MEMORY REINFORCEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def reinforce(self, memory_id: str):
        """Reinforce a memory, making it stronger and less likely to decay."""
        if memory_id in self.store.memories:
            memory = self.store.memories[memory_id]
            memory.reinforce()
            self.store._save_memory(memory)
    
    def get_strongest_memories(self, n: int = 10) -> List[Memory]:
        """Get the strongest memories by current importance."""
        memories = list(self.store.memories.values())
        memories.sort(key=lambda m: m.decay_importance(), reverse=True)
        return memories[:n]
    
    def get_emotional_memories(self, valence: str = "positive", n: int = 10) -> List[Memory]:
        """Get memories by emotional valence."""
        memories = list(self.store.memories.values())
        
        if valence == "positive":
            filtered = [m for m in memories if m.emotional_valence > 0.3]
        elif valence == "negative":
            filtered = [m for m in memories if m.emotional_valence < -0.3]
        else:
            filtered = memories
        
        filtered.sort(key=lambda m: abs(m.emotional_valence), reverse=True)
        return filtered[:n]
    
    def get_stats(self) -> Dict:
        """Get comprehensive memory system statistics."""
        stats = self.store.get_stats()
        stats["rag"] = self.rag.get_stats()
        
        # Working memory stats
        stats["working_memory"] = {
            "current_size": len(self.working.items),
            "capacity": self.working.capacity,
            "focus": self.working.focus is not None,
            "context_depth": len(self.working.context_stack)
        }
        
        # Dream consolidation stats
        stats["consolidation"] = {
            "unconsolidated_memories": self.get_unconsolidated_count(),
            "dream_cycles": len(self.dreamer.dream_log),
            "last_dream": self.dreamer.dream_log[-1]["timestamp"] if self.dreamer.dream_log else None
        }
        
        # Emotional memory stats
        positive_memories = len([m for m in self.store.memories.values() if m.emotional_valence > 0.3])
        negative_memories = len([m for m in self.store.memories.values() if m.emotional_valence < -0.3])
        
        stats["emotional"] = {
            "positive_memories": positive_memories,
            "negative_memories": negative_memories,
            "neutral_memories": len(self.store.memories) - positive_memories - negative_memories
        }
        
        return stats
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RAG METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def ingest_document(self, text: str, metadata: Dict = None) -> int:
        """Ingest a document into the RAG system."""
        doc_id = hashlib.md5(text[:100].encode()).hexdigest()[:12]
        return self.rag.ingest_document(doc_id, text, metadata)
    
    def ingest_file(self, file_path: Path) -> int:
        """Ingest a file into the RAG system."""
        return self.rag.ingest_file(file_path)
    
    def query_with_context(self, query: str) -> Dict:
        """Query using RAG for contextual answers."""
        return self.rag.generate_with_context(query)
    
    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Perform semantic search on vector store."""
        return self.rag.retrieve(query, limit)
    
    def add_to_vector_store(self, text: str, metadata: Dict = None) -> str:
        """Add a single item to the vector store."""
        doc_id = hashlib.md5(f"{text}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        self.vector_store.add(doc_id, text, metadata)
        return doc_id


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_memory(db_path: Path, workspace_path: Path, llm_client=None) -> LuminaMemory:
    """Initialize Lumina's enhanced memory system with RAG."""
    return LuminaMemory(db_path, workspace_path, llm_client)


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

