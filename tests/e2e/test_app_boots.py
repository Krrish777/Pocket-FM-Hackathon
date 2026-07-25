"""L3 end-to-end — the whole app wired together actually boots and its schema initializes.

Exercises the real composition root through an ASGI client: the container builds, the SQLite schema
is created at startup, the app serves OpenAPI, and the versioned route is mounted. This is the
system-level termination check — proof the pieces work together, not just in isolation.

Note: a full premise->episode->persist request path is NOT yet E2E-testable (the LLM adapter is
deferred to the event brief; `StubLLM` raises by design). That gap is tracked in PROGRESS.md.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from story_engine.api.app import create_app
from story_engine.bootstrap import Container, build_container
from story_engine.config.settings import Settings


@pytest.fixture
def booted(tmp_path: Path) -> tuple[TestClient, Settings, Container]:
    """Build the full app against a fresh tmp SQLite DB (explicit init arg beats any .env)."""
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'e2e.db'}")
    container = build_container(settings)
    return TestClient(create_app(container)), settings, container


@pytest.mark.e2e
def test_app_boots_and_serves_openapi(
    booted: tuple[TestClient, Settings, Container],
) -> None:
    client, settings, _ = booted

    resp = client.get(f"{settings.api_v1_str}/openapi.json")

    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert (
        f"{settings.api_v1_str}/episodes/" in paths
    )  # route mounted under the version prefix


@pytest.mark.e2e
def test_db_schema_initialized_on_boot(
    booted: tuple[TestClient, Settings, Container],
) -> None:
    _, _, container = booted

    tables = inspect(container.engine).get_table_names()

    assert "episode_summary" in tables  # init_db created the schema end-to-end
