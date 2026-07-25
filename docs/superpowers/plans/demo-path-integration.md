# Plan — Close the demo path: novel → KB → natural-language action → evolving world

**Branch:** `integration-demo-path` · **Written:** 2026-07-26 · **Provider decision: OpenAI**

## Context

The engine is not a scaffold. The Knowledge Base, the spoiler guard, knowledge propagation, the turn
loop, and PDF ingestion are **built and tested** (497 tests green at `78bddd7`). What is missing is
**integration**: the turn loop is reachable only from a CLI, it narrates from an authored script
instead of a model, the player picks a numbered option instead of typing, and `bootstrap.py` wires
none of the knowledge base.

This plan closes exactly those gaps and nothing else. **The architecture is frozen.** No task here
redesigns a store, a port, or the guard.

The deliverable is one scenario working end to end:

> Start a story → select Dexter → his memory loads → type a natural-language action → the model
> maps that intent onto one of the constrained actions offered at this decision point → the turn
> engine executes it → canon, graph and agent memories update → the other characters react on only
> what they know → narration is generated → type another action immediately → the world stays
> consistent → nothing leaks → it continues.

### Name the input honestly

This is **natural-language intent mapped onto a constrained action set** — *not* open-ended agency.
The player types anything; a classifier routes that text to one of the 2-4 options the Branch Oracle
already offers at this chapter, and the engine executes only pre-validated consequences.

Say it that way in code, docstrings, API field names, and any demo copy. **Do not call it
"free-form actions", "do anything", or "open-ended".** Two reasons, one honest and one practical:
the claim would be false, and a judge who types "I fly to Cuba and start a new life" will find the
seam in about four seconds. The defensible pitch is the real one — *"say it however you want; we
ground it in a divergence fan fiction actually wrote"* — and that is a **feature**, because an
unvalidated generated branch is exactly the incoherence this product claims to have solved.

The classifier is a router. It is not a game engine, and no task in this plan may grow it into one.

## Global Constraints

These bind every task. A violation is a Critical review finding regardless of what a task's own text
says.

1. **The model never decides state.** Every state transition is computed in code *before* the model
   is called. The model does two jobs only: classify a natural-language intent into an
   already-offered option, and render prose. `PlaythroughService.advance` remains the sole applier
   of a consequence.
   **Naming is binding:** call it *natural-language intent* or *intent routing*, never "free-form
   action" or "open-ended". A name that overclaims is a Critical finding — it is how a classifier
   gets mistaken for a game engine, first in the copy and then in the code.
2. **Exactly one narration call per turn.** Per-character narration calls are forbidden — the
   epistemic guarantee comes from what is *absent* from the assembled context, not from instructing
   a model to withhold.
3. **One store, two projections, one guard.** Canon is the source of truth; the graph and the vector
   index are projections over it. **Do not add a fourth read path.** Every read of a fact routes
   through `story_engine.domain.models.canon.is_visible`. An unguarded lane beside a guarded store
   is a spoiler side-channel.
4. **Propagation stays monotonic.** `domain/propagation.py` may add a knower or move an acquisition
   earlier; never remove a knower or delay one. Do not modify that module.
5. **Vendor SDKs only in `adapters/outbound/`.** `domain/` and `services/` import no `openai`.
6. **Prompts are versioned files** in `prompts/<name>/vN.jinja`. Never a string literal in code, and
   never edit a shipped version in place — add `vN+1`.
7. **Every LLM call goes through `LLMPort`** and sets `max_tokens`. No direct SDK calls anywhere else.
8. **Model output is untrusted input.** Validate it with Pydantic at the boundary before it reaches
   the core.
9. **Authored data stays auditable.** Any `ChoiceOption` not mined from a real fan-fiction work keeps
   `source_work_id=None`.
10. **Type hints on every public signature**; modern syntax only (`list[str]`, `X | None`). No bare
    `except:`, no `except: pass`. `mypy --strict` must pass.
