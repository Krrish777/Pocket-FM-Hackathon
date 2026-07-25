# Pydantic v2 (+ pydantic-settings) — Story Engine reference note

> Runtime data-validation built on type hints — our validation boundary that turns untrusted input
> (especially LLM output) into typed, invariant-checked domain objects, and (via pydantic-settings)
> loads/validates config + secrets.

- **Version pin (ours):** `pydantic>=2`, `pydantic-settings>=2`
- **Latest stable (verified):** pydantic **2.13.4** (2026-05-06); pydantic-settings **2.14.2** (2026-06-19) — checked 2026-07 via PyPI.
- **Upstream `llms.txt`:** yes — vendored at `./llms.txt`. Full `llms-full.txt` also exists upstream. (The file asks agents to append `intent`/`stack`/`harness` query params when fetching doc pages.)
- **Docs home:** https://pydantic.dev/docs/validation/latest/ (old `docs.pydantic.dev/latest/` now 301-redirects here).

## How Story Engine uses it
- Shared `DomainModel(BaseModel)` base with `ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True, validate_assignment=True, validate_default=True)`; all domain models inherit it → immutable, strictly-typed narrative objects.
- Pydantic is the validation boundary for untrusted input — LLM output is parsed/validated before it reaches the pure domain core (never let unvalidated model output into `domain/`).
- `computed_field` + `@field_validator` for derived/parsed values (CORS list parsing, computed settings properties).
- pydantic-settings: single `Settings(BaseSettings)` with `SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")`, `SecretStr` for API keys (`.get_secret_value()` only at the network edge), `BeforeValidator` for coercion, `@lru_cache` `get_settings()` singleton.

## Read this for… (task → doc link)
- Configure a model / `ConfigDict` (`frozen`, `extra`, `validate_assignment`, `validate_default`, `str_strip_whitespace`) → https://pydantic.dev/docs/validation/latest/concepts/config/
- Write field/model validators (`@field_validator`, `@model_validator`) → https://pydantic.dev/docs/validation/latest/concepts/validators/
- `computed_field` and derived properties → https://pydantic.dev/docs/validation/latest/concepts/fields/#the-computed-field-decorator
- Models, `model_copy`, `model_construct`, `model_validate` → https://pydantic.dev/docs/validation/latest/concepts/models/
- Settings, `SecretStr`, `env_file`, custom sources, `BeforeValidator` → https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- v1→v2 migration / behavior changes → https://pydantic.dev/docs/validation/latest/migration/

## Gotchas that bite us
- **`model_copy(update=...)` does NOT re-validate** — the update dict is written straight onto the copy, skipping validators and coercion (same family as `model_construct()`). Avoid it for untrusted/derived values: round-trip through validation instead, e.g. `Model.model_validate({**old.model_dump(), **updates})`, or construct a fresh instance. Reserve `model_copy(update=)` for values you already trust. _(This is the `in_memory.py:63` bug.)_
- **`frozen=True` + `validate_assignment=True`:** `frozen` blocks attribute assignment entirely and makes the model hashable, so `validate_assignment` has almost nothing to guard on a fully-frozen model — the real mutation path is `model_copy`/re-validate. Both together is fine, just know `validate_assignment` earns its keep only on non-frozen models.
- **`SecretStr` unwrap only at the edge:** `str()`/repr/logs show `**********`; `.get_secret_value()` is required at the network boundary. Forgetting it sends the mask instead of the key — and keep that call out of logs/domain code.
- **`extra="forbid"` (domain) vs `extra="ignore"` (settings) is deliberate:** domain rejects unknown fields (catches drifting LLM/JSON schemas loudly); settings ignores unknown env vars (so unrelated env entries don't crash startup). Don't unify them.

_Sources: pypi.org/project/pydantic, pypi.org/project/pydantic-settings, pydantic.dev/docs, github.com/pydantic/pydantic-settings. Verified 2026-07-24._
