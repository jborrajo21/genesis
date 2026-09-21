from typing import TYPE_CHECKING

from genesis.adapter import Completion, Message, StopReason, ToolCall, ToolDef
from genesis.errors import AdapterAuthError, AdapterError

if TYPE_CHECKING:
    from anthropic.types import MessageParam

_STOP_REASON_MAP: dict[str | None, StopReason] = {
    "end_turn": StopReason.DONE,
    "stop_sequence": StopReason.DONE,
    "max_tokens": StopReason.TRUNCATED,
    "model_context_window_exceeded": StopReason.TRUNCATED,
    "tool_use": StopReason.TOOL_USE,
    "refusal": StopReason.OTHER,
}

SUPPORTED_MODELS = ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"]
DEFAULT_MODEL = "claude-haiku-4-5"


class AnthropicAdapter:
    def __init__(
        self, model: str = DEFAULT_MODEL, max_tokens: int = 20, api_key: str | None = None
    ):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        response_schema: dict | None = None,
    ) -> Completion:
        import anthropic

        has_system = messages[0].role == "system"
        system = messages[0].content if has_system else None
        convo = messages[1:] if has_system else messages
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[self._to_anthropic(m) for m in convo],
                system=system if system else anthropic.omit,
                tools=[
                    {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                    for t in tools
                ]
                if tools
                else anthropic.omit,
                output_config={"format": {"type": "json_schema", "schema": response_schema}}
                if response_schema
                else anthropic.omit,
            )

            text = next((b.text for b in response.content if b.type == "text"), "")
            tool_calls = [
                ToolCall(id=b.id, name=b.name, arguments=b.input)
                for b in response.content
                if b.type == "tool_use"
            ]
            usage = response.usage.input_tokens + response.usage.output_tokens
            return Completion(
                text=text,
                tool_calls=tool_calls,
                usage=usage,
                stop_reason=_STOP_REASON_MAP.get(response.stop_reason, StopReason.OTHER),
            )
        except anthropic.AuthenticationError as e:
            raise AdapterAuthError("the API key was rejected by Anthropic") from e
        except anthropic.APIError as e:
            raise AdapterError(f"the Anthropic API call failed: {e}") from e

    def _to_anthropic(self, m: Message) -> "MessageParam":
        if m.role == "tool":
            if m.tool_call_id is None:
                raise ValueError("tool message has no tool_call_id")
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
