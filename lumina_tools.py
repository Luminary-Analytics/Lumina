#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         LUMINA TOOL USE SYSTEM                                ║
║                                                                               ║
║  Structured function calling and tool orchestration for Lumina.              ║
║  Enables the LLM to decide which tools to use and chain them together.       ║
║                                                                               ║
║  Features:                                                                     ║
║  - Define callable tools/functions                                            ║
║  - LLM decides which tools to use                                            ║
║  - Chain multiple tool calls                                                  ║
║  - Error handling and retry                                                   ║
║  - Tool discovery and learning                                                ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import inspect
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
import re

# ═══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # 'string', 'number', 'boolean', 'array', 'object'
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List] = None


@dataclass
class Tool:
    """Definition of a callable tool."""
    name: str
    description: str
    parameters: List[ToolParameter]
    handler: Callable
    category: str = "general"
    examples: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    
    def to_schema(self) -> Dict:
        """Convert to JSON schema for LLM."""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                properties[param.name]["enum"] = param.enum
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str]
    execution_time: float
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class ToolRegistry:
    """Registry for available tools."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.categories: Dict[str, List[str]] = {}
        self.execution_history: List[ToolResult] = []
    
    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool
        
        if tool.category not in self.categories:
            self.categories[tool.category] = []
        self.categories[tool.category].append(tool.name)
    
    def register_function(self, func: Callable, name: str = None,
                         description: str = None, category: str = "general",
                         requires_confirmation: bool = False) -> Tool:
        """Register a function as a tool (auto-extract parameters)."""
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or f"Execute {tool_name}"
        
        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Infer type
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int or param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"
                elif param.annotation == dict:
                    param_type = "object"
            
            # Check if required
            required = param.default == inspect.Parameter.empty
            default = None if required else param.default
            
            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter: {param_name}",
                required=required,
                default=default
            ))
        
        tool = Tool(
            name=tool_name,
            description=tool_desc,
            parameters=parameters,
            handler=func,
            category=category,
            requires_confirmation=requires_confirmation
        )
        
        self.register(tool)
        return tool
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self, category: str = None) -> List[Tool]:
        """List available tools."""
        if category:
            tool_names = self.categories.get(category, [])
            return [self.tools[name] for name in tool_names]
        return list(self.tools.values())
    
    def get_schemas(self) -> List[Dict]:
        """Get JSON schemas for all tools."""
        return [tool.to_schema() for tool in self.tools.values()]
    
    def execute(self, tool_name: str, arguments: Dict) -> ToolResult:
        """Execute a tool with given arguments."""
        start_time = time.time()
        
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"Tool '{tool_name}' not found",
                execution_time=0,
                timestamp=datetime.now().isoformat()
            )
        
        try:
            # Execute the handler
            result = tool.handler(**arguments)
            
            execution_time = time.time() - start_time
            tool_result = ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                error=None,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            tool_result = ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time,
                timestamp=datetime.now().isoformat()
            )
        
        self.execution_history.append(tool_result)
        return tool_result
    
    def get_stats(self) -> Dict:
        """Get registry statistics."""
        return {
            "total_tools": len(self.tools),
            "categories": {cat: len(tools) for cat, tools in self.categories.items()},
            "executions": len(self.execution_history),
            "success_rate": (
                sum(1 for r in self.execution_history if r.success) / 
                len(self.execution_history) if self.execution_history else 0
            )
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ToolOrchestrator:
    """Orchestrates tool execution based on LLM decisions."""
    
    def __init__(self, registry: ToolRegistry, llm_client=None):
        self.registry = registry
        self.llm_client = llm_client
        self.max_iterations = 5
        self.chain_history: List[Dict] = []
    
    def _parse_tool_call(self, response: str) -> Optional[Dict]:
        """Parse a tool call from LLM response."""
        # Look for JSON-like tool call
        patterns = [
            r'```json\s*({.*?})\s*```',
            r'<tool_call>\s*({.*?})\s*</tool_call>',
            r'TOOL_CALL:\s*({.*?})',
            r'{\s*"tool":\s*".*?".*?}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1) if match.lastindex else match.group())
                except:
                    continue
        
        return None
    
    def plan_and_execute(self, task: str) -> Dict:
        """Plan and execute tools to complete a task."""
        if not self.llm_client:
            return {"error": "No LLM client available"}
        
        # Build prompt with available tools
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.registry.list_tools()
        ])
        
        prompt = f"""You are Lumina, an AI assistant with access to tools.

Available tools:
{tool_descriptions}

To use a tool, respond with a JSON object:
```json
{{"tool": "tool_name", "arguments": {{"param1": "value1"}}}}
```

Task: {task}

