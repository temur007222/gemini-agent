"""FileReaderTool - CUSTOM tool. Read local text files from a sandboxed folder."""

import os
from pathlib import Path
from typing import Any, Dict, List

from .base_tool import BaseTool


# Sandbox: only files inside ./agent_files (relative to current working dir) are readable.
_SANDBOX_DIR = Path(os.environ.get("AGENT_FILES_DIR", "./agent_files")).resolve()
_MAX_BYTES = 50_000  # Hard cap to keep responses short
_ALLOWED_EXTS = {".txt", ".md", ".log", ".csv", ".json", ".py", ".yaml", ".yml"}


class FileReaderTool(BaseTool):
    @property
    def name(self) -> str:
        return "read_local_file"

    @property
    def description(self) -> str:
        return (
            "Read a text file from the sandboxed agent_files/ folder, or list "
            "available files. Use action='list' to see files, action='read' with "
            "filename to read one."
        )

    def _ensure_sandbox(self) -> None:
        _SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    def _list_files(self) -> List[str]:
        self._ensure_sandbox()
        return sorted(
            p.name for p in _SANDBOX_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in _ALLOWED_EXTS
        )

    def execute(self, action: str, filename: str = "") -> Dict[str, Any]:  # type: ignore[override]
        action = (action or "").lower().strip()

        if action == "list":
            return {
                "status": "success",
                "sandbox_dir": str(_SANDBOX_DIR),
                "files": self._list_files(),
            }

        if action != "read":
            return {"status": "error", "error": "action must be 'list' or 'read'"}

        if not filename:
            return {"status": "error", "error": "filename is required when action='read'"}

        # Resolve and confirm the path stays inside the sandbox (defense vs path traversal)
        target = (_SANDBOX_DIR / filename).resolve()
        try:
            target.relative_to(_SANDBOX_DIR)
        except ValueError:
            return {"status": "error", "error": "Path traversal blocked: file must be inside sandbox"}

        if target.suffix.lower() not in _ALLOWED_EXTS:
            return {"status": "error", "error": f"Extension not allowed. Allowed: {sorted(_ALLOWED_EXTS)}"}
        if not target.exists() or not target.is_file():
            return {"status": "error", "error": f"File '{filename}' not found in sandbox"}

        try:
            data = target.read_bytes()
        except OSError as e:
            return {"status": "error", "error": f"Read failed: {e}"}

        truncated = len(data) > _MAX_BYTES
        text = data[:_MAX_BYTES].decode("utf-8", errors="replace")
        return {
            "status": "success",
            "filename": filename,
            "size_bytes": len(data),
            "truncated": truncated,
            "content": text,
        }

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "read"],
                        "description": "'list' to show files, 'read' to fetch one",
                    },
                    "filename": {
                        "type": "string",
                        "description": "File name (required when action='read')",
                    },
                },
                "required": ["action"],
            },
        }
