"""
Agent - orchestrates the ReAct loop (Reason → Act → Observe).

Depends only on abstractions:
    - ToolRegistry (not concrete tools)
    - MemoryManager (not a concrete storage backend)
    - AgentObserver (optional pub/sub bus)

This satisfies SRP (orchestration only), OCP (new tools require zero
changes here), and DIP (depends on interfaces, not implementations).
"""

from typing import Any, Dict, List, Optional

import google.generativeai as genai

from memory_manager import MemoryManager
from tools import ToolRegistry
from observer import (
    AgentObserver,
    EVT_USER_INPUT, EVT_LLM_REQUEST, EVT_LLM_RESPONSE,
    EVT_TOOL_CALL, EVT_TOOL_RESULT, EVT_FINAL_ANSWER, EVT_ERROR,
)


_DEFAULT_SYSTEM_INSTRUCTION = (
    "You are a helpful, adaptive personal assistant. "
    "You have access to tools (functions). Reason about the user's request, "
    "decide whether you can answer directly or need a tool, then act. "
    "After receiving a tool result, observe it and either call another tool "
    "or produce a clear, concise final answer in natural language. "
    "Never invent tool results — always call the tool. If a tool errors, "
    "explain the problem to the user briefly and suggest a next step."
)


class Agent:
    def __init__(
        self,
        registry: ToolRegistry,
        memory: MemoryManager,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
        observer: Optional[AgentObserver] = None,
        system_instruction: str = _DEFAULT_SYSTEM_INSTRUCTION,
        max_iterations: int = 6,
    ) -> None:
        self.registry = registry
        self.memory = memory
        self.observer = observer or AgentObserver()
        self.max_iterations = max_iterations

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            tools=[{"function_declarations": registry.get_declarations()}] if registry.list_names() else None,
        )

    def chat(self, user_input: str) -> str:
        """Run one user turn through the ReAct loop. Returns the final text."""
        self.observer.emit(EVT_USER_INPUT, {"text": user_input})
        self.memory.add_user_message(user_input)

        for iteration in range(self.max_iterations):
            try:
                response = self._call_llm()
            except Exception as e:
                msg = f"LLM call failed: {e}"
                self.observer.emit(EVT_ERROR, {"message": msg})
                return f"[Agent error] {msg}"

            parts = self._extract_parts(response)
            if parts is None:
                self.observer.emit(EVT_ERROR, {"message": "Empty LLM response"})
                return "[Agent error] Empty response from model"

            function_calls = self._collect_function_calls(parts)
            text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]

            stored: List[Dict[str, Any]] = []
            for p in parts:
                if hasattr(p, "text") and p.text:
                    stored.append({"text": p.text})
                if hasattr(p, "function_call") and p.function_call and p.function_call.name:
                    stored.append({
                        "function_call": {
                            "name": p.function_call.name,
                            "args": dict(p.function_call.args or {}),
                        }
                    })
            if stored:
                self.memory.add_model_message(stored)

            if not function_calls:
                final = "\n".join(text_parts).strip() or "(no answer produced)"
                self.observer.emit(EVT_FINAL_ANSWER, {"text": final})
                return final

            for fc in function_calls:
                self._execute_and_record(fc["name"], fc["args"])

        self.observer.emit(EVT_ERROR, {"message": "Max iterations reached"})
        return "[Agent error] Reasoning loop exceeded max iterations."

    def _call_llm(self):
        history = self.memory.get_history()
        self.observer.emit(EVT_LLM_REQUEST, {"history_size": len(history)})
        response = self._model.generate_content(history)
        has_fc = any(
            hasattr(p, "function_call") and p.function_call and p.function_call.name
            for p in self._extract_parts(response) or []
        )
        self.observer.emit(EVT_LLM_RESPONSE, {"has_function_call": has_fc})
        return response

    @staticmethod
    def _extract_parts(response) -> Optional[List[Any]]:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None
        content = getattr(candidates[0], "content", None)
        if content is None:
            return None
        return list(getattr(content, "parts", []) or [])

    @staticmethod
    def _collect_function_calls(parts: List[Any]) -> List[Dict[str, Any]]:
        calls = []
        for p in parts:
            fc = getattr(p, "function_call", None)
            if fc and fc.name:
                calls.append({"name": fc.name, "args": dict(fc.args or {})})
        return calls

    def _execute_and_record(self, name: str, args: Dict[str, Any]) -> None:
        self.observer.emit(EVT_TOOL_CALL, {"name": name, "arguments": args})
        result = self.registry.execute(name, args)
        self.observer.emit(EVT_TOOL_RESULT, {"name": name, "result": result})
        self.memory.add_function_response(name, result)
