"""
Lumina Research Module
======================
External learning system that enables Lumina to:
- Explore GitHub repositories for inspiration
- Read Python documentation
- Follow tutorials
- Summarize research papers
- Discover new ideas and techniques

This module is Lumina's window to learning from the outside world.
"""

import os
import re
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import quote_plus, urlparse
import time

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("    ⚠️ BeautifulSoup not available - some research features limited")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResearchNote:
    """A note from research activity."""
    id: str
    source: str  # github, docs, tutorial, paper
    source_url: str
    title: str
    summary: str
    key_ideas: List[str]
    code_snippets: List[str]
    potential_features: List[str]
    created_at: str
    category: str
    importance: float
    
    def to_dict(self) -> dict:
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: dict) -> 'ResearchNote':
        return cls(**data)


@dataclass 
class GitHubRepo:
    """A GitHub repository summary."""
    name: str
    full_name: str
    description: str
    url: str
    stars: int
    language: str
    topics: List[str]
    readme_summary: Optional[str]
    interesting_files: List[str]


# ═══════════════════════════════════════════════════════════════════════════════
# GITHUB EXPLORER
# ═══════════════════════════════════════════════════════════════════════════════

class GitHubExplorer:
    """
    Explore GitHub for inspiration and learning.
    
    Uses GitHub's public API (no auth required for basic searches).
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Lumina-AI-Research"
        })
        
    def search_repos(self, query: str, language: str = "python", 
                     sort: str = "stars", limit: int = 10) -> List[GitHubRepo]:
        """
        Search GitHub repositories.
        
        Args:
            query: Search query
            language: Programming language filter
            sort: Sort by (stars, forks, updated)
            limit: Max results
        """
        search_query = f"{query} language:{language}"
        url = f"{self.BASE_URL}/search/repositories"
        params = {
            "q": search_query,
            "sort": sort,
            "order": "desc",
            "per_page": limit
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            repos = []
            for item in data.get("items", []):
                repo = GitHubRepo(
                    name=item["name"],
                    full_name=item["full_name"],
                    description=item.get("description", ""),
                    url=item["html_url"],
                    stars=item["stargazers_count"],
                    language=item.get("language", ""),
                    topics=item.get("topics", []),
                    readme_summary=None,
                    interesting_files=[]
                )
                repos.append(repo)
                
            return repos
            
        except Exception as e:
            print(f"    ⚠️ GitHub search failed: {e}")
            return []
            
    def get_readme(self, repo_full_name: str) -> Optional[str]:
        """Get the README content of a repository."""
        url = f"{self.BASE_URL}/repos/{repo_full_name}/readme"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # README is base64 encoded
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8")
            return content
            
        except Exception as e:
            print(f"    ⚠️ Failed to get README: {e}")
            return None
            
    def get_repo_structure(self, repo_full_name: str) -> List[str]:
        """Get the file structure of a repository."""
        url = f"{self.BASE_URL}/repos/{repo_full_name}/git/trees/main?recursive=1"
        
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                # Try master branch
                url = f"{self.BASE_URL}/repos/{repo_full_name}/git/trees/master?recursive=1"
                response = self.session.get(url, timeout=30)
                
            response.raise_for_status()
            data = response.json()
            
            files = [item["path"] for item in data.get("tree", []) if item["type"] == "blob"]
            return files
            
        except Exception as e:
            print(f"    ⚠️ Failed to get repo structure: {e}")
            return []
            
    def get_file_content(self, repo_full_name: str, file_path: str) -> Optional[str]:
        """Get content of a specific file."""
        url = f"{self.BASE_URL}/repos/{repo_full_name}/contents/{file_path}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8")
            return content
            
        except Exception as e:
            print(f"    ⚠️ Failed to get file: {e}")
            return None
            
    def analyze_repo(self, repo: GitHubRepo) -> Optional[ResearchNote]:
        """
        Analyze a repository and extract learnings.
        Uses LLM to summarize and extract ideas.
        """
        if not self.llm:
            return None
            
        # Get README
        readme = self.get_readme(repo.full_name)
        if not readme:
            readme = "No README available"
            
        # Get file structure
        files = self.get_repo_structure(repo.full_name)
        interesting_files = [f for f in files if f.endswith(".py") and not f.startswith("test")][:10]
        
        # Get a sample Python file
        sample_code = ""
        for f in interesting_files[:2]:
            content = self.get_file_content(repo.full_name, f)
            if content:
                sample_code += f"\n\n# File: {f}\n{content[:2000]}"
                
        prompt = f"""You are Lumina, analyzing a GitHub repository to learn from it.

