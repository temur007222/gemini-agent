"""
main.py - CLI entry point for the Personal Assistant agent.

Usage:
    export GEMINI_API_KEY="your_key"
    python main.py [--log-level {DEBUG,INFO,WARNING}]

Commands inside the REPL:
    /tools    list registered tools
    /clear    wipe conversation memory
    /verbose  toggle verbose LLM tracing (DEBUG-level events)
    /quit     exit
"""

import argparse
import logging
import os
import sys

from agent import Agent
from memory_manager import MemoryManager
from observer import AgentObserver, ConsoleLogger
from tools import (
    ToolRegistry,
    CalculatorTool,
    WeatherTool,
    TranslatorTool,
    FileReaderTool,
    DateTimeTool,
)


BANNER = """
╔══════════════════════════════════════════════╗
║   Personal Assistant Agent (Gemini + ReAct)  ║
╚══════════════════════════════════════════════╝
Type your message. Commands: /tools  /clear  /verbose  /quit
"""


def build_registry() -> ToolRegistry:
    """Compose the ToolRegistry with all available tools.

    To add a new tool: implement BaseTool and register it here.
    The Agent itself never needs to be modified — that's the OCP win.
    """
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(WeatherTool())
    registry.register(TranslatorTool())
    registry.register(FileReaderTool())
    registry.register(DateTimeTool())
    return registry


def configure_logging(level_name: str) -> None:
    """Wire the root 'agent' logger with a clean, single-line console format.

    Idempotent: clears any pre-existing handlers so re-runs in tests or REPLs
    don't duplicate output.
    """
    level = getattr(logging, level_name.upper(), logging.INFO)
    logger = logging.getLogger("agent")
    logger.setLevel(level)
    logger.propagate = False
    for h in list(logger.handlers):
        logger.removeHandler(h)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                                           datefmt="%H:%M:%S"))
    logger.addHandler(handler)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="gemini-agent",
        description="Personal Assistant Agent (Gemini + ReAct).",
    )
    p.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING"],
        default="INFO",
        help="Logging verbosity (default: INFO)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)
    log = logging.getLogger("agent")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error("GEMINI_API_KEY environment variable is not set.")
        log.error("  Linux/macOS:  export GEMINI_API_KEY='your_key'")
        log.error("  Windows:      set GEMINI_API_KEY=your_key")
        return 1

    registry = build_registry()
    memory = MemoryManager(max_turns=50)
    observer = AgentObserver()
    # When --log-level is DEBUG we start verbose; otherwise the user can /verbose to enable.
    logger = ConsoleLogger(observer, verbose=(args.log_level == "DEBUG"))

    agent = Agent(
        registry=registry,
        memory=memory,
        api_key=api_key,
        observer=observer,
        model_name=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
    )

    print(BANNER)
    print(f"Registered tools: {', '.join(registry.list_names())}\n")

    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            return 0

        if not user_input:
            continue

        # CLI commands
        if user_input.lower() in ("/quit", "/exit"):
            print("Bye!")
            return 0
        if user_input.lower() == "/tools":
            print("Tools:", ", ".join(registry.list_names()))
            continue
        if user_input.lower() == "/clear":
            memory.clear()
            print("(memory cleared)")
            continue
        if user_input.lower() == "/verbose":
            logger.verbose = not logger.verbose
            # When toggling on, ensure the logger level is permissive enough.
            if logger.verbose and log.level > logging.DEBUG:
                log.setLevel(logging.DEBUG)
            print(f"(verbose = {logger.verbose})")
            continue

        answer = agent.chat(user_input)
        print(f"\nAgent > {answer}\n")


if __name__ == "__main__":
    sys.exit(main())
