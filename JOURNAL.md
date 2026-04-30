# Project Journal

Course: **Lietišķo datorsistēmu programmatūra** (Application Computer Systems Software), 2025/26
Author: **Temur Khaydarov** (RTU, BSc Computer Systems, 3rd year)
Project: Personal Assistant Agent — Gemini API + ReAct loop with pluggable tools

Each entry below was written at the corresponding submission stage and is
preserved verbatim as the project evolved. Repetition is intentionally
avoided — every stage describes what changed since the previous one.

---

## Step 1 — 24 April 2026 (planning)

### Planned system and its goal
A single-agent Python application that accepts free-form natural-language
requests at the command line and answers them by deciding, on each turn,
whether it can answer directly from its training or whether it needs to call
an external **tool**. The goal is to demonstrate a practical, self-contained
application of agent-based software design that another student could
extend without modifying the core orchestration code.

### AI / agent-based approach
- **Single intelligent agent** (not multi-agent) running a **ReAct** loop:
  *Reason → Act → Observe* — repeated until the model produces a final
  natural-language answer or a max-iteration cap is reached.
- LLM: **Google Gemini** via the `google-generativeai` Python SDK, using the
  function-calling capability so the model itself decides when to invoke a
  tool.
- The agent is **stateful within a session** through a `MemoryManager` that
  records every user/model/function turn in the format Gemini expects on the
  next call.

### Tools planned
1. `calculator` — safe arithmetic without `eval`.
2. `get_weather` — current weather for a city (Open-Meteo, no API key).
3. `translate_text` — text translation (MyMemory free API).
4. `read_local_file` — sandboxed reader for a local notes folder.

### Programming concepts expected
- Object-oriented design (abstract base class `BaseTool`, concrete subclasses).
- SOLID principles, especially **Open/Closed** and **Dependency Inversion**.
- Gang-of-Four patterns: **Strategy**, **Registry/Factory**, **Observer**.
- HTTP client usage with `requests`.
- AST-level expression parsing (`ast` module) for safe evaluation.
- File-system sandboxing using `pathlib`.
- CLI loop with command parsing.
- `typing` annotations and `abc.ABC`.

---

## Step 2 — 8 May 2026 (implementation progress)

### Updated system description
The architecture from Step 1 has been implemented end-to-end. The agent
runs through a ReAct loop, dispatches tool calls through a registry, and
stores conversation turns in the Gemini-native message format. Reorganized
into a `tools/` Python package so the registry can import strategies via
relative imports while the orchestration layer (`agent.py`, `main.py`,
`memory_manager.py`, `observer.py`) lives at the project root.

### Programming concepts actually used (and where)
| Concept | Where in the code |
|---|---|
| Abstract Base Class | `tools/base_tool.py` — `BaseTool(ABC)` with `@abstractmethod` |
| Strategy pattern | Each tool subclasses `BaseTool`; the agent never knows which one is in use |
| Registry pattern | `tools/tool_registry.py::ToolRegistry.execute(name, args)` |
| Observer pattern | `observer.py::AgentObserver` with named events `EVT_TOOL_CALL` etc. |
| Dependency Inversion | `Agent.__init__` accepts `ToolRegistry` and `MemoryManager` — never imports a concrete tool |
| Open/Closed Principle | New tool = new file + one `register(...)` line in `main.py`; `agent.py` never grows |
| AST-based safe evaluation | `tools/calculator_tool.py::_safe_eval` whitelists node types |
| Path traversal defense | `tools/file_reader_tool.py` resolves the path and verifies it via `Path.relative_to(_SANDBOX_DIR)` |
| Structured error returns | All tools return `{"status": "success" \| "error", ...}` — no exceptions cross the agent boundary |
| Type hints + `mypy --strict` | All production modules type-check clean |
| Iterator/generator-friendly memory | `MemoryManager.get_history()` returns a defensive copy |

### How tools are integrated
The `Agent` constructor receives a `ToolRegistry`. On every LLM turn the
agent:
1. Passes the registered tools' JSON schemas to Gemini via
   `tools=[{"function_declarations": registry.get_declarations()}]`.
2. Inspects each `function_call` part in the model's response.
3. Calls `registry.execute(name, args)`, which routes to the matching
   `BaseTool.safe_execute(**args)` — wrapping any unexpected exception in a
   structured error.
4. Records the result with role `user` and a `function_response` part — the
   format Gemini requires when continuing a tool-calling turn.
5. Loops until the model produces text-only output, capped at
   `max_iterations` (default 6).

