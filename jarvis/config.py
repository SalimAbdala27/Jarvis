import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass
class Settings:
    host: str
    port: int
    model: str
    workspace: Path
    browser_headless: bool
    max_tool_calls: int
    ollama_base_url: str

    @property
    def resolved_workspace(self):
        workspace = self.workspace.expanduser().resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace


def _load_dotenv(path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _as_bool(value):
    return str(value).lower() in {"1", "true", "yes", "on"}


@lru_cache()
def get_settings():
    _load_dotenv(Path.cwd() / ".env")
    return Settings(
        host=os.environ.get("JARVIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("JARVIS_PORT", "8765")),
        model=os.environ.get("JARVIS_MODEL", "qwen2.5-coder:1.5b"),
        workspace=Path(os.environ.get("JARVIS_WORKSPACE", str(Path.cwd() / "workspace"))),
        browser_headless=_as_bool(os.environ.get("JARVIS_BROWSER_HEADLESS", "false")),
        max_tool_calls=int(os.environ.get("JARVIS_MAX_TOOL_CALLS", "6")),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    )
