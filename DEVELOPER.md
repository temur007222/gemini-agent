# Developer Guide

This document is for someone who wants to **read, modify, or extend** the
project. If you only want to run it, see [`USER.md`](USER.md).

## Architecture in one paragraph

`Agent` orchestrates a ReAct loop: it asks **Gemini** what to do, executes
any tool the model calls via **`ToolRegistry`**, records the round-trip in
**`MemoryManager`**, and emits lifecycle events through **`AgentObserver`**.
Every tool is a `BaseTool` subclass — the agent never imports a concrete
tool, which is what keeps the system **Open/Closed**: adding a new tool
means adding a file and one `register(...)` line in `main.py`. Nothing
else has to change.

```
main.py
  └─ Agent  (orchestrates Reason → Act → Observe loop)
       ├─ MemoryManager      (Single Responsibility: conversation history)
       ├─ ToolRegistry       (Registry/Factory: dispatches by tool name)
       │     └─ BaseTool     (Strategy interface — the abstraction Agent depends on)
       │           ├─ CalculatorTool
       │           ├─ WeatherTool
       │           ├─ TranslatorTool
       │           ├─ FileReaderTool
       │           └─ DateTimeTool
       └─ AgentObserver      (Observer: pub/sub for logging, metrics, UI)
```

## File layout

```
.
├── agent.py                 # ReAct loop. Depends ONLY on abstractions.
├── main.py                  # CLI entry point. Composition root for all tools.
├── memory_manager.py        # Stores Gemini-format message history.
├── observer.py              # Pub/sub bus + ConsoleLogger (uses `logging`).
├── tools/
│   ├── base_tool.py         # Abstract Strategy interface.
│   ├── tool_registry.py     # Registry/Factory.
│   ├── calculator_tool.py   # AST-whitelist arithmetic — no eval.
│   ├── weather_tool.py      # Open-Meteo (geocode + forecast).
│   ├── translator_tool.py   # MyMemory free translation API.
│   ├── file_reader_tool.py  # Sandboxed reader, traversal-safe.
│   └── datetime_tool.py     # IANA timezone lookup via stdlib zoneinfo.
├── tests/
│   ├── conftest.py          # adds project root to sys.path.
│   ├── test_agent.py        # ReAct loop tests with mocked Gemini SDK.
│   ├── test_*.py            # one file per module.
├── scripts/
│   ├── make_demo.py         # Real-API DEMO.md generator.
│   └── _make_demo_offline.py# Deterministic DEMO.md (mocked SDK + HTTP).
├── agent_files/notes.md     # Sandbox seed file.
├── README.md                # High-level overview, diagrams, gates.
├── USER.md                  # End-user runbook.
├── DEVELOPER.md             # This file.
├── DEMO.md                  # Captured session transcript.
├── JOURNAL.md               # Staged progress log (course requirement).
├── LICENSE                  # MIT.
├── pyproject.toml           # ruff, mypy, pytest config.
├── requirements.txt         # Runtime + dev deps.
├── .env.example             # Documents environment variables.
└── .gitignore
```

## Adding a new tool (the 5-minute path)

The `DateTimeTool` is the canonical example — it was added in late
development specifically to prove that no other file needed to change.

1. Create `tools/your_tool.py`:

   ```python
   from typing import Any, Dict
   from .base_tool import BaseTool

   class YourTool(BaseTool):
       @property
       def name(self) -> str:
           return "your_tool"

       @property
       def description(self) -> str:
           return "What it does, in 1–2 sentences for the LLM."

       def execute(self, foo: str, bar: int = 0) -> Dict[str, Any]:  # type: ignore[override]
           # ... your logic, returning {"status": "success"|"error", ...}
           return {"status": "success", "result": ...}

       def get_declaration(self) -> Dict[str, Any]:
           return {
               "name": self.name,
               "description": self.description,
               "parameters": {
                   "type": "object",
                   "properties": {
                       "foo": {"type": "string", "description": "..."},
                       "bar": {"type": "integer", "description": "..."},
                   },
                   "required": ["foo"],
               },
           }
   ```

2. Export it from `tools/__init__.py`:
   ```python
   from .your_tool import YourTool
   __all__ = [..., "YourTool"]
   ```

3. Register it in `main.py::build_registry`:
   ```python
   registry.register(YourTool())
   ```

4. Add a unit test under `tests/test_your_tool.py`. If your tool calls
   external services, mock `requests` (see `test_translator_tool.py` for
   the pattern).

5. Run the gates:
   ```bash
   pytest -q && mypy && ruff check .
   ```

That's the full procedure. **You should not need to touch `agent.py`.**
There's even a regression test (`test_datetime_tool.py::test_ocp_demonstration_register_without_agent_change`)
that greps `agent.py` and fails if any concrete tool name appears there.

## Why the `# type: ignore[override]` on every `execute(...)`

`BaseTool.execute` declares `**kwargs: Any` (because it has to fit any
strategy). Each concrete tool declares typed parameters
(`expression: str`, `city: str`, etc.) so we get static-typing benefits
inside the tool itself. mypy `--strict` calls this an LSP violation; at
runtime `BaseTool.safe_execute` catches the resulting `TypeError` and
turns it into a structured error, which is the exact contract the
registry depends on. The ignore comment is therefore intentional and
documented per file — don't remove it without re-thinking the contract.

## Quality gates

```bash
pytest -q           # 70 cases, ~0.2 s
mypy                # --strict, 12 source files
ruff check .        # bug-finding subset (E, F, W, B)
python -m compileall agent.py main.py memory_manager.py observer.py tools tests scripts
```

All four must be green before committing. The same four steps map onto a
GitHub Actions workflow with no extra setup.

## Where the seams are

If you want to swap something out, these are the contractual boundaries:

| Want to change... | Replace this | Don't touch this |
|---|---|---|
| The LLM provider | `Agent.__init__` (the `genai.GenerativeModel(...)` lines) | `Agent.chat`, the registry, the tools |
| Persistent memory (e.g. Redis) | `MemoryManager` (keep the public methods) | `Agent.chat` |
| Output channel (file, web, Slack) | Subscribe new callbacks to `AgentObserver` | `Agent.chat`, tools |
| Observer transport (e.g. async, OpenTelemetry) | `AgentObserver.emit` body | the public `subscribe`/`emit` API |
| New tool | New `BaseTool` subclass + register call | everything else |

## Common gotchas

- **`MemoryManager.max_turns` trims by raw turn count.** A long
  function-call/response pair could be split if the head is right at the
  cap. The fix is a token-aware trimmer; see "Known limitations" in
  README.
- **`google.generativeai` is upstream-deprecated.** It still works, but
  Google has shipped `google-genai` as the successor. Migration is
  scoped to the `genai.configure / genai.GenerativeModel` lines in
  `agent.py`. Tests use a SDK mock so they don't care.
- **`zoneinfo` in slim Docker images.** `python:3.12-slim` includes
  `zoneinfo` but **not** the full IANA tzdata. Add `tzdata` (Debian) or
  `pip install tzdata` if the container reports `ZoneInfoNotFoundError`
  for known names.
- **MyMemory has a daily anonymous quota.** Translation tests are mocked
  so they aren't affected, but a real session can hit the cap.

## Versioning the API

If you ever extend `BaseTool` (for example, adding an async variant), do
it as a **new** abstract class — `AsyncBaseTool` — and let `ToolRegistry`
detect which type it dispatches against. Don't change `BaseTool`'s
existing methods; that breaks every tool subclass at once.
