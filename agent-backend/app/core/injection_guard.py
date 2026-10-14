import asyncio
import logging
import os
from functools import lru_cache
from pathlib import Path

from app.core import observability
from app.core.config import get_settings

logger = logging.getLogger(__name__)

PROMPT_GUARD_MODEL = "meta-llama/Llama-Prompt-Guard-2-86M"

BLOCKED_MESSAGE = (
    "Sorry, I can't process that message. Please rephrase it in your own words, "
    "or contact the bank if you need help."
)

_prompt_guard_unavailable = False


class InjectionBlocked(Exception):
    def __init__(self, source: str, score: float | None):
        super().__init__(BLOCKED_MESSAGE)
        self.source = source
        self.score = score


def _model_cached() -> bool:
    home = os.environ.get("HF_HOME") or "~/.cache/huggingface"
    return Path(os.path.expanduser(home), "hub", "models--" + PROMPT_GUARD_MODEL.replace("/", "--")).exists()


@lru_cache
def _firewall(with_prompt_guard: bool):
    from llamafirewall import LlamaFirewall, Role, ScannerType

    scanners = [ScannerType.PROMPT_GUARD, ScannerType.HIDDEN_ASCII] if with_prompt_guard else [ScannerType.HIDDEN_ASCII]
    return LlamaFirewall(scanners={Role.USER: scanners})


def _disable_prompt_guard(reason: str) -> None:
    global _prompt_guard_unavailable
    if not _prompt_guard_unavailable:
        logger.error(
            "Prompt Guard unavailable (%s). Screening for hidden characters only until %s can be loaded; "
            "restart agent-backend once Hugging Face access is granted.",
            reason, PROMPT_GUARD_MODEL,
        )
    _prompt_guard_unavailable = True


def _scan(text: str):
    from llamafirewall import UserMessage

    message = UserMessage(content=text)
    if not _prompt_guard_unavailable:
        if not _model_cached() and not os.environ.get("HF_TOKEN"):
            _disable_prompt_guard("no HF_TOKEN and no cached model")
        else:
            try:
                return _firewall(True).scan(message), "prompt_guard+hidden_ascii"
            except OSError as exc:
                _disable_prompt_guard(str(exc).splitlines()[0])
    return _firewall(False).scan(message), "hidden_ascii_only"


def warm_up() -> str:
    return _scan("Hello, I would like to apply for a loan.")[1]


async def screen(text: str | None, source: str) -> None:
    if not get_settings().prompt_guard_enabled or not text or not text.strip():
        return
    from llamafirewall import ScanDecision

    result, scanners = await asyncio.to_thread(_scan, text)
    allowed = result.decision == ScanDecision.ALLOW
    observability.record_guardrail(
        "llamafirewall",
        allowed,
        {"source": source, "decision": result.decision.value, "score": result.score, "scanners": scanners},
    )
    if not allowed:
        logger.warning(
            "Blocked %s input: decision=%s score=%s scanners=%s session=%s",
            source, result.decision.value, result.score, scanners, observability.session_id.get(),
        )
        raise InjectionBlocked(source, result.score)
