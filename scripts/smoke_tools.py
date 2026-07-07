from pathlib import Path

from jarvis.config import get_settings
from jarvis.tools import BrowserTool, FileTools, TerminalTool


def main():
    settings = get_settings()
    workspace = settings.resolved_workspace

    files = FileTools(workspace)
    terminal = TerminalTool(workspace)
    browser = BrowserTool(
        headless=True,
        profile_dir=Path.cwd() / "browser-profile-smoke",
        workspace=workspace,
    )

    checks = [
        files.list_files("."),
        terminal.run_terminal("pwd"),
    ]

    try:
        checks.append(browser.browser_action("goto", url="https://example.com"))
        checks.append(browser.browser_action("text"))
    finally:
        browser.stop()

    failed = False
    for result in checks:
        status = "OK" if result.ok else "FAIL"
        print("{} {}: {}".format(status, result.name, result.content.splitlines()[0]))
        failed = failed or not result.ok

    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
