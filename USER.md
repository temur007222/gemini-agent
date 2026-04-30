# User Guide

This is the runbook for **using** the Personal Assistant Agent. If you want
to read the code or extend it, see [`DEVELOPER.md`](DEVELOPER.md) instead.

## What it does

You type a question in plain English (or any language Gemini speaks). The
agent decides whether it can answer directly, or whether it should call one
of its tools — a calculator, a weather lookup, a translator, a local-file
reader, or a date/time lookup. After it gets the result, it writes the
answer back to you in plain language.

## Prerequisites

- Python 3.11 or newer (3.12, 3.13, 3.14 all tested).
- A Google **Gemini API key** — get one free at
  <https://aistudio.google.com/app/apikey>.
- Internet access (for Gemini and for the weather/translator tools).

## Setup (5 minutes)

```bash
# 1. Get the project
unzip gemini_agent_final.zip -d gemini-agent
cd gemini-agent

# 2. Create an isolated Python environment
python3 -m venv .venv
source .venv/bin/activate           # macOS/Linux
# .venv\Scripts\activate            # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
cp .env.example .env
# Open .env in any editor and replace `replace_me` with your real key.
# Then export it (or use a tool like direnv / dotenv-cli):
export GEMINI_API_KEY="paste-your-key-here"
```

## Running

```bash
python main.py
```

You'll see:

```
╔══════════════════════════════════════════════╗
║   Personal Assistant Agent (Gemini + ReAct)  ║
╚══════════════════════════════════════════════╝
Type your message. Commands: /tools  /clear  /verbose  /quit

Registered tools: calculator, get_weather, translate_text, read_local_file, get_datetime

You >
```

### REPL commands

| Command | What it does |
|---|---|
| anything else | sent to the agent |
| `/tools` | list the tools the agent can use |
| `/verbose` | toggle a live trace of every tool call and LLM round-trip |
| `/clear` | wipe the conversation memory (start fresh) |
| `/quit` (or `/exit`) | leave the program |

### Optional flags

```bash
python main.py --log-level DEBUG    # show every LLM round-trip + tool call
python main.py --log-level WARNING  # quietest; only show errors
python main.py --help               # show all options
```

## Examples to try

```
You > What's 17 * 23 + 5?
You > Weather in Riga, and translate "good morning" to Latvian
You > What time is it in Tashkent right now?
You > List the files in my notes folder.
You > Read notes.md and summarize it.
You > Who wrote Hamlet?
```

## Where your files live

The `read_local_file` tool can read text files from `./agent_files/`.
That folder is sandboxed: the agent **cannot** read anywhere else, even if
you ask it to. Allowed extensions: `.txt`, `.md`, `.log`, `.csv`, `.json`,
`.py`, `.yaml`, `.yml`. Files larger than 50 KB are truncated.

To add your own notes, just drop a file into `agent_files/`:

```bash
echo "My TODO list..." > agent_files/todo.md
```

You can also point the sandbox at a different folder:

```bash
export AGENT_FILES_DIR="/Users/me/Documents/AgentNotes"
python main.py
```

## What if something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `ERROR: GEMINI_API_KEY environment variable is not set` | the key isn't exported in the current shell | re-run `export GEMINI_API_KEY="..."` |
| `[Agent error] LLM call failed: ...` | invalid key, quota exceeded, or no internet | check the key and your connection; try again in a minute |
| Tool returns `"City 'X' not found"` | Open-Meteo's geocoder doesn't recognise the city | retry with a more standard name (e.g. "Tashkent" not "Toshkent") |
| `Translation API failed` | MyMemory daily limit hit (anonymous quota) | wait an hour or use a smaller batch |
| `Path traversal blocked` | you asked the agent to read a file outside `agent_files/` | this is intentional; move the file in or set `AGENT_FILES_DIR` |
| `[Agent error] Reasoning loop exceeded max iterations` | the model kept trying tool calls without converging | clear memory with `/clear` and rephrase |

## Privacy & safety

- Your messages are sent to **Google Gemini** for inference. Read Google's
  privacy notice before using sensitive data.
- The translator tool sends the text to **MyMemory**. The weather tool
  sends a **city name** to Open-Meteo (no personal data).
- The local file reader is **strictly sandboxed** — it cannot escape
  `./agent_files/` even if the model asks it to.
- Conversation memory is **not persisted to disk** — it lives only in the
  process and is wiped when you exit.

## Uninstall

Just delete the project folder:

```bash
deactivate                 # leave the venv if you're inside it
rm -rf gemini-agent
```

No system-level files are written outside the project folder and the
configured `AGENT_FILES_DIR`.