11. **Done means the gate passes, checked by exit code** — never by reading piped output, because a
    pipeline reports the *filter's* status and a red gate then reads as green. Redirect to a file
    and check `$?`.
    **The full `make check` takes 11m23s** (measured 2026-07-26, 497 tests), so per-task it is:
    `uv run ruff format <changed files>` → `uv run ruff check src tests` → `uv run mypy src` →
    the task's own targeted `pytest` selection. Those are seconds, not minutes, and catch every
    class of failure the gate caught in this session. The **controller** runs the full `make check`
    at task boundaries; an implementer runs it only if explicitly told to.
12. **Tests assert schema and invariants, never exact generated text.** The LLM is mocked in unit
    tests; no test may require an API key.

## Existing interfaces tasks must build against

```python
# ports/llm.py
class LLMPort(Protocol):
    def generate(self, *, messages: list[dict[str, str]], model: str, max_tokens: int,
                 temperature: float, idempotency_key: str | None = None) -> Generation: ...
class Generation(DomainModel):  # output, model, prompt_tokens, completion_tokens, cost_usd

# ports/canon_store.py — CanonStorePort
append(fact) · get(fact_id) · register_fork(fork) · get_fork(fork_id) · lineage(fork_id)
all_facts(fork_id) · as_of(...) · visible_to(fork_id, knower, chapter) · withheld_from(...)
record_learning(fact_id, knower_scope) · supersede(...)

# ports/branch_oracle.py
class BranchOraclePort(Protocol):
    def options_at(self, *, fork_id: str, chapter: ChapterIndex,
                   protagonist: str) -> tuple[ChoiceOption, ...]: ...   # 2-4, or () when thin

# services/working_memory.py
WorkingMemory(store).assemble(fork_id, knower, chapter) -> MemoryPacket
MemoryPacket: knower, chapter, facts: tuple[Fact,...], graph: LoreGraph, withheld_count: int

# services/playthrough.py — PlaythroughService(store=, memory=, oracle=, llm=, prompts=, cast=, model=)
begin(fork_id=, protagonist=, chapter=) -> Playthrough
advance(run, choice_id) -> Playthrough          # raises UnknownChoiceError for an unoffered id
replay_as(run, character) -> Playthrough

# domain/models/play.py
Consequence(subject_id, predicate, object_literal, roster: tuple[Presence,...], secret, discloses)
ChoiceOption(id, label, source_work_id: str | None, consequence)
Turn(index, chapter, protagonist, scene, choices, citations, withheld_count)   # 2-4 choices or ()
Playthrough(fork_id, protagonist, chapter, turns)   # MAX_DEPTH = 10

# resources/dexter_demo.py — FORK_ID = "canon", CAST: dict[str, str] (5 members)
# services/demo_seed.py — seed_canon(store, source, novel_path) -> list[Fact]; demo_branches()
# DEFAULT_NOVEL = data/external/Darkly-Dreaming-Dexter-1.pdf
```

---

## Task 1 — Test and wire the OpenAI adapter

`src/story_engine/adapters/outbound/openai_llm.py` **already exists** (written by the controller,
ruff + mypy clean, uncommitted). `openai>=1.50` is already in `pyproject.toml`; settings already
carry `llm_provider`, `default_model="gpt-4o"`, `intent_model="gpt-4o-mini"`. Your job is to prove it
works and to make it selectable — **not** to rewrite it.

**Write `tests/unit/adapters/test_openai_llm.py`.** Inject a fake client (the adapter takes
`client=`), never the real SDK, and never a key. Cover:

1. A normal call returns a `Generation` whose `output`, `model`, `prompt_tokens`,
   `completion_tokens` match the fake response.
2. `max_completion_tokens` is present in every request the adapter issues.
3. `temperature` is sent for `gpt-4o` and **omitted** for a `gpt-5*` model.
4. **A repeated `idempotency_key` does not call the client a second time** and returns the identical
   `Generation` — assert the fake's call count is 1 after two `generate()` calls.
