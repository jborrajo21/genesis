from genesis.adapter import Completion, Message, ToolCall, ToolDef


class AnthropicAdapter:
    def __init__(self, model: str = "claude-haiku-4-5", max_tokens: int = 20):
        import anthropic

        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, messages: list[Message], tools: list[ToolDef] | None = None) -> Completion:
        has_system = messages[0].role == "system"
        system = messages[0].content if has_system else None
        convo = messages[1:] if has_system else messages

        kwargs = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [self._to_anthropic(m) for m in convo],
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ]

        response = self._client.messages.create(**kwargs)

        text = next((b.text for b in response.content if b.type == "text"), "")
        tool_calls = [
            ToolCall(id=b.id, name=b.name, arguments=b.input)
            for b in response.content
            if b.type == "tool_use"
        ]
        usage = response.usage.input_tokens + response.usage.output_tokens
        return Completion(text=text, tool_calls=tool_calls, usage=usage)

    def _to_anthropic(self, m: Message) -> dict:
        if m.role == "tool":
            return {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}
                ],
            }
        if m.role == "assistant" and m.tool_calls:
            return {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                    for tc in m.tool_calls
                ],
            }
        return {"role": m.role, "content": m.content}
