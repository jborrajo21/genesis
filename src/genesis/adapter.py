from dataclasses import dataclass
from typing import Literal, Protocol


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