5. `spent_usd` accumulates from the pricing table, and a **replayed** call does not increase it.
6. An unpriced model (`"some-unknown-model"`) yields `cost_usd == 0.0` and logs a warning
   (`caplog`), rather than a fabricated price.
7. A dated snapshot (`"gpt-4o-2024-08-06"`) prices as `gpt-4o` via longest-prefix match.
8. Empty content, and a response with no choices, each raise `GenerationError`.
9. A retryable failure (an exception whose class name is `RateLimitError`, or `status_code=429`)
   is retried and then succeeds; construct the adapter with `backoff_seconds=0` so the test is fast.
10. A non-retryable failure (`status_code=400`) raises `GenerationError` after exactly **one**
    attempt.
11. Constructing with neither `client` nor `api_key` raises `GenerationError`.
12. `budget_usd` already reached raises `BudgetExceededError` **before** any client call.

**Then add a provider factory** — `adapters/outbound/llm_factory.py`, function
`build_llm(settings: Settings) -> LLMPort`:

- `settings.llm_provider == "openai"` → `OpenAILLM(api_key=settings.openai_api_key,
  budget_usd=settings.request_budget_usd)`. If `openai_api_key` is `None`, raise `GenerationError`
  naming `OPENAI_API_KEY` — fail fast at boot, not mid-demo.
- `settings.llm_provider == "scripted"` → `ScriptedLLM(DEMO_SCRIPT)`, the offline stage fallback.

Unit-test both branches, including the missing-key failure.

**Do not** touch `bootstrap.py` (Task 3 owns it) or delete `stub_llm.py` (Task 3 owns its removal).

**Verification:** `uv run pytest tests/unit/adapters/test_openai_llm.py -v` passes with no key set,
and `make check` exits 0.

---

## Task 2 — Natural-language intent router

**Depends on Task 1.** This closes the gap between "pick option 2" and "type it in your own words".
It is a **router onto a constrained action set**, not an open-world action interpreter — see *Name
the input honestly* above, which binds every identifier and docstring you write here.

Create `src/story_engine/services/intent_router.py`.

```python
class ResolvedIntent(DomainModel):
    choice_id: str | None      # None => nothing offered matched
    confidence: float          # 0.0-1.0
    reasoning: str             # one short sentence, shown to the player as "you chose to ..."

class IntentRouter:
    def __init__(self, *, llm: LLMPort, prompts: PromptStorePort,
                 model: str, threshold: float = 0.6) -> None: ...
    def resolve(self, *, action: str, options: tuple[ChoiceOption, ...],
                protagonist: str) -> ResolvedIntent: ...
```

Behaviour, in this order:

1. **No options offered** → return `choice_id=None` without calling the model. Do not spend a call
   to classify against an empty set.
2. Render `prompts/interpret_intent/v1.jinja` with the protagonist, the player's typed action, and the
   offered options (id + label only — never the consequence; the model has no business seeing what a
   choice does to the world).
3. Call the LLM at **low temperature (0.2)** with `max_tokens=200` and
   `idempotency_key=f"intent:{protagonist}:{hash of action+ids}"`.
4. **Validate the response with Pydantic.** The model must return JSON
   `{"choice_id": ..., "confidence": ..., "reasoning": ...}`. Anything else — malformed JSON, a
   missing field, **or a `choice_id` that was not in `options`** — is treated as no match
   (`choice_id=None`) and logged at WARNING. A hallucinated id must never reach `advance()`.
5. `confidence < threshold` → `choice_id=None`.

The prompt must instruct the model to pick the offered option closest in *intent* to what the player
typed, and to return null when none is close.

**Tests** (`tests/unit/services/test_intent_router.py`, LLM mocked, no key):

- A clear match routes to the right `choice_id`.
- **A `choice_id` the model invented is rejected** → `choice_id=None`. This is the security test.
- Malformed JSON → `choice_id=None`, no exception escapes.
- Below-threshold confidence → `choice_id=None`.
- Empty options → `choice_id=None` and **zero** LLM calls (assert the mock was not called).
- The rendered prompt contains the option labels and **does not contain** any consequence field
  (`predicate` / `object_literal` values).

