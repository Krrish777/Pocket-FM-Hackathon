# Research: Pydantic v2 Domain Modeling, Error Handling & Logging (hexagonal LLM app)

> **Provenance:** Web research by a `general-purpose` sub-agent. Distilled into the scaffold under
> `src/story_engine/` (`domain/base.py`, `shared/errors.py`, `observability/logging.py`).

## 1. Pydantic v2 domain modeling
- **`BaseModel` is the default** for domain entities, value objects, DTOs, LLM structured outputs
  (`model_dump`, `model_validate`, JSON-schema, generics, `extra` control). Pydantic docs: pydantic
  dataclasses are "not a replacement for" `BaseModel`.
- Stdlib `@dataclass` only for internal, trusted, no-validation structs. `pydantic.dataclasses` = niche
  (dataclass interop + validation; no `extra='allow'`).
- **Shared base model** centralizing config:
```python
# src/story_engine/domain/base.py
from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        validate_default=True,
        use_enum_values=False,
    )
```
  `frozen=True` (immutable + hashable; not enforced for nested mutables) · `extra="forbid"` (reject unknown
  fields) · `str_strip_whitespace` · `validate_assignment` (mutable subclasses) · `from_attributes=True`
  and `populate_by_name=True` belong on a **DTO base**, not the domain base.
- **Separate DTOs from domain models** — API request/response schemas live in the adapter
  (`adapters/inbound/api/schemas.py`) with their own base (`extra='forbid'`, `populate_by_name`,
  `from_attributes`); the adapter maps DTO ⇄ domain explicitly.
- `field_validator` (`@classmethod`, single field) · `model_validator(mode="after")` (cross-field, returns
  `self`) · `computed_field` + `@property` (derived, serialized). Enums as `str, Enum` (JSON-friendly, typed).
- **Do NOT use one god `models.py`** — split `domain/` by aggregate (one module per aggregate root). Collapse
  only if the whole domain is <~150 lines.

**Placement:** `domain/base.py`, `domain/enums.py`, `domain/models/<aggregate>.py`,
`adapters/inbound/api/schemas.py` (DTOs, NOT in domain).

## 2. Error handling / exception hierarchy
- Single base `AppError(Exception)` (never `BaseException`) in one module; specific typed subclasses with
  structured attributes (`code`, `context`). Keep the module **HTTP-agnostic** — map `code`→HTTP status in
  the inbound adapter, don't put `status_code` on domain exceptions.
```python
class AppError(Exception):
    code = "app_error"

    def __init__(self, message, *, context=None):
        super().__init__(message)
        self.message = message
        self.context = context or {}


class DomainError(AppError):
    code = "domain_error"


class StoryNotFoundError(DomainError):
    code = "story_not_found"


class LLMError(AppError):
    code = "llm_error"


class LLMTimeoutError(LLMError):
    code = "llm_timeout"
```
- **Chain** when translating vendor errors: `raise LLMTimeoutError(...) from exc` (sets `__cause__`). Never
  swallow (`except: pass`).
- **FastAPI mapping:** register one handler for the `AppError` base at the composition root; small
  `{ExcType: status}` table; log with `exc_info` before returning. Routers/services raise domain errors freely.

**Placement:** `domain/errors.py` OR (per this repo's "one folder" request) `shared/errors.py`;
`adapters/inbound/api/error_handlers.py` for `register_error_handlers(app)`.

## 3. Logging & utilities
- **Module-level loggers:** `logger = logging.getLogger(__name__)` (or `structlog.get_logger(__name__)`) at
  the top of every module → automatic `story_engine.x.y` hierarchy.
- **Configure once, centrally**, via `logging.config.dictConfig` (never `basicConfig`/ad-hoc `addHandler`
  scattered around). Libraries *get* loggers; the composition root *configures* them.
- **Structured/JSON:** structlog recommended for a new service (dict events, request-scoped context, ~2× faster
  for simple messages); stdlib `dictConfig` + JSON formatter is the zero-dep fallback.
```python
# src/story_engine/observability/logging.py  (stdlib-only variant, no new dep)
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}
            },
            "handlers": {
                "stdout": {"class": "logging.StreamHandler", "formatter": "json"}
            },
            "root": {"handlers": ["stdout"], "level": level},
        }
    )
```
  Call `configure_logging()` exactly once from the composition root; never at import time of a shared module.
- **The `utils.py` anti-pattern ("dunghill"):** a catch-all `utils.py`/`helpers.py`/`common.py` becomes an
  unorganizable junk magnet. Instead: **name modules by what they do** (`text.py`, `retry.py`,
  `token_counting.py`) — small, cohesive, single-purpose; put a helper **next to the code it serves**;
  promote to a shared module only when genuinely cross-layer, and still give it a specific name.

**Placement:** `observability/logging.py` (+ optional `metrics.py`); focused `shared/` modules
(`text.py`, `retry.py`); layer-local helpers stay in their layer.

## Sources
- https://pydantic.dev/docs/validation/latest/concepts/models/ — model_config/ConfigDict, frozen, extra, validators, computed_field.
- https://pydantic.dev/docs/validation/latest/concepts/dataclasses/ — pydantic dataclasses vs BaseModel; limitations.
- https://medium.com/@ThinkingLoop/12-pydantic-v2-model-patterns-youll-reuse-forever-543426b3c003 — shared base-DTO pattern.
- https://medium.com/@Nexumo_/10-pydantic-v2-moves-for-safer-faster-apis-9925080ed602 — extra='forbid', DTO/domain separation.
- https://fastapi.tiangolo.com/tutorial/handling-errors/ — exception_handler / add_exception_handler.
- https://deepwiki.com/fastapi-practices/fastapi-best-architecture/9.4-exception-handling — AppError base + single handler mapping.
- https://thecodeforge.io/python/custom-exceptions-python/ — inherit Exception, be specific, chaining.
- https://tutorials.technology/tutorials/python-logging-best-practices-structlog-loguru-2026.html — dictConfig, getLogger(__name__), structlog.
- https://medium.com/@dhruvshirar/structured-logging-in-python-a-practical-guide-for-production-systems-9659f461fa93 — logger hierarchy, configure-once, JSON.
- https://www.structlog.org/en/stable/standard-library.html — structlog.configure processors + BoundLogger/LoggerFactory.
- https://mattilehtinen.com/articles/dunghill-anti-pattern-why-utility-classes-and-modules-smell/ , https://www.yanglinzhao.com/posts/utils-antipattern/ — utils/common anti-pattern → focused modules.
