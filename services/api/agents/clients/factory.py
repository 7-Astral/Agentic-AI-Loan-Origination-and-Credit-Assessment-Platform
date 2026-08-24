from agents.clients.base import LLMProvider
from core.config import settings


def get_llm_provider() -> LLMProvider:
    """Returns the active LLM provider per LLM_PROVIDER. Agent code should depend only on
    the LLMProvider protocol, obtained through this function — never import a specific
    provider class directly — so the vendor can be swapped via config alone."""
    if settings.llm_provider == "anthropic":
        from agents.clients.anthropic_provider import AnthropicProvider

        return AnthropicProvider()

    from agents.clients.ollama_provider import OllamaProvider

    return OllamaProvider()
