# Research: Python OOP, Structure & Error Handling (2025)

> **Provenance:** Web research by a `general-purpose` sub-agent. Raw cited artifact; distilled rules live in
> `.claude/rules/python/03-oop-design.md`, `04-errors-logging.md`, and `.claude/rules/structure/`.
> Note: realpython.com returned 403 to automated fetch, so every rule is re-anchored to a primary source
> (docs.python.org, peps.python.org, pydantic.dev, pytest, packaging.python.org, OWASP, Effective Python).

---

# 1. OOP & Design

## 1.1 Composition over inheritance
- Default to composition ("has-a"); inheritance only for genuine, shallow, stable "is-a" (GoF).
- Don't subclass merely to reuse code — hold an instance and delegate. Subclass only if substitutable (Liskov).
- Keep hierarchies shallow (depth ≤ 2) — avoid the fragile base class problem.
- Express shared interfaces via Protocol/ABC, not an implementation-carrying base.

## 1.2 `@dataclass` vs plain class vs Pydantic `BaseModel`
| Use | When | Why |
|---|---|---|
| Plain class | Behavior-rich: methods, invariants, lifecycle, polymorphism | You model behavior, not fields |
| `@dataclass` | Internal structured data you already trust | Auto init/repr/eq; zero validation cost |
| Pydantic `BaseModel` | Untrusted/external data at a boundary (HTTP, config, env, LLM output) | Validation, coercion, JSON, JSON-Schema |
- Validate/parse at the boundary with Pydantic; pass plain dataclasses inward.
- Never `@dataclass` for data arriving from outside the process (no validation).
- Don't use Pydantic for trusted hot internal structures (needless validation cost).
- `pydantic.dataclasses` = middle option. Choose a plain class when identity is its behavior.

## 1.3 Frozen / immutable dataclasses
- Default value objects to `@dataclass(frozen=True, slots=True)`.
- `frozen=True` → `FrozenInstanceError` on mutation; frozen + `eq=True` → hashable (dict keys/set members).
- `slots=True` removes per-instance `__dict__` (less memory, faster access, blocks accidental attrs); returns a new class.
- **Flag:** frozen has a small write penalty; slots gives a small speedup — don't claim "frozen = faster."

## 1.4 Mutable default argument pitfall
- Never a mutable default (`[]`, `{}`, `set()`); use `None` sentinel and build inside. In dataclasses use
  `field(default_factory=...)`. (Defaults created once at def time — shared across calls.)

## 1.5 `typing.Protocol` vs ABCs (structural vs nominal)
- Default to **Protocol** for interfaces (matches duck typing; implicit conformance, no inheritance/registration).
- Protocol to annotate collaborators you don't own (composition-friendly).
- **ABC** when you want nominal enforced contracts and/or shared implementation (abstract methods fail on
  instantiation; base supplies defaults; `register()`; built-in isinstance).
- `@runtime_checkable` checks method *presence only*, not signatures — weak guard.
- Rule: *consume* an interface → Protocol; *define/enforce* a family you own → ABC. (PEP 544: "complement not replace".)

## 1.6 Enums
- Closed set of related values → `enum.Enum`, not loose constants/magic strings. `auto()` when value irrelevant;
  explicit values when mapping to external protocol/DB. Compare by identity (`is`). `StrEnum`/`IntEnum` only when
  the member must also *be* a str/int.

## 1.7 Encapsulation
- Start with a plain public attribute (it *is* the API); don't pre-write `get_x()`/`set_x()` (un-Pythonic).
- Signal internal with single leading underscore `_name`; reserve `__name` mangling for real subclass collisions.
- Promote to `@property` only when you need validation/computation/side-effect — client API unchanged.
- Keep setters cheap; use an explicit method for heavy work.

## 1.8 Single responsibility / small classes
- One class, one reason to change. If you can't state its job without "and," split it.
- Smells: many unrelated fields; methods touching disjoint field subsets; `-Manager`/`-Helper`/`-Utils` names.
- Prefer small collaborating objects over a god class.

