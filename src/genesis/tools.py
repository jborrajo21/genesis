from dataclasses import dataclass
from typing import Callable

from genesis.adapter import ToolDef


@dataclass
class Tool:
    definition: ToolDef
    func: Callable[..., str]


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._by_name = {t.definition.name: t for t in tools}

    def definitions(self) -> list[ToolDef]:
        return [self._by_name[t].definition for t in self._by_name]

    def run(self, name: str, arguments: dict) -> str:
        return self._by_name[name].func(**arguments)


def _add(a: int, b: int) -> str:
    return str(a + b)


add_tool = Tool(
    definition=ToolDef(
        name="add",
        description="Add two integers and return the sum.",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    ),
    func=_add,
)
