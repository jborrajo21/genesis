import os

from genesis.openai_adapter import OpenAICompatibleAdapter

DEFAULT_BASE_URL = "http://localhost:11434/v1"
SUPPORTED_MODELS = [
    "gemma4:latest",
    "mistral",
    "qwen2.5-coder",
]
DEFAULT_MODEL = "gemma4:latest"


class OllamaAdapter(OpenAICompatibleAdapter):
    def __init__(self, model=DEFAULT_MODEL, max_tokens=10000, base_url=None, timeout=120):
        super().__init__(
            model=model,
            max_tokens=max_tokens,
            base_url=base_url or os.environ.get("GENESIS_OLLAMA_BASE_URL") or DEFAULT_BASE_URL,
            timeout=timeout,
            api_key_env=None,
            backend_name="Ollama",
            unreachable_hint="Run: ollama serve",
        )
