import json
import os
import urllib.error
import urllib.request

from genesis.adapter import Completion, Message, StopReason, ToolDef
from genesis.errors import AdapterAuthError, AdapterError

DEFAULT_BASE_URL = "https://api.openai.com/v1"
SUPPORTED_MODELS = ["gpt-6-astra", "gpt-6.1-sol", "gpt-6-luna"]
DEFAULT_MODEL = "gpt-6-luna"

_FINISH_REASON_MAP = {
    "stop": StopReason.DONE,
    "length": StopReason.TRUNCATED,
    "tool_calls": StopReason.TOOL_USE,
}


class OpenAICompatibleAdapter:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 10000,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 120,
        api_key_env: str | None = "OPENAI_API_KEY",
        backend_name: str = "The API",
        unreachable_hint: str = "",
    ) -> None:
        resolved = base_url or os.environ.get("GENESIS_OPENAI_BASE_URL") or DEFAULT_BASE_URL
        self._model = model
        self._max_tokens = max_tokens
        self._url = f"{resolved.rstrip('/')}/chat/completions"
        self._timeout = timeout
        self._api_key = api_key or (os.environ.get(api_key_env) if api_key_env else None)
        self._backend_name = backend_name
        self._unreachable_hint = unreachable_hint

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        response_schema: dict | None = None,
    ) -> Completion:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "max_tokens": self._max_tokens,
        }
        if response_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": response_schema},
            }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = urllib.request.Request(
            self._url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.load(response)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise AdapterAuthError(f"not authorized for {self._backend_name}") from e
            raise AdapterError(
                f"{self._backend_name} rejected the request ({e.code}): {e.read().decode()[:200]}"
            ) from e
        except urllib.error.URLError as e:
            raise AdapterError(
                f"Could not reach {self._backend_name} at {self._url}"
                f" ({e.reason}). {self._unreachable_hint}"
            ) from e

        choice = body["choices"][0]
        usage = body.get("usage") or {}
        return Completion(
            text=choice["message"]["content"],
            tool_calls=[],  # D-036: local tool-calling is unreliable — degrade to text-only.
            usage=usage.get("total_tokens"),
            stop_reason=_FINISH_REASON_MAP.get(choice.get("finish_reason"), StopReason.OTHER),
        )
