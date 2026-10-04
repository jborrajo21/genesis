import io
import json
import urllib.error

import pytest

from genesis.adapter import Message
from genesis.errors import AdapterAuthError, AdapterError
from genesis.openai_adapter import DEFAULT_BASE_URL, DEFAULT_MODEL, OpenAICompatibleAdapter


def _body(content="Hi!", finish_reason="stop"):
    """A minimal OpenAI-compatible chat completion response."""
    return {
        "choices": [
            {"message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}
        ],
        "usage": {"total_tokens": 24},
    }


def _fake_urlopen(body, captured=None):
    def fake(request, timeout=None):
        if captured is not None:
            captured["request"] = request
        return io.BytesIO(json.dumps(body).encode())

    return fake


def _patch(monkeypatch, body, captured=None):
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(body, captured))


@pytest.fixture(autouse=True)
def _no_ambient_config(monkeypatch):
    """The developer's own OPENAI_API_KEY must not decide what these tests assert."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GENESIS_OPENAI_BASE_URL", raising=False)


def _send(monkeypatch, **kwargs):
    """Run one completion and hand back the Request that would have gone out."""
    captured = {}
    _patch(monkeypatch, _body(), captured)
    OpenAICompatibleAdapter(**kwargs).complete([Message(role="user", content="hi")])
    return captured["request"]


# --- the credential ---------------------------------------------------------


def test_no_authorization_header_when_no_key_resolves(monkeypatch):
    assert "Authorization" not in _send(monkeypatch, model="m").headers


def test_explicit_key_is_sent_as_a_bearer_token(monkeypatch):
    request = _send(monkeypatch, model="m", api_key="sk-explicit")
    assert request.headers["Authorization"] == "Bearer sk-explicit"


def test_key_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    assert _send(monkeypatch, model="m").headers["Authorization"] == "Bearer sk-from-env"


def test_explicit_key_beats_the_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    request = _send(monkeypatch, model="m", api_key="sk-explicit")
    assert request.headers["Authorization"] == "Bearer sk-explicit"


def test_api_key_env_none_ignores_the_environment(monkeypatch):
    """D-103: the subclass declares it has no credential source, so OPENAI_API_KEY
    must not reach a keyless backend."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-must-not-be-sent")
    request = _send(monkeypatch, model="m", api_key_env=None)
    assert "Authorization" not in request.headers


# # --- the base URL -----------------------------------------------------------


def test_base_url_defaults_to_openai(monkeypatch):
    assert _send(monkeypatch, model="m").full_url == f"{DEFAULT_BASE_URL}/chat/completions"


def test_base_url_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("GENESIS_OPENAI_BASE_URL", "http://env:1/v1")
    assert _send(monkeypatch, model="m").full_url == "http://env:1/v1/chat/completions"


def test_explicit_base_url_beats_the_environment(monkeypatch):
    monkeypatch.setenv("GENESIS_OPENAI_BASE_URL", "http://env:1/v1")
    request = _send(monkeypatch, model="m", base_url="http://explicit:2/v1")
    assert request.full_url == "http://explicit:2/v1/chat/completions"


def test_model_defaults_to_the_cheapest_rung(monkeypatch):
    """D-104: capability anti-correlates with pipeline fit, so the default is not the flagship."""
    assert json.loads(_send(monkeypatch).data)["model"] == DEFAULT_MODEL


# --- error mapping (D-101 decision 3, D-091) --------------------------------


def _raising(exc):
    def fake(request, timeout=None):
        raise exc(request) if callable(exc) else exc

    return fake


def test_401_raises_adapter_auth_error(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        _raising(
            lambda r: urllib.error.HTTPError(r.full_url, 401, "Unauthorized", {}, io.BytesIO(b"{}"))
        ),
    )
    with pytest.raises(AdapterAuthError):
        OpenAICompatibleAdapter(model="m", api_key="sk-bad").complete(
            [Message(role="user", content="hi")]
        )


def test_other_http_error_raises_plain_adapter_error(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        _raising(
            lambda r: urllib.error.HTTPError(
                r.full_url, 500, "Server Error", {}, io.BytesIO(b'{"error":"boom"}')
            )
        ),
    )
    with pytest.raises(AdapterError, match="500") as excinfo:
        OpenAICompatibleAdapter(model="m").complete([Message(role="user", content="hi")])
    assert not isinstance(excinfo.value, AdapterAuthError)


def test_unreachable_host_raises_adapter_error_naming_the_url(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", _raising(urllib.error.URLError("refused")))
    with pytest.raises(AdapterError, match="explicit:2"):
        OpenAICompatibleAdapter(model="m", base_url="http://explicit:2/v1").complete(
            [Message(role="user", content="hi")]
        )


def test_backend_name_appears_in_errors(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", _raising(urllib.error.URLError("refused")))
    with pytest.raises(AdapterError, match="Fakebackend"):
        OpenAICompatibleAdapter(model="m", backend_name="Fakebackend").complete(
            [Message(role="user", content="hi")]
        )
