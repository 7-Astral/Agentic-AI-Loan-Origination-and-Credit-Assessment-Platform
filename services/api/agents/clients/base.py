from typing import Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


class LLMProvider(Protocol):
    """Vendor-agnostic interface agent code talks to. Swap the vendor by swapping the
    implementation returned from `agents.clients.factory.get_llm_provider` — no other
    agent code should import a specific provider directly."""

    async def complete(self, system_prompt: str, messages: list[ChatMessage]) -> str:
        """Return the assistant's natural-language reply for the given conversation."""
        ...

    async def extract(self, instruction: str, text: str) -> str:
        """Ask the model to return a small structured (JSON) value derived from `text`,
        per `instruction`. Returns the raw text of the model's reply (expected to be JSON);
        callers are responsible for parsing and validating it."""
        ...
