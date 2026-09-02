from genesis.adapter import Completion, Message, ToolDef


class CountingAdapter:
    """Wraps an adapter, recording rounds and token usage. Protocol-compatible."""

    def __init__(self, inner):
        self.adapter = inner
        self.rounds = 0
        self.tokens = 0

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        response_schema: dict | None = None,
    ) -> Completion:
        self.rounds += 1
        response = self.adapter.complete(messages, tools, response_schema)
        self.tokens += response.usage or 0
        return response