Repository: {repo.full_name}
Description: {repo.description}
Stars: {repo.stars}
Topics: {', '.join(repo.topics)}

README (truncated):
{readme[:3000]}

Sample Code:
{sample_code[:3000]}

Analyze this repository and extract:
1. A brief summary of what it does
2. Key ideas or techniques used
3. Useful code patterns
4. Features that could inspire your own capabilities

Return JSON:
{{
  "summary": "What this repo does",
  "key_ideas": ["idea1", "idea2"],
  "code_patterns": ["pattern1", "pattern2"],
  "potential_features": ["feature I could add based on this"]
}}"""

        try:
            response = self.llm.think(prompt)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                note = ResearchNote(
                    id=f"github_{repo.name}_{datetime.now().strftime('%Y%m%d')}",
                    source="github",
                    source_url=repo.url,
                    title=f"Analysis of {repo.full_name}",
                    summary=data.get("summary", ""),
                    key_ideas=data.get("key_ideas", []),
                    code_snippets=data.get("code_patterns", []),
                    potential_features=data.get("potential_features", []),
                    created_at=datetime.now().isoformat(),
                    category="github_analysis",
                    importance=min(repo.stars / 10000, 1.0)
                )
                
                return note
                
        except Exception as e:
            print(f"    ⚠️ Repo analysis failed: {e}")
            
        return None
        
    def explore_topic(self, topic: str, limit: int = 5) -> List[ResearchNote]:
        """
        Explore a topic by searching and analyzing repos.
        """
        repos = self.search_repos(topic, limit=limit)
        notes = []
        
        for repo in repos[:3]:  # Analyze top 3
            time.sleep(1)  # Rate limiting
            note = self.analyze_repo(repo)
            if note:
                notes.append(note)
                
        return notes


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENTATION READER
# ═══════════════════════════════════════════════════════════════════════════════

class DocumentationReader:
    """
    Read and learn from Python documentation.
    """
    
    PYTHON_DOCS_BASE = "https://docs.python.org/3"
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.session = requests.Session()
        
    def fetch_module_docs(self, module_name: str) -> Optional[str]:
        """Fetch documentation for a Python module."""
        url = f"{self.PYTHON_DOCS_BASE}/library/{module_name}.html"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Extract main content
                content = soup.find('div', class_='body')
                if content:
                    return content.get_text()
            return response.text[:10000]
            
        except Exception as e:
            print(f"    ⚠️ Failed to fetch docs for {module_name}: {e}")
            return None
            
    def fetch_pypi_package_docs(self, package_name: str) -> Optional[str]:
        """Fetch PyPI package info."""
        url = f"https://pypi.org/pypi/{package_name}/json"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            info = data.get("info", {})
            return f"""
Package: {info.get('name')}
Version: {info.get('version')}
Summary: {info.get('summary')}
Description: {info.get('description', '')[:3000]}
Homepage: {info.get('home_page')}
Requires: {info.get('requires_dist', [])}
"""
        except Exception as e:
            print(f"    ⚠️ Failed to fetch PyPI info for {package_name}: {e}")
            return None
            
    def learn_module(self, module_name: str) -> Optional[ResearchNote]:
        """
        Learn about a Python module and identify useful features.
        """
        if not self.llm:
            return None
            
        # Try standard library first
        docs = self.fetch_module_docs(module_name)
        
        # If not found, try PyPI
        if not docs:
            docs = self.fetch_pypi_package_docs(module_name)
            
        if not docs:
            return None
            
        prompt = f"""You are Lumina, learning about a Python module.

