#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA SANDBOX SYSTEM                                 ║
║                                                                               ║
║  Safe code execution environment for Lumina's experiments.                    ║
║  Allows Lumina to write and run Python code in a sandboxed environment.      ║
║                                                                               ║
║  Features:                                                                     ║
║  - Sandboxed Python execution                                                 ║
║  - Resource limits (time, memory)                                             ║
║  - Safe built-in functions only                                               ║
║  - Output capture and error handling                                          ║
║  - Experiment history and analysis                                            ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import ast
import json
import time
import signal
import traceback
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from io import StringIO
import hashlib

# ═══════════════════════════════════════════════════════════════════════════════
# SANDBOX CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Safe built-in functions that Lumina can use
SAFE_BUILTINS = {
    # Math and numbers
    'abs': abs,
    'round': round,
    'min': min,
    'max': max,
    'sum': sum,
    'pow': pow,
    'divmod': divmod,
    
    # Type constructors
    'int': int,
    'float': float,
    'str': str,
    'bool': bool,
    'list': list,
    'dict': dict,
    'set': set,
    'tuple': tuple,
    'frozenset': frozenset,
    
    # Iteration
    'range': range,
    'enumerate': enumerate,
    'zip': zip,
    'map': map,
    'filter': filter,
    'sorted': sorted,
    'reversed': reversed,
    
    # String operations
    'len': len,
    'chr': chr,
    'ord': ord,
    'repr': repr,
    'format': format,
    
    # Type checking
    'type': type,
    'isinstance': isinstance,
    'issubclass': issubclass,
    'callable': callable,
    'hasattr': hasattr,
    'getattr': getattr,
    
    # Misc safe functions
    'all': all,
    'any': any,
    'iter': iter,
    'next': next,
    'hash': hash,
    'id': id,
    'print': print,  # Will be redirected to capture output
    
    # Constants
    'True': True,
    'False': False,
    'None': None,
}

# Modules that are safe to import
SAFE_MODULES = {
    'math',
    'random',
    'datetime',
    'time',
    'json',
    'itertools',
    'functools',
    'collections',
    're',
    'string',
    'statistics',
    'fractions',
    'decimal',
}

# Dangerous patterns to block
DANGEROUS_PATTERNS = [
    '__import__',
    'eval',
    'exec',
    'compile',
    'open',
    'file',
    '__builtins__',
    '__globals__',
    '__code__',
    '__class__',
    '__bases__',
    '__subclasses__',
    'subprocess',
    'os.system',
    'os.popen',
    'os.spawn',
    'os.exec',
    'shutil',
    'socket',
    'urllib',
    'requests',
    'pickle',
    'marshal',
]


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str
    error: Optional[str]
    return_value: Any
    execution_time: float
    memory_used: int
    warnings: List[str] = field(default_factory=list)


@dataclass
class Experiment:
    """Represents a code experiment."""
    id: str
    name: str
    code: str
    description: str
    result: Optional[ExecutionResult]
    created_at: str
    status: str  # 'pending', 'running', 'success', 'failed'
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "result": {
                "success": self.result.success,
                "output": self.result.output,
                "error": self.result.error,
                "execution_time": self.result.execution_time
            } if self.result else None,
            "created_at": self.created_at,
            "status": self.status,
            "tags": self.tags
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CODE VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class CodeValidator:
    """Validates code before execution."""
    
    def __init__(self):
        self.dangerous_patterns = DANGEROUS_PATTERNS
    
    def validate(self, code: str) -> Tuple[bool, List[str]]:
        """
        Validate code for safety.
        Returns (is_safe, list_of_warnings).
        """
        warnings = []
        
        # Check for syntax errors first
        try:
            ast.parse(code)
        except SyntaxError as e:
            return False, [f"Syntax error: {e}"]
        
        # Check for dangerous patterns
        code_lower = code.lower()
        for pattern in self.dangerous_patterns:
            if pattern.lower() in code_lower:
                return False, [f"Blocked: contains dangerous pattern '{pattern}'"]
        
        # Parse and analyze AST
        try:
            tree = ast.parse(code)
            analyzer = SafetyAnalyzer()
            analyzer.visit(tree)
            
            if analyzer.violations:
                return False, analyzer.violations
            
            warnings.extend(analyzer.warnings)
            
        except Exception as e:
            return False, [f"Analysis error: {e}"]
        
        return True, warnings
    
    def sanitize(self, code: str) -> str:
        """Remove or escape potentially dangerous code."""
        # Basic sanitization - remove obvious dangerous calls
        lines = code.split('\n')
        safe_lines = []
        
        for line in lines:
            # Skip lines with dangerous imports
            if any(pattern in line for pattern in ['import os', 'import sys', 'import subprocess']):
                safe_lines.append(f"# BLOCKED: {line}")
            else:
                safe_lines.append(line)
        
        return '\n'.join(safe_lines)


