import os
import sys
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


def _install_stub(monkeypatch, captured):
    """Stand in for the anthropic module so offline tests need no SDK (D-017)."""

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="hi")],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
            stop_reason="end_turn",
        )

    stub_omit = object()
    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    monkeypatch.setitem(
        sys.modules, "anthropic", SimpleNamespace(Anthropic=lambda: client, omit=stub_omit)
    )
    return stub_omit


def test_response_schema_becomes_output_config(monkeypatch):
    captured = {}
    _install_stub(monkeypatch, captured)
    adapter = AnthropicAdapter(model="m", max_tokens=100)
    schema = {"type": "object", "properties": {}, "additionalProperties": False}
    adapter.complete([Message(role="user", content="hi")], response_schema=schema)
    assert captured["output_config"]["format"]["type"] == "json_schema"
    assert captured["output_config"]["format"]["schema"] == schema


def test_no_output_config_without_schema(monkeypatch):
    captured = {}
    stub_omit = _install_stub(monkeypatch, captured)
    adapter = AnthropicAdapter(model="m", max_tokens=100)
    adapter.complete([Message(role="user", content="hi")])
    assert captured["output_config"] is stub_omit
