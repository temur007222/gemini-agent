"""
BaseTool - Abstract Strategy interface for all tools.

Implements:
    - Strategy Pattern: each concrete tool is an interchangeable strategy.
    - Open/Closed Principle: new tools extend BaseTool without modifying Agent.
    - Dependency Inversion: Agent depends on this abstraction, not concretions.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Abstract contract every tool strategy must fulfill."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier used by the LLM to call this tool."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human/LLM-readable description of what the tool does."""
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Run the tool with validated arguments.

        Returns:
            A JSON-serializable dict with at minimum a 'status' key
            ('success' | 'error') and either 'result' or 'error' payload.
        """
        ...

    @abstractmethod
    def get_declaration(self) -> Dict[str, Any]:
        """
        Return the Gemini function-calling JSON schema for this tool.
        Format: {"name": ..., "description": ..., "parameters": {...}}
        """
        ...

    def safe_execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Wrapper that converts unexpected exceptions into structured errors."""
        try:
            return self.execute(**kwargs)
        except TypeError as e:
            # Wrong / missing arguments from the LLM
            return {"status": "error", "error": f"Invalid arguments for '{self.name}': {e}"}
        except Exception as e:  # noqa: BLE001 — boundary catch is intentional
            return {"status": "error", "error": f"Tool '{self.name}' failed: {e}"}
