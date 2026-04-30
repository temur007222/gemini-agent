"""
Observer pattern (bonus).

Decouples logging / UI / metrics from the core Agent loop.
Subscribers register a callback for named events; the Agent emits events
without knowing or caring who is listening.
"""

import logging
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
    """Observer that emits a trace of agent activity through `logging`.

    Levels:
        DEBUG    -> includes LLM-request/response trace (when verbose)
        INFO     -> tool calls and tool results (always shown by default)
        WARNING  -> agent error events
    """

    def __init__(
        self,
        observer: AgentObserver,
        verbose: bool = False,
        logger: logging.Logger | None = None,
    ) -> None:
        self._verbose = verbose
        self._logger = logger or logging.getLogger("agent")
        self._observer = observer

        observer.subscribe(EVT_TOOL_CALL, self._on_tool_call)
        observer.subscribe(EVT_TOOL_RESULT, self._on_tool_result)
        observer.subscribe(EVT_ERROR, self._on_error)
        # Always subscribe — the verbose flag gates emission, not subscription,
        # so toggling /verbose at runtime takes effect immediately.
        observer.subscribe(EVT_LLM_REQUEST, self._on_llm_req)
        observer.subscribe(EVT_LLM_RESPONSE, self._on_llm_resp)

    @property
    def verbose(self) -> bool:
        return self._verbose

    @verbose.setter
    def verbose(self, value: bool) -> None:
        self._verbose = bool(value)

    def _on_tool_call(self, p: Dict[str, Any]) -> None:
        self._logger.info("[tool→] %s(%s)", p.get("name"), p.get("arguments"))

    def _on_tool_result(self, p: Dict[str, Any]) -> None:
        result = p.get("result", {}) or {}
        status = result.get("status", "?")
        self._logger.info("[tool←] %s status=%s", p.get("name"), status)

    def _on_error(self, p: Dict[str, Any]) -> None:
        self._logger.warning("[error] %s", p.get("message"))

    def _on_llm_req(self, p: Dict[str, Any]) -> None:
        if self._verbose:
            self._logger.debug("[llm→] turns_in_history=%s", p.get("history_size"))

    def _on_llm_resp(self, p: Dict[str, Any]) -> None:
        if self._verbose:
            self._logger.debug("[llm←] has_function_call=%s", p.get("has_function_call"))
