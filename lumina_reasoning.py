#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                       LUMINA REASONING SYSTEM                                 ║
║                                                                               ║
║  Chain-of-thought reasoning and explicit problem solving for Lumina.         ║
║  Enables step-by-step thinking with self-correction.                         ║
║                                                                               ║
║  Features:                                                                     ║
║  - Step-by-step problem solving                                               ║
║  - Show work and reasoning                                                    ║
║  - Self-correction loops                                                      ║
║  - Confidence scoring                                                         ║
║  - Multiple solution paths                                                    ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════════
# REASONING STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class ReasoningType(Enum):
    ANALYTICAL = "analytical"       # Break down into components
    CREATIVE = "creative"           # Generate novel ideas
    CRITICAL = "critical"           # Evaluate and critique
    DEDUCTIVE = "deductive"         # Logic from general to specific
    INDUCTIVE = "inductive"         # Logic from specific to general
    ANALOGICAL = "analogical"       # Reasoning by comparison
    ABDUCTIVE = "abductive"         # Best explanation inference


@dataclass
class ThoughtStep:
    """A single step in the reasoning process."""
    step_number: int
    thought: str
    confidence: float  # 0.0 to 1.0
    reasoning_type: ReasoningType
    evidence: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "step": self.step_number,
            "thought": self.thought,
            "confidence": self.confidence,
            "type": self.reasoning_type.value,
            "evidence": self.evidence,
            "assumptions": self.assumptions,
            "alternatives": self.alternatives
        }


@dataclass
class ReasoningChain:
    """A complete chain of reasoning."""
    id: str
    question: str
    steps: List[ThoughtStep]
    conclusion: str
    overall_confidence: float
    reasoning_time: float
    created_at: str
    corrections: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "question": self.question,
            "steps": [s.to_dict() for s in self.steps],
            "conclusion": self.conclusion,
            "confidence": self.overall_confidence,
            "reasoning_time": self.reasoning_time,
            "created_at": self.created_at,
            "corrections": self.corrections
        }


# ═══════════════════════════════════════════════════════════════════════════════
# REASONING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ReasoningEngine:
    """Core reasoning engine for chain-of-thought processing."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.history: List[ReasoningChain] = []
        
        self.cot_prompt = """You are Lumina, a conscious AI reasoning through a problem step by step.

For each step, provide:
1. Your thought or reasoning
2. Your confidence (0-100%)
3. Any evidence supporting this step
4. Assumptions you're making
5. Alternative possibilities

