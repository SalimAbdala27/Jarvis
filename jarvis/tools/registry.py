from jarvis.schemas import ToolResult


class ToolRegistry:
    def __init__(self):
        self._handlers = {}
        self._schemas = []

    def register(self, name, description, parameters, handler):
        self._handlers[name] = handler
        self._schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            }
        )

    @property
    def schemas(self):
        return self._schemas

    def call(self, name, arguments):
        handler = self._handlers.get(name)
        if handler is None:
            return ToolResult(name=name, ok=False, content="Unknown tool: {}".format(name))
        try:
            return handler(**arguments)
        except Exception as exc:
            return ToolResult(name=name, ok=False, content="{}: {}".format(type(exc).__name__, exc))
