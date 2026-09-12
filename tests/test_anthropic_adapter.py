import os
from types import SimpleNamespace

import pytest

from genesis.adapter import Message
from genesis.anthropic_adapter import AnthropicAdapter


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="no ANTHROPIC_API_KEY set; live smoke test skipped",
)
def test_anthropic_adapter_smoke():
    adapter = AnthropicAdapter(model="claude-haiku-4-5", max_tokens=20)
    result = adapter.complete([Message(role="user", content="Say hi in one word")])
    assert result.text
    assert result.usage and result.usage > 0


def _stub_client(captured, *, text="hi", stop_reason="end_turn"):
    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
            stop_reason=stop_reason,
        )

    return SimpleNamespace(messages=SimpleNamespace(create=create))


def test_response_schema_becomes_output_config(monkeypatch):
    captured = {}
    adapter = AnthropicAdapter(model="m", max_tokens=100)
    adapter._client = _stub_client(captured)
    schema = {"type": "object", "properties": {}, "additionalProperties": False}
    adapter.complete([Message(role="user", content="hi")], response_schema=schema)
    assert captured["output_config"]["format"]["type"] == "json_schema"
    assert captured["output_config"]["format"]["schema"] == schema


def test_no_output_config_without_schema(monkeypatch):
    captured = {}
    adapter = AnthropicAdapter(model="m", max_tokens=100)
    adapter._client = _stub_client(captured)
    adapter.complete([Message(role="user", content="hi")])
    assert "output_config" not in captured
