from typing import Literal, cast

from anthropic import AsyncAnthropic

from agents.clients.base import ChatMessage
from core.config import settings

DEFAULT_MODEL = "claude-sonnet-5"


class AnthropicProvider:
    """Talks to the Anthropic Messages API. Requires ANTHROPIC_API_KEY / LLM_PROVIDER=anthropic."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set but LLM_PROVIDER=anthropic")
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = model

    async def complete(self, system_prompt: str, messages: list[ChatMessage]) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": cast(Literal["user", "assistant"], m["role"]), "content": m["content"]}
                for m in messages
            ],
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()

    async def extract(self, instruction: str, text: str) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=256,
            system=instruction,
            messages=[{"role": "user", "content": text}],
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()