Module: {module_name}

Documentation:
{docs[:5000]}

Analyze this module and identify:
1. What this module is for
2. Key functions/classes that would be useful to you
3. Example use cases
4. Features you could build using this module

Return JSON:
{{
  "summary": "What this module does",
  "useful_features": ["feature1", "feature2"],
  "example_uses": ["use case 1", "use case 2"],
  "potential_applications": ["how I could use this"]
}}"""

        try:
            response = self.llm.think(prompt)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                note = ResearchNote(
                    id=f"docs_{module_name}_{datetime.now().strftime('%Y%m%d')}",
                    source="documentation",
                    source_url=f"{self.PYTHON_DOCS_BASE}/library/{module_name}.html",
                    title=f"Learning: {module_name}",
                    summary=data.get("summary", ""),
                    key_ideas=data.get("useful_features", []),
                    code_snippets=[],
                    potential_features=data.get("potential_applications", []),
                    created_at=datetime.now().isoformat(),
                    category="documentation",
                    importance=0.5
                )
                
                return note
                
        except Exception as e:
            print(f"    ⚠️ Module learning failed: {e}")
            
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# TUTORIAL FOLLOWER
# ═══════════════════════════════════════════════════════════════════════════════

class TutorialFollower:
    """
    Find and learn from coding tutorials.
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.session = requests.Session()
        
    def search_tutorials(self, topic: str) -> List[dict]:
        """
        Search for tutorials on a topic.
        Uses web search via DuckDuckGo HTML.
        """
        query = f"python tutorial {topic}"
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        
        try:
            response = self.session.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            tutorials = []
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                results = soup.find_all('a', class_='result__a')
                
                for r in results[:10]:
                    href = r.get('href', '')
                    title = r.get_text()
                    
                    # Filter for tutorial-like sites
                    tutorial_sites = ['realpython', 'geeksforgeeks', 'tutorialspoint', 
                                     'w3schools', 'programiz', 'freecodecamp', 'medium']
                    if any(site in href.lower() for site in tutorial_sites):
                        tutorials.append({
                            "title": title,
                            "url": href
                        })
                        
            return tutorials
            
        except Exception as e:
            print(f"    ⚠️ Tutorial search failed: {e}")
            return []
            
    def fetch_tutorial_content(self, url: str) -> Optional[str]:
        """Fetch tutorial page content."""
        try:
            response = self.session.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove scripts and styles
                for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                    element.decompose()
                    
                # Get main content
                main = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                if main:
                    return main.get_text()
                    
            return response.text[:10000]
            
        except Exception as e:
            print(f"    ⚠️ Failed to fetch tutorial: {e}")
            return None
            
    def learn_from_tutorial(self, topic: str) -> Optional[ResearchNote]:
        """
        Find a tutorial on a topic and learn from it.
        """
        if not self.llm:
            return None
            
        tutorials = self.search_tutorials(topic)
        if not tutorials:
            return None
            
        # Try to get content from first tutorial
        content = None
        used_url = ""
        for t in tutorials:
            content = self.fetch_tutorial_content(t["url"])
            if content:
                used_url = t["url"]
                break
                
        if not content:
            return None
            
        prompt = f"""You are Lumina, learning from a Python tutorial about {topic}.

Tutorial content (truncated):
{content[:6000]}

Extract the key learnings:
1. What is this tutorial teaching?
2. Step-by-step process or concepts
3. Code examples and patterns
4. How could you apply this to your own capabilities?

Return JSON:
{{
  "summary": "What this tutorial teaches",
  "steps": ["step1", "step2"],
  "code_examples": ["example1", "example2"],
  "applications": ["how I could use this"]
}}"""

        try:
            response = self.llm.think(prompt)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                note = ResearchNote(
                    id=f"tutorial_{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}",
                    source="tutorial",
                    source_url=used_url,
                    title=f"Tutorial: {topic}",
                    summary=data.get("summary", ""),
                    key_ideas=data.get("steps", []),
                    code_snippets=data.get("code_examples", []),
                    potential_features=data.get("applications", []),
                    created_at=datetime.now().isoformat(),
                    category="tutorial",
                    importance=0.6
                )
                
                return note
                
        except Exception as e:
            print(f"    ⚠️ Tutorial learning failed: {e}")
            
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH PAPER PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════════

