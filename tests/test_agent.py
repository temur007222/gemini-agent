"""Tests for the Agent ReAct loop with a mocked Gemini SDK.

Strategy: patch `agent.genai` so that constructing a `GenerativeModel` returns a
fake model whose `generate_content(...)` yields scripted responses (text-only
or function-call). This lets us drive the loop deterministically without any
network or API-key dependency.
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from agent import Agent
from memory_manager import MemoryManager
from observer import (
    AgentObserver,
    EVT_FINAL_ANSWER,
    EVT_TOOL_CALL,
    EVT_TOOL_RESULT,
    EVT_USER_INPUT,
)
from tools import CalculatorTool, ToolRegistry
from tools.base_tool import BaseTool


# --- Fake Gemini response objects (duck-typed to match the SDK shape) -------

class _FakePart:
    def __init__(self, text: str | None = None, function_call: Any = None) -> None:
        self.text = text
        self.function_call = function_call


class _FakeFunctionCall:
    def __init__(self, name: str, args: Dict[str, Any]) -> None:
        self.name = name
        self.args = args


class _FakeContent:
    def __init__(self, parts: List[_FakePart]) -> None:
        self.parts = parts


class _FakeCandidate:
    def __init__(self, parts: List[_FakePart]) -> None:
        self.content = _FakeContent(parts)


class _FakeResponse:
    def __init__(self, parts: List[_FakePart]) -> None:
        self.candidates = [_FakeCandidate(parts)]


def _text_response(text: str) -> _FakeResponse:
    return _FakeResponse([_FakePart(text=text)])


def _tool_call_response(name: str, args: Dict[str, Any]) -> _FakeResponse:
    return _FakeResponse([_FakePart(function_call=_FakeFunctionCall(name, args))])


# --- Helpers ---------------------------------------------------------------

def _build_agent(
    monkeypatch: pytest.MonkeyPatch,
    scripted_responses: List[_FakeResponse],
) -> tuple[Agent, AgentObserver, MagicMock]:
    """Wire up an Agent backed by a fake genai module. Returns (agent, observer, model_mock)."""
    fake_model = MagicMock()
    fake_model.generate_content = MagicMock(side_effect=scripted_responses)

    fake_genai = MagicMock()
    fake_genai.configure = MagicMock()
    fake_genai.GenerativeModel = MagicMock(return_value=fake_model)

    monkeypatch.setattr("agent.genai", fake_genai)

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    memory = MemoryManager()
    observer = AgentObserver()

    agent = Agent(
        registry=registry,
        memory=memory,
        api_key="fake-key",
        observer=observer,
    )
    return agent, observer, fake_model


# --- Tests -----------------------------------------------------------------

def test_direct_answer_no_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    agent, _obs, model = _build_agent(monkeypatch, [_text_response("Shakespeare wrote Hamlet.")])
    out = agent.chat("Who wrote Hamlet?")
    assert out == "Shakespeare wrote Hamlet."
    assert model.generate_content.call_count == 1


def test_react_loop_executes_tool_then_returns_final(monkeypatch: pytest.MonkeyPatch) -> None:
    """First turn: function_call. Second turn: final text after seeing result."""
    agent, _obs, model = _build_agent(
        monkeypatch,
        [
            _tool_call_response("calculator", {"expression": "2+2"}),
            _text_response("The answer is 4."),
        ],
    )
    out = agent.chat("What is 2+2?")
    assert out == "The answer is 4."
    assert model.generate_content.call_count == 2


def test_observer_events_fire_for_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, list[Any]] = {"calls": [], "results": [], "final": [], "user": []}

    agent, observer, _model = _build_agent(
        monkeypatch,
        [
            _tool_call_response("calculator", {"expression": "1+1"}),
            _text_response("Two."),
        ],
    )
    observer.subscribe(EVT_USER_INPUT, lambda p: received["user"].append(p))
    observer.subscribe(EVT_TOOL_CALL, lambda p: received["calls"].append(p))
    observer.subscribe(EVT_TOOL_RESULT, lambda p: received["results"].append(p))
    observer.subscribe(EVT_FINAL_ANSWER, lambda p: received["final"].append(p))

    agent.chat("1+1?")

    assert len(received["user"]) == 1
    assert received["calls"][0]["name"] == "calculator"
    assert received["results"][0]["result"]["status"] == "success"
    assert received["results"][0]["result"]["result"] == 2
    assert received["final"][0]["text"] == "Two."


def test_max_iterations_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Agent must stop after max_iterations even if model keeps calling tools."""
    forever_tool_calls = [_tool_call_response("calculator", {"expression": "1+1"}) for _ in range(20)]

    fake_model = MagicMock()
    fake_model.generate_content = MagicMock(side_effect=forever_tool_calls)
    fake_genai = MagicMock()
    fake_genai.configure = MagicMock()
    fake_genai.GenerativeModel = MagicMock(return_value=fake_model)
    monkeypatch.setattr("agent.genai", fake_genai)

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    agent = Agent(
        registry=registry,
        memory=MemoryManager(),
        api_key="k",
        max_iterations=3,
    )
    out = agent.chat("loop forever")
    assert "max iterations" in out.lower()
    assert fake_model.generate_content.call_count == 3


def test_llm_exception_returns_structured_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = MagicMock()
    fake_model.generate_content = MagicMock(side_effect=RuntimeError("API down"))
    fake_genai = MagicMock()
    fake_genai.configure = MagicMock()
    fake_genai.GenerativeModel = MagicMock(return_value=fake_model)
    monkeypatch.setattr("agent.genai", fake_genai)

    agent = Agent(
        registry=ToolRegistry(),
        memory=MemoryManager(),
        api_key="k",
    )
    out = agent.chat("hi")
    assert out.startswith("[Agent error]")
    assert "API down" in out


def test_unknown_tool_call_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the model hallucinates a tool name, the registry returns an error and
    the loop continues — eventually the model produces a final text answer."""
    agent, _obs, _model = _build_agent(
        monkeypatch,
        [
            _tool_call_response("nonexistent_tool", {"x": 1}),
            _text_response("I couldn't run that. Sorry."),
        ],
    )
    out = agent.chat("do something weird")
    assert out == "I couldn't run that. Sorry."


def test_multi_tool_in_single_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    """A single model response with two function_calls -> both execute, then loop continues."""

    class _MultiTool(BaseTool):
        @property
        def name(self) -> str:
            return "echo"

        @property
        def description(self) -> str:
            return "echo"

        def execute(self, **kwargs: Any) -> Dict[str, Any]:
            return {"status": "success", "result": kwargs}

        def get_declaration(self) -> Dict[str, Any]:
            return {"name": self.name, "description": self.description, "parameters": {}}

    multi_response = _FakeResponse([
        _FakePart(function_call=_FakeFunctionCall("echo", {"q": "a"})),
        _FakePart(function_call=_FakeFunctionCall("echo", {"q": "b"})),
    ])

    fake_model = MagicMock()
    fake_model.generate_content = MagicMock(side_effect=[multi_response, _text_response("done")])
    fake_genai = MagicMock()
    fake_genai.configure = MagicMock()
    fake_genai.GenerativeModel = MagicMock(return_value=fake_model)
    monkeypatch.setattr("agent.genai", fake_genai)

    registry = ToolRegistry()
    registry.register(_MultiTool())
    observer = AgentObserver()
    calls: list[Any] = []
    observer.subscribe(EVT_TOOL_CALL, lambda p: calls.append(p))

    agent = Agent(registry=registry, memory=MemoryManager(), api_key="k", observer=observer)
    out = agent.chat("do two things")
    assert out == "done"
    assert len(calls) == 2
