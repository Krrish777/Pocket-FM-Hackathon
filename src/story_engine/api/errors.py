"""Map domain exceptions to HTTP responses at the edge.

The domain raises pure `StoryEngineError`s (no HTTP concern); this adapter translates them. One
handler covers the whole tree via the base class; the table maps specific types to status codes.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from story_engine.services.playthrough import PlaythroughError, UnknownChoiceError
from story_engine.shared.errors import (
    BudgetExceededError,
    ContinuityError,
    NoIntentMatchError,
    PlaythroughNotFoundError,
    PromptError,
    RunCompleteError,
    StoryEngineError,
    StoryNotFoundError,
)

_STATUS: dict[type[StoryEngineError], int] = {
    StoryNotFoundError: 404,
    ContinuityError: 422,
    BudgetExceededError: 402,
    PromptError: 500,
    # `_STATUS.get(type(exc), 500)` is an EXACT type lookup, not an isinstance walk — a subclass
    # does NOT inherit its parent's status code. `UnknownChoiceError` and `PlaythroughError` are
    # both subclasses of `StoryEngineError` (via `PlaythroughError(StoryEngineError)`) and must
    # each be registered explicitly, or they silently fall through to 500.
    PlaythroughNotFoundError: 404,
    UnknownChoiceError: 422,
    PlaythroughError: 422,
    NoIntentMatchError: 422,
    # 409, not 422: the request is well-formed and the action string may well be a fine parse —
    # what's gone is the resource the client is asking to act on (an offered choice to route
    # onto). That is a conflict between the request and the run's current state, not malformed
    # input, so 409 fits better than the 422 used for a genuine no-match.
    RunCompleteError: 409,
}


async def _handle(request: Request, exc: Exception) -> JSONResponse:
    # Registered only for StoryEngineError, but FastAPI types the handler as (Request, Exception);
    # narrow explicitly so the status lookup is type-safe and any stray error falls through to 500.
    status = _STATUS.get(type(exc), 500) if isinstance(exc, StoryEngineError) else 500
    code = getattr(exc, "code", "error")
    body: dict[str, object] = {"code": code, "message": str(exc)}
    # `context` is the only channel structured detail (e.g. `NoIntentMatchError`'s offered option
    # labels) can reach the client through this ONE handler — omitted entirely when empty so every
    # existing error's envelope shape is unchanged.
    context = getattr(exc, "context", None)
    if context:
        body["context"] = context
    return JSONResponse(status_code=status, content={"error": body})


def register_exception_handlers(app: FastAPI) -> None:
    """Register the domain-error handler (covers all `StoryEngineError` subclasses)."""
    app.add_exception_handler(StoryEngineError, _handle)
