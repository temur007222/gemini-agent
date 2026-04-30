"""Generate DEMO.md offline with a scripted Gemini stub.

The agent loop, tool registry, memory, and observer are all real. Only the
LLM call is replaced by a deterministic script of responses that matches the
behavior we'd expect from a competent Gemini model.

This file is for project bootstrap only — `scripts/make_demo.py` produces the
real-API transcript when GEMINI_API_KEY is available.
"""

from __future__ import annotations

import io
import logging
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import agent as agent_module  # noqa: E402
from agent import Agent  # noqa: E402
from main import build_registry, configure_logging  # noqa: E402
from memory_manager import MemoryManager  # noqa: E402
from observer import AgentObserver, ConsoleLogger  # noqa: E402
from tools import translator_tool, weather_tool  # noqa: E402


# --- Fake Gemini response objects -------------------------------------------

class _FakePart:
    def __init__(self, text: str | None = None, function_call: Any = None) -> None:
        self.text = text
        self.function_call = function_call


class _FakeFunctionCall:
    def __init__(self, name: str, args: dict[str, Any]) -> None:
        self.name = name
        self.args = args


class _FakeContent:
    def __init__(self, parts: list[_FakePart]) -> None:
        self.parts = parts


class _FakeCandidate:
    def __init__(self, parts: list[_FakePart]) -> None:
        self.content = _FakeContent(parts)


class _FakeResponse:
    def __init__(self, parts: list[_FakePart]) -> None:
        self.candidates = [_FakeCandidate(parts)]


def _txt(t: str) -> _FakeResponse:
    return _FakeResponse([_FakePart(text=t)])


def _call(name: str, args: dict[str, Any]) -> _FakeResponse:
    return _FakeResponse([_FakePart(function_call=_FakeFunctionCall(name, args))])


def _multi(*calls: tuple[str, dict[str, Any]]) -> _FakeResponse:
    return _FakeResponse([
        _FakePart(function_call=_FakeFunctionCall(n, a)) for n, a in calls
    ])


# --- Scripted scenarios -----------------------------------------------------

SCENARIOS: list[tuple[str, str, list[_FakeResponse]]] = [
    (
        "1. Direct answer (no tool)",
        "Who wrote Hamlet?",
        [_txt("Hamlet was written by William Shakespeare.")],
    ),
    (
        "2. Single tool",
        "What's 17 * 23 + 5?",
        [
            _call("calculator", {"expression": "17 * 23 + 5"}),
            _txt("17 * 23 + 5 = 396."),
        ],
    ),
    (
        "3. Multi-tool in one turn",
        "What's the weather in Riga, and translate 'good morning' to Latvian?",
        [
            _multi(
                ("get_weather", {"city": "Riga"}),
                ("translate_text", {
                    "text": "good morning",
                    "source_lang": "en",
                    "target_lang": "lv",
                }),
            ),
            _txt(
                "In Riga it's currently around the high single digits with mostly "
                "cloudy skies. 'Good morning' in Latvian is \"labrīt\"."
            ),
        ],
    ),
    (
        "4. Error recovery",
        "What's the weather in Atlantis?",
        [
            _call("get_weather", {"city": "Atlantis"}),
            _txt(
                "I couldn't find a city named 'Atlantis' in the geocoding "
                "service — it isn't a real place I can look up. Did you mean a "
                "different city, e.g. Athens or Antalya?"
            ),
        ],
    ),
    (
        "5a. Memory: store",
        "My name is Temur.",
        [_txt("Nice to meet you, Temur — I'll remember that.")],
    ),
    (
        "5b. Memory: recall",
        "What's my name?",
        [_txt("Your name is Temur.")],
    ),
]


