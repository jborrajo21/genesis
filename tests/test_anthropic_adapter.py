import os
import sys
from types import SimpleNamespace

import pytest

from genesis.adapter import Message
from genesis.anthropic_adapter import AnthropicAdapter
from genesis.errors import AdapterAuthError, AdapterError


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

    def Anthropic(api_key=None, **kwargs):
        # Mirrors the real client, which exposes the resolved key as .api_key.
        client.api_key = api_key
        return client

    # The error classes are part of the contract the adapter catches on, so the
    # stub must carry them or the except clauses are unreachable in these tests.
    class APIError(Exception):
        pass

    class AuthenticationError(APIError):
        pass

    monkeypatch.setitem(
        sys.modules,
        "anthropic",
        SimpleNamespace(
            Anthropic=Anthropic,
            omit=stub_omit,
            APIError=APIError,
            AuthenticationError=AuthenticationError,
        ),
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


def test_byok_key_reaches_the_client(monkeypatch):
    """The BYOK parameter must reach the SDK; storing it without using it would
    silently bill the server's own credential instead of the caller's."""
    _install_stub(monkeypatch, {})
    adapter = AnthropicAdapter(model="m", max_tokens=100, api_key="sk-caller")
    assert adapter._client.api_key == "sk-caller"


def test_no_key_falls_through_to_the_sdk_default(monkeypatch):
    _install_stub(monkeypatch, {})
    assert AnthropicAdapter(model="m", max_tokens=100)._client.api_key is None


def test_the_adapter_keeps_no_copy_of_the_key(monkeypatch):
    """The key necessarily lives inside the SDK client, which needs it to sign
    requests. What BYOK promises is that Genesis keeps no second copy of its
    own — the one thing that would outlive the client and reach a log line."""
    _install_stub(monkeypatch, {})
    adapter = AnthropicAdapter(model="m", max_tokens=100, api_key="sk-secret")
    own_attributes = {k: v for k, v in vars(adapter).items() if k != "_client"}
    assert "sk-secret" not in repr(own_attributes)


@pytest.mark.parametrize(
    "stub_error,expected",
    [("AuthenticationError", AdapterAuthError), ("APIError", AdapterError)],
)
def test_sdk_errors_become_typed_genesis_errors(monkeypatch, stub_error, expected):
    _install_stub(monkeypatch, {})
    import anthropic

    def boom(**kwargs):
        raise getattr(anthropic, stub_error)("upstream detail")

    monkeypatch.setattr(anthropic.Anthropic().messages, "create", boom)
    adapter = AnthropicAdapter(model="m", max_tokens=100, api_key="k")

    with pytest.raises(expected) as exc:
        adapter.complete([Message(role="user", content="hi")])
    assert exc.value.__cause__ is not None
