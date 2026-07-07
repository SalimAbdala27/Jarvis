import json
import mimetypes
import signal
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from jarvis.agent import JarvisAgent
from jarvis.config import get_settings
from jarvis.llm import OllamaClient
from jarvis.tools import BrowserTool, FileTools, TerminalTool, ToolRegistry
from jarvis.tools.browser import register_browser_tool
from jarvis.tools.files import register_file_tools
from jarvis.tools.terminal import register_terminal_tool


ROOT = Path(__file__).parent
STATIC = ROOT / "static"

settings = get_settings()
registry = ToolRegistry()
file_tools = FileTools(settings.resolved_workspace)
terminal_tool = TerminalTool(settings.resolved_workspace)
browser_tool = BrowserTool(
    headless=settings.browser_headless,
    profile_dir=Path.cwd() / "browser-profile",
    workspace=settings.resolved_workspace,
)
register_file_tools(registry, file_tools)
register_terminal_tool(registry, terminal_tool)
register_browser_tool(registry, browser_tool)
agent = JarvisAgent(settings=settings, llm=OllamaClient(settings), tools=registry)


class JarvisHandler(BaseHTTPRequestHandler):
    server_version = "Jarvis/0.1"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_file(STATIC / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/health":
            self._send_json({"status": "ok", "workspace": str(settings.resolved_workspace)})
            return
        if parsed.path == "/api/tools":
            self._send_json(registry.schemas)
            return
        if parsed.path.startswith("/static/"):
            requested = (STATIC / parsed.path[len("/static/") :]).resolve()
            if STATIC.resolve() == requested or STATIC.resolve() in requested.parents:
                self._send_file(requested)
                return
        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/chat":
            self._send_json({"error": "Not found"}, status=404)
            return

        try:
            payload = self._read_json()
            message = str(payload.get("message", "")).strip()
            session_id = str(payload.get("session_id", "default"))
            if not message:
                self._send_json({"error": "message is required"}, status=400)
                return
            response = agent.chat(session_id=session_id, message=message)
            self._send_json(response.to_dict())
        except Exception as exc:
            self._send_json({"error": "{}: {}".format(type(exc).__name__, exc)}, status=500)

    def log_message(self, fmt, *args):
        print("{} - {}".format(self.address_string(), fmt % args))

    def _read_json(self):
        length = int(self.headers.get("content-length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        return json.loads(raw_body or "{}")

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type=None):
        if not path.is_file():
            self._send_json({"error": "Not found"}, status=404)
            return
        body = path.read_bytes()
        guessed_type = content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("content-type", guessed_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run():
    server = ThreadingHTTPServer((settings.host, settings.port), JarvisHandler)

    def shutdown(_signum, _frame):
        browser_tool.stop()
        server.server_close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print("Jarvis running at http://{}:{}".format(settings.host, settings.port))
    print("Workspace: {}".format(settings.resolved_workspace))
    server.serve_forever()


if __name__ == "__main__":
    run()