The pattern means the *agent code* depends only on `BaseTool` and
`ToolRegistry` — adding a new tool never requires touching `agent.py`.

---

## Step 3 — 15 May 2026 (testing + deployment prep)

### Testing process
Tests were written in parallel with implementation, not after, using
**pytest** + **pytest-mock**. Each module has a corresponding test file
under `tests/`. Network-dependent tools (`get_weather`, `translate_text`)
are tested with mocked `requests` so the suite runs fully offline. The
Gemini SDK is mocked at the module level in `test_agent.py` — the agent's
ReAct loop is exercised against a deterministic script of fake responses,
which means CI (and graders) need no API key to verify correctness.

### Test scenarios
- **Direct answer (no tool)** — model returns text only; verify `chat()` returns it unchanged and the SDK was called once.
- **Single tool** — model returns a `function_call`, then text; verify the tool fires, the result lands in memory, and the second call yields the final answer.
- **Multi-tool in one turn** — model returns two `function_call` parts; verify both fire before the loop continues.
- **Unknown tool** — model hallucinates a tool name; verify the registry returns a structured error and the loop survives.
- **Max-iteration cap** — model loops on tool calls forever; verify the agent breaks and returns `[Agent error] ...`.
- **LLM exception** — the SDK raises; verify it surfaces as `[Agent error] ...` and is emitted on the observer bus.
- **Calculator: safety** — `__import__('os').system('...')`, attribute access, function calls all rejected.
- **Calculator: maths** — basic ops, parentheses, power, unary minus, modulo, floor-div, division-by-zero error.
- **Translator: language whitelist** — invalid ISO-639-1 codes rejected; same-source-and-target short-circuits **without a network call** (asserted via mock spy).
- **Translator: network** — `ConnectionError` from `requests` produces a structured error.
- **Weather: city not found** — empty geocoder result handled.
- **Weather: tiered network errors** — failure on geocode vs. failure on forecast surface different messages.
- **File reader: traversal** — `../../../etc/passwd` and `/etc/passwd` both rejected.
- **File reader: extension whitelist** — `.exe` files cannot be listed or read.
- **File reader: truncation** — files larger than `_MAX_BYTES` return `truncated=True`.
- **MemoryManager** — Gemini wire format, role assignment, `max_turns` trimming, defensive-copy semantics.
- **OCP regression test** — `test_datetime_tool::test_ocp_demonstration_register_without_agent_change` greps `agent.py`'s source and fails the build if it ever imports a concrete tool.

Final result: **70 tests, 0 failures**, full run in ~0.2 s. `mypy --strict`
and `ruff check` are also part of the gate.

### Deployment preparation
- `requirements.txt` pins runtime + dev tooling.
- `pyproject.toml` configures `mypy`, `ruff`, and `pytest`.
- `.env.example` documents `GEMINI_API_KEY`, `GEMINI_MODEL`, `AGENT_FILES_DIR`.
- `.gitignore` excludes secrets, caches, sandbox files (except the seed `notes.md`).
- `LICENSE` (MIT) at repository root.
- `python -m compileall` is part of the local pre-release check.

