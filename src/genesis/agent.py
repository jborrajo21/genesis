from dataclasses import dataclass, field
from typing import Literal

from genesis.adapter import Message, ModelAdapter, ToolCall
from genesis.tools import ToolRegistry


@dataclass
class AgentResult:
    text: str
    stop_reason: Literal["done", "max_turns", "budget"]
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: int = 0
    turns: int = 0


class Agent:
    def __init__(
        self,
        adapter: ModelAdapter,
        registry: ToolRegistry,
        max_turns: int = 10,
        token_budget: int = 1024,
    ):
        self._adapter = adapter
        self._registry = registry
        self._max_turns = max_turns
        self._token_budget = token_budget

    def run(self, prompt: str) -> AgentResult:
        messages = [Message(role="user", content=prompt)]
        total_usage = 0
        tool_calls: list[ToolCall] = []
        last_text = ""
        for turn in range(self._max_turns):
            completion = self._adapter.complete(messages, tools=self._registry.definitions())
            last_text = completion.text
            total_usage += completion.usage or 0
            if not completion.tool_calls:
                return AgentResult(last_text, "done", tool_calls, total_usage, turn + 1)

            if total_usage > self._token_budget:
                return AgentResult(last_text, "budget", tool_calls, total_usage, turn + 1)
            messages.append(
                Message(role="assistant", content=completion.text, tool_calls=completion.tool_calls)
            )
            for call in completion.tool_calls:
                tool_calls.append(call)
                result = self._registry.run(call.name, call.arguments)
                messages.append(Message(role="tool", content=result, tool_call_id=call.id))
        return AgentResult(last_text, "max_turns", tool_calls, total_usage, turn + 1)
