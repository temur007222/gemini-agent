"""DateTimeTool - return current date/time for any IANA timezone.

Demonstrates the Open/Closed Principle: this entire file is new, the Agent
class is unchanged, and registration happens with a single line in `main.py`.

Uses only the standard library (`zoneinfo`, available since Python 3.9) — no
new dependencies are introduced.
"""

from datetime import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .base_tool import BaseTool


class DateTimeTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_datetime"

    @property
    def description(self) -> str:
        return (
            "Get the current date and time for an IANA timezone "
            "(e.g. 'Europe/Riga', 'Asia/Tashkent', 'UTC'). "
            "Defaults to UTC if no timezone is provided."
        )

    def execute(self, timezone: str = "UTC") -> Dict[str, Any]:  # type: ignore[override]
        tz_name = (timezone or "UTC").strip()
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            return {
                "status": "error",
                "error": f"Unknown timezone '{tz_name}'. Use IANA names like 'Europe/Riga'.",
            }

        now = datetime.now(tz)
        return {
            "status": "success",
            "timezone": tz_name,
            "iso8601": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A"),
            "utc_offset": now.strftime("%z"),
        }

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": (
                            "IANA timezone identifier, e.g. 'Europe/Riga', "
                            "'Asia/Tashkent', 'America/New_York'. Defaults to UTC."
                        ),
                    }
                },
                "required": [],
            },
        }