## 1.9 When NOT to use a class
- Stateless logic → module-level function (Effective Python Item 23; functions are first-class).
- Never a class as a namespace of `@staticmethod`s (that's a module with extra steps).
- Avoid the poltergeist (short-lived stateless object for one method call).
- Heuristic: single calc / no state → **function**; data + persistent behavior → **class**; data that travels
  together → **dataclass**; untrusted data entering → **Pydantic**.

---

# 2. Project Structure & Packaging

## 2.1 `src/` layout (team-mandated)
- All importable/shippable code under `src/` (`src/mypkg/`). Install (`pip install -e .` / `uv sync`) before running/testing.
- Don't rely on CWD being on `sys.path`.
- PyPA's three reasons: forces testing the installed version; prevents CWD import shadowing; enforces only
  meant-to-be-importable files import. (PyPA/pytest recommend but don't mandate — the mandate is a team convention.)

## 2.2 Where tests go
- Tests outside the package in top-level `tests/` (default) → catches packaging glitches.
- Mirror package structure (`src/mypkg/db/models.py` → `tests/db/test_models.py`).
- Prefer `--import-mode=importlib`; keep a single root `conftest.py`.
- Config discovery is "first match wins" — since we standardize on `pyproject.toml`, don't also add `pytest.ini`.

## 2.3 `pyproject.toml` single config hub
- Exactly one at root; no setup.py/setup.cfg/pytest.ini/mypy.ini unless a tool truly can't use it.
- MUST include `[build-system]`; declare `[project]` metadata (PEP 621); tool config in `[tool.*]`.

## 2.4 `__init__.py`
- Include in every regular package dir; keep light (empty is the right default for leaf packages).
- Top-level `__init__.py` may expose public API + `__all__` (curated, minimal).
- Namespace packages (PEP 420) only when deliberately splitting a namespace across distributions.

---

# 3. Error Handling & Logging

## 3.1 Custom exception hierarchies
- One base exception per app (`class AppError(Exception)`); derive all app-specific from it.
- Derive from `Exception`, never `BaseException`. Suffix names `Error`. Keep shallow: base → category → specific
  leaves only where callers must distinguish. Keep them simple; put in a dedicated `errors.py`/`exceptions.py`.

## 3.2 No bare `except:`, no silent swallowing
- No bare `except:` (catches SystemExit/KeyboardInterrupt/GeneratorExit). No `except X: pass` (hides bugs).
- Catch the most specific type you can handle; keep the `try` body minimal.
- Broad `except Exception:` only at a genuine boundary (framework loop, request handler, `main`) AND only if you log
  with traceback and/or re-raise.
- To intentionally ignore a specific error: `contextlib.suppress(SpecificError)`, not `except: pass`.

## 3.3 Exception chaining
- `raise NewError(...) from err` when translating (records `__cause__`, PEP 3134).
- Don't raise inside `except` without `from err`/`from None`. Use `from None` only at an external boundary to avoid
  leaking internal/secret detail.

## 3.4 `logging` not `print`
- Use `logging`; `print()` only for ordinary CLI output. Level by semantics (DEBUG/INFO/WARNING/ERROR/CRITICAL).
- Report unrecoverable conditions by raising, not log-and-continue. Use `logger.exception(...)` / `exc_info=True` in `except`.
- Deferred formatting: `logger.debug("x=%s", value)`, not f-strings, on hot paths.

## 3.5 Module-level loggers
- `logger = logging.getLogger(__name__)` per module. No root logging from library code. No handlers/`basicConfig` in
  library/import code except a single `NullHandler` on the library's top logger. App entry points configure handlers once.

## 3.6 Never log secrets or PII
- Don't log tokens/passwords/session IDs/keys/connection strings/payment data/PII (OWASP). Redact/mask before writing
  (filter). Sanitize against log injection (strip CR/LF). Avoid logging whole request/response bodies or config objects.

---

# Cross-source disagreements
1. `src/` vs flat — recommended not mandated by PyPA/pytest; flat OK for tiny scripts. Mandate = team convention.
2. Broad `except Exception:` — anti-pattern writeups say specific-only; PEP 8 permits broad **at a boundary** with
   log/re-raise. Reconcile by scope.
3. `from None` vs chaining — preserve internally; hide only at external trust boundary.
4. `frozen` perf — small write penalty; `slots` small speedup.
5. `@runtime_checkable` — presence only, not signatures.

# Sources
- https://docs.python.org/3/library/dataclasses.html — dataclass methods, frozen/slots/default_factory (1.2–1.4).
- https://docs.python.org/3/faq/programming.html — mutable-default pitfall (1.4).
- https://peps.python.org/pep-0544/ — Protocols / structural subtyping (1.5).
- https://docs.python.org/3/library/abc.html — ABC/abstractmethod/register (1.5).
- https://pydantic.dev/docs/validation/latest/get-started/ , /concepts/dataclasses/ — Pydantic purpose vs dataclasses (1.2).
- https://docs.python.org/3/howto/enum.html — enums (1.6).
- https://docs.python.org/3/library/functions.html#property — property, API-preserving (1.7).
- https://effectivepython.com/2015/02/12/accept-functions-for-simple-interfaces-instead-of-classes — functions over classes (1.8–1.9).
- https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/ — src reasons (2.1).
- https://docs.pytest.org/en/stable/explanation/goodpractices.html — tests layout, importlib (2.1–2.2).
- https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ ; https://peps.python.org/pep-0621/ — pyproject/[project] (2.3).
- https://docs.pytest.org/en/stable/reference/customize.html — config discovery order (2.2–2.3).
- https://packaging.python.org/en/latest/guides/packaging-namespace-packages/ — regular vs namespace packages (2.4).
- https://docs.python.org/3/tutorial/errors.html — user exceptions, from/from None (3.1–3.3).
- https://peps.python.org/pep-0008/ — bare-except, Exception not BaseException (3.1–3.2).
- https://peps.python.org/pep-3134/ — __context__ vs __cause__ (3.3).
- https://docs.python.org/3/howto/logging.html — logging vs print, getLogger(__name__), NullHandler (3.4–3.5).
- https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html — data to exclude, log injection (3.6).
