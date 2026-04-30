"""
MemoryManager - stores conversation turns in Gemini-compatible format.

Single Responsibility: knows only how to store/retrieve history.
The Agent depends on this abstraction; swapping it for a Redis-backed
or vector-DB-backed memory would not require Agent changes.
"""

from typing import Any, Dict, List


class MemoryManager:
    def __init__(self, max_turns: int = 50) -> None:
        """max_turns caps history to avoid runaway token usage."""
        self._history: List[Dict[str, Any]] = []
        self._max_turns = max_turns

    # --- Gemini 'contents' format: {"role": "user"|"model", "parts": [...]} ---

    def add_user_message(self, text: str) -> None:
        self._append({"role": "user", "parts": [{"text": text}]})

    def add_model_message(self, parts: List[Dict[str, Any]]) -> None:
        """parts can include {'text': ...} and/or {'function_call': ...}"""
        self._append({"role": "model", "parts": parts})

    def add_function_response(self, tool_name: str, response: Dict[str, Any]) -> None:
        """Function results are sent back with role='user' per Gemini spec."""
        self._append({
            "role": "user",
            "parts": [{"function_response": {"name": tool_name, "response": response}}],
        })

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()

    def turn_count(self) -> int:
        return len(self._history)

    def _append(self, entry: Dict[str, Any]) -> None:
        self._history.append(entry)
        # Trim oldest while keeping the structure valid (drop in pairs from the front).
        if len(self._history) > self._max_turns:
            overflow = len(self._history) - self._max_turns
            self._history = self._history[overflow:]