**Then wire it into the CLI**: `story-engine play` accepts natural-language text at the prompt. A player may
still type a number (keep that — it is the rehearsal path). Non-numeric input goes through the
router; a resolved intent echoes `> interpreted as: <label>` before advancing; an unresolved intent
re-prompts with a plain message listing the options again, and **does not** advance the turn.

**Verification:** `uv run pytest tests/unit/services/test_intent_router.py -v` and `make check` exit 0.

---

## Task 3 — Wire the Knowledge Base into the composition root

`bootstrap.py` today wires only `EpisodeGenerator` with `StubLLM` and an in-memory bible. The whole
knowledge base and the turn loop are unreachable from anything but the CLI.

Extend `Container` with: `canon_store: SqliteCanonStore`, `memory: WorkingMemory`,
`playthrough: PlaythroughService`, `intent_router: IntentRouter`, `llm: LLMPort`.

- Build the LLM via Task 1's `build_llm(settings)`.
- `SqliteCanonStore` over the same engine `create_db_engine(settings.database_url)` returns.
- `PlaythroughService(store=..., memory=WorkingMemory(store), oracle=..., llm=..., prompts=
  FilePromptStore("prompts"), cast=CAST, model=settings.default_model)`.
- **Delete `stub_llm.py`** and its import; `EpisodeGenerator` takes the real LLM. If nothing else
  references `EpisodeGenerator`, leave it wired — do not delete it in this task.
- Keep `build_container()` importable and callable **without** an API key when
  `LLM_PROVIDER=scripted`, so the test suite and the offline demo still boot.

Add a **seed-on-empty** helper, `services/canon_ingest.py::CanonIngestService`, that writes a fact to
the canon store **and** its vector-index entry as **one unit of work** — two independent writes
drift, and a fact in canon but absent from the vector index is a fact the semantic lane silently
cannot see. Use it from bootstrap when the store is empty for `FORK_ID`. Signature:

```python
class CanonIngestService:
    def __init__(self, *, store: CanonStorePort, vectors: VectorStorePort,
                 embedder: EmbedderPort) -> None: ...
    def ingest(self, facts: Sequence[Fact]) -> int:   # returns count written
```

### The atomicity policy is MANDATED, not left to the implementer

"One unit of work" without a stated failure policy is how drift arrives during the demo. The policy
below is decided here, in the cold. **Implement exactly this; do not substitute your own.**

**Write order: canon FIRST, vector SECOND.** The order is forced by Global Constraint 3, not by
taste. Consider each failure direction:

- *Vector-first, canon fails* → a vector entry exists for a fact the canon store has never heard of.
  That entry is retrievable by similarity but has no canon row to gate against, which is precisely
  an **unguarded fourth read path** — a spoiler side-channel. Unacceptable at any probability.
- *Canon-first, vector fails* → the fact is in the source of truth and missing from a derived index.
  Semantic recall under-returns; the guard, the graph and every correctness property still hold.
  This is a **degradation, not a correctness violation**, and it is repairable.

An asymmetric failure mode with one safe direction is not a coin flip. Take the safe direction.

**On vector-write failure:** do **not** attempt to compensate by deleting the canon row. The canon
store is append-only by design (`supersede` closes a validity window, it does not delete), so a
"rollback" would mean writing a phantom correction claiming the fact was never true. Instead:

1. Log at ERROR with the fact id and the underlying exception (never swallow it).
2. Continue ingesting the remaining facts — one bad embedding must not abort a novel-length ingest.
3. Return the orphan ids on the result, and **raise `IngestDriftError`** (new, deriving from
   `StoryEngineError`) at the end of `ingest()` if any orphans remain. Fail loud, after doing all
   the work that could succeed.

**Add `reconcile()` to the same service** — the repair path, and the reason step 3 can be non-fatal
to the batch:

```python
def reconcile(self, fork_id: str) -> tuple[int, int]:
    """Re-index canon facts missing from the vector lane. Returns (repaired, still_missing)."""
```

