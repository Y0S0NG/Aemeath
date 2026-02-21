import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    max_retries: int = 1,
    delay: float = 0.0,
) -> T:
    """
    Call an async function, retrying up to max_retries times on exception.

    Args:
        fn: Zero-argument async callable to invoke.
        max_retries: Number of additional attempts after the first failure.
        delay: Seconds to wait between retries.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries and delay > 0:
                await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]