The user runs:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="..."
python main.py                  # default INFO logs
python main.py --log-level DEBUG  # full ReAct trace
```

### Data conversion / porting
The system speaks several formats and must convert between them at clean
boundaries:

| Boundary | Input format | Conversion | Output format |
|---|---|---|---|
| User → Agent | UTF-8 string from `input()` | trimmed, then wrapped as `{"role": "user", "parts": [{"text": ...}]}` | Gemini message |
| Agent → Gemini | Memory list of messages | passed verbatim via `model.generate_content(history)` | Gemini API request |
| Gemini → Agent | `Candidate.content.parts` (objects with `.text` and `.function_call`) | iterated; `.function_call.args` (a `proto.MapComposite`) is converted via `dict(...)` to a plain JSON-safe dict | Python dicts |
| Agent → Tool | `{"name": ..., "args": {...}}` | unpacked as `**kwargs` into `BaseTool.execute` | Python kwargs |
| Tool → Agent | `{"status": "...", ...}` Python dict | wrapped as `{"role": "user", "parts": [{"function_response": {"name": ..., "response": ...}}]}` | Gemini message |
| External APIs | JSON over HTTPS | `requests.get(...).json()` then field-by-field extraction with safe defaults | Python dict |

Two real conversions worth flagging:
1. The Open-Meteo geocoding endpoint returns city candidates with `latitude`/`longitude`, which become the *input* to a second forecast call. Two HTTP requests, joined in-process by the tool — the Agent never sees them as separate steps.
2. MyMemory translation expects a `langpair` of the form `"src|tgt"`. The tool builds it from two separate kwargs (`source_lang`, `target_lang`) and validates both against an ISO-639-1 whitelist before issuing the request.

Correctness across the boundary is preserved by:
- Always returning structured `dict[str, Any]` from tools (never raising).
- Validating types at each boundary (`isinstance(text, str)`, etc.).
- Using `dict(...)` to coerce Gemini's `MapComposite` → plain `dict` so the
  result is JSON-serialisable when fed back into memory.

---

## Final — 22 May 2026

### Final system description
A command-line **Personal Assistant Agent** built on the Google Gemini API.
It receives a free-form question, runs a ReAct loop, calls one or more
tools when useful, observes the structured result, and either calls more
tools or produces a final natural-language answer. State is preserved
across turns via a `MemoryManager` that uses Gemini's native message
format. The codebase is small (~600 production LOC, 12 source files) but
strictly typed (`mypy --strict`), linted (`ruff`), and unit-tested
(70 pytest cases).

### Final programming concepts and where they live
Same list as Step 2, plus:
- **Test doubles / mocks** — `unittest.mock.MagicMock` is used to swap out
  the Gemini SDK for a deterministic script in tests (and in
  `scripts/_make_demo_offline.py`).
- **Pure-stdlib timezone handling** — `DateTimeTool` uses
  `zoneinfo` (Python 3.9+) to demonstrate that adding a tool requires no
  new dependencies.
- **`logging` module hierarchy** — `ConsoleLogger` writes through a named
  logger so the level can be reconfigured at runtime via `/verbose` or by
  command-line flag.
- **`pyproject.toml` as a single source of truth** — replaces three
  separate config files for `mypy`, `ruff`, and `pytest`.

### Final tools and their role
| Tool | Role | Pattern note |
|---|---|---|
| `calculator` | Safe arithmetic | Strategy: AST whitelist instead of `eval` |
| `get_weather` | External-API integration | Two-step request (geocode + forecast) hidden behind one tool |
| `translate_text` | External-API integration | Validates ISO-639-1 codes; short-circuits same-language requests |
| `read_local_file` | Local-data integration | Path-traversal-safe sandbox; extension whitelist; size cap |
| `get_datetime` | Stdlib-only utility | Added in late development to prove OCP compliance |

### Final testing results and conclusions
- 70 pytest cases, 0 failures, ~0.2 s wall time.
- `mypy --strict` clean across all 12 production source files.
- `ruff check` clean.
- `python -m compileall` exits 0.
- A regression test enforces OCP by greping the agent's own source.
- A deterministic offline demo (`scripts/_make_demo_offline.py`)
  reproduces all five grading scenarios end-to-end without an API key.

The single most useful investment was writing the agent test against a
mocked SDK *before* writing any tool integration tests — it made the loop
correctness independent of any external service.

### Final deployment preparation
A short, copy-pasteable runbook is in `USER.md`. The system ships as:
- `requirements.txt` and `pyproject.toml` for installation.
- A single CLI entry point (`python main.py`).
- An optional offline-demo script that does not require credentials.
- A `.env.example` documenting every environment variable the system reads.
- A `.gitignore` and MIT `LICENSE`.

### Chosen deployment strategy
**Local CLI tool with staged release**, layered as follows:

1. **Local development** (the default audience): clone, `pip install`,
   `export GEMINI_API_KEY`, run. Suitable for individual users, students,
   and graders.
2. **Reproducible container** (next iteration, not yet shipped): a small
   `Dockerfile` based on `python:3.12-slim` that installs the same
   `requirements.txt`, sets `PYTHONUNBUFFERED=1`, and runs
   `python main.py`. The `GEMINI_API_KEY` is injected at runtime — never
   baked into the image.
3. **Hosted assistant** (future): the same `Agent` class wraps cleanly
   behind a tiny FastAPI front-end (`POST /chat`, body = user text,
   response = final answer plus emitted tool events). `MemoryManager`
   moves to Redis or SQLite so sessions survive restarts. The fact that
   `Agent` depends only on the `MemoryManager` interface makes that a
   one-file change.

A staged rollout would gate each step on the previous one passing CI:
local → container → staging service → production. Pre-release checks
already in place that map directly onto a CI pipeline:
`pytest -q` → `mypy` → `ruff check` → `python -m compileall`. Adding
GitHub Actions to run those four steps is a ~30-line follow-up.

---
