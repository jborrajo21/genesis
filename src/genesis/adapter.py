from dataclasses import dataclass
from typing import Protocol, Literal

@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str

@dataclass
class Completion:
    text: str
    usage: int | None = None

class ModelAdapter(Protocol):
    def complete(self, messages: list[Message]) -> Completion: ...