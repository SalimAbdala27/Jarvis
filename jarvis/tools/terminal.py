import shlex
import subprocess
from pathlib import Path

from jarvis.schemas import ToolResult

BLOCKED_COMMANDS = {
    "chmod",
    "chown",
    "curl",
    "dd",
    "kill",
    "mv",
    "osascript",
    "pkill",
    "rm",
    "rmdir",
    "sudo",
}
BLOCKED_ARGS = {("git", "reset"), ("git", "checkout")}
SHELL_METACHARS = {";", "&&", "||", "|", ">", ">>", "<", "$(", "`"}


class TerminalTool:
    def __init__(self, workspace):
        self.workspace = workspace

    def _parse(self, command):
        if any(token in command for token in SHELL_METACHARS):
            raise ValueError("Shell metacharacters are blocked; run one simple command at a time")
        args = shlex.split(command)
        if not args:
            raise ValueError("Command is empty")
        executable = Path(args[0]).name
        if executable in BLOCKED_COMMANDS:
            raise ValueError("Blocked command: {}".format(executable))
        if len(args) > 1 and (executable, args[1]) in BLOCKED_ARGS:
            raise ValueError("Blocked command: {} {}".format(executable, args[1]))
        return args

    def run_terminal(self, command, timeout_seconds=20):
        args = self._parse(command)
        timeout_seconds = min(max(timeout_seconds, 1), 60)
        try:
            completed = subprocess.run(
                args,
                cwd=str(self.workspace),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(name="run_terminal", ok=False, content="Command timed out")

        output = completed.stdout.decode(errors="replace")
        error = completed.stderr.decode(errors="replace")
        content = output
        if error:
            content += ("\n" if content else "") + "[stderr]\n{}".format(error)
        if len(content) > 12000:
            content = content[:12000] + "\n[truncated]"
        return ToolResult(name="run_terminal", ok=completed.returncode == 0, content=content or "(no output)")


def register_terminal_tool(registry, terminal_tool):
    registry.register(
        "run_terminal",
        "Run a single non-destructive terminal command inside the Jarvis workspace.",
        {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_seconds": {"type": "integer", "default": 20},
            },
            "required": ["command"],
        },
        terminal_tool.run_terminal,
    )