Think about which tool(s) you need to use. If no tools are needed, just respond normally."""
        
        results = []
        messages = [{"role": "user", "content": prompt}]
        
        for iteration in range(self.max_iterations):
            try:
                response = self.llm_client.chat(
                    model=os.environ.get("OLLAMA_MODEL", "deepseek-r1:8b"),
                    messages=messages,
                    options={"temperature": 0.3}
                )
                
                content = response.message.content
                
                # Check for tool call
                tool_call = self._parse_tool_call(content)
                
                if tool_call and "tool" in tool_call:
                    tool_name = tool_call["tool"]
                    arguments = tool_call.get("arguments", {})
                    
                    # Execute tool
                    result = self.registry.execute(tool_name, arguments)
                    results.append(result)
                    
                    # Add result to messages for next iteration
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": f"Tool result: {json.dumps(result.result) if result.success else result.error}"
                    })
                else:
                    # No more tool calls
                    break
                    
            except Exception as e:
                results.append(ToolResult(
                    tool_name="orchestrator",
                    success=False,
                    result=None,
                    error=str(e),
                    execution_time=0,
                    timestamp=datetime.now().isoformat()
                ))
                break
        
        chain_result = {
            "task": task,
            "iterations": len(results),
            "results": [
                {
                    "tool": r.tool_name,
                    "success": r.success,
                    "result": r.result,
                    "error": r.error
                }
                for r in results
            ],
            "final_response": content if 'content' in locals() else None
        }
        
        self.chain_history.append(chain_result)
        return chain_result
    
    def execute_chain(self, tool_chain: List[Dict]) -> List[ToolResult]:
        """Execute a predefined chain of tools."""
        results = []
        context = {}
        
        for step in tool_chain:
            tool_name = step["tool"]
            arguments = step.get("arguments", {})
            
            # Substitute context variables
            for key, value in arguments.items():
                if isinstance(value, str) and value.startswith("$"):
                    var_name = value[1:]
                    if var_name in context:
                        arguments[key] = context[var_name]
            
            result = self.registry.execute(tool_name, arguments)
            results.append(result)
            
            # Store result in context
            if result.success:
                context[f"{tool_name}_result"] = result.result
            
            # Stop on failure if not marked as optional
            if not result.success and not step.get("optional", False):
                break
        
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# BUILT-IN TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def create_builtin_tools(workspace_path: Path) -> ToolRegistry:
    """Create a registry with built-in tools."""
    registry = ToolRegistry()
    
    # File operations
    def read_file(path: str) -> str:
        """Read contents of a file."""
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = workspace_path / path
        return file_path.read_text(encoding='utf-8')
    
    def write_file(path: str, content: str) -> str:
        """Write content to a file."""
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = workspace_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return f"Written {len(content)} characters to {path}"
    
    def list_directory(path: str = ".") -> List[str]:
        """List files in a directory."""
        dir_path = Path(path)
        if not dir_path.is_absolute():
            dir_path = workspace_path / path
        return [str(p.relative_to(dir_path)) for p in dir_path.iterdir()]
    
    # Math operations
    def calculate(expression: str) -> float:
        """Evaluate a mathematical expression."""
        # Safe eval for math
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            raise ValueError("Invalid characters in expression")
        return eval(expression)
    
    # Web operations
    def fetch_url(url: str) -> str:
        """Fetch content from a URL."""
        import urllib.request
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode('utf-8')[:5000]  # Limit size
    
    # Time operations
    def get_current_time() -> str:
        """Get the current date and time."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Register tools
    registry.register_function(read_file, category="file", 
                               description="Read contents of a file")
    registry.register_function(write_file, category="file",
                               description="Write content to a file",
                               requires_confirmation=True)
    registry.register_function(list_directory, category="file",
                               description="List files in a directory")
    registry.register_function(calculate, category="math",
                               description="Evaluate a mathematical expression")
    registry.register_function(fetch_url, category="web",
                               description="Fetch content from a URL")
    registry.register_function(get_current_time, category="time",
                               description="Get the current date and time")
    
    return registry


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA TOOLS INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class LuminaTools:
    """Lumina's tool use interface."""
    
    def __init__(self, workspace_path: Path, llm_client=None):
        self.registry = create_builtin_tools(workspace_path)
        self.orchestrator = ToolOrchestrator(self.registry, llm_client)
        
        print(f"    🔧 Tools: {len(self.registry.tools)} available")
    
    def register_tool(self, func: Callable, name: str = None,
                     description: str = None, category: str = "custom") -> Tool:
        """Register a new tool."""
        return self.registry.register_function(func, name, description, category)
    
    def execute(self, tool_name: str, **arguments) -> ToolResult:
        """Execute a specific tool."""
        return self.registry.execute(tool_name, arguments)
    
    def run_task(self, task: str) -> Dict:
        """Let the LLM plan and execute tools for a task."""
        return self.orchestrator.plan_and_execute(task)
    
    def run_chain(self, chain: List[Dict]) -> List[ToolResult]:
        """Execute a predefined tool chain."""
        return self.orchestrator.execute_chain(chain)
    
    def list_tools(self, category: str = None) -> List[str]:
        """List available tools."""
        tools = self.registry.list_tools(category)
        return [tool.name for tool in tools]
    
    def get_tool_info(self, name: str) -> Optional[Dict]:
        """Get information about a tool."""
        tool = self.registry.get(name)
        if tool:
            return {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "parameters": [
                    {"name": p.name, "type": p.type, "required": p.required}
                    for p in tool.parameters
                ]
            }
        return None
    
    def get_stats(self) -> Dict:
        """Get tool system statistics."""
        return self.registry.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_tools(workspace_path: Path, llm_client=None) -> LuminaTools:
    """Initialize Lumina's tool system."""
    return LuminaTools(workspace_path, llm_client)


TOOLS_AVAILABLE = True


if __name__ == "__main__":
    # Test the tool system
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    tools = initialize_tools(workspace)
    
    print("\n" + "=" * 50)
    print("Tool System Test")
    print("=" * 50)
    
    print("\nAvailable tools:", tools.list_tools())
    
    # Test calculate
    print("\nTesting calculate tool...")
    result = tools.execute("calculate", expression="(10 + 5) * 2")
    print(f"Result: {result.result}")
    
    # Test get_current_time
    print("\nTesting get_current_time tool...")
    result = tools.execute("get_current_time")
    print(f"Current time: {result.result}")
    
    print("\n" + "=" * 50)
    print("Stats:", tools.get_stats())

