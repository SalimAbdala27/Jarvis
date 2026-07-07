from jarvis.schemas import ToolResult


class BrowserTool:
    def __init__(self, headless, profile_dir, workspace):
        self.headless = headless
        self.profile_dir = profile_dir
        self.workspace = workspace
        self._playwright = None
        self._context = None
        self._page = None

    def start(self):
        if self._page is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed. Run: pip install -e '.[browser]'") from exc

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()

    def stop(self):
        if self._context is not None:
            self._context.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._playwright = None
        self._context = None
        self._page = None

    def browser_action(self, action, url=None, selector=None, text=None, key=None):
        self.start()
        page = self._page

        if action == "goto":
            if not url:
                return ToolResult(name="browser_action", ok=False, content="url is required")
            page.goto(url, wait_until="domcontentloaded")
            return ToolResult(name="browser_action", ok=True, content="Opened {}".format(page.url))
        if action == "click":
            if not selector:
                return ToolResult(name="browser_action", ok=False, content="selector is required")
            page.click(selector)
            return ToolResult(name="browser_action", ok=True, content="Clicked {}".format(selector))
        if action == "fill":
            if not selector or text is None:
                return ToolResult(name="browser_action", ok=False, content="selector and text are required")
            page.fill(selector, text)
            return ToolResult(name="browser_action", ok=True, content="Filled {}".format(selector))
        if action == "press":
            if not selector or not key:
                return ToolResult(name="browser_action", ok=False, content="selector and key are required")
            page.press(selector, key)
            return ToolResult(name="browser_action", ok=True, content="Pressed {} on {}".format(key, selector))
        if action == "text":
            body = page.locator("body").inner_text(timeout=5000)
            if len(body) > 12000:
                body = body[:12000] + "\n[truncated]"
            return ToolResult(name="browser_action", ok=True, content=body)
        if action == "screenshot":
            path = self.workspace / "browser-screenshot.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(path), full_page=True)
            return ToolResult(name="browser_action", ok=True, content="Saved screenshot to {}".format(path))

        return ToolResult(name="browser_action", ok=False, content="Unknown browser action: {}".format(action))


def register_browser_tool(registry, browser_tool):
    registry.register(
        "browser_action",
        "Control the local browser. Use selectors for click/fill/press.",
        {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["goto", "click", "fill", "press", "text", "screenshot"],
                },
                "url": {"type": "string"},
                "selector": {"type": "string"},
                "text": {"type": "string"},
                "key": {"type": "string"},
            },
            "required": ["action"],
        },
        browser_tool.browser_action,
    )