It diffs canon fact ids against vector entry ids and re-adds the missing ones. This is safe to run
repeatedly because Session D made `VectorStorePort.add()` idempotent and added `remove()` — do not
re-derive that, it is already true.

**Expose it** as `story-engine reconcile --fork canon`, so drift is a 5-second command during the
demo rather than a debugging session.

**Tests that must exist for this policy** (vector adapter faked to fail on a chosen fact):

- A vector failure leaves the canon fact present, the vector entry absent, and raises
  `IngestDriftError` naming that fact id.
- The other facts in the same batch were still written — one failure does not abort the batch.
- `reconcile()` afterwards returns `(1, 0)` and leaves canon and vector counts equal.
- `reconcile()` on a healthy store is a no-op returning `(0, 0)` — idempotence.
- **No test may assert the vector-first ordering**; a test that locks in the unsafe order is itself
  a defect.

**Tests:** an integration test that `build_container()` with `LLM_PROVIDER=scripted` produces a
container whose `playthrough.begin(...)` returns a `Turn`, against a temp SQLite file; and a unit
test that `CanonIngestService.ingest` leaves canon and vector counts equal.

**Verification:** `uv run pytest tests/integration -k container -v` and `make check` exit 0.

---

## Task 4 — Playthrough persistence

A `Playthrough` is currently an in-memory object. `POST /play` then `POST /play/{id}/act` are two
processes' worth of apart, so the run must survive.

Add `adapters/outbound/persistence/playthrough_repository.py`:

```python
class SqlitePlaythroughRepository:          # implements PlaythroughRepositoryPort (new port)
    def create(self, run: Playthrough) -> str: ...        # returns a run_id
    def get(self, run_id: str) -> Playthrough | None: ...
    def save(self, run_id: str, run: Playthrough) -> None: ...
```

Store the run envelope as JSON in one SQLModel row (`run_id`, `fork_id`, `protagonist`,
`created_at`, `payload`). **This is not a second source of truth**: canon facts already live in the
canon store, and the envelope is a replayable view. Say so in the module docstring.

`run_id` is a `uuid4` hex string generated in the repository, not supplied by the caller.

**Tests:** round-trip a 3-turn run through a real on-disk temp DB, **close and reopen the engine**,
and assert the reloaded run is equal — the durability proof this repo uses everywhere else.

**Verification:** `uv run pytest tests/integration -k playthrough_repo -v` exits 0.

> **Who runs `make check`.** Per Global Constraint 11 the **controller** runs the full gate at task
> boundaries; an implementer runs only its targeted selection plus `ruff` and `mypy`. A task's own
> Verification block therefore lists the targeted commands only. **A reviewer must not treat a missing
> `make check` in an implementer's report as a spec gap** — it is the process working as designed.
> (Recorded because a Task 4 review did exactly that, and blamed the implementer for following its
> dispatch instructions.)

---

## Task 5 — The minimum turn-loop API

**Depends on Tasks 3 and 4.** Thin inbound adapter only: parse DTO → call service → map DTO. No
narrative logic in routers. Build `api/routers/play.py`, mounted in `api/main.py`. **These endpoints
and no others:**

| Method | Path | Body / params | Returns |
|---|---|---|---|
| GET | `/characters` | — | `[{id, name}]` from `CAST` |
| POST | `/play` | `{character_id}` | `{run_id, turn}` — starts at `FORK_ID`, chapter 1 |
| GET | `/play/{run_id}` | — | `{run_id, turn}` (current turn) |
| POST | `/play/{run_id}/act` | `{action: str}` natural language | `{run_id, turn, interpreted_as, reactions}` |
| POST | `/play/{run_id}/replay-as` | `{character_id}` | `{run_id, turns: [...]}` |

`TurnResponse` carries: `index`, `chapter`, `protagonist`, `scene`, `choices` (`id` + `label` +
`source_work_id` only — **never** the consequence, or the client can read the future), `citations`,
`withheld_count`.

