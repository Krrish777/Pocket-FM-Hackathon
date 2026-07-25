---
paths:
  - "**/*.py"
---

# Python OOP, Design, Errors & Logging

## Decision heuristic (what construct to reach for)
- Single calculation, no retained state → **plain function**.
- Data that travels together, already trusted → **`@dataclass`**.
- Untrusted data entering the system (HTTP, config, env, **LLM output**) → **Pydantic `BaseModel`**.
- Data + persistent behavior that belong together → **class**.
> Don't reach for a class by default. A class of only `@staticmethod`s is a module with extra steps.

## Composition over inheritance
- Default to composition ("has-a"); hold a collaborator and delegate.
- Inheritance only for a genuine, **shallow (depth ≤ 2)**, substitutable "is-a" (Liskov). Don't
  subclass just to reuse code (fragile base class).
- Share interfaces via `Protocol`/ABC, not an implementation-carrying base.

## Dataclasses & value objects
- Value objects: `@dataclass(frozen=True, slots=True)` — immutable + hashable; slots cut memory.
- **Never a mutable default arg** (`= []`, `= {}`): use `field(default_factory=list)`, or a `None`
  sentinel in functions.

## Interfaces: Protocol vs ABC
- **Consume an interface** (annotate a collaborator you don't own) → **`Protocol`** (structural).
- **Define/enforce a family you own**, or share default impl → **ABC** (`@abstractmethod`).
- `@runtime_checkable` checks method *presence* only — weak guard. Generic ports use PEP 695:
  `class Repo[T](Protocol): ...`.

```python
from typing import Protocol


class LLMPort(Protocol):  # a port the domain consumes
    def generate(self, *, messages: list[dict], max_tokens: int) -> str: ...
```

## Encapsulation (Pythonic)
- Start with a plain public attribute — exposing it *is* the API. No Java-style `get_x`/`set_x`.
- Mark internal with a single leading underscore. Promote to `@property` only when you later need
  validation/computation (client API `obj.x = 5` unchanged).

## Enums
- Closed set of values → `enum.Enum` (not magic strings); compare members with `is`. For **string**
  values crossing a JSON/LLM boundary, use **`enum.StrEnum`** (3.11+) — members are real `str`s (this
  repo's domain enums use `StrEnum`).

## Single responsibility
- If you can't state a class's job without "and", split it. `-Manager`/`-Helper`/`-Utils` names are a smell.

## Exception hierarchy
- One base per package: `class StoryEngineError(Exception)`. Derive all app errors from it (never
  `BaseException`). Suffix names with `Error`. Keep shallow: base → category (`GenerationError`,
  `PromptError`) → specific leaves only where callers must distinguish. Put them in `errors.py`.

```python
class StoryEngineError(Exception): ...


class GenerationError(StoryEngineError): ...


class BudgetExceededError(GenerationError):
    def __init__(self, spent_usd: float, limit_usd: float):
        super().__init__(f"spent ${spent_usd:.4f} exceeds ${limit_usd:.2f}")
        self.spent_usd, self.limit_usd = spent_usd, limit_usd
```

## No silent failures
- **No bare `except:`** and **no `except X: pass`**. Catch the most specific type you can handle; keep
  the `try` body minimal; let the unexpected propagate.
- Broad `except Exception:` **only** at a genuine boundary (request handler, framework loop, `main`)
  **and only if you log with traceback and/or re-raise**.
- Deliberately ignore a specific error with `contextlib.suppress(SpecificError)`, not `except: pass`.
- Preserve the cause: `raise GenerationError("...") from err`. Use `from None` only at an external
  trust boundary to avoid leaking secret-bearing detail.
> Reinforced by the `silent-failure-hunter` review agent.

## Logging
- Use `logging`, not `print()`. One logger per module: `logging.getLogger(__name__)`.
- Report unrecoverable conditions by **raising**, not log-and-continue. In `except`, use
  `logger.exception(...)` (or `exc_info=True`).
- Deferred formatting on hot paths: `logger.info("tokens=%s", n)`, not f-strings.
- Library/import code adds no handlers except a single `NullHandler`; the app entry point configures
  logging once.
- **Never log secrets or PII.** Prompts/completions can contain secrets — don't log full prompt bodies
  at INFO; redact and strip CR/LF (log injection).
