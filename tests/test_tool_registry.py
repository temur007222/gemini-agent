"""Tests for ToolRegistry — registration, dispatch, error paths."""

from typing import Any, Dict

import pytest

from tools import ToolRegistry
from tools.base_tool import BaseTool


class _DummyTool(BaseTool):
    def __init__(self, name: str = "dummy") -> None:
        self._n = name

    @property
    def name(self) -> str:
        return self._n

    @property
    def description(self) -> str:
        return "dummy"

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        return {"status": "success", "result": kwargs}

    def get_declaration(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": {}}


class _BrokenTool(BaseTool):
    @property
    def name(self) -> str:
        return "broken"

    @property
    def description(self) -> str:
        return "always raises"

    def execute(self, **kwargs: Any) -> Dict[str, Any]:
        raise RuntimeError("boom")

    def get_declaration(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": {}}


def test_register_and_list() -> None:
    r = ToolRegistry()
    r.register(_DummyTool())
    assert r.list_names() == ["dummy"]
    assert r.has("dummy") is True
    assert r.get("dummy") is not None


def test_duplicate_name_rejected() -> None:
    r = ToolRegistry()
    r.register(_DummyTool())
    with pytest.raises(ValueError, match="already registered"):
        r.register(_DummyTool())


def test_register_rejects_non_basetool() -> None:
    r = ToolRegistry()
    with pytest.raises(TypeError):
        r.register("not a tool")  # type: ignore[arg-type]


def test_unknown_tool_dispatch_returns_structured_error() -> None:
    r = ToolRegistry()
    r.register(_DummyTool())
    out = r.execute("nope", {})
    assert out["status"] == "error"
    assert "Unknown tool" in out["error"]


def test_bad_args_object_returns_structured_error() -> None:
    r = ToolRegistry()
    r.register(_DummyTool())
    out = r.execute("dummy", "not a dict")  # type: ignore[arg-type]
    assert out["status"] == "error"
    assert "JSON object" in out["error"]


def test_dispatch_executes_tool() -> None:
    r = ToolRegistry()
    r.register(_DummyTool())
    out = r.execute("dummy", {"x": 1})
    assert out == {"status": "success", "result": {"x": 1}}


def test_dispatch_wraps_tool_exceptions() -> None:
    """Tool runtime errors must never escape — registry surfaces structured error."""
    r = ToolRegistry()
    r.register(_BrokenTool())
    out = r.execute("broken", {})
    assert out["status"] == "error"
    assert "boom" in out["error"]


def test_unregister() -> None:
    r = ToolRegistry()
    r.register(_DummyTool())
    r.unregister("dummy")
    assert r.has("dummy") is False
    # idempotent
    r.unregister("dummy")


def test_get_declarations_returns_all() -> None:
    r = ToolRegistry()
    r.register(_DummyTool("a"))
    r.register(_DummyTool("b"))
    decls = r.get_declarations()
    names = [d["name"] for d in decls]
    assert sorted(names) == ["a", "b"]
