import functools
import inspect
import logging
import re
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from enum import Enum
from functools import lru_cache
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

session_id: ContextVar[str | None] = ContextVar("trace_session_id", default=None)
_active: ContextVar[bool] = ContextVar("langfuse_trace_active", default=False)

DATA_URL = re.compile(r"data:[\w/+.-]+;base64,[A-Za-z0-9+/=]+")
UNTRACEABLE = ("AsyncSession", "Request", "CompiledStateGraph", "Pregel", "Guard")
MAX_ITEMS = 200


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        value = DATA_URL.sub("[document image omitted]", value)
        if get_settings().pii_masking_enabled:
            from app.core.privacy import redact

            value = redact(value)
        return value
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub(v) for v in value]
    return value


def _mask(*, data: Any, **kwargs: Any) -> Any:
    try:
        return _scrub(data)
    except Exception:
        logger.exception("Trace masking failed; dropping the field")
        return "[masking failed]"


@lru_cache
def client():
    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    from langfuse import Langfuse

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        environment=settings.app_env,
        mask=_mask,
    )


def plain(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "[nested too deep]"
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"[{len(value)} bytes]"
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): plain(v, depth + 1) for k, v in list(value.items())[:MAX_ITEMS]}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        out = [plain(v, depth + 1) for v in items[:MAX_ITEMS]]
        if len(items) > MAX_ITEMS:
            out.append(f"[{len(items) - MAX_ITEMS} more]")
        return out
    if is_dataclass(value) and not isinstance(value, type):
        return plain(asdict(value), depth + 1)
    if hasattr(value, "model_dump"):
        return plain(value.model_dump(), depth + 1)
    if hasattr(value, "content") and hasattr(value, "type"):
        return {"role": value.type, "content": plain(value.content, depth + 1)}
    if type(value).__name__ in UNTRACEABLE:
        return f"[{type(value).__name__}]"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _without(value: Any, omit: tuple[str, ...]) -> Any:
    if isinstance(value, dict) and omit:
        return {k: v for k, v in value.items() if k not in omit}
    return value


def in_trace() -> bool:
    return client() is not None and _active.get()


def current_trace_id() -> str | None:
    return client().get_current_trace_id() if in_trace() else None


@contextmanager
def trace(
    name: str,
    *,
    input: Any = None,
    user_id: str | None = None,
    session: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    as_type: str = "span",
) -> Iterator[Any]:
    lf = client()
    if lf is None:
        yield None
        return
    from langfuse import propagate_attributes
    from opentelemetry import context as otel_context

    trace_metadata = {k: str(v)[:200] for k, v in (metadata or {}).items() if v is not None}
    detached = otel_context.attach(otel_context.Context())
    active = _active.set(True)
    try:
        with propagate_attributes(
            trace_name=name,
            session_id=session or session_id.get(),
            user_id=user_id,
            tags=tags,
            metadata=trace_metadata or None,
        ):
            with lf.start_as_current_observation(name=name, as_type=as_type, input=plain(input)) as root:
                yield root
    finally:
        _active.reset(active)
        otel_context.detach(detached)


@contextmanager
def span(
    name: str,
    *,
    as_type: str = "span",
    input: Any = None,
    metadata: dict[str, Any] | None = None,
    only_in_trace: bool = False,
) -> Iterator[Any]:
    lf = client()
    if lf is None or (only_in_trace and not _active.get()):
        yield None
        return
    if not _active.get():
        with trace(name, as_type=as_type, input=input, metadata=metadata) as observation:
            yield observation
        return
    with lf.start_as_current_observation(
        name=name, as_type=as_type, input=plain(input), metadata=plain(metadata)
    ) as observation:
        yield observation


def _is_control_flow(exc: BaseException) -> bool:
    return any(cls.__name__ in ("GraphBubbleUp", "GraphInterrupt") for cls in type(exc).__mro__)


def _record_error(observation: Any, exc: BaseException) -> None:
    if observation is None:
        return
    if _is_control_flow(exc):
        observation.update(output={"interrupted": "waiting for the customer's reply"})
        return
    status = getattr(exc, "status_code", None)
    level = "WARNING" if isinstance(status, int) and status < 500 else "ERROR"
    observation.update(level=level, status_message=f"{type(exc).__name__}: {str(exc)[:500]}")


