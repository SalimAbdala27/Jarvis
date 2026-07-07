import uuid
from pathlib import Path

from jarvis.schemas import ToolResult


class UnknownTokenError(Exception):
    pass


BINARY_SAMPLE_SIZE = 8192
BINARY_REPLACEMENT_RATIO_THRESHOLD = 0.01


class FileTools:
    def __init__(self, workspace):
        self.workspace = workspace
        self.home = Path.home().resolve()
        self._pending = {}

    def _resolve(self, path):
        candidate = Path(path).expanduser()
        target = candidate if candidate.is_absolute() else self.workspace / candidate
        return target.resolve()

    @staticmethod
    def _is_within(target, root):
        return target == root or root in target.parents

    def _in_workspace(self, target):
        return self._is_within(target, self.workspace)

    def _ensure_within_bounds(self, target):
        if not self._in_workspace(target) and not self._is_within(target, self.home):
            raise ValueError("Path is outside the home directory")

    def list_files(self, path="."):
        target = self._resolve(path)
        self._ensure_within_bounds(target)
        if not target.exists():
            return ToolResult(name="list_files", ok=False, content="Not found: {}".format(path))
        if not target.is_dir():
            return ToolResult(name="list_files", ok=False, content="Not a directory: {}".format(path))
        lines = []
        for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            suffix = "/" if child.is_dir() else ""
            lines.append("{}{}".format(child.name, suffix))
        return ToolResult(name="list_files", ok=True, content="\n".join(lines) or "(empty)")

    def read_file(self, path, max_chars=12000):
        target = self._resolve(path)
        self._ensure_within_bounds(target)
        if not target.is_file():
            return ToolResult(name="read_file", ok=False, content="Not a file: {}".format(path))
        if self._looks_binary(target):
            return ToolResult(
                name="read_file", ok=False, content="Binary file, cannot display as text: {}".format(path)
            )
        content = target.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            content = content[:max_chars] + "\n[truncated]"
        return ToolResult(name="read_file", ok=True, content=content)

    @staticmethod
    def _looks_binary(target):
        with target.open("rb") as fh:
            sample = fh.read(BINARY_SAMPLE_SIZE)
        if b"\x00" in sample:
            return True
        if not sample:
            return False
        decoded = sample.decode("utf-8", errors="replace")
        replacement_ratio = decoded.count("�") / len(decoded)
        return replacement_ratio > BINARY_REPLACEMENT_RATIO_THRESHOLD

    def write_file(self, path, content, overwrite=False):
        target = self._resolve(path)
        self._ensure_within_bounds(target)
        if self._in_workspace(target):
            return self._perform_write(target, content, overwrite)

        exists = target.exists()
        if exists and not overwrite:
            return ToolResult(name="write_file", ok=False, content="File exists; set overwrite=true")

        description = "Write {} chars to {}{}".format(
            len(content), target, " (overwrite existing file)" if exists else ""
        )
        return self._queue(
            action="write_file",
            target=target,
            payload={"content": content, "overwrite": overwrite},
            description=description,
        )

    def delete_file(self, path):
        target = self._resolve(path)
        self._ensure_within_bounds(target)
        if self._in_workspace(target):
            return self._perform_delete(target)

        if not target.exists():
            return ToolResult(name="delete_file", ok=False, content="Not found: {}".format(target))
        if not target.is_file():
            return ToolResult(name="delete_file", ok=False, content="Not a file: {}".format(target))

        return self._queue(
            action="delete_file",
            target=target,
            payload={},
            description="Delete {}".format(target),
        )

    def confirm(self, token):
        pending = self._pop_pending(token)
        target = pending["target"]
        if pending["action"] == "write_file":
            return self._perform_write(target, pending["payload"]["content"], pending["payload"]["overwrite"])
        return self._perform_delete(target)

    def discard(self, token):
        pending = self._pop_pending(token)
        return ToolResult(name="discard", ok=True, content="Discarded: {}".format(pending["description"]))

    def _pop_pending(self, token):
        pending = self._pending.pop(token, None)
        if pending is None:
            raise UnknownTokenError("Unknown or already-resolved token: {}".format(token))
        return pending

    def _queue(self, action, target, payload, description):
        token = uuid.uuid4().hex
        self._pending[token] = {
            "action": action,
            "target": target,
            "payload": payload,
            "description": description,
        }
        return ToolResult(
            name=action,
            ok=True,
            content="Confirmation required: {}. Token: {}".format(description, token),
            requires_confirmation=True,
            confirmation_token=token,
        )

    def _perform_write(self, target, content, overwrite):
        if target.exists() and not overwrite:
            return ToolResult(name="write_file", ok=False, content="File exists; set overwrite=true")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(name="write_file", ok=True, content="Wrote {}".format(target))

    def _perform_delete(self, target):
        if not target.exists():
            return ToolResult(name="delete_file", ok=False, content="Not found: {}".format(target))
        if not target.is_file():
            return ToolResult(name="delete_file", ok=False, content="Not a file: {}".format(target))
        target.unlink()
        return ToolResult(name="delete_file", ok=True, content="Deleted {}".format(target))


def register_file_tools(registry, file_tools):
    registry.register(
        "list_files",
        "List files and directories under the Jarvis workspace or the user's home directory.",
        {
            "type": "object",
            "properties": {"path": {"type": "string", "default": "."}},
        },
        file_tools.list_files,
    )
    registry.register(
        "read_file",
        "Read a UTF-8 text file from the Jarvis workspace or the user's home directory.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_chars": {"type": "integer", "default": 12000},
            },
            "required": ["path"],
        },
        file_tools.read_file,
    )
    registry.register(
        "write_file",
        (
            "Write a UTF-8 text file. Writes inside the Jarvis workspace happen immediately. "
            "Writes elsewhere under the home directory are queued and require confirmation "
            "via POST /api/confirm before they take effect."
        ),
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "overwrite": {"type": "boolean", "default": False},
            },
            "required": ["path", "content"],
        },
        file_tools.write_file,
    )
    registry.register(
        "delete_file",
        (
            "Delete a single file (not a directory). Deletes inside the Jarvis workspace happen "
            "immediately. Deletes elsewhere under the home directory are queued and require "
            "confirmation via POST /api/confirm before they take effect."
        ),
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        file_tools.delete_file,
    )
