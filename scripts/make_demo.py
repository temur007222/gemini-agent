"""Run the 5 grading scenarios against the live agent and write DEMO.md.

Usage:
    export GEMINI_API_KEY=your_key
    python scripts/make_demo.py

Captures everything printed by the REPL plus the verbose tool-call/result
trace from `ConsoleLogger`, and saves it to `DEMO.md` at the project root.
"""

from __future__ import annotations

import io
import logging
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

# Make the project root importable when running from `scripts/`.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from agent import Agent  # noqa: E402
from main import build_registry, configure_logging  # noqa: E402
from memory_manager import MemoryManager  # noqa: E402
from observer import AgentObserver, ConsoleLogger  # noqa: E402


SCENARIOS: list[tuple[str, str]] = [
    ("Direct answer (no tool)", "Who wrote Hamlet?"),
    ("Single tool", "What's 17 * 23 + 5?"),
    ("Multi-tool in one turn", "What's the weather in Riga, and translate 'good morning' to Latvian?"),
    ("Error recovery", "What's the weather in Atlantis?"),
    ("Memory: store", "My name is Temur."),
    ("Memory: recall", "What's my name?"),
]


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set. Aborting.", file=sys.stderr)
        return 1

    # Wire up the agent with verbose logging routed to a string buffer.
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
        api_key=api_key,
        observer=observer,
        model_name=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
    )

    sections: list[str] = [
        "# Demo Transcript — Personal Assistant Agent",
        "",
        "Real session captured by `scripts/make_demo.py` against the live "
        "Gemini API with `--log-level DEBUG`.",
        "",
        f"_Tools registered_: `{', '.join(registry.list_names())}`",
        "",
        "---",
        "",
    ]

    for title, user_input in SCENARIOS:
        # Drain log buffer between turns so each section only shows its own events.
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
