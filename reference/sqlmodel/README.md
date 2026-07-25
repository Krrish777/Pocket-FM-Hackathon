# SQLModel (on SQLite) — Story Engine reference note

> Tiangolo's Pydantic-over-SQLAlchemy ORM; used only in the persistence adapter to map SQLite rows
> to/from a pure-Pydantic domain.

- **Version pin (ours):** `sqlmodel>=0.0.22`
- **Latest stable (verified):** 0.0.39 (PyPI 2026-06-25; checked 2026-07) — still **pre-1.0** (0.0.x); the leading zeros are real, API is not yet frozen.
- **Upstream `llms.txt`:** none — `sqlmodel.tiangolo.com/llms.txt` is 404 (tiangolo family). Use the docs site.
- **Docs home:** https://sqlmodel.tiangolo.com/

## How Story Engine uses it
- `table=True` classes live ONLY in `adapters/outbound/persistence/tables.py`; the domain stays pure Pydantic and the adapter maps Row⇄domain explicitly (never hand a table instance to the core or the wire).
- `db.py` owns engine creation, a `session_scope` context manager, and `init_db` calling `SQLModel.metadata.create_all(engine)` at startup from `bootstrap`.
- Repos convert Row→domain INSIDE the session scope so lazy attribute loads succeed before the session closes.
- JSON-ish domain fields (tuples/lists/dicts) stored as JSON columns, converted explicitly at the boundary (tuple⇄list, since JSON has no tuple type).
- Under strict mypy we wrap column attributes in `sqlmodel.col()` inside `where`/`order_by` instead of blanket `type: ignore`.

## Read this for… (task → doc link)
- Create tables / `metadata.create_all(engine)` at startup → https://sqlmodel.tiangolo.com/tutorial/create-db-and-table/
- Create the engine and use a `Session` (insert/commit/refresh) → https://sqlmodel.tiangolo.com/tutorial/insert/
- Read rows with `select()` → https://sqlmodel.tiangolo.com/tutorial/select/
- Filter with `.where()` and the `col()` wrapper (incl. `col(...).in_()`) → https://sqlmodel.tiangolo.com/tutorial/where/
- Store JSON-ish fields via `sa_column=Column(JSON)` (JSON has no dedicated tutorial page — map to `sqlalchemy.JSON`) → https://sqlmodel.tiangolo.com/
- Relationships (if ever needed) → https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/

## Gotchas that bite us
- **Never reuse a `table=True` model as the domain or wire model** — keep it in `tables.py`; map to/from pure-Pydantic domain in the adapter.
- **Map Row→domain inside `session_scope`** — touching an attribute after the session closes raises `DetachedInstanceError` (we already hit this — HARDEN-01).
- **Strict mypy sees column attrs as their Python type, not SQL expressions** — wrap them in `sqlmodel.col()` in `where`/`order_by` rather than silencing with `type: ignore`.
- **Pre-1.0 (0.0.x) API churn risk** — pin a version and re-check on upgrades; signatures can shift between 0.0.x releases. For anything SQLModel doesn't expose, drop to SQLAlchemy directly (`sa_column`).
- **`create_all` is not migrations** — it creates missing tables, never alters existing ones; fine for the hackathon (no Alembic), but a schema change means dropping/recreating the SQLite file.

_Sources: pypi.org/project/sqlmodel, sqlmodel.tiangolo.com, official release notes. Verified 2026-07-24._
