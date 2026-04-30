# Demo Transcript — Personal Assistant Agent

> ⚠️ **This transcript was generated offline** by `scripts/_make_demo_offline.py`
> with the Gemini SDK stubbed. The Agent loop, ToolRegistry, MemoryManager, ConsoleLogger, and the real tools (Calculator AST evaluator, Open-Meteo geocoding/forecast, MyMemory translation, sandboxed file reader, IANA zoneinfo) all execute normally — only the LLM's textual responses are scripted. To regenerate this file with the real Gemini API, run `python scripts/make_demo.py` after exporting `GEMINI_API_KEY`.

_Tools registered_: `calculator, get_weather, translate_text, read_local_file, get_datetime`

All scenarios run with `/verbose` enabled (`--log-level DEBUG`) so the ReAct loop, tool calls, and tool results are visible.

---

## 1. Direct answer (no tool)

```
You > Who wrote Hamlet?
  [DEBUG] [llm→] turns_in_history=1
  [DEBUG] [llm←] has_function_call=False

Agent > Hamlet was written by William Shakespeare.
```

## 2. Single tool

```
You > What's 17 * 23 + 5?
  [DEBUG] [llm→] turns_in_history=3
  [DEBUG] [llm←] has_function_call=True
  [INFO] [tool→] calculator({'expression': '17 * 23 + 5'})
  [INFO] [tool←] calculator status=success
  [DEBUG] [llm→] turns_in_history=5
  [DEBUG] [llm←] has_function_call=False

Agent > 17 * 23 + 5 = 396.
```

## 3. Multi-tool in one turn

```
You > What's the weather in Riga, and translate 'good morning' to Latvian?
  [DEBUG] [llm→] turns_in_history=7
  [DEBUG] [llm←] has_function_call=True
  [INFO] [tool→] get_weather({'city': 'Riga'})
  [INFO] [tool←] get_weather status=success
  [INFO] [tool→] translate_text({'text': 'good morning', 'source_lang': 'en', 'target_lang': 'lv'})
  [INFO] [tool←] translate_text status=success
  [DEBUG] [llm→] turns_in_history=10
  [DEBUG] [llm←] has_function_call=False

Agent > In Riga it's currently around the high single digits with mostly cloudy skies. 'Good morning' in Latvian is "labrīt".
```

## 4. Error recovery

```
You > What's the weather in Atlantis?
  [DEBUG] [llm→] turns_in_history=12
  [DEBUG] [llm←] has_function_call=True
  [INFO] [tool→] get_weather({'city': 'Atlantis'})
  [INFO] [tool←] get_weather status=error
  [DEBUG] [llm→] turns_in_history=14
  [DEBUG] [llm←] has_function_call=False

Agent > I couldn't find a city named 'Atlantis' in the geocoding service — it isn't a real place I can look up. Did you mean a different city, e.g. Athens or Antalya?
```

## 5a. Memory: store

```
You > My name is Temur.
  [DEBUG] [llm→] turns_in_history=16
  [DEBUG] [llm←] has_function_call=False

Agent > Nice to meet you, Temur — I'll remember that.
```

## 5b. Memory: recall

```
You > What's my name?
  [DEBUG] [llm→] turns_in_history=18
  [DEBUG] [llm←] has_function_call=False

Agent > Your name is Temur.
```
