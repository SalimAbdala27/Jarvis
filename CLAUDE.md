# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Jarvis is a Phase 1 scaffold for a local, text-first AI assistant backed by a local Ollama model, with real tool access (files, terminal, browser) scoped to a workspace directory. No voice, remote access, or smart home integration yet — the standalone voice scripts in `jarvis/` (see below) are prototypes, not wired into the running service.

## Setup & commands

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e .                              # core install
pip install -e '.[browser]' --no-use-pep517   # + Playwright for browser tool
playwright install chromium
pip install -e '.[dev]'                       # ruff
cp .env.example .env                          # then edit as needed
```

Run the service (reads config from `.env` / env vars via `jarvis.config.get_settings`):
```bash
python -m jarvis.main
# -> http://127.0.0.1:8765
```

Lint:
```bash
ruff check .
```

There is no pytest suite. The closest thing to tests is a direct smoke script that exercises tools against the real filesystem/terminal/browser (no mocking):
```bash
python scripts/smoke_tools.py
```

Manual API exercise:
```bash
curl -s http://127.0.0.1:8765/api/chat -H 'content-type: application/json' \
  -d '{"message":"List the files in my workspace."}'
curl -s http://127.0.0.1:8765/api/tools
```

Requires a local Ollama server with the configured model pulled (default `qwen2.5-coder:1.5b`, see `JARVIS_MODEL`):
```bash
ollama pull qwen2.5-coder:1.5b
```

## Architecture

**No web framework** — `jarvis/main.py` wires everything up at module scope (settings, tool registry, agent) and serves HTTP with the stdlib `http.server.ThreadingHTTPServer`/`BaseHTTPRequestHandler`. Routes are hand-dispatched in `do_GET`/`do_POST`: `/` and `/static/*` serve the vanilla JS/HTML/CSS chat UI in `jarvis/static/`, `/api/tools` dumps tool schemas, `/api/chat` drives the agent.

**Tool-calling agent loop** (`jarvis/agent.py`): `JarvisAgent.chat()` keeps per-`session_id` message history in memory (no persistence across restarts) and loops up to `settings.max_tool_calls` times: call the LLM with the full tool schema list, execute any `tool_calls` the model returns, append `role: tool` messages, repeat until the model returns plain content with no calls. Because small local models often don't emit native `tool_calls`, there's a fallback (`_extract_text_tool_call`) that parses a JSON object (optionally fenced in a ```` ``` ```` block) with `name`/`arguments` out of the assistant's text content and treats it as a single tool call — but only for one round, after which it returns a summary of tool results instead of looping again.

**LLM client** (`jarvis/llm.py`): a minimal `urllib`-based client that POSTs to Ollama's `/api/chat` (`OLLAMA_BASE_URL`), non-streaming.

**Tool registry pattern** (`jarvis/tools/registry.py` + `jarvis/tools/*.py`): each tool module (`files.py`, `terminal.py`, `browser.py`) defines a class holding the actual logic and a `register_*_tool(registry, instance)` function that registers the OpenAI/Ollama-style function schema plus a bound handler. `ToolRegistry.call()` catches all handler exceptions and turns them into a failed `ToolResult` rather than raising — tool code can validate by raising, and it becomes a graceful failure back to the model. All results flow through the `ToolResult`/`ChatResponse` dataclasses in `jarvis/schemas.py`.

**Safety boundaries are enforced in the tool layer, not the LLM prompt:**
- `FileTools._resolve` (`jarvis/tools/files.py`) resolves every path against `JARVIS_WORKSPACE` and raises if it escapes that directory.
- `TerminalTool` (`jarvis/tools/terminal.py`) runs commands via `shlex.split` + `subprocess.run` (no shell), rejects shell metacharacters (`;`, `&&`, `|`, redirects, `` ` ``, `$(`), and blocks a fixed set of destructive commands/subcommands (`rm`, `mv`, `chmod`, `sudo`, `git reset`, `git checkout`, etc.) and always runs cwd'd inside the workspace.
- `BrowserTool` (`jarvis/tools/browser.py`) drives a persistent local Playwright Chromium context (profile dir configurable; defaults to `./browser-profile`), lazily started on first use, closed on server shutdown (`SIGINT`/`SIGTERM` in `main.py`).

When adding a new tool, follow the existing shape: a class with plain methods returning `ToolResult`, plus a `register_*_tool` function adding the JSON-schema `parameters` block, and wire it into `jarvis/main.py`.

**Config** (`jarvis/config.py`): `get_settings()` is `lru_cache`d, loads `.env` with a hand-rolled parser (`_load_dotenv`, only fills vars not already set in the environment — real env vars always win), then builds a `Settings` dataclass from `os.environ`.

**Voice prototypes**: `listen_loop.py`, `wake_word_test.py`, `stt_test.py`, `tts_test.py` are standalone scripts (not imported by the package) that use `pyaudio`/`openwakeword`/`faster_whisper` and call the running HTTP service (`/api/chat`) directly — they are exploratory and not part of Phase 1's supported surface.