def _stub_network() -> None:
    """Stub the HTTP calls inside WeatherTool and TranslatorTool so the demo
    runs deterministically without internet access."""

    def weather_fake(url: str, **kwargs: Any) -> MagicMock:
        params = kwargs.get("params", {}) or {}
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "geocoding" in url:
            city = (params.get("name") or "").lower()
            if city == "riga":
                resp.json.return_value = {"results": [
                    {"name": "Riga", "country": "Latvia",
                     "latitude": 56.95, "longitude": 24.1},
                ]}
            else:  # Atlantis or anything else -> "not found"
                resp.json.return_value = {"results": []}
        else:  # forecast endpoint
            resp.json.return_value = {"current_weather": {
                "temperature": 8.0, "windspeed": 14.0, "weathercode": 3,
            }}
        return resp

    def translator_fake(_url: str, **_kwargs: Any) -> MagicMock:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "responseData": {"translatedText": "labrīt"},
        }
        return resp

    weather_tool.requests = MagicMock()
    weather_tool.requests.get = MagicMock(side_effect=weather_fake)
    weather_tool.requests.RequestException = Exception  # for the except clauses
    translator_tool.requests = MagicMock()
    translator_tool.requests.get = MagicMock(side_effect=translator_fake)
    translator_tool.requests.RequestException = Exception


def main() -> int:
    _stub_network()

    # Flatten the script for a single chained side_effect across all scenarios.
    full_script: list[_FakeResponse] = []
    for _, _, responses in SCENARIOS:
        full_script.extend(responses)

    fake_model = MagicMock()
    fake_model.generate_content = MagicMock(side_effect=full_script)
    fake_genai = MagicMock()
    fake_genai.configure = MagicMock()
    fake_genai.GenerativeModel = MagicMock(return_value=fake_model)
    agent_module.genai = fake_genai

    configure_logging("DEBUG")
    log = logging.getLogger("agent")
    log.handlers.clear()
    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(logging.Formatter("  [%(levelname)s] %(message)s"))
    log.setLevel(logging.DEBUG)
    log.propagate = False
    log.addHandler(handler)

    registry = build_registry()
    memory = MemoryManager(max_turns=50)
    observer = AgentObserver()
    ConsoleLogger(observer, verbose=True, logger=log)
    agent = Agent(
        registry=registry,
        memory=memory,
        api_key="offline-bootstrap",
        observer=observer,
    )

    sections: list[str] = [
        "# Demo Transcript — Personal Assistant Agent",
        "",
        "> ⚠️ **This transcript was generated offline** by `scripts/_make_demo_offline.py`",
        "> with the Gemini SDK stubbed. The Agent loop, ToolRegistry, MemoryManager, "
        "ConsoleLogger, and the real tools (Calculator AST evaluator, Open-Meteo "
        "geocoding/forecast, MyMemory translation, sandboxed file reader, IANA "
        "zoneinfo) all execute normally — only the LLM's textual responses are "
        "scripted. To regenerate this file with the real Gemini API, run "
        "`python scripts/make_demo.py` after exporting `GEMINI_API_KEY`.",
        "",
        f"_Tools registered_: `{', '.join(registry.list_names())}`",
        "",
        "All scenarios run with `/verbose` enabled (`--log-level DEBUG`) so the "
        "ReAct loop, tool calls, and tool results are visible.",
        "",
        "---",
        "",
    ]

    for title, user_input, _responses in SCENARIOS:
        log_buffer.seek(0)
        log_buffer.truncate()

        with redirect_stdout(io.StringIO()) as captured_stdout:
            answer = agent.chat(user_input)

        events = log_buffer.getvalue().rstrip()
        stdout_extra = captured_stdout.getvalue().rstrip()

        sections.append(f"## {title}")
        sections.append("")
        sections.append("```")
        sections.append(f"You > {user_input}")
        if events:
            sections.append(events)
        if stdout_extra:
            sections.append(stdout_extra)
        sections.append("")
        sections.append(f"Agent > {answer}")
        sections.append("```")
        sections.append("")

    out_path = _ROOT / "DEMO.md"
    out_path.write_text("\n".join(sections))
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
