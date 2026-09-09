import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar


T = TypeVar("T")


class ToolExecutionError(RuntimeError):
    """Raised when a tool exhausts retries and should return a friendly error."""


def format_exception(exc: BaseException) -> str:
    name = exc.__class__.__name__
    message = str(exc).strip()
    return f"{name}: {message}" if message else name


async def run_blocking(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    return await asyncio.to_thread(func, *args, **kwargs)


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except retry_on as exc:
            last_error = exc
            if attempt >= attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, delay * 0.2)
            await asyncio.sleep(delay)
    raise ToolExecutionError(format_exception(last_error or RuntimeError("unknown error")))


async def retry_blocking(
    func: Callable[..., T],
    *args: Any,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    **kwargs: Any,
) -> T:
    return await retry_async(
        lambda: run_blocking(func, *args, **kwargs),
        attempts=attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on=retry_on,
    )
