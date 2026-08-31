import re

_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render_prompt(content: str, context: dict[str, str]) -> str:
    """Replaces `{{key}}` placeholders in `content` with values from `context`.
    A placeholder with no matching key is left untouched."""

    def _substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        return context.get(key, match.group(0))

    return _PLACEHOLDER_RE.sub(_substitute, content)
