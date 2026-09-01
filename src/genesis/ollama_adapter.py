import json
import urllib.error
import urllib.request

from genesis.adapter import Completion, Message, StopReason, ToolDef

DEFAULT_BASE_URL = "http://localhost:11434/v1"
SUPPORTED_MODELS = [
    "gemma4:latest",
    "mistral",
    "qwen2.5-coder",
]

_FINISH_REASON_MAP = {
    "stop": StopReason.DONE,
    "length": StopReason.TRUNCATED,
    "tool_calls": StopReason.TOOL_USE,
}


class OllamaAdapter:
    def __init__(
        self,
        model: str = "gemma4:latest",
        max_tokens: int = 10000,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 120,
    ):
        self._model = model
        self._max_tokens = max_tokens
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._timeout = timeout

    def complete(self, messages: list[Message], tools: list[ToolDef] | None = None) -> Completion:
        """Complete a conversation. Tools are accepted but never sent or returned (D-036)."""
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "max_tokens": self._max_tokens,
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
            raise ValueError(f"Ollama rejected the request ({e.code}): {e.read().decode()[:200]}")
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Could not reach Ollama at {self._url} ({e.reason}). Run: ollama serve"
            )

        choice = body["choices"][0]
        usage = body.get("usage") or {}
        return Completion(
            text=choice["message"]["content"],
            tool_calls=[],  # D-036: local tool-calling is unreliable — degrade to text-only
            usage=usage.get("total_tokens"),
            stop_reason=_FINISH_REASON_MAP.get(choice.get("finish_reason"), StopReason.OTHER),
        )
