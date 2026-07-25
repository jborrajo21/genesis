from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass
class ToolDef:
    name: str
    description: str
    input_schema: dict


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None


@dataclass
class Completion:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: int | None = None


class ModelAdapter(Protocol):
    def complete(
        self, messages: list[Message], tools: list[ToolDef] | None = None
    ) -> Completion: ...
