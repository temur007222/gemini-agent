"""Tests for MemoryManager — turn count, trimming, Gemini wire format."""


from memory_manager import MemoryManager


def test_starts_empty() -> None:
    m = MemoryManager()
    assert m.turn_count() == 0
    assert m.get_history() == []


def test_user_message_format() -> None:
    m = MemoryManager()
    m.add_user_message("hi")
    h = m.get_history()
    assert h == [{"role": "user", "parts": [{"text": "hi"}]}]


def test_model_message_format() -> None:
    m = MemoryManager()
    m.add_model_message([{"text": "hello"}])
    assert m.get_history() == [{"role": "model", "parts": [{"text": "hello"}]}]


def test_function_response_format_uses_user_role() -> None:
    """Per Gemini spec, function results travel back with role='user'."""
    m = MemoryManager()
    m.add_function_response("calculator", {"status": "success", "result": 4})
    h = m.get_history()
    assert h[0]["role"] == "user"
    assert "function_response" in h[0]["parts"][0]
    assert h[0]["parts"][0]["function_response"]["name"] == "calculator"
    assert h[0]["parts"][0]["function_response"]["response"] == {
        "status": "success",
        "result": 4,
    }


def test_turn_count_increments() -> None:
    m = MemoryManager()
    m.add_user_message("a")
    m.add_model_message([{"text": "b"}])
    m.add_user_message("c")
    assert m.turn_count() == 3


def test_clear_resets_state() -> None:
    m = MemoryManager()
    m.add_user_message("a")
    m.add_user_message("b")
    m.clear()
    assert m.turn_count() == 0
    assert m.get_history() == []


def test_max_turns_trims_oldest() -> None:
    m = MemoryManager(max_turns=3)
    for i in range(5):
        m.add_user_message(f"msg-{i}")
    h = m.get_history()
    assert len(h) == 3
    # oldest two ("msg-0", "msg-1") were dropped
    assert h[0]["parts"][0]["text"] == "msg-2"
    assert h[-1]["parts"][0]["text"] == "msg-4"


def test_get_history_returns_copy_not_reference() -> None:
    m = MemoryManager()
    m.add_user_message("x")
    snapshot = m.get_history()
    snapshot.clear()
    assert m.turn_count() == 1, "external mutation must not affect internal state"


def test_model_message_with_function_call_part() -> None:
    m = MemoryManager()
    m.add_model_message([
        {"text": "Let me check"},
        {"function_call": {"name": "calculator", "args": {"expression": "2+2"}}},
    ])
    h = m.get_history()
    assert h[0]["role"] == "model"
    assert len(h[0]["parts"]) == 2
    assert "function_call" in h[0]["parts"][1]
