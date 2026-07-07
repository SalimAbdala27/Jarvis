from dataclasses import dataclass, field


@dataclass
class ChatRequest:
    message: str
    session_id: str = "default"


@dataclass
class ToolCall:
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    name: str
    ok: bool
    content: str
    requires_confirmation: bool = False
    confirmation_token: str = None


@dataclass
class ChatResponse:
    session_id: str
    answer: str
    tool_results: list = field(default_factory=list)

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "answer": self.answer,
            "tool_results": [result.__dict__ for result in self.tool_results],
        }
