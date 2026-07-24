import anthropic

from genesis.adapter import Completion, Message


class AnthropicAdapter:
    def __init__(self, model: str = "claude-haiku-4-5", max_tokens: int = 20):
        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, messages: list[Message]) -> Completion:
        has_system = messages[0].role == "system"

        if has_system:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=messages[0].content,
                messages=[{"role": m.role, "content": m.content} for m in messages[1:]],
            )
        else:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            )
        text = next((b.text for b in response.content if b.type == "text"), "")
        usage = response.usage.input_tokens + response.usage.output_tokens
        return Completion(text=text, usage=usage)
