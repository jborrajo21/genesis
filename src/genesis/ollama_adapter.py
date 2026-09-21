import json
import os
import urllib.error
import urllib.request

from genesis.adapter import Completion, Message, StopReason, ToolDef
from genesis.errors import AdapterError

DEFAULT_BASE_URL = "http://localhost:11434/v1"
SUPPORTED_MODELS = [
    "gemma4:latest",
    "mistral",
    "qwen2.5-coder",
]
DEFAULT_MODEL = "gemma4:latest"

_FINISH_REASON_MAP = {
    "stop": StopReason.DONE,
    "length": StopReason.TRUNCATED,
    "tool_calls": StopReason.TOOL_USE,
}


class OllamaAdapter:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 10000,
        base_url: str | None = None,
        timeout: int = 120,
    ):
        resolved = base_url or os.environ.get("GENESIS_OLLAMA_BASE_URL") or DEFAULT_BASE_URL
        self._model = model
        self._max_tokens = max_tokens
        self._url = f"{resolved.rstrip('/')}/chat/completions"
        self._timeout = timeout

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
        request = urllib.request.Request(
            self._url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.load(response)
        except urllib.error.HTTPError as e:
            raise AdapterError(
                f"Ollama rejected the request ({e.code}): {e.read().decode()[:200]}"
            ) from e
        except urllib.error.URLError as e:
            raise AdapterError(
                f"Could not reach Ollama at {self._url} ({e.reason}). Run: ollama serve"
            ) from e

        choice = body["choices"][0]
        usage = body.get("usage") or {}
        return Completion(
            text=choice["message"]["content"],
            tool_calls=[],  # D-036: local tool-calling is unreliable — degrade to text-only
            usage=usage.get("total_tokens"),
            stop_reason=_FINISH_REASON_MAP.get(choice.get("finish_reason"), StopReason.OTHER),
        )
