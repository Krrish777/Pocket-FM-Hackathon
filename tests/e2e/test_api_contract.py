"""Frontend/backend contract smoke test (Task 9).

The frontend was built against a superseded single-flip-divergence API and now runs on mock data
(`NEXT_PUBLIC_USE_MOCK`). `frontend/src/lib/contract.ts` is a hand-written TypeScript mirror of the
turn-loop DTOs the backend actually serves. The two files can drift silently — a backend field
rename would otherwise only be discovered when the frontend is wired up (Task 10), at demo time.

This test boots the real app (`create_app`, `llm_provider="scripted"`, a `tmp_path` SQLite DB — no
API key, no network), fetches the served `/api/v1/openapi.json`, and asserts every path and every
response field name `contract.ts` declares actually exists in that schema. A backend rename FAILS
THIS TEST instead of silently breaking the UI.

`_CONTRACT_FIELDS` is a duplicated, explicit list bound to `frontend/src/lib/contract.ts` by this
comment — if a type in that file gains/loses/renames a field, update `_CONTRACT_FIELDS` in the same
change, or this test's binding to the frontend is a lie.
"""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from story_engine.api.app import create_app
from story_engine.bootstrap import Container, build_container
from story_engine.config.settings import Settings

pytestmark = pytest.mark.e2e

# --- paths the frontend contract assumes exist ---------------------------------------------------

_EXPECTED_PATHS: dict[str, set[str]] = {
    "/api/v1/characters": {"get"},
    "/api/v1/play": {"post"},
    "/api/v1/play/{run_id}": {"get"},
    "/api/v1/play/{run_id}/act": {"post"},
    "/api/v1/play/{run_id}/replay-as": {"post"},
}

# --- field names bound to frontend/src/lib/contract.ts, type by type -----------------------------
# Keep this dict in lockstep with contract.ts: same type names (as comments), same field sets.

_CONTRACT_FIELDS: dict[str, set[str]] = {
    "Character": {"id", "name"},  # contract.ts: Character
    "ChoiceDTO": {"id", "label", "source_work_id"},  # contract.ts: ChoiceDTO
    "CitationDTO": {
        "fact_id",
        "source_id",
        "chapter",
        "quote",
    },  # contract.ts: CitationDTO
    "TurnDTO": {
        "index",
        "chapter",
        "protagonist",
        "scene",
        "choices",
        "citations",
        "withheld_count",
    },  # contract.ts: TurnDTO
    "ReactionDTO": {"name", "tension", "blind_spots"},  # contract.ts: ReactionDTO
    "PlayRequest": {"character_id"},  # contract.ts: PlayRequest
    "PlayResponse": {"run_id", "turn"},  # contract.ts: PlayResponse
    "ActRequest": {"action"},  # contract.ts: ActRequest
    "ActResponse": {
        "run_id",
        "turn",
        "interpreted_as",
        "reactions",
    },  # contract.ts: ActResponse
    "ReplayAsRequest": {"character_id"},  # contract.ts: ReplayAsRequest
    "ReplayResponse": {"run_id", "turns"},  # contract.ts: ReplayResponse
}

# Maps the frontend's logical DTO name onto the backend's actual `schemas.py` class name — the
# backend is authoritative on the exact model, but the two names are allowed to differ.
_BACKEND_SCHEMA_NAME: dict[str, str] = {
    "Character": "CharacterResponse",
    "ChoiceDTO": "ChoiceOptionResponse",
    "CitationDTO": "CitationResponse",
    "TurnDTO": "TurnResponse",
    "ReactionDTO": "ReactionResponse",
    "PlayRequest": "PlayRequest",
    "PlayResponse": "PlayResponse",
    "ActRequest": "ActRequest",
    "ActResponse": "ActResponse",
    "ReplayAsRequest": "ReplayAsRequest",
    "ReplayResponse": "ReplayResponse",
}


@pytest.fixture
def app_client(tmp_path: Path) -> TestClient:
    """A booted app with no API key and no network — scripted LLM, tmp SQLite DB."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'contract.db'}", llm_provider="scripted"
    )
    container: Container = build_container(settings)
    return TestClient(create_app(container))


def _resolve_schema(components: dict[str, Any], schema_name: str) -> dict[str, Any]:
    schemas = components.get("schemas", {})
    assert schema_name in schemas, (
        f"expected schema {schema_name!r} in served openapi.json components — "
        f"available: {sorted(schemas)}"
    )
    return dict(schemas[schema_name])


def _schema_field_names(schema: dict[str, Any]) -> set[str]:
    properties = schema.get("properties", {})
    return set(properties.keys())


@pytest.mark.e2e
def test_openapi_declares_every_path_the_frontend_contract_assumes(
    app_client: TestClient,
) -> None:
    resp = app_client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    openapi = resp.json()

    served_paths: dict[str, Any] = openapi["paths"]
    for path, methods in _EXPECTED_PATHS.items():
        assert path in served_paths, (
            f"contract.ts assumes {path!r} exists, but it is missing from the served openapi.json "
            f"— available paths: {sorted(served_paths)}"
        )
        for method in methods:
            assert method in served_paths[path], (
                f"contract.ts assumes {method.upper()} {path!r} exists, but that method is not "
                f"declared for it in the served openapi.json"
            )


@pytest.mark.e2e
def test_openapi_response_schemas_carry_every_field_the_frontend_contract_declares(
    app_client: TestClient,
) -> None:
    """Every field name `contract.ts` declares must exist on the matching backend schema.

    This is deliberately a one-way check (contract.ts subset of backend schema, not equality) —
    the backend may carry fields the frontend does not yet consume, but every field the frontend
    DOES declare must be real, or a UI screen would read `undefined` from a live response.
    """
    resp = app_client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    openapi = resp.json()
    components = openapi["components"]

    for contract_name, expected_fields in _CONTRACT_FIELDS.items():
        backend_name = _BACKEND_SCHEMA_NAME[contract_name]
        schema = _resolve_schema(components, backend_name)
        actual_fields = _schema_field_names(schema)
        missing = expected_fields - actual_fields
        assert not missing, (
            f"contract.ts's {contract_name!r} declares field(s) {sorted(missing)} that are not "
            f"present on the backend's {backend_name!r} schema (has: {sorted(actual_fields)}) — "
            f"a backend rename broke the frontend contract"
        )