def traced(
    name: str | None = None,
    *,
    as_type: str = "span",
    omit: tuple[str, ...] = (),
    output: Callable[[Any], Any] | None = None,
    capture_input: bool = True,
    only_in_trace: bool = False,
):
    def decorate(fn):
        label = name or f"{fn.__module__.removeprefix('app.agents.').removeprefix('app.')}.{fn.__name__}"
        signature = inspect.signature(fn)

        def _input(args, kwargs):
            if not capture_input:
                return None
            try:
                bound = signature.bind_partial(*args, **kwargs)
            except TypeError:
                return None
            return {
                k: _without(v, omit)
                for k, v in bound.arguments.items()
                if k not in omit and k not in ("self", "cls")
            }

        def _finish(observation, result):
            if observation is not None:
                observation.update(output=plain(output(result) if output else result))

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                failure = None
                with span(label, as_type=as_type, input=_input(args, kwargs), only_in_trace=only_in_trace) as obs:
                    try:
                        result = await fn(*args, **kwargs)
                    except BaseException as exc:
                        _record_error(obs, exc)
                        failure = exc
                    else:
                        _finish(obs, result)
                if failure is not None:
                    raise failure
                return result

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            failure = None
            with span(label, as_type=as_type, input=_input(args, kwargs), only_in_trace=only_in_trace) as obs:
                try:
                    result = fn(*args, **kwargs)
                except BaseException as exc:
                    _record_error(obs, exc)
                    failure = exc
                else:
                    _finish(obs, result)
            if failure is not None:
                raise failure
            return result

        return sync_wrapper

    return decorate


def _usage(response: Any) -> dict[str, int] | None:
    meta = getattr(response, "usage_metadata", None) or {}
    if not meta:
        return None
    usage = {
        "input": int(meta.get("input_tokens") or 0),
        "output": int(meta.get("output_tokens") or 0),
        "total": int(meta.get("total_tokens") or 0),
    }
    for key, value in (meta.get("input_token_details") or {}).items():
        usage[f"input_{key}"] = int(value or 0)
    for key, value in (meta.get("output_token_details") or {}).items():
        usage[f"output_{key}"] = int(value or 0)
    return usage


@contextmanager
def generation(
    name: str, *, model: str | None, messages: list[Any], model_parameters: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Callable[..., None]]:
    lf = client()
    if lf is None:
        yield lambda *args, **kwargs: None
        return

    with ExitStack() as stack:
        if not _active.get():
            stack.enter_context(trace(name, input=messages, tags=["standalone"]))
        gen = stack.enter_context(lf.start_as_current_observation(
            name=name, as_type="generation", model=model, input=plain(messages),
            model_parameters=model_parameters, metadata=plain(metadata),
        ))

        def finish(response: Any, **extra: Any) -> None:
            response_meta = getattr(response, "response_metadata", None) or {}
            gen.update(
                output=plain(getattr(response, "content", response)),
                usage_details=_usage(response),
                metadata=plain({
                    **(metadata or {}),
                    "finish_reason": response_meta.get("finish_reason"),
                    "model_version": response_meta.get("model_name"),
                    **extra,
                }),
                level="WARNING" if response_meta.get("finish_reason") not in (None, "STOP") else None,
            )

        try:
            yield finish
        except BaseException as exc:
            _record_error(gen, exc)
            raise


def annotate(**metadata: Any) -> None:
    lf = client()
    if lf is None or not _active.get():
        return
    try:
        lf.update_current_span(metadata=plain(metadata))
    except Exception:
        logger.exception("Could not annotate the current Langfuse span")


def trace_io(*, input: Any = None, output: Any = None) -> None:
    lf = client()
    if lf is None or not _active.get():
        return
    try:
        lf.set_current_trace_io(
            input=plain(input) if input is not None else None,
            output=plain(output) if output is not None else None,
        )
    except Exception:
        logger.exception("Could not set Langfuse trace input/output")


def score(name: str, value: float | str | bool, *, comment: str | None = None) -> None:
    lf = client()
    if lf is None or not _active.get() or value is None:
        return
    if isinstance(value, bool):
        data_type, value = "BOOLEAN", 1.0 if value else 0.0
    elif isinstance(value, str):
        data_type = "CATEGORICAL"
    else:
        data_type, value = "NUMERIC", float(value)
    try:
        lf.score_current_trace(name=name, value=value, data_type=data_type, comment=comment)
    except Exception:
        logger.exception("Could not record Langfuse score %s", name)


def record_guardrail(name: str, passed: bool, output: dict[str, Any]) -> None:
    lf = client()
    if lf is None:
        return
    try:
        with span(name, as_type="guardrail") as observation:
            observation.update(
                output=plain({"passed": passed, **output}),
                level="DEFAULT" if passed else "WARNING",
            )
        if not passed:
            score(f"guardrail.{name}", False, comment=str(output)[:500])
    except Exception:
        logger.exception("Could not record guardrail result in Langfuse")


def flush() -> None:
    lf = client()
    if lf is not None:
        lf.flush()
