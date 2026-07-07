# Jarvis

Phase 1 scaffold for a local, text-first AI assistant with real tools:

- Local file access, limited to `JARVIS_WORKSPACE`
- Terminal command execution, run from `JARVIS_WORKSPACE`
- Browser navigation/form interaction through Playwright
- Persistent HTTP service with a simple web chat UI
- Ollama-compatible local model backend

This intentionally does not include voice, remote access, or smart home integration yet.

## Setup

1. Install Python 3.7+.
2. Install Ollama and pull a local model:

   ```bash
   ollama pull qwen2.5-coder:1.5b
   ```

3. Create the environment:

   ```bash
   cp .env.example .env
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -e .
   ```

   If your local `pip` is old and tries to download build tools for an editable install:

   ```bash
   pip install -e . --no-use-pep517
   ```

   Browser control needs Playwright:

   ```bash
   pip install -e '.[browser]' --no-use-pep517
   playwright install chromium
   ```

4. Start the local service:

   ```bash
   python -m jarvis.main
   ```

5. Open:

   ```text
   http://127.0.0.1:8765
   ```

## API

Send a text message:

```bash
curl -s http://127.0.0.1:8765/api/chat \
  -H 'content-type: application/json' \
  -d '{"message":"List the files in my workspace."}'
```

List available tools:

```bash
curl -s http://127.0.0.1:8765/api/tools
```

Run direct tool smoke tests:

```bash
python scripts/smoke_tools.py
```

## Safety Boundaries

Jarvis is a local assistant, but Phase 1 still gives it real capability.

- File tools can only read/write under `JARVIS_WORKSPACE`.
- Terminal commands run inside `JARVIS_WORKSPACE`.
- Shell metacharacters such as `&&`, `;`, pipes, and redirection are blocked.
- Destructive terminal commands such as `rm`, `mv`, `chmod`, and `git reset` are blocked.
- Browser automation uses a local Playwright Chromium session when Playwright is installed.

These are starter guardrails, not a complete security sandbox. Keep the service bound to
`127.0.0.1` until Phase 3 authentication is added.
