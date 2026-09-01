from dataclasses import dataclass, field
from enum import Enum
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


class StopReason(Enum):
    DONE = "done"
    TRUNCATED = "truncated"
    TOOL_USE = "tool_use"
    OTHER = "other"


@dataclass
class Completion:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: int | None = None
    stop_reason: StopReason = StopReason.DONE


class ModelAdapter(Protocol):
    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        response_schema: dict | None = None,
    ) -> Completion: ...
