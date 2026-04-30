# Changelog

All notable changes to this project. Format follows
[Keep a Changelog](https://keepachangelog.com/), versioning follows
[Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-04-30 — Final submission

### Added
- **CI/CD**: `.github/workflows/ci.yml` running `ruff`, `mypy --strict`,
  `pytest -v`, `compileall`, and the offline-demo smoke test on Ubuntu
  Python 3.11/3.12/3.13 and macOS Python 3.13.
- **Container**: `Dockerfile` (multi-stage, non-root user, `tzdata` for
  `zoneinfo`) and `docker-compose.yml` for one-command launch.
- **Docs**: `tests/SCENARIOS.md` mapping every required scenario to a
  test, `CHANGELOG.md`, README badges (CI, license, Python).
- **Default model**: bumped from `gemini-2.0-flash` to `gemini-2.5-flash`
  for forward compatibility (overridable via `GEMINI_MODEL`).

### Changed
- README: added Data porting and conversion table, System deployment
  strategy section, and Quick verification (no API key) section.

## [0.3.0] — 2026-04-30 — Type checking, linting, polish

### Added
- `pyproject.toml` configuring `ruff`, `mypy --strict`, and `pytest`.
- `mypy>=1.8`, `ruff>=0.4`, `types-requests` in `requirements.txt`.
- `scripts/make_demo.py` (live API) and `scripts/_make_demo_offline.py`
  (deterministic SDK + HTTP stubs) for reproducible session transcripts.
- `DEMO.md` checked in (offline-generated, clearly labelled).
- `LICENSE` (MIT), `.env.example`, `USER.md`, `DEVELOPER.md`, `JOURNAL.md`.

### Fixed
- All `mypy --strict` errors (typed Strategy overrides via targeted
  `# type: ignore[override]`; coerced numeric AST evaluation; typed
  third-party SDK boundary).
- Silenced `google-generativeai` deprecation `FutureWarning` at import
  time so it doesn't pollute test or REPL output.

## [0.2.0] — 2026-04-30 — Tests + 5th tool (OCP demo)

### Added
- `tests/` directory with **70 pytest cases** across 8 files.
- `DateTimeTool` using stdlib `zoneinfo` — registered only in `main.py`;
  `agent.py` is provably untouched (regression test enforces this).
- Migrated `ConsoleLogger` from `print()` to the `logging` module.
- `--log-level {DEBUG,INFO,WARNING}` CLI flag.

## [0.1.0] — 2026-04-30 — Initial scaffold

### Added
- `BaseTool` abstract Strategy interface.
- `ToolRegistry` Registry/Factory with structured error envelopes.
- `Agent` orchestrating a ReAct loop (Reason → Act → Observe).
- `MemoryManager` storing Gemini-format conversation history.
- `AgentObserver` pub/sub bus (events: USER_INPUT, LLM_REQUEST/RESPONSE,
  TOOL_CALL/RESULT, ERROR, FINAL_ANSWER).
- Concrete tools: `CalculatorTool` (AST whitelist),
  `WeatherTool` (Open-Meteo two-step), `TranslatorTool` (MyMemory),
  `FileReaderTool` (sandboxed reader).
- CLI entry point in `main.py` with `/tools`, `/clear`, `/verbose`,
  `/quit` commands.

[1.0.0]: https://github.com/temur007222/gemini-agent/releases/tag/v1.0.0
[0.3.0]: https://github.com/temur007222/gemini-agent/releases/tag/v0.3.0
[0.2.0]: https://github.com/temur007222/gemini-agent/releases/tag/v0.2.0
[0.1.0]: https://github.com/temur007222/gemini-agent/releases/tag/v0.1.0
