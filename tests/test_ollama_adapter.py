import io
import json
import urllib.error
import urllib.request

import pytest

from genesis.adapter import Message, StopReason, ToolDef
from genesis.errors import AdapterError
from genesis.ollama_adapter import OllamaAdapter


def _body(content="Hi!", finish_reason="stop", total_tokens=24):
    """A minimal OpenAI-compatible chat completion response."""
    body = {
        "choices": [
            {"message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}
        ]
    }
    if total_tokens is not None:
        body["usage"] = {"prompt_tokens": 21, "completion_tokens": 3, "total_tokens": total_tokens}
    return body


def _fake_urlopen(body, captured=None):
    """Stand in for urlopen, returning body as JSON and optionally recording the Request."""

    def fake(request, timeout=None):
        if captured is not None:
            captured["request"] = request
        return io.BytesIO(json.dumps(body).encode())

    return fake


def _patch(monkeypatch, body, captured=None):
    monkeypatch.setattr(
        "genesis.ollama_adapter.urllib.request.urlopen", _fake_urlopen(body, captured)
    )


def test_complete_maps_response(monkeypatch):
    _patch(monkeypatch, _body())
    result = OllamaAdapter(model="m").complete([Message(role="user", content="hi")])
    assert result.text == "Hi!"
    assert result.usage == 24
    assert result.stop_reason is StopReason.DONE
    assert result.tool_calls == []


def test_complete_usage_is_none_when_absent(monkeypatch):
    _patch(monkeypatch, _body(total_tokens=None))
    assert OllamaAdapter(model="m").complete([Message(role="user", content="hi")]).usage is None


@pytest.mark.parametrize(
    "finish_reason,expected",
    [
        ("stop", StopReason.DONE),
        ("length", StopReason.TRUNCATED),
        ("tool_calls", StopReason.TOOL_USE),
        ("something_new", StopReason.OTHER),
        (None, StopReason.OTHER),
    ],
)
def test_complete_maps_finish_reason(monkeypatch, finish_reason, expected):
    _patch(monkeypatch, _body(finish_reason=finish_reason))
    result = OllamaAdapter(model="m").complete([Message(role="user", content="hi")])
    assert result.stop_reason is expected


def test_complete_accepts_tools_but_never_sends_them(monkeypatch):
    captured = {}
    _patch(monkeypatch, _body(), captured)
    tools = [ToolDef(name="t", description="d", input_schema={})]
    result = OllamaAdapter(model="m").complete([Message(role="user", content="hi")], tools=tools)
    assert result.tool_calls == []
    assert "tools" not in json.loads(captured["request"].data)


def test_request_shape(monkeypatch):
    captured = {}
    _patch(monkeypatch, _body(), captured)
    OllamaAdapter(model="m", base_url="http://host:1234/v1").complete(
        [Message(role="system", content="sys"), Message(role="user", content="hi")]
    )
    request = captured["request"]
    assert request.full_url == "http://host:1234/v1/chat/completions"
    assert request.method == "POST"
    assert request.headers["Content-type"] == "application/json"
    payload = json.loads(request.data)
    assert payload["model"] == "m"
    assert payload["stream"] is False
    assert payload["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]


def test_trailing_slash_in_base_url_is_normalised(monkeypatch):
    captured = {}
    _patch(monkeypatch, _body(), captured)
    OllamaAdapter(model="m", base_url="http://host:1234/v1/").complete(
        [Message(role="user", content="hi")]
    )
    assert captured["request"].full_url == "http://host:1234/v1/chat/completions"


def test_http_error_raises_adapter_error(monkeypatch):
    def fake(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 404, "Not Found", {}, io.BytesIO(b'{"error":"model not found"}')
        )

    monkeypatch.setattr("genesis.ollama_adapter.urllib.request.urlopen", fake)
    with pytest.raises(AdapterError, match="404"):
        OllamaAdapter(model="nope").complete([Message(role="user", content="hi")])


def test_connection_refused_raises_connection_error(monkeypatch):
    def fake(request, timeout=None):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr("genesis.ollama_adapter.urllib.request.urlopen", fake)
    with pytest.raises(AdapterError, match="ollama serve"):
        OllamaAdapter(model="m").complete([Message(role="user", content="hi")])


def _installed_models():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1) as response:
            return [m["name"] for m in json.load(response).get("models", [])]
    except OSError:
        return []


LOCAL_MODELS = _installed_models()


@pytest.mark.slow
@pytest.mark.skipif(not LOCAL_MODELS, reason="no local Ollama server with models; test skipped")
def test_ollama_adapter_smoke():
    result = OllamaAdapter(model=LOCAL_MODELS[0]).complete(
        [Message(role="user", content="Say hi in one word")]
    )
    assert result.text
    assert result.usage and result.usage > 0
    assert result.stop_reason is StopReason.DONE


def test_max_tokens_is_sent(monkeypatch):
    captured = {}
    _patch(monkeypatch, _body(), captured)
    OllamaAdapter(model="m", max_tokens=4096).complete([Message(role="user", content="hi")])
    assert json.loads(captured["request"].data)["max_tokens"] == 4096


def test_response_schema_is_forwarded(monkeypatch):
    captured = {}
    _patch(monkeypatch, _body(), captured)
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    OllamaAdapter(model="m").complete([Message(role="user", content="hi")], response_schema=schema)
    fmt = json.loads(captured["request"].data)["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["schema"] == schema


def test_no_response_format_without_schema(monkeypatch):
    captured = {}
    _patch(monkeypatch, _body(), captured)
    OllamaAdapter(model="m").complete([Message(role="user", content="hi")])
    assert "response_format" not in json.loads(captured["request"].data)
