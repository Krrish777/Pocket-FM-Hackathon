"""Map domain exceptions to HTTP responses at the edge.

The domain raises pure `StoryEngineError`s (no HTTP concern); this adapter translates them. One
handler covers the whole tree via the base class; the table maps specific types to status codes.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from story_engine.shared.errors import (
    BudgetExceededError,
    ContinuityError,
    PromptError,
    StoryEngineError,
    StoryNotFoundError,
)

_STATUS: dict[type[StoryEngineError], int] = {
    StoryNotFoundError: 404,
    ContinuityError: 422,
    BudgetExceededError: 402,
    PromptError: 500,
}


async def _handle(request: Request, exc: Exception) -> JSONResponse:
    # Registered only for StoryEngineError, but FastAPI types the handler as (Request, Exception);
    # narrow explicitly so the status lookup is type-safe and any stray error falls through to 500.
    status = _STATUS.get(type(exc), 500) if isinstance(exc, StoryEngineError) else 500
    code = getattr(exc, "code", "error")
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": str(exc)}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the domain-error handler (covers all `StoryEngineError` subclasses)."""
    app.add_exception_handler(StoryEngineError, _handle)
