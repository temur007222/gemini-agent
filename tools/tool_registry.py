"""
ToolRegistry - Registry/Factory for BaseTool strategies.

Implements:
    - Registry Pattern: maps tool names -> BaseTool instances.
    - Factory behavior: dispatches execution by name.
    - OCP: Agent never grows an if/elif chain; tools self-register here.
"""

from typing import Dict, List, Any
from .base_tool import BaseTool


class ToolRegistry:
    """Central registry that owns and dispatches all tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool. Raises ValueError on duplicate names."""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Expected BaseTool, got {type(tool).__name__}")
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_declarations(self) -> List[Dict[str, Any]]:
        """Return the Gemini-formatted declarations for ALL registered tools."""
        return [t.get_declaration() for t in self._tools.values()]

    def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch a tool call by name. Returns a structured result dict.
        Handles unknown tools and bad arguments gracefully.
        """
        tool = self.get(name)
        if tool is None:
            return {
                "status": "error",
                "error": f"Unknown tool '{name}'. Available: {self.list_names()}",
            }
        if not isinstance(arguments, dict):
            return {"status": "error", "error": "Arguments must be a JSON object"}
        return tool.safe_execute(**arguments)
