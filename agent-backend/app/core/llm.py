from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings

AGENTS = ("interaction", "document", "assessment", "decision")


@lru_cache
def get_llm(agent: str, max_retries: int | None = None) -> ChatGoogleGenerativeAI:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")

    extra = {} if max_retries is None else {"max_retries": max_retries}
    return ChatGoogleGenerativeAI(
        model=settings.model_for(agent),
        google_api_key=settings.gemini_api_key,
        timeout=60,
        **extra,
    )


def as_text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()

    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts).strip()