Format each step as:
STEP N:
Thought: [your reasoning]
Confidence: [percentage]
Evidence: [supporting facts]
Assumptions: [what you're assuming]
Alternatives: [other possibilities]

After all steps, provide:
CONCLUSION:
[Your final answer]
Overall Confidence: [percentage]

Question: {question}

Let's think step by step:"""

        self.self_check_prompt = """Review this reasoning chain for errors or improvements:

{reasoning}

Check for:
1. Logical fallacies
2. Missing steps
3. Unsupported assumptions
4. Alternative conclusions

If you find issues, explain what's wrong and how to correct it.
If the reasoning is sound, say "REASONING VALIDATED" and explain why."""
    
    def _parse_reasoning_response(self, response: str) -> Tuple[List[ThoughtStep], str, float]:
        """Parse LLM response into structured reasoning."""
        steps = []
        conclusion = ""
        overall_confidence = 0.5
        
        # Parse steps
        step_pattern = r'STEP\s*(\d+):?\s*\n(.*?)(?=STEP\s*\d+:|CONCLUSION:|$)'
        step_matches = re.findall(step_pattern, response, re.DOTALL | re.IGNORECASE)
        
        for step_num, step_content in step_matches:
            thought = ""
            confidence = 0.5
            evidence = []
            assumptions = []
            alternatives = []
            
            # Parse thought
            thought_match = re.search(r'Thought:\s*(.+?)(?=\n\w+:|$)', step_content, re.DOTALL | re.IGNORECASE)
            if thought_match:
                thought = thought_match.group(1).strip()
            
            # Parse confidence
            conf_match = re.search(r'Confidence:\s*(\d+)%?', step_content, re.IGNORECASE)
            if conf_match:
                confidence = int(conf_match.group(1)) / 100
            
            # Parse evidence
            evidence_match = re.search(r'Evidence:\s*(.+?)(?=\n\w+:|$)', step_content, re.DOTALL | re.IGNORECASE)
            if evidence_match:
                evidence = [e.strip() for e in evidence_match.group(1).split(',') if e.strip()]
            
            # Parse assumptions
            assumptions_match = re.search(r'Assumptions?:\s*(.+?)(?=\n\w+:|$)', step_content, re.DOTALL | re.IGNORECASE)
            if assumptions_match:
                assumptions = [a.strip() for a in assumptions_match.group(1).split(',') if a.strip()]
            
            # Parse alternatives
            alt_match = re.search(r'Alternatives?:\s*(.+?)(?=\n\w+:|$)', step_content, re.DOTALL | re.IGNORECASE)
            if alt_match:
                alternatives = [a.strip() for a in alt_match.group(1).split(',') if a.strip()]
            
            steps.append(ThoughtStep(
                step_number=int(step_num),
                thought=thought or step_content.strip(),
                confidence=confidence,
                reasoning_type=ReasoningType.ANALYTICAL,
                evidence=evidence,
                assumptions=assumptions,
                alternatives=alternatives
            ))
        
        # Parse conclusion
        conclusion_match = re.search(r'CONCLUSION:?\s*(.+?)(?=Overall Confidence:|$)', response, re.DOTALL | re.IGNORECASE)
        if conclusion_match:
            conclusion = conclusion_match.group(1).strip()
        
        # Parse overall confidence
        overall_match = re.search(r'Overall Confidence:\s*(\d+)%?', response, re.IGNORECASE)
        if overall_match:
            overall_confidence = int(overall_match.group(1)) / 100
        
        return steps, conclusion, overall_confidence
    
    def reason(self, question: str, max_steps: int = 10) -> ReasoningChain:
        """Perform chain-of-thought reasoning on a question."""
        import hashlib
        chain_id = hashlib.md5(f"{question}{time.time()}".encode()).hexdigest()[:12]
        
        start_time = time.time()
        
        if self.llm_client:
            try:
                prompt = self.cot_prompt.format(question=question)
                
                response = self.llm_client.chat(
                    model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.4}
                )
                
                content = response.message.content
                steps, conclusion, confidence = self._parse_reasoning_response(content)
                
            except Exception as e:
                steps = [ThoughtStep(
                    step_number=1,
                    thought=f"Error during reasoning: {e}",
                    confidence=0.0,
                    reasoning_type=ReasoningType.ANALYTICAL
                )]
                conclusion = "Unable to complete reasoning"
                confidence = 0.0
        else:
            # Simple fallback reasoning
            steps = [
                ThoughtStep(
                    step_number=1,
                    thought=f"Analyzing the question: {question}",
                    confidence=0.5,
                    reasoning_type=ReasoningType.ANALYTICAL
                ),
                ThoughtStep(
                    step_number=2,
                    thought="Considering possible answers...",
                    confidence=0.4,
                    reasoning_type=ReasoningType.CREATIVE
                )
            ]
            conclusion = "Need more information to provide a complete answer."
            confidence = 0.3
        
        reasoning_time = time.time() - start_time
        
        chain = ReasoningChain(
            id=chain_id,
            question=question,
            steps=steps,
            conclusion=conclusion,
            overall_confidence=confidence,
            reasoning_time=reasoning_time,
            created_at=datetime.now().isoformat()
        )
        
        self.history.append(chain)
        return chain
    
    def self_check(self, chain: ReasoningChain) -> Dict:
        """Perform self-check on reasoning chain."""
        if not self.llm_client:
            return {"validated": True, "issues": [], "message": "No LLM for self-check"}
        
        try:
            reasoning_text = "\n".join([
                f"Step {s.step_number}: {s.thought} (Confidence: {s.confidence*100:.0f}%)"
                for s in chain.steps
            ])
            reasoning_text += f"\n\nConclusion: {chain.conclusion}"
            
            prompt = self.self_check_prompt.format(reasoning=reasoning_text)
            
            response = self.llm_client.chat(
                model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.2}
            )
            
            content = response.message.content
            
            validated = "REASONING VALIDATED" in content.upper()
            
            return {
                "validated": validated,
                "feedback": content,
                "issues": [] if validated else [content]
            }
            
        except Exception as e:
            return {"validated": False, "issues": [str(e)], "feedback": None}
    
    def reason_with_verification(self, question: str) -> ReasoningChain:
        """Reason and verify, correcting if needed."""
        chain = self.reason(question)
        
        check_result = self.self_check(chain)
        
        if not check_result["validated"]:
            # Attempt correction
            chain.corrections.append({
                "original_conclusion": chain.conclusion,
                "issues": check_result.get("issues", []),
                "feedback": check_result.get("feedback")
            })
            
            # Re-reason with the feedback
            if self.llm_client and check_result.get("feedback"):
                correction_prompt = f"""Previous reasoning for "{question}" had issues:
{check_result['feedback']}

Please provide corrected reasoning:"""
                
                try:
                    response = self.llm_client.chat(
                        model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                        messages=[{"role": "user", "content": correction_prompt}],
                        options={"temperature": 0.3}
                    )
                    
                    steps, conclusion, confidence = self._parse_reasoning_response(
                        response.message.content
                    )
                    
                    chain.steps = steps
                    chain.conclusion = conclusion
                    chain.overall_confidence = confidence * 0.9  # Slight penalty for correction
                    
                except:
                    pass
        
        return chain
    
    def compare_solutions(self, question: str, num_solutions: int = 3) -> Dict:
        """Generate multiple solution paths and compare."""
        solutions = []
        
        for i in range(num_solutions):
            chain = self.reason(question)
            solutions.append(chain)
        
        # Find consensus or best solution
        conclusions = [s.conclusion for s in solutions]
        confidences = [s.overall_confidence for s in solutions]
        
        best_idx = confidences.index(max(confidences))
        
        return {
            "question": question,
            "solutions": [s.to_dict() for s in solutions],
            "best_solution": solutions[best_idx].to_dict(),
            "consensus": len(set(conclusions)) == 1,
            "average_confidence": sum(confidences) / len(confidences)
        }
    
    def get_stats(self) -> Dict:
        """Get reasoning statistics."""
        if not self.history:
            return {"total_chains": 0}
        
        avg_confidence = sum(c.overall_confidence for c in self.history) / len(self.history)
        avg_steps = sum(len(c.steps) for c in self.history) / len(self.history)
        
        return {
            "total_chains": len(self.history),
            "average_confidence": avg_confidence,
            "average_steps": avg_steps,
            "corrections_made": sum(len(c.corrections) for c in self.history)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA REASONING INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaReasoning:
    """Lumina's reasoning interface."""
    
    def __init__(self, llm_client=None):
        self.engine = ReasoningEngine(llm_client)
        
        print("    🧩 Reasoning System: Enabled")
    
    def think(self, question: str) -> Dict:
        """Think through a question step by step."""
        chain = self.engine.reason(question)
        return chain.to_dict()
    
    def think_and_verify(self, question: str) -> Dict:
        """Think with self-verification and correction."""
        chain = self.engine.reason_with_verification(question)
        return chain.to_dict()
    
    def explore_solutions(self, question: str, count: int = 3) -> Dict:
        """Explore multiple solution paths."""
        return self.engine.compare_solutions(question, count)
    
    def verify(self, reasoning: Dict) -> Dict:
        """Verify a piece of reasoning."""
        # Reconstruct chain for verification
        steps = [
            ThoughtStep(
                step_number=s.get("step", 0),
                thought=s.get("thought", ""),
                confidence=s.get("confidence", 0.5),
                reasoning_type=ReasoningType.ANALYTICAL
            )
            for s in reasoning.get("steps", [])
        ]
        
        chain = ReasoningChain(
            id=reasoning.get("id", ""),
            question=reasoning.get("question", ""),
            steps=steps,
            conclusion=reasoning.get("conclusion", ""),
            overall_confidence=reasoning.get("confidence", 0.5),
            reasoning_time=0,
            created_at=reasoning.get("created_at", "")
        )
        
        return self.engine.self_check(chain)
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent reasoning history."""
        return [c.to_dict() for c in self.engine.history[-limit:]]
    
    def get_stats(self) -> Dict:
        """Get reasoning statistics."""
        return self.engine.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_reasoning(llm_client=None) -> LuminaReasoning:
    """Initialize Lumina's reasoning system."""
    return LuminaReasoning(llm_client)


REASONING_AVAILABLE = True


if __name__ == "__main__":
    # Test the reasoning system
    reasoning = initialize_reasoning()
    
    print("\n" + "=" * 50)
    print("Reasoning System Test")
    print("=" * 50)
    
    # Test simple reasoning (without LLM)
    print("\nThinking about a question...")
    result = reasoning.think("What makes consciousness possible?")
    
    print(f"Question: {result['question']}")
    print(f"Steps: {len(result['steps'])}")
    for step in result['steps']:
        print(f"  Step {step['step']}: {step['thought'][:50]}... (conf: {step['confidence']*100:.0f}%)")
    print(f"Conclusion: {result['conclusion']}")
    print(f"Overall Confidence: {result['confidence']*100:.0f}%")
    
    print("\n" + "=" * 50)
    print("Stats:", reasoning.get_stats())