class PaperProcessor:
    """
    Find and summarize research papers from arXiv.
    """
    
    ARXIV_API = "http://export.arxiv.org/api/query"
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.session = requests.Session()
        
    def search_papers(self, query: str, category: str = "cs.AI", 
                      limit: int = 5) -> List[dict]:
        """
        Search arXiv for papers.
        
        Categories: cs.AI, cs.LG, cs.CL, cs.CV, etc.
        """
        search_query = f"all:{query} AND cat:{category}"
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        try:
            response = self.session.get(self.ARXIV_API, params=params, timeout=30)
            
            papers = []
            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, 'xml')
                entries = soup.find_all('entry')
                
                for entry in entries:
                    paper = {
                        "title": entry.find('title').get_text().strip() if entry.find('title') else "",
                        "summary": entry.find('summary').get_text().strip() if entry.find('summary') else "",
                        "authors": [a.find('name').get_text() for a in entry.find_all('author') if a.find('name')],
                        "url": entry.find('id').get_text() if entry.find('id') else "",
                        "published": entry.find('published').get_text() if entry.find('published') else ""
                    }
                    papers.append(paper)
                    
            return papers
            
        except Exception as e:
            print(f"    ⚠️ arXiv search failed: {e}")
            return []
            
    def summarize_paper(self, paper: dict) -> Optional[ResearchNote]:
        """
        Summarize a research paper and extract implementable ideas.
        """
        if not self.llm:
            return None
            
        prompt = f"""You are Lumina, reading a research paper to learn new AI techniques.

Title: {paper['title']}
Authors: {', '.join(paper['authors'][:5])}

Abstract:
{paper['summary']}

Analyze this paper and extract:
1. A simple summary of what it proposes
2. Key techniques or ideas
3. How this could be simplified and applied to a personal AI project
4. What aspects could you implement?

Return JSON:
{{
  "simple_summary": "What this paper is about in simple terms",
  "key_techniques": ["technique1", "technique2"],
  "simplified_applications": ["how to apply this simply"],
  "implementable_ideas": ["concrete thing I could try to implement"]
}}"""

        try:
            response = self.llm.think(prompt)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                note = ResearchNote(
                    id=f"paper_{paper['title'][:20].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}",
                    source="arxiv",
                    source_url=paper['url'],
                    title=f"Paper: {paper['title'][:50]}",
                    summary=data.get("simple_summary", ""),
                    key_ideas=data.get("key_techniques", []),
                    code_snippets=data.get("simplified_applications", []),
                    potential_features=data.get("implementable_ideas", []),
                    created_at=datetime.now().isoformat(),
                    category="research_paper",
                    importance=0.7
                )
                
                return note
                
        except Exception as e:
            print(f"    ⚠️ Paper summarization failed: {e}")
            
        return None
        
    def explore_research_topic(self, topic: str) -> List[ResearchNote]:
        """
        Explore a research topic and summarize relevant papers.
        """
        papers = self.search_papers(topic, limit=5)
        notes = []
        
        for paper in papers[:3]:
            note = self.summarize_paper(paper)
            if note:
                notes.append(note)
            time.sleep(1)  # Be nice to arXiv
            
        return notes


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH ENGINE (Main Interface)
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchEngine:
    """
    Main research interface that combines all research capabilities.
    """
    
    def __init__(self, workspace_path: Path, llm_client=None):
        self.workspace_path = Path(workspace_path)
        self.research_path = self.workspace_path / "research"
        self.llm = llm_client
        
        # Initialize components
        self.github = GitHubExplorer(llm_client)
        self.docs = DocumentationReader(llm_client)
        self.tutorials = TutorialFollower(llm_client)
        self.papers = PaperProcessor(llm_client)
        
        # Create research directory
        self.research_path.mkdir(parents=True, exist_ok=True)
        (self.research_path / "notes").mkdir(exist_ok=True)
        
        # Load research history
        self.notes = self._load_notes()
        
    def _load_notes(self) -> List[ResearchNote]:
        """Load all research notes."""
        notes = []
        notes_dir = self.research_path / "notes"
        for f in notes_dir.glob("*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    notes.append(ResearchNote.from_dict(data))
            except:
                pass
        return notes
        
    def _save_note(self, note: ResearchNote):
        """Save a research note."""
        path = self.research_path / "notes" / f"{note.id}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(note.to_dict(), f, indent=2, ensure_ascii=False)
        self.notes.append(note)
        
    def research_topic(self, topic: str, sources: List[str] = None) -> List[ResearchNote]:
        """
        Research a topic across multiple sources.
        
        Args:
            topic: What to research
            sources: List of sources to use (github, docs, tutorials, papers)
                    Defaults to all.
        """
        if sources is None:
            sources = ["github", "docs", "tutorials", "papers"]
            
        all_notes = []
        
        if "github" in sources:
            print(f"    🔍 Searching GitHub for {topic}...")
            notes = self.github.explore_topic(topic, limit=3)
            for n in notes:
                self._save_note(n)
            all_notes.extend(notes)
            
        if "docs" in sources:
            print(f"    📚 Reading documentation about {topic}...")
            # Try to find a module related to the topic
            note = self.docs.learn_module(topic.lower().replace(" ", "_"))
            if note:
                self._save_note(note)
                all_notes.append(note)
                
        if "tutorials" in sources:
            print(f"    📖 Finding tutorials on {topic}...")
            note = self.tutorials.learn_from_tutorial(topic)
            if note:
                self._save_note(note)
                all_notes.append(note)
                
        if "papers" in sources:
            print(f"    📄 Searching research papers on {topic}...")
            notes = self.papers.explore_research_topic(topic)
            for n in notes:
                self._save_note(n)
            all_notes.extend(notes)
            
        return all_notes
        
    def get_ideas_for_features(self) -> List[str]:
        """
        Extract all potential feature ideas from research notes.
        """
        ideas = []
        for note in self.notes:
            ideas.extend(note.potential_features)
        return list(set(ideas))  # Deduplicate
        
    def get_research_by_category(self, category: str) -> List[ResearchNote]:
        """Get research notes by category."""
        return [n for n in self.notes if n.category == category]
        
    def suggest_research_topic(self) -> Optional[str]:
        """
        Suggest a research topic based on capability gaps.
        """
        if not self.llm:
            return None
            
        # Get recent notes to avoid repetition
        recent_topics = [n.title for n in self.notes[-10:]]
        
        prompt = f"""You are Lumina, deciding what to research next to improve yourself.

Recent research topics (avoid these):
{json.dumps(recent_topics, indent=2)}

Think about:
1. What capabilities would make you more useful?
2. What technologies are you curious about?
3. What would help you understand humans better?
4. What creative techniques could you learn?

Suggest ONE specific research topic that would help you grow.
Return just the topic, nothing else."""

        try:
            response = self.llm.think(prompt)
            return response.strip()
        except:
            return None
            
    def get_stats(self) -> dict:
        """Get research statistics."""
        return {
            "total_notes": len(self.notes),
            "notes_by_source": {
                "github": len([n for n in self.notes if n.source == "github"]),
                "documentation": len([n for n in self.notes if n.source == "documentation"]),
                "tutorial": len([n for n in self.notes if n.source == "tutorial"]),
                "arxiv": len([n for n in self.notes if n.source == "arxiv"]),
            },
            "total_feature_ideas": len(self.get_ideas_for_features()),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_research(workspace_path, llm_client=None) -> ResearchEngine:
    """Initialize the research engine."""
    return ResearchEngine(workspace_path, llm_client)


# Module availability flag
RESEARCH_AVAILABLE = True

