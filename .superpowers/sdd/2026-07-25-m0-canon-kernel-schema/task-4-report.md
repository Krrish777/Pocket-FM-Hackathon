# Task 4 Report: Entity, Scene, Commitment, Flag Models

**Status:** DONE
**Commit:** d456b2e (worktree-knowledge-base branch)
**Date:** 2026-07-25
**Test Count:** 29 passed (8 new tests added)

## Summary

Task 4 successfully implements four new domain models for the Canon Kernel schema:
- **CanonEntity**: Persistent story entities with name matching (canonical + aliases)
- **Presence**: Entity presence grade in a scene (ACTIVE, SILENT, REFERENCED)
- **Scene**: Narrative unit with roster and witness derivation (excludes REFERENCED entities)
- **Commitment**: Narrative debt lifecycle with state machine (PLANTED → TRIGGERED/BROKEN → PAID_OFF)
- **Flag**: Verifier findings with evidence requirements (hard-lane flags must cite ≥1 fact)

All models inherit `DomainModel` (frozen, extra="forbid", immutable collections). Full gate passes end-to-end.

## Steps Executed

### Step 1: Append Tests
Appended 8 new test functions to `tests/unit/domain/test_canon_models.py`:
- `test_entity_matches_any_of_its_aliases_case_insensitively()`
- `test_scene_witnesses_exclude_merely_referenced_entities()`
- `test_commitment_allows_only_forward_transitions()`
- `test_paid_off_commitment_is_terminal()`
- `test_paid_off_commitment_must_record_where_it_paid_off()`
- `test_payoff_must_not_precede_planting()`
- `test_hard_lane_flag_must_cite_at_least_one_fact()`
- `test_flag_renders_a_citation()`

Plus helper function `_commitment(**overrides)` for test factory pattern.

### Step 2: Verify Tests Fail
```bash
uv run pytest tests/unit/domain/test_canon_models.py -v
```
**Result:** FAILED with `ImportError: cannot import name 'CanonEntity'` (expected).

### Step 3: Implement Models

Extended enum imports in `canon.py`:
```python
from story_engine.domain.enums import (
    AssertionMode,
    CommitmentState,
    CommitmentType,
    EntityStatus,
    EntityType,
    FactStatus,
    FlagSeverity,
    InvariantKind,
    PresenceGrade,
    SourceType,
    VerificationLane,
)
```

Appended models to `src/story_engine/domain/models/canon.py`:

#### `_FORWARD_TRANSITIONS`
Private state machine lookup table:
- `PLANTED` → {TRIGGERED, BROKEN}
- `TRIGGERED` → {PAID_OFF, BROKEN}
- `PAID_OFF` → {} (terminal)
- `BROKEN` → {} (terminal)

#### `CanonEntity`
- `id: str`, `fork_id: str`, `type: EntityType`
- `canonical_name: str`, `aliases: tuple[str, ...] = ()`
- `status: EntityStatus = EntityStatus.ACTIVE`
- Method: `matches_name(name: str) -> bool` — case-insensitive name/alias resolution

#### `Presence`
- `entity_id: str`, `grade: PresenceGrade`

#### `Scene`
- `id: str`, `fork_id: str`, `chapter: ChapterIndex`, `order_in_chapter: int`
- `summary: str`, `roster: tuple[Presence, ...] = ()`
- **Property: `witnesses -> frozenset[str]`** — returns entity_ids where grade is NOT REFERENCED
  - Design spec requirement: "Being talked about is not being present"
  - Correctly filters: `if p.grade is not PresenceGrade.REFERENCED`

#### `Commitment`
- `id: str`, `fork_id: str`, `type: CommitmentType`
- `planted_at: ChapterIndex`, `state: CommitmentState = CommitmentState.PLANTED`
- `payoff_at: ChapterIndex | None = Field(default=None, ge=1)`
- `entity_ids: tuple[str, ...] = ()`, `provenance: Provenance`
- **Property: `is_open -> bool`** — True if state in {PLANTED, TRIGGERED}
- **Method: `can_transition_to(state) -> bool`** — checks `_FORWARD_TRANSITIONS`
- **Validator: `_payoff_is_consistent()`**
  - If `state is PAID_OFF and payoff_at is None` → ValueError
  - If `payoff_at is not None and payoff_at < planted_at` → ValueError

#### `Flag`
- `id: str`, `invariant: InvariantKind`, `severity: FlagSeverity`, `lane: VerificationLane`
- `draft_span: str`, `cited_fact_ids: tuple[str, ...] = ()`
- `citation_text: str`, `suggested_action: str | None = None`
- **Validator: `_hard_lane_flags_cite_evidence()`**
  - If `lane is VerificationLane.HARD and not cited_fact_ids` → ValueError
  - Soft-lane flags may have empty `cited_fact_ids`

Updated `src/story_engine/domain/models/__init__.py`:
- Added imports: `CanonEntity`, `Commitment`, `Flag`, `Presence`, `Scene`
- Updated `__all__` list (alphabetical order maintained)

### Step 4: Verify Tests Pass
```bash
uv run pytest tests/unit/domain/test_canon_models.py -v
```
**Result:** 29 PASSED ✓

