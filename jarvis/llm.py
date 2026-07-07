import json
from urllib import request


class OllamaClient:
    def __init__(self, settings):
        self.settings = settings

    def chat(self, messages, tools):
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {
                "temperature": 0.2,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            self.settings.ollama_base_url.rstrip("/") + "/api/chat",
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        with request.urlopen(http_request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