`/act` flow: load run → `IntentRouter.resolve(action, current turn's choices)` → if
`choice_id is None`, return **HTTP 422** with the offered labels and **do not advance**; else
`PlaythroughService.advance(run, choice_id)` → save → respond. `interpreted_as` echoes the resolved
label so the player sees what the system understood.

`reactions` exposes the derived per-character directives (`domain/reactions.py`) so the UI can show
the ripple: `[{name, tension, blind_spots}]`. These are computed at render time — do not store them.

Errors: unknown `run_id` → 404. `UnknownChoiceError` → 422. `BudgetExceededError` → 402. Map through
`api/errors.py`'s existing `code → status` mechanism; do not invent a second error path.

**Tests** (`tests/e2e/test_play_api_e2e.py`, `TestClient`, `LLM_PROVIDER=scripted`, real temp DB):
full sequence `GET /characters` → `POST /play` → `POST /act` twice → `GET /play/{id}` →
`POST /replay-as`, asserting the run advances and the replay changes `withheld_count`.

**Verification:** `uv run pytest tests/e2e/test_play_api_e2e.py -v` and `make check` exit 0.

---

## Task 6 — Bind the Branch Oracle to real harvested fan-fiction

**The honesty gap.** Options come from an authored table in `resources/dexter_demo.py`; only the
`source_work_id` values are genuine, and `data/raw/` is empty.

1. Re-harvest (**needs network**):
   `uv run story-engine harvest "Dexter" --kind novel --show-branches`. If the network is
   unavailable, **stop and report BLOCKED** — do not fabricate a corpus.
2. Build `adapters/outbound/fanfic/corpus_branch_oracle.py::CorpusBranchOracle` implementing
   `BranchOraclePort`, reading `data/raw/fanfic/dexter/stories.jsonl` + `manifest.json` and mapping
   mined branch points to chapters.
3. **Known constraint, do not re-derive:** every `premise_group` in the real Dexter harvest has
   `size: 1` and every branch point `support: 1`. Code written assuming multi-member groups gets
   empty results. A canon baseline + one mined alternate is a legal 2-option decision point.
4. Where the corpus is thin, fall back to the authored options — but the fallback options **keep
   `source_work_id=None`** so a judge can still tell mined from authored. Log which chapters fell back.

**Tests:** a unit test over a small fixture corpus asserting mined options carry a real
`source_work_id` and that `options_at` returns 2-4 or `()`; and a test that a thin chapter falls back
without raising.

**Verification:** `uv run pytest tests/unit -k branch_oracle -v` and `make check` exit 0.

---

## Task 7 — Full-novel KB bootstrap across all three lanes

Ingest the Dexter PDF at real depth through Task 3's `CanonIngestService` so canon, vector and graph
are populated from one write path.

- A `story-engine ingest --novel <path>` CLI command that reports facts written and lanes synced.
- Assert post-conditions: canon fact count == vector entry count; the graph projection builds from
  canon without error; the guard still gates by chapter in **all three** lanes.
- **Restart proof:** close the engine, reopen, and confirm counts and visibility are identical.

Leave `HashingEmbedder` in place — swapping in `fastembed` is out of scope for this plan and its
docstring already states the limitation honestly.

**Verification:** `uv run pytest tests/e2e -k ingest -v` and `make check` exit 0.

---

## Task 8 — End-to-end verification of the full scenario

One e2e test, `tests/e2e/test_full_scenario_e2e.py`, walking the deliverable exactly:

1. Start a story; select Dexter; assert his memory packet is non-empty.
2. Submit a **natural-language string** (not a choice id); assert it resolves to an offered option.
3. Assert canon grew, the graph rebuilt, and the witnesses' `knower_scope` gained exactly the
   characters present — and **no one else**.
4. Assert the other cast members' directives name only what the actor already knows.
5. **The leak assertion, done properly:** take a fact only Dexter knows, and assert its
   `object_literal` does not appear in the *assembled prompt* for any other character. Assert on the
   real rendered prompt string, not on a helper that reuses the guard — `PROGRESS.md` records that
   the existing flagship leak test uses a tautological oracle, so do not copy its shape.
