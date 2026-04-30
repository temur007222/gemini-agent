"""TranslatorTool - CUSTOM tool. Translation via MyMemory free API."""

from typing import Any, Dict

import requests

from .base_tool import BaseTool


_API_URL = "https://api.mymemory.translated.net/get"

# Common ISO-639-1 codes the agent might receive
_VALID_CODES = {
    "en", "ru", "uz", "tr", "ko", "lv", "de", "fr", "es", "it",
    "ja", "zh", "ar", "pt", "pl", "uk", "nl", "sv", "fi", "cs",
}


class TranslatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "translate_text"

    @property
    def description(self) -> str:
        return (
            "Translate text between languages. Use ISO-639-1 codes "
            "(en, ru, uz, tr, ko, lv, de, fr, es, ja, zh, ar, ...)."
        )

    def execute(  # type: ignore[override]
        self, text: str, source_lang: str, target_lang: str,
    ) -> Dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            return {"status": "error", "error": "text must be a non-empty string"}
        src = (source_lang or "").lower().strip()
        tgt = (target_lang or "").lower().strip()
        if src not in _VALID_CODES or tgt not in _VALID_CODES:
            return {
                "status": "error",
                "error": f"Unsupported language code. Supported: {sorted(_VALID_CODES)}",
            }
        if src == tgt:
            return {"status": "success", "translated_text": text, "note": "source == target"}

        try:
            resp = requests.get(
                _API_URL,
                params={"q": text, "langpair": f"{src}|{tgt}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {"status": "error", "error": f"Translation API failed: {e}"}

        translated = (data.get("responseData") or {}).get("translatedText")
        if not translated:
            return {"status": "error", "error": "Empty translation response"}

        return {
            "status": "success",
            "source_lang": src,
            "target_lang": tgt,
            "original_text": text,
            "translated_text": translated,
        }

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to translate"},
                    "source_lang": {"type": "string", "description": "Source ISO-639-1 code"},
                    "target_lang": {"type": "string", "description": "Target ISO-639-1 code"},
                },
                "required": ["text", "source_lang", "target_lang"],
            },
        }