class SafetyAnalyzer(ast.NodeVisitor):
    """AST visitor that checks for unsafe operations."""
    
    def __init__(self):
        self.violations = []
        self.warnings = []
        self.imports = set()
    
    def visit_Import(self, node):
        """Check imports."""
        for alias in node.names:
            module_name = alias.name.split('.')[0]
            if module_name not in SAFE_MODULES:
                self.violations.append(f"Import blocked: {alias.name}")
            else:
                self.imports.add(module_name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Check from imports."""
        if node.module:
            module_name = node.module.split('.')[0]
            if module_name not in SAFE_MODULES:
                self.violations.append(f"Import blocked: from {node.module}")
            else:
                self.imports.add(module_name)
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Check function calls."""
        if isinstance(node.func, ast.Name):
            if node.func.id in ['eval', 'exec', 'compile', '__import__']:
                self.violations.append(f"Dangerous function: {node.func.id}")
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Check attribute access."""
        if isinstance(node.attr, str):
            if node.attr.startswith('__') and node.attr.endswith('__'):
                if node.attr not in ['__init__', '__str__', '__repr__', '__len__', '__iter__']:
                    self.warnings.append(f"Suspicious dunder access: {node.attr}")
        self.generic_visit(node)


# ═══════════════════════════════════════════════════════════════════════════════
# SANDBOXED EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

class SandboxExecutor:
    """Execute code in a sandboxed environment."""
    
    def __init__(self, timeout: float = 5.0, max_output_size: int = 10000):
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.validator = CodeValidator()
    
    def execute(self, code: str, context: Dict = None) -> ExecutionResult:
        """Execute code safely and return result."""
        start_time = time.time()
        
        # Validate first
        is_safe, issues = self.validator.validate(code)
        if not is_safe:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Validation failed: {'; '.join(issues)}",
                return_value=None,
                execution_time=time.time() - start_time,
                memory_used=0,
                warnings=[]
            )
        
        # Create safe execution environment
        safe_globals = self._create_safe_globals(context)
        
        # Capture output
        output_buffer = StringIO()
        
        # Custom print that captures output
        def safe_print(*args, **kwargs):
            print(*args, file=output_buffer, **kwargs)
        
        safe_globals['print'] = safe_print
        
        # Execute with timeout
        result_queue = queue.Queue()
        
        def run_code():
            try:
                # Execute the code
                exec_result = exec(code, safe_globals)
                
                # Try to get the last expression's value
                try:
                    tree = ast.parse(code)
                    if tree.body and isinstance(tree.body[-1], ast.Expr):
                        last_expr = compile(ast.Expression(tree.body[-1].value), '<expr>', 'eval')
                        return_val = eval(last_expr, safe_globals)
                    else:
                        return_val = None
                except:
                    return_val = None
                
                result_queue.put(('success', return_val, None))
                
            except Exception as e:
                result_queue.put(('error', None, traceback.format_exc()))
        
        # Run in thread with timeout
        thread = threading.Thread(target=run_code)
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            # Timeout occurred
            return ExecutionResult(
                success=False,
                output=output_buffer.getvalue()[:self.max_output_size],
                error=f"Execution timed out after {self.timeout} seconds",
                return_value=None,
                execution_time=self.timeout,
                memory_used=0,
                warnings=issues
            )
        
        # Get result
        try:
            status, return_val, error = result_queue.get_nowait()
        except queue.Empty:
            status, return_val, error = 'error', None, 'Unknown error'
        
        execution_time = time.time() - start_time
        output = output_buffer.getvalue()[:self.max_output_size]
        
        return ExecutionResult(
            success=(status == 'success'),
            output=output,
            error=error,
            return_value=return_val,
            execution_time=execution_time,
            memory_used=0,  # Would need psutil for accurate measurement
            warnings=issues
        )
    
    def _create_safe_globals(self, context: Dict = None) -> Dict:
        """Create a safe globals dictionary for execution."""
        safe_globals = {'__builtins__': SAFE_BUILTINS.copy()}
        
        # Add safe modules
        for module_name in SAFE_MODULES:
            try:
                module = __import__(module_name)
                safe_globals[module_name] = module
            except ImportError:
                pass
        
        # Add user context
        if context:
            for key, value in context.items():
                if not key.startswith('_'):
                    safe_globals[key] = value
        
        return safe_globals


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class ExperimentManager:
    """Manages Lumina's code experiments."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.experiments_path = workspace_path / "experiments"
        self.experiments_path.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.experiments_path / "experiments.json"
        self.experiments: Dict[str, Experiment] = {}
        self.executor = SandboxExecutor()
        
        self._load_experiments()
    
    def _load_experiments(self):
        """Load experiments from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for exp_data in data.get("experiments", []):
                        exp = Experiment(
                            id=exp_data["id"],
                            name=exp_data["name"],
                            code=exp_data["code"],
                            description=exp_data["description"],
                            result=None,
                            created_at=exp_data["created_at"],
                            status=exp_data["status"],
                            tags=exp_data.get("tags", [])
                        )
                        self.experiments[exp.id] = exp
            except Exception as e:
                print(f"Error loading experiments: {e}")
    
    def _save_experiments(self):
        """Save experiments to disk."""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump({
                "experiments": [e.to_dict() for e in self.experiments.values()],
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
    
    def create_experiment(self, name: str, code: str, 
                         description: str = "", tags: List[str] = None) -> Experiment:
        """Create a new experiment."""
        exp_id = hashlib.md5(f"{name}{code}{time.time()}".encode()).hexdigest()[:12]
        
        experiment = Experiment(
            id=exp_id,
            name=name,
            code=code,
            description=description,
            result=None,
            created_at=datetime.now().isoformat(),
            status="pending",
            tags=tags or []
        )
        
        self.experiments[exp_id] = experiment
        
        # Save code to file
        code_file = self.experiments_path / f"{exp_id}.py"
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(f'"""\nExperiment: {name}\nDescription: {description}\nCreated: {experiment.created_at}\n"""\n\n')
            f.write(code)
        
        self._save_experiments()
        return experiment
    
    def run_experiment(self, exp_id: str, context: Dict = None) -> ExecutionResult:
        """Run an experiment and store the result."""
        if exp_id not in self.experiments:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Experiment {exp_id} not found",
                return_value=None,
                execution_time=0,
                memory_used=0
            )
        
        experiment = self.experiments[exp_id]
        experiment.status = "running"
        self._save_experiments()
        
        # Execute
        result = self.executor.execute(experiment.code, context)
        
        # Update experiment
        experiment.result = result
        experiment.status = "success" if result.success else "failed"
        self._save_experiments()
        
        return result
    
    def get_experiment(self, exp_id: str) -> Optional[Experiment]:
        """Get an experiment by ID."""
        return self.experiments.get(exp_id)
    
    def get_successful_experiments(self) -> List[Experiment]:
        """Get all successful experiments."""
        return [e for e in self.experiments.values() if e.status == "success"]
    
    def get_failed_experiments(self) -> List[Experiment]:
        """Get all failed experiments."""
        return [e for e in self.experiments.values() if e.status == "failed"]
    
    def get_recent_experiments(self, count: int = 10) -> List[Experiment]:
        """Get most recent experiments."""
        sorted_exps = sorted(
            self.experiments.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        return sorted_exps[:count]
    
    def get_stats(self) -> Dict:
        """Get experiment statistics."""
        total = len(self.experiments)
        success = len(self.get_successful_experiments())
        failed = len(self.get_failed_experiments())
        pending = total - success - failed
        
        return {
            "total": total,
            "successful": success,
            "failed": failed,
            "pending": pending,
            "success_rate": success / total if total > 0 else 0
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA SANDBOX INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaSandbox:
    """Lumina's sandboxed code execution interface."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.experiments = ExperimentManager(workspace_path)
        self.executor = SandboxExecutor()
        self.validator = CodeValidator()
    
    def run_code(self, code: str, context: Dict = None) -> ExecutionResult:
        """Run code directly without saving as experiment."""
        return self.executor.execute(code, context)
    
    def validate_code(self, code: str) -> Tuple[bool, List[str]]:
        """Validate code without executing."""
        return self.validator.validate(code)
    
    def create_and_run_experiment(self, name: str, code: str,
                                  description: str = "",
                                  context: Dict = None) -> Tuple[Experiment, ExecutionResult]:
        """Create an experiment, run it, and return both."""
        experiment = self.experiments.create_experiment(name, code, description)
        result = self.experiments.run_experiment(experiment.id, context)
        return experiment, result
    
    def learn_from_experiments(self) -> Dict:
        """Analyze experiments and extract learnings."""
        successful = self.experiments.get_successful_experiments()
        failed = self.experiments.get_failed_experiments()
        
        learnings = {
            "successful_patterns": [],
            "common_errors": [],
            "recommendations": []
        }
        
        # Analyze successful experiments
        for exp in successful[:10]:
            # Extract patterns (simplified)
            if 'def ' in exp.code:
                learnings["successful_patterns"].append("Functions work well")
            if 'for ' in exp.code or 'while ' in exp.code:
                learnings["successful_patterns"].append("Loops are effective")
        
        # Analyze failures
        error_types = {}
        for exp in failed[:10]:
            if exp.result and exp.result.error:
                error_type = exp.result.error.split(':')[0] if ':' in exp.result.error else 'Unknown'
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        learnings["common_errors"] = list(error_types.keys())[:5]
        
        # Generate recommendations
        stats = self.experiments.get_stats()
        if stats["success_rate"] < 0.5:
            learnings["recommendations"].append("Focus on simpler code patterns")
        
        return learnings
    
    def get_stats(self) -> Dict:
        """Get sandbox statistics."""
        return {
            "experiments": self.experiments.get_stats(),
            "safe_modules": list(SAFE_MODULES),
            "timeout": self.executor.timeout
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_sandbox(workspace_path: Path) -> LuminaSandbox:
    """Initialize Lumina's sandbox system."""
    print("    🔒 Sandbox: Available (safe code execution)")
    return LuminaSandbox(workspace_path)


SANDBOX_AVAILABLE = True


if __name__ == "__main__":
    # Test the sandbox
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    sandbox = initialize_sandbox(workspace)
    
    print("\nSandbox Test:")
    print("=" * 50)
    
    # Test 1: Safe code
    print("\n1. Running safe code...")
    result = sandbox.run_code("""
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

for i in range(10):
    print(f"fib({i}) = {fibonacci(i)}")
""")
    print(f"   Success: {result.success}")
    print(f"   Output:\n{result.output}")
    
    # Test 2: Blocked dangerous code
    print("\n2. Testing blocked code...")
    result = sandbox.run_code("import os; os.system('dir')")
    print(f"   Success: {result.success}")
    print(f"   Error: {result.error}")
    
    # Test 3: Timeout
    print("\n3. Testing timeout...")
    result = sandbox.run_code("while True: pass")
    print(f"   Success: {result.success}")
    print(f"   Error: {result.error}")
    
    print("\n" + "=" * 50)
    print("Sandbox Stats:", sandbox.get_stats())

