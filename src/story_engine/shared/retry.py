"""A small retry/backoff decorator for flaky I/O (e.g. LLM/network calls).

Focused, single-purpose module. Retries the given exception types with exponential backoff. For LLM
rate limits (429), pair this with an idempotency key so retries don't double-count cost
(see .claude/rules/llm-storytelling.md).
"""

import functools
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def retry(
    *,
    attempts: int = 3,
    backoff_seconds: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Retry the wrapped callable up to `attempts` times with exponential backoff.

    Args:
        attempts: Total attempts (>= 1).
        backoff_seconds: Base delay; attempt n waits `backoff_seconds * 2**(n-1)`.
        exceptions: Exception types that trigger a retry. Others propagate immediately.

    Returns:
        A decorator preserving the wrapped callable's signature.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == attempts:
                        break
                    time.sleep(backoff_seconds * (2 ** (attempt - 1)))
            assert last_exc is not None  # loop ran at least once
            raise last_exc

        return wrapper

    return decorator
