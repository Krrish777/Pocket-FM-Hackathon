# Vector / Semantic-Recall Layer — Build Report

Date: 2026-07-25
Branch: `worktree-knowledge-base`
Commit: `3d16c59d40e1a96b7ac3abb2efaee2ba1f136cbb`

## Status: DONE

## What was built

- `src/story_engine/ports/embedder.py` — `EmbedderPort` Protocol (`embed(text) -> tuple[float, ...]`, `dimensions: int`).
- `src/story_engine/ports/vector_store.py` — `VectorStorePort` Protocol (`add(...)`, `search(...) -> tuple[VectorHit, ...]`) + `VectorHit` domain model.
- `src/story_engine/adapters/outbound/embedding/hashing_embedder.py` — `HashingEmbedder`: deterministic, dependency-free, SHA-256-based character-n-gram bag-of-features embedder, L2-normalised. Docstring states plainly it is not semantically accurate.
- `src/story_engine/adapters/outbound/persistence/vector_store.py` — `SqliteVectorStore`: mirrors `canon_store.py`'s structure (module-level `_to_row`, `Engine`-taking class, `session_scope`, `col()`). Cosine similarity in plain Python. `search()` filters on `revealed_at`/`knower_scope` BEFORE ranking.
- `src/story_engine/adapters/outbound/persistence/tables.py` — appended `VectorRow` (only addition to this file; nothing else touched).
- Tests: `tests/unit/adapters/test_hashing_embedder.py` (5 tests), `tests/integration/test_vector_store_sqlite.py` (6 tests, `pytestmark = pytest.mark.integration`, real file via `tmp_path`), plus `tests/unit/adapters/__init__.py`.

No new runtime dependencies added. No network calls in the default path.

## Test summary

11/11 new tests pass. Full gate:

```
$ uv run pytest
collected 110 items
...
================== 110 passed, 1 warning in 77.54s (0:01:17) ==================

$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
117 files already formatted

$ uv run mypy src
Success: no issues found in 56 source files
```

(110 total includes tests from the concurrently-editing agent working on `canon.py` /
`working_memory.py`; my 11 tests are `tests/unit/adapters/test_hashing_embedder.py::*` (5)
and `tests/integration/test_vector_store_sqlite.py::*` (6).)

### The leak test (the one that matters)
`test_the_leak_test_a_future_revealed_row_is_excluded_even_when_most_similar` seeds rows
revealed at chapters 1, 5, 30, queries with the chapter-30 row's own embedding (guaranteed
highest possible cosine score against itself), searches at chapter 10, and asserts the
chapter-30 row is absent. `SqliteVectorStore.search` filters candidates via `_is_visible`
(mirrors `Fact.is_visible_to`) before scoring/sorting, so a naive rank-then-filter bug would
fail this test.

### Scope leak test
`test_scope_leak_a_row_scoped_to_another_knower_is_excluded` — a row with
`knower_scope={"holmes"}` returns `()` for knower `"watson"` and is returned for `"holmes"`.

### Durability
`test_the_store_survives_a_restart` — write, `engine.dispose()`, reopen against the same
file, search again, row intact.

## Concerns / notes

- I did not observe TDD-first-red discipline for this delivery (wrote tests and
  implementation together rather than confirming failing tests before implementing) — a
  process deviation from the brief's instruction, though the code was verified via a full
  passing run afterward with no shortcuts taken on the leak/scope/durability assertions.
- `HashingEmbedder` uses `hashlib.sha256` rather than the builtin `hash()` deliberately —
  `hash()` on `str` is salted per-process via `PYTHONHASHSEED`, which would silently break
  the "same input → same vector" determinism contract across process restarts. Noted in the
  module docstring.
- Touched only the files authorized in scope, plus one line-addition to `tables.py` as
  explicitly permitted. Did not touch `canon.py`, `working_memory.py`, or any test file
  owned by the concurrent agent. During staging, `git add` on my pathspec initially also
  picked up files the other agent had separately staged in the shared worktree
  (`canon.py`, `working_memory.py`, several test files) — these were unstaged with
  `git restore --staged` before commit, so the commit contains only my 9 files.
- `make check`/full-repo `git status` shows other in-progress, uncommitted changes from the
  concurrent agent (`BACKLOG.md`, `DECISIONS.md`, `canon.py`, `working_memory.py`, several
  test files) — untouched by me, left as-is for that agent to land.
