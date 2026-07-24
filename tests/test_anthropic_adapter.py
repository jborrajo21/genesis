import os
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