6. Submit a second natural-language action immediately; assert the world state at turn 2 reflects turn 1.
7. **Restart** the DB mid-scenario; assert the run and all per-character knowledge survive.
8. Replay as Deborah; assert her `withheld_count` is strictly greater than Dexter's at the same turn.

**Strengthen the existing leak test; do not replace it.** `PROGRESS.md` flags the flagship leak test
as using a tautological oracle — it verifies the guard by consulting the guard, so it passes by
construction and would keep passing if the guard were wrong. Keep that test (it still covers the
store-level contract) and **add a real oracle to it**: an independent assertion over the rendered
prompt string, which is the artifact that actually reaches the model. A test that cannot fail is not
coverage, and deleting it loses the case it does cover — so the fix is an added assertion, not a
rewrite.

**Verification:** `uv run pytest tests/e2e/test_full_scenario_e2e.py -v` and `make check` exit 0.

---

## Task 9 — API contract check *(runs immediately after Task 5, not after Task 8)*

**The mismatch is already known, so it must not be re-discovered late.** `frontend/src/lib/api.ts`
targets `getMoments` / `postDivergence` / `postRegenerate`; the backend will serve a turn loop. Task
10 is correctly last, but a contract break found *after* everything else is green is found at the
worst possible moment — with no runway left to absorb it.

This task is small and deliberately sequenced early: **do it as soon as Task 5 lands**, so the shape
of the gap is measured while there is still time to act on it, even though the rewire itself waits.

Build two things:

1. **A machine-checked contract file** — `frontend/src/lib/contract.ts`, TypeScript types for the
   Task 5 payloads (`Character`, `TurnDTO`, `PlayResponse`, `ActRequest`, `ActResponse`,
   `ReplayResponse`), written to match the FastAPI response models field for field.
2. **A contract smoke test** — `tests/e2e/test_api_contract.py`. Boot the app with `TestClient`,
   fetch `/openapi.json`, and assert every path **and every response field name** the frontend
   contract declares exists in the served schema. Parse `contract.ts` for the field names or keep a
   single duplicated list in the test with a comment binding the two files together — the point is
   that a backend rename **fails a test** rather than silently breaking the UI at demo time.

Also write `frontend/src/lib/adapters.ts` — a **thin shim** mapping the new turn-loop payloads onto
the shapes the existing screens already render (`Moment`, `RippleResult`). Nothing in the shim may
contain logic beyond field renaming and reshaping; if a mapping needs a decision, that decision
belongs in the backend. The shim exists so Task 10 is a swap at one seam rather than a rewrite of
six screens, and so an incompatibility shows up as a compile error in a 40-line file.

**If the contract check reveals a gap the shim cannot bridge** — a field the UI needs that no
endpoint serves — report it immediately rather than widening the API unilaterally. That is a scope
decision, and it belongs to the maintainer.

**Verification:** `uv run pytest tests/e2e/test_api_contract.py -v` passes, and
`cd frontend && npx tsc --noEmit` compiles.

---

## Task 10 — Frontend rewire *(only if Tasks 1-9 are all verified green)*

Replace `frontend/src/lib/api.ts`'s superseded `CanonClient`
(`getMoments`/`postDivergence`/`postRegenerate`) with the Task 5 contract, **via Task 9's shim** —
`adapters.ts` already does the reshaping, so this task wires it in rather than re-deriving it. Add a
natural-language text input to the play screen; flip `NEXT_PUBLIC_USE_MOCK=false`. **Keep the mock
path intact** as the stage fallback — it is the only thing that runs if the backend dies during the
demo.

**Verification:** `npm run build` succeeds and the Playwright demo-path spec passes against the live
backend.

---

## Out of scope — do not build

Self-improving agent loops · per-character LLM calls · a separate graph database · a real embedder
swap · creator surfaces · audio (S1) · accounts/saves/sharing · auto-repair of flagged
contradictions · continuous ingestion. Anything not in Tasks 1-9 is not happening.
