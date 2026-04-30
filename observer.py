"""
Observer pattern (bonus).

Decouples logging / UI / metrics from the core Agent loop.
Subscribers register a callback for named events; the Agent emits events
without knowing or caring who is listening.
"""

from typing import Any, Callable, Dict, List


# Event constants
EVT_USER_INPUT = "user_input"
EVT_LLM_REQUEST = "llm_request"
EVT_LLM_RESPONSE = "llm_response"
EVT_TOOL_CALL = "tool_call"
EVT_TOOL_RESULT = "tool_result"
EVT_FINAL_ANSWER = "final_answer"
EVT_ERROR = "error"


class AgentObserver:
    """Pub/sub bus for Agent lifecycle events."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def subscribe(self, event: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._subscribers.setdefault(event, []).append(callback)

    def emit(self, event: str, payload: Dict[str, Any]) -> None:
        for cb in self._subscribers.get(event, []):
            try:
                cb(payload)
            except Exception:  # observer failure must never break the agent
                pass


class ConsoleLogger:
    """Minimal observer that prints a verbose trace of agent activity."""

    def __init__(self, observer: AgentObserver, verbose: bool = False) -> None:
        self.verbose = verbose
        observer.subscribe(EVT_TOOL_CALL, self._on_tool_call)
        observer.subscribe(EVT_TOOL_RESULT, self._on_tool_result)
        observer.subscribe(EVT_ERROR, self._on_error)
        if verbose:
            observer.subscribe(EVT_LLM_REQUEST, self._on_llm_req)
            observer.subscribe(EVT_LLM_RESPONSE, self._on_llm_resp)

    def _on_tool_call(self, p: Dict[str, Any]) -> None:
        print(f"  [tool→] {p.get('name')}({p.get('arguments')})")

    def _on_tool_result(self, p: Dict[str, Any]) -> None:
        result = p.get("result", {})
        status = result.get("status", "?")
        print(f"  [tool←] {p.get('name')} status={status}")

    def _on_error(self, p: Dict[str, Any]) -> None:
        print(f"  [error] {p.get('message')}")

    def _on_llm_req(self, p: Dict[str, Any]) -> None:
        print(f"  [llm→] turns_in_history={p.get('history_size')}")

    def _on_llm_resp(self, p: Dict[str, Any]) -> None:
        print(f"  [llm←] has_function_call={p.get('has_function_call')}")
