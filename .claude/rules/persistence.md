---
paths:
  - "**/persistence/**"
---

# Persistence (SQLModel on SQLite)

This project persists with **SQLModel on local SQLite** — no Postgres/Docker/Alembic for the hackathon.

## The hexagon rule (the one that matters)
- **`table=True` SQLModel classes are a persistence detail — they live in
  `adapters/outbound/persistence/`, never in `domain/`.** The domain core stays pure Pydantic; the
  adapter maps Row ⇄ domain explicitly and implements a repository *port*.
- **Never reuse one class as both the domain/wire model and the DB table.** Conflating them leaks ORM
  concerns into the core and couples your API schema to your table schema.

## Sessions & units of work
- **One `Session` per unit of work**, via a context manager: `with Session(engine) as session: ...`.
  Don't share a session across requests or threads.
- **Map Row → domain *inside* the session scope.** Attributes lazy-load; touching them after the
  session closes raises `DetachedInstanceError` (the HARDEN-01 bug — map before returning).
- **Create the engine + schema once at startup** in the composition root (`bootstrap.py`):
  `SQLModel.metadata.create_all(engine)`. No Alembic — `create_all` is enough.

## Types & mapping
- JSON-ish domain fields (lists, tuples, nested models) → JSON columns; convert explicitly on the way
  in and out (e.g. tuple ⇄ list) so the round-trip is lossless and typed.
- Keep `table=True` models (`tables.py`), engine/session helpers (`db.py`), and the repository adapter
  (`episode_log_repository.py`) in separate files.

## Strict-mypy note
- SQLModel/SQLAlchemy column attributes can confuse strict mypy; use the documented column helpers
  rather than blanket `# type: ignore`. Prefer a narrow, commented ignore if one is truly unavoidable.
