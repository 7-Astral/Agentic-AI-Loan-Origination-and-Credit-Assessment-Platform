import asyncio
from functools import lru_cache

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core import observability
from app.core.config import get_settings
from app.core.privacy import Pseudonymizer

AGENTS = ("interaction", "document", "assessment", "decision")


def _map_text(content, fn):
    if isinstance(content, str):
        return fn(content)
    blocks = []
    for block in content:
        if isinstance(block, str):
            blocks.append(fn(block))
        elif isinstance(block, dict) and block.get("type") == "text":
            blocks.append({**block, "text": fn(block.get("text", ""))})
        else:
            blocks.append(block)
    return blocks


def _mask_messages(messages: list[BaseMessage], pseudonymizer: Pseudonymizer) -> list[BaseMessage]:
    return [
        HumanMessage(content=_map_text(m.content, pseudonymizer.mask)) if isinstance(m, HumanMessage) else m
        for m in messages
    ]


class GuardedChatModel:
    def __init__(self, agent: str, model: ChatGoogleGenerativeAI):
        self.agent = agent
        self.model = model

    async def ainvoke(self, messages: list[BaseMessage], config: dict | None = None, **kwargs):
        pseudonymizer = Pseudonymizer() if get_settings().pii_masking_enabled else None
        if pseudonymizer is not None:
            messages = await asyncio.to_thread(_mask_messages, messages, pseudonymizer)

        with observability.generation(
            f"{self.agent}.gemini",
            model=getattr(self.model, "model", None),
            messages=messages,
            model_parameters={
                key: getattr(self.model, key)
                for key in ("temperature", "max_retries", "timeout")
                if getattr(self.model, key, None) is not None
            },
            metadata={"agent": self.agent},
        ) as finish:
            response = await self.model.ainvoke(messages, config=config, **kwargs)
            finish(response, pii_values_masked=pseudonymizer.masked_count if pseudonymizer else 0)

        if pseudonymizer is not None and pseudonymizer.masked_count:
            response = response.model_copy(update={"content": _map_text(response.content, pseudonymizer.restore)})
        return response


@lru_cache
def get_llm(agent: str, max_retries: int | None = None) -> GuardedChatModel:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")

    extra = {} if max_retries is None else {"max_retries": max_retries}
    model = ChatGoogleGenerativeAI(
        model=settings.model_for(agent),
        google_api_key=settings.gemini_api_key,
        timeout=60,
        **extra,
    )
    return GuardedChatModel(agent, model)


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
