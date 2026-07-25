"""FastAPI app factory (inbound adapter).

`create_app()` builds the container (composition root), configures the app from settings, registers
exception handlers, and mounts the versioned router aggregate under `settings.api_v1_str`.
ASGI target: `story_engine.api.app:app` (e.g. `uv run uvicorn story_engine.api.app:app`).
Patterns (custom operation-ids, CORS, router aggregation) adapted from the tiangolo template.

The module-level `app` is built LAZILY, via `__getattr__` (PEP 562), rather than eagerly at import
time. `build_container` now wires a real `LLMPort` (`llm_factory.build_llm`), which fails fast at
construction when `llm_provider="openai"` and no key is configured — exactly the intended
fail-at-boot behaviour for a real deployment, but it must not fire merely because something
imported this module (this test suite does, via `create_app`, using its own tmp-DB/scripted
container). Only an actual attribute access of `app` — which is what an ASGI server does — builds
the default container from process settings.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from story_engine.api.errors import register_exception_handlers
from story_engine.api.main import api_router
from story_engine.bootstrap import Container, build_container


def custom_generate_unique_id(route: APIRoute) -> str:
    """Stable, readable operationIds ('<tag>-<name>') for cleaner generated client SDKs."""
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


def create_app(container: Container | None = None) -> FastAPI:
    """Construct a fully-wired FastAPI app. Pass a `container` (e.g. tmp DB) for tests."""
    container = container or build_container()
    settings = container.settings
    app = FastAPI(
        title=settings.project_name,
        version="0.0.1",
        openapi_url=f"{settings.api_v1_str}/openapi.json",
        generate_unique_id_function=custom_generate_unique_id,
    )
    app.state.container = container
    if settings.all_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.all_cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_str)
    return app


def __getattr__(name: str) -> Any:
    """Lazily build the default ASGI `app` on first access — see the module docstring."""
    if name == "app":
        return create_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
