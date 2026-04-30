"""Tests for FileReaderTool — sandbox, traversal, extension whitelist, missing file."""

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point AGENT_FILES_DIR to a temp dir and reload the module so the
    module-level _SANDBOX_DIR constant is rebuilt against the new path.
    """
    monkeypatch.setenv("AGENT_FILES_DIR", str(tmp_path))
    import tools.file_reader_tool as frt

    importlib.reload(frt)
    return tmp_path


def _new_tool(sandbox: Path):
    """Build a tool instance against the reloaded module (sandbox-aware)."""
    import tools.file_reader_tool as frt

    return frt.FileReaderTool()


def test_list_action_empty_sandbox(sandbox: Path) -> None:
    tool = _new_tool(sandbox)
    out = tool.execute(action="list")
    assert out["status"] == "success"
    assert out["files"] == []


def test_list_returns_only_allowed_extensions(sandbox: Path) -> None:
    (sandbox / "ok.md").write_text("# notes")
    (sandbox / "blocked.exe").write_bytes(b"\x00")
    (sandbox / "another.txt").write_text("hello")

    tool = _new_tool(sandbox)
    out = tool.execute(action="list")
    assert out["status"] == "success"
    assert sorted(out["files"]) == ["another.txt", "ok.md"]


def test_read_existing_file(sandbox: Path) -> None:
    (sandbox / "notes.md").write_text("Hello world")
    tool = _new_tool(sandbox)
    out = tool.execute(action="read", filename="notes.md")
    assert out["status"] == "success"
    assert "Hello world" in out["content"]
    assert out["truncated"] is False


def test_read_missing_file(sandbox: Path) -> None:
    tool = _new_tool(sandbox)
    out = tool.execute(action="read", filename="nope.txt")
    assert out["status"] == "error"
    assert "not found" in out["error"]


def test_read_blocked_extension(sandbox: Path) -> None:
    (sandbox / "secret.exe").write_bytes(b"binary")
    tool = _new_tool(sandbox)
    out = tool.execute(action="read", filename="secret.exe")
    assert out["status"] == "error"
    assert "Extension not allowed" in out["error"]


def test_path_traversal_blocked(sandbox: Path) -> None:
    """`../etc/passwd` style paths must be rejected, not resolved."""
    tool = _new_tool(sandbox)
    out = tool.execute(action="read", filename="../../../etc/passwd")
    assert out["status"] == "error"
    assert "Path traversal blocked" in out["error"]


def test_absolute_path_outside_sandbox_blocked(sandbox: Path) -> None:
    tool = _new_tool(sandbox)
    # An absolute path joined onto the sandbox is reset to that absolute path
    # by pathlib semantics, which then resolve outside the sandbox.
    out = tool.execute(action="read", filename="/etc/passwd")
    assert out["status"] == "error"
    assert "Path traversal blocked" in out["error"]


def test_unknown_action(sandbox: Path) -> None:
    tool = _new_tool(sandbox)
    out = tool.execute(action="delete")
    assert out["status"] == "error"
    assert "list" in out["error"] and "read" in out["error"]


def test_read_without_filename(sandbox: Path) -> None:
    tool = _new_tool(sandbox)
    out = tool.execute(action="read")
    assert out["status"] == "error"
    assert "filename is required" in out["error"]


def test_truncation_on_large_file(sandbox: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.file_reader_tool as frt

    monkeypatch.setattr(frt, "_MAX_BYTES", 10)
    big = "X" * 100
    (sandbox / "big.txt").write_text(big)
    tool = frt.FileReaderTool()
    out = tool.execute(action="read", filename="big.txt")
    assert out["status"] == "success"
    assert out["truncated"] is True
    assert len(out["content"]) == 10