### Step 5: Full Gate Verification
```bash
make check
```

#### Ruff Check
```
uv run ruff check .
All checks passed!
```

#### Ruff Format
```
uv run ruff format --check .
97 files already formatted
```
(Formatter auto-fixed line wrapping in test calls and Scene.witnesses property)

#### Mypy (Strict)
```
uv run mypy src
Success: no issues found in 46 source files
```

#### Pytest (Full Suite)
```
uv run pytest
============================= test session starts =============================
...
tests\e2e\test_app_boots.py ..                                           [  5%]
tests\integration\test_episode_log_sqlite.py ....                        [ 16%]
tests\unit\domain\test_canon_models.py .............................     [ 97%]
tests\unit\test_smoke.py .                                               [100%]

============================== 36 passed, 1 warning in 8.54s ========================
```

**Gate Result:** GREEN ✓

### Step 6: Commit

Used pathspec syntax as specified:
```bash
git commit -m "Task 4: Add CanonEntity, Presence, Scene, Commitment, Flag models..." \
  -- src/story_engine/domain/models/canon.py \
     src/story_engine/domain/models/__init__.py \
     tests/unit/domain/test_canon_models.py
```

**Commit SHA:** d456b2e
**Branch:** worktree-knowledge-base (as instructed — no push)

## Design Verification

### Constraint Checks

1. **Python 3.12+ typing:** All signatures use `X | None`, `tuple[...]`, `frozenset[...]` ✓
2. **DomainModel inheritance:** All four models inherit `DomainModel` (frozen, extra="forbid") ✓
3. **No clock calls:** No `datetime.now()`, `utcnow()`, or clock-dependent defaults ✓
4. **No vendor imports in domain/:** Pydantic only at boundary ✓
5. **Google-style docstrings:** Every public class and method has docstring ✓
6. **Line length 88:** `ruff format` verified ✓

### Design Points

1. **`Scene.witnesses` excludes REFERENCED entities:** ✓
   - Implementation: `if p.grade is not PresenceGrade.REFERENCED`
   - Test: `test_scene_witnesses_exclude_merely_referenced_entities()` validates frozenset
   - Rationale: "Being talked about is not being present — it must not confer knowledge"

2. **Hard-lane flags require ≥1 cited fact:** ✓
   - Validator: `if self.lane is VerificationLane.HARD and not self.cited_fact_ids`
   - Test: `test_hard_lane_flag_must_cite_at_least_one_fact()` raises on empty cite
   - Test: `test_flag_renders_a_citation()` validates citation_text render
   - Rationale: "An uncited flag is an opinion; a cited flag is evidence"

3. **State machine correctness:** ✓
   - `_FORWARD_TRANSITIONS` enforced by `can_transition_to()`
   - Test: `test_commitment_allows_only_forward_transitions()` validates PLANTED→{TRIGGERED,BROKEN}
   - Test: `test_paid_off_commitment_is_terminal()` validates PAID_OFF→{}
   - Terminal states (PAID_OFF, BROKEN) have no outbound transitions

4. **Immutability & invariants:** ✓
   - All collections use immutable types: `tuple`, `frozenset`
   - `@model_validator(mode="after")` enforces temporal invariants
   - Pydantic `frozen=True` via `DomainModel`

## File Changes Summary

| File | Changes | Lines |
|---|---|---|
| `src/story_engine/domain/models/canon.py` | Extend enum imports; add _FORWARD_TRANSITIONS dict; add 5 classes + 2 validators | +165 |
| `tests/unit/domain/test_canon_models.py` | Add 8 tests + 1 helper; extend imports | +99 |
| `src/story_engine/domain/models/__init__.py` | Update imports & __all__ | +10 |

**Total additions:** 274 lines of code and tests.

## Test Coverage (Task 4 Tests)

| Test | Purpose | Status |
|---|---|---|
| `test_entity_matches_any_of_its_aliases_case_insensitively` | Name resolution with aliases | ✓ |
| `test_scene_witnesses_exclude_merely_referenced_entities` | Witness roster logic | ✓ |
| `test_commitment_allows_only_forward_transitions` | State machine forward edges | ✓ |
| `test_paid_off_commitment_is_terminal` | State machine terminal edge | ✓ |
| `test_paid_off_commitment_must_record_where_it_paid_off` | Invariant: PAID_OFF requires payoff_at | ✓ |
| `test_payoff_must_not_precede_planting` | Invariant: temporal ordering | ✓ |
| `test_hard_lane_flag_must_cite_at_least_one_fact` | Evidence requirement (hard-lane) | ✓ |
| `test_flag_renders_a_citation` | Citation text property | ✓ |

All tests pass deterministically; no flakes or timing issues observed.

## Blockers / Concerns

None. Implementation follows the brief exactly; all design points verified; gate is green.

## Next Steps (Task 5)

Task 5 will import these models and integrate them into narrative processing logic. Current implementation is ready for consumption:
- Models are exported in `__init__.py`
- All public methods and properties are documented
- Type hints are strict and complete
- Validators are deterministic (no clock dependency)

---

**Report Generated:** 2026-07-25
**Verified by:** Full `make check` gate (ruff check, ruff format, mypy strict, pytest full suite)
