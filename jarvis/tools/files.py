from jarvis.schemas import ToolResult


class FileTools:
    def __init__(self, workspace):
        self.workspace = workspace

    def _resolve(self, path):
        target = (self.workspace / path).expanduser().resolve()
        if target != self.workspace and self.workspace not in target.parents:
            raise ValueError("Path is outside the configured Jarvis workspace")
        return target

    def list_files(self, path="."):
        target = self._resolve(path)
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
        if not target.is_file():
            return ToolResult(name="read_file", ok=False, content="Not a file: {}".format(path))
        content = target.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            content = content[:max_chars] + "\n[truncated]"
        return ToolResult(name="read_file", ok=True, content=content)

    def write_file(self, path, content, overwrite=False):
        target = self._resolve(path)
        if target.exists() and not overwrite:
            return ToolResult(name="write_file", ok=False, content="File exists; set overwrite=true")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(name="write_file", ok=True, content="Wrote {}".format(target.relative_to(self.workspace)))


def register_file_tools(registry, file_tools):
    registry.register(
        "list_files",
        "List files and directories inside the Jarvis workspace.",
        {
            "type": "object",
            "properties": {"path": {"type": "string", "default": "."}},
        },
        file_tools.list_files,
    )
    registry.register(
        "read_file",
        "Read a UTF-8 text file from the Jarvis workspace.",
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
        "Write a UTF-8 text file inside the Jarvis workspace.",
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
