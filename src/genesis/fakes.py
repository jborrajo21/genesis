from genesis.adapter import Completion, Message, ToolDef


class FakeAdapter:
    def __init__(self, responses: list[Completion]):
        self._responses = list(responses)
        self.calls: list[list[Message]] = []

    def complete(self, messages: list[Message], tools: list[ToolDef] | None = None) -> Completion:
        self.calls.append(list(messages))
        return self._responses.pop(0)
