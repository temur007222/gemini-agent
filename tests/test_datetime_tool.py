"""Tests for DateTimeTool — timezone handling, error path, OCP demo."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tools import DateTimeTool


@pytest.fixture
def dt() -> DateTimeTool:
    return DateTimeTool()


def test_default_timezone_is_utc(dt: DateTimeTool) -> None:
    out = dt.execute()
    assert out["status"] == "success"
    assert out["timezone"] == "UTC"
    # UTC offset is +0000
    assert out["utc_offset"] in ("+0000", "+0000")


def test_named_timezone(dt: DateTimeTool) -> None:
    out = dt.execute(timezone="Europe/Riga")
    assert out["status"] == "success"
    assert out["timezone"] == "Europe/Riga"
    # ISO8601-shaped string
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", out["iso8601"])


def test_unknown_timezone_returns_error(dt: DateTimeTool) -> None:
    out = dt.execute(timezone="Mars/Olympus")
    assert out["status"] == "error"
    assert "Unknown timezone" in out["error"]


def test_empty_string_falls_back_to_utc(dt: DateTimeTool) -> None:
    out = dt.execute(timezone="")
    assert out["status"] == "success"
    assert out["timezone"] == "UTC"


def test_returned_time_close_to_now(dt: DateTimeTool) -> None:
    """Sanity: the returned ISO timestamp should be within a few seconds of now."""
    out = dt.execute(timezone="UTC")
    parsed = datetime.fromisoformat(out["iso8601"])
    delta = abs((datetime.now(ZoneInfo("UTC")) - parsed).total_seconds())
    assert delta < 5


def test_declaration_shape(dt: DateTimeTool) -> None:
    decl = dt.get_declaration()
    assert decl["name"] == "get_datetime"
    # `timezone` is optional (default UTC)
    assert decl["parameters"]["required"] == []
    assert "timezone" in decl["parameters"]["properties"]


def test_ocp_demonstration_register_without_agent_change() -> None:
    """The whole point: a new tool plugs into the registry; Agent is untouched.

    This verifies that `Agent` never imports `DateTimeTool` directly — it only
    knows about the abstractions `ToolRegistry`/`BaseTool`.
    """
    import inspect

    import agent as agent_module

    src = inspect.getsource(agent_module)
    assert "DateTimeTool" not in src, "Agent must not depend on a concrete tool"
    assert "datetime_tool" not in src, "Agent must not import a concrete tool module"
