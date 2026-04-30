# Test Scenarios

Each scenario the assignment requires is mapped here to the test that proves
it works. All 70 cases run **fully offline** (Gemini SDK and HTTP clients
are mocked) so a grader can verify correctness without an API key.

Run the whole suite:
```bash
pytest -v
```

Run one scenario:
```bash
pytest tests/test_agent.py::test_react_loop_executes_tool_then_returns_final -v
```

---

## Functional testing of the main workflow

| Scenario | Test |
|---|---|
| Direct answer (model returns text only, no tool call) | `tests/test_agent.py::test_direct_answer_no_tool_call` |
| Single-tool ReAct round-trip (tool call → tool result → final text) | `tests/test_agent.py::test_react_loop_executes_tool_then_returns_final` |
| Multi-tool in one turn (two `function_call` parts in one response) | `tests/test_agent.py::test_multi_tool_in_single_turn` |
| Observer events fire in order during a tool call | `tests/test_agent.py::test_observer_events_fire_for_tool_call` |
| Memory format (Gemini wire schema) preserved across user/model/function turns | `tests/test_memory_manager.py::test_function_response_format_uses_user_role` and siblings |

## Tool testing — every tool, happy path + edge cases

### CalculatorTool
| Scenario | Test |
|---|---|
| Valid arithmetic | `test_calculator_tool.py::test_valid_arithmetic` |
| Parentheses + power | `test_parentheses_and_power` |
| Floor division and modulo | `test_floor_div_and_mod` |
| Unary minus | `test_unary_minus` |
| Empty / syntax-error expression | `test_empty_expression`, `test_syntax_error` |
| AST whitelist blocks `__import__`, attribute access, function calls | `test_no_eval_access_*` (3 tests) |
| Internal `_safe_eval` rejects non-whitelisted nodes | `test_internal_safe_eval_only_handles_whitelist` |

### WeatherTool
| Scenario | Test |
|---|---|
| City not found (geocoder returns empty) | `test_weather_tool.py::test_city_not_found` |
| Successful two-step request (geocode + forecast) | `test_successful_weather_mocked` |
| Network error on geocoding step | `test_network_error_on_geocoding` |
| Network error on forecast step | `test_network_error_on_forecast` |
| Unknown weather code falls back to "Unknown" | `test_unknown_weathercode_falls_back` |

### TranslatorTool
| Scenario | Test |
|---|---|
| Invalid source / target language code | `test_invalid_source_lang`, `test_invalid_target_lang` |
| Same language short-circuits — no network call | `test_same_language_short_circuit_no_network` |
| Successful translation (mocked HTTP) | `test_successful_translation_mocked` |
| Network failure mapped to structured error | `test_network_error_returns_structured_error` |
| Empty translation response handled | `test_empty_response_handled` |

### FileReaderTool
| Scenario | Test |
|---|---|
| List sandbox (empty + with files) | `test_list_action_empty_sandbox`, `test_list_returns_only_allowed_extensions` |
| Read existing file | `test_read_existing_file` |
| Read missing file | `test_read_missing_file` |
| Blocked extension (e.g. `.exe`) | `test_read_blocked_extension` |
| **Path traversal blocked** (`../../../etc/passwd`) | `test_path_traversal_blocked` |
| **Absolute path blocked** (`/etc/passwd`) | `test_absolute_path_outside_sandbox_blocked` |
| Unknown action argument | `test_unknown_action` |
| Truncation on oversize files | `test_truncation_on_large_file` |

### DateTimeTool
| Scenario | Test |
|---|---|
| Default timezone is UTC | `test_default_timezone_is_utc` |
| Named IANA timezone | `test_named_timezone` |
| Unknown timezone returns structured error | `test_unknown_timezone_returns_error` |
| Empty string falls back to UTC | `test_empty_string_falls_back_to_utc` |
| Returned timestamp is close to current time | `test_returned_time_close_to_now` |
| **OCP regression**: Agent.py never imports a concrete tool | `test_ocp_demonstration_register_without_agent_change` |

### ToolRegistry
| Scenario | Test |
|---|---|
| Registration + listing | `test_register_and_list` |
| Duplicate name rejected | `test_duplicate_name_rejected` |
| Non-`BaseTool` instance rejected | `test_register_rejects_non_basetool` |
| Unknown tool dispatch returns structured error | `test_unknown_tool_dispatch_returns_structured_error` |
| Bad arguments object (not a dict) returns structured error | `test_bad_args_object_returns_structured_error` |
| Tool runtime exceptions wrapped, never escape | `test_dispatch_wraps_tool_exceptions` |
| Unregister is idempotent | `test_unregister` |

## Input validation testing

- Empty/whitespace string in every tool that accepts text
  (`test_calculator_tool::test_empty_expression`,
   `test_translator_tool::test_empty_text`,
   `test_weather_tool::test_empty_city`).
- Wrong types via `safe_execute()` (TypeError → structured error)
  (`test_calculator_tool::test_safe_execute_with_wrong_args`).
- Invalid action verb in `FileReaderTool`
  (`test_file_reader_tool::test_unknown_action`).
- Missing required argument when reading files
  (`test_file_reader_tool::test_read_without_filename`).

## Error handling testing

- LLM API exceptions surface as `[Agent error] ...` and emit ERROR event
  (`test_agent.py::test_llm_exception_returns_structured_error`).
- Max-iteration cap stops runaway tool-call loops
  (`test_agent.py::test_max_iterations_cap`).
- Hallucinated tool name → registry returns error → loop continues, gets final
  text answer (`test_agent.py::test_unknown_tool_call_recovers`).
- Network errors in `requests.get` → structured tool error, never raises out
  of the tool layer (`test_translator_tool::test_network_error_*`,
  `test_weather_tool::test_network_error_*`).

## Coverage summary

```
70 passed in 0.28s
```

Run the suite yourself:
```bash
pytest -v       # show every scenario
pytest -q       # one-line summary
mypy            # strict type-check 12 source files
ruff check .    # lint
```
