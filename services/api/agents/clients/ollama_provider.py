import httpx

from agents.clients.base import ChatMessage
from core.config import settings


class OllamaProvider:
    """Talks to a local Ollama server's chat API (https://github.com/ollama/ollama/blob/main/docs/api.md)."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.ollama_model

    async def complete(self, system_prompt: str, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "stream": False,
            # Thinking models otherwise spend their whole token budget on a hidden
            # reasoning trace and can return empty `content`. We only need the answer.
            "think": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()
        data = response.json()
        return str(data["message"]["content"]).strip()

    async def extract(self, instruction: str, text: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": text},
            ],
            "stream": False,
            "format": "json",
            "think": False,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()
        data = response.json()
        return str(data["message"]["content"]).strip()
