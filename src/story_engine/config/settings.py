"""Typed application settings (pydantic-settings).

The ONLY place configuration is read. Import `get_settings()` at the composition root
(`bootstrap.build_container`), never scatter `os.getenv` through business logic. Secrets are
`SecretStr` so they are masked in logs/reprs; call `.get_secret_value()` only at the network edge.
App/API/CORS/DB patterns are adapted from the tiangolo full-stack-fastapi-template, restructured to
our conventions (lowercase snake fields, sectioned, plain env names — no prefix).
See .claude/rules/llm-storytelling.md.
"""

from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import AnyUrl, BeforeValidator, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors(value: Any) -> list[str] | str:
    """Accept CORS origins as a comma-separated string OR a real list (both env-friendly)."""
    if isinstance(value, str) and not value.startswith("["):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list | str):
        return value
    raise ValueError(value)


class Settings(BaseSettings):
    """Environment-driven settings. Reads `.env` (gitignored); env vars override."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App / API ----
    project_name: str = "Story Engine"
    api_v1_str: str = "/api/v1"
    environment: Literal["local", "staging", "production"] = "local"
    backend_cors_origins: Annotated[
        list[AnyUrl] | str, BeforeValidator(_parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        """CORS origins as plain strings (trailing slash stripped) for the middleware."""
        return [str(origin).rstrip("/") for origin in self.backend_cors_origins]

    # ---- Persistence ----
    # SQLite by default (local file). Override via DATABASE_URL; tests pass their own.
    database_url: str = "sqlite:///./story_engine.db"

    # ---- LLM provider (set the one you use; fails fast at startup if required and missing) ----
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None

    # ---- Generation defaults ----
    # `scripted` swaps the real adapter for the deterministic one — the offline stage fallback,
    # so a demo cannot die to a timeout, a rate limit, or an unlucky sample.
    llm_provider: Literal["openai", "scripted"] = "openai"
    default_model: str = "gpt-4o"
    intent_model: str = "gpt-4o-mini"
    """Intent classification is a structured, continuity-critical call, not prose: a small model at
    a low temperature is both cheaper and more reliable at it than the narrator model."""
    max_output_tokens: int = 2000
    temperature_prose: float = 0.8
    temperature_structured: float = 0.2

    # ---- Branch Oracle ----
    # `authored` is the DEFAULT and MUST stay the default: `corpus` changes a chapter's option set,
    # which changes the visible-fact count `DEMO_SCRIPT` keys on (`{knower}:{chapter}:{fact_count}`),
    # silently degrading the rehearsed beats into mechanical fallback prose. See DECISIONS.md,
    # 2026-07-26 session 8.
    branch_oracle: Literal["authored", "corpus"] = "authored"
    branch_oracle_corpus_dir: str = "data/raw/fanfic/dexter"

    # ---- Cost governance ----
    request_budget_usd: float = 0.50

    # ---- Observability ----
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton (validated once at first call)."""
    return Settings()
