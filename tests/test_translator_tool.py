"""Tests for TranslatorTool — language codes, same-language short-circuit, mocked HTTP."""

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from tools import TranslatorTool


@pytest.fixture
def tr() -> TranslatorTool:
    return TranslatorTool()


def test_invalid_source_lang(tr: TranslatorTool) -> None:
    out = tr.execute(text="hello", source_lang="xx", target_lang="en")
    assert out["status"] == "error"
    assert "Unsupported language code" in out["error"]


def test_invalid_target_lang(tr: TranslatorTool) -> None:
    out = tr.execute(text="hello", source_lang="en", target_lang="xx")
    assert out["status"] == "error"


def test_empty_text(tr: TranslatorTool) -> None:
    out = tr.execute(text="", source_lang="en", target_lang="lv")
    assert out["status"] == "error"


def test_same_language_short_circuit_no_network(tr: TranslatorTool, mocker: Any) -> None:
    """Source == target must NOT hit the network."""
    spy = mocker.patch("tools.translator_tool.requests.get")
    out = tr.execute(text="hello", source_lang="en", target_lang="en")
    assert out["status"] == "success"
    assert out["translated_text"] == "hello"
    spy.assert_not_called()


def test_successful_translation_mocked(tr: TranslatorTool, mocker: Any) -> None:
    fake = MagicMock()
    fake.json.return_value = {"responseData": {"translatedText": "labrīt"}}
    fake.raise_for_status = MagicMock()
    mocker.patch("tools.translator_tool.requests.get", return_value=fake)

    out = tr.execute(text="good morning", source_lang="en", target_lang="lv")
    assert out["status"] == "success"
    assert out["translated_text"] == "labrīt"
    assert out["source_lang"] == "en"
    assert out["target_lang"] == "lv"


def test_network_error_returns_structured_error(tr: TranslatorTool, mocker: Any) -> None:
    mocker.patch(
        "tools.translator_tool.requests.get",
        side_effect=requests.ConnectionError("dns fail"),
    )
    out = tr.execute(text="hello", source_lang="en", target_lang="lv")
    assert out["status"] == "error"
    assert "Translation API failed" in out["error"]


def test_empty_response_handled(tr: TranslatorTool, mocker: Any) -> None:
    fake = MagicMock()
    fake.json.return_value = {"responseData": {"translatedText": ""}}
    fake.raise_for_status = MagicMock()
    mocker.patch("tools.translator_tool.requests.get", return_value=fake)

    out = tr.execute(text="hello", source_lang="en", target_lang="lv")
    assert out["status"] == "error"
    assert "Empty translation response" in out["error"]


def test_declaration_shape(tr: TranslatorTool) -> None:
    decl = tr.get_declaration()
    assert decl["name"] == "translate_text"
    required = decl["parameters"]["required"]
    assert set(required) == {"text", "source_lang", "target_lang"}
