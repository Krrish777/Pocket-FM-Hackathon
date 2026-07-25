# Session Handoff

> The single per-session **clock-out** note. At session start read this first, then `PROGRESS.md` and
> `DECISIONS.md`. Five sessions have clocked out here: **Session A** (product definition), **Session B**
> (EXT-1 scraper build), **Session C** (EXT-1 IV&V audit), **Session D** (knowledge-base IV&V audit
> + remediation), and **Session E** (worktree cleanup, scope lock, novel ingestion, **and the
> playable demo**). **Session E is the most recent.**
>
> **▶ THE DEMO RUNS:** `uv run story-engine play --auto --turns 5 --replay-as deborah`
> — no API key needed. `demo.md` §0 explains what to watch.

---

## Session F — 2026-07-26 (INTEGRATION: the engine stops being CLI-only)

**Branch:** `integration-demo-path` (15 commits, **not merged, not pushed to main**).
**Gate:** `make check` **exit 0, 579 passed** (from 497 — +82 tests, zero regressions).
**Features:** **41/48**, every flip earned by its own passing verification command.

### The one thing to read next
**`docs/superpowers/plans/demo-path-integration.md`** — its **12 Global Constraints** are what the
review subagents enforced all session, and they are still the rules for this codebase. Then
`.superpowers/sdd/demo-path-integration/progress.md` for every finding and every ruling.

### Run it
```bash
# Terminal, no API key, the rehearsed path (unchanged this session):
uv run story-engine play --auto --turns 5 --replay-as deborah

# Over HTTP, no API key — the real demo:
LLM_PROVIDER=scripted uv run uvicorn story_engine.api.app:app --port 8899
#   GET  /api/v1/characters
#   POST /api/v1/play                    {"character_id":"dexter"}
#   POST /api/v1/play/{run_id}/act       {"action":"I go finish the priest tonight"}
#   POST /api/v1/play/{run_id}/replay-as {"character_id":"deborah"}

# Browser: cd frontend && npm run dev  ->  /play

# Serve the FULL novel (612 facts) instead of the demo anchors:
uv run story-engine ingest --novel data/external/Darkly-Dreaming-Dexter-1.pdf
DATABASE_URL=sqlite:///data/interim/canon_ingest.db uv run uvicorn story_engine.api.app:app

# Options mined from real fan fiction (default is authored):
BRANCH_ORACLE=corpus uv run story-engine play --auto --turns 5
```

### What was built
A real **OpenAI adapter** behind the existing `LLMPort` (metered, retried, replay-safe) ·
**natural-language intent routing** onto the constrained option set · the **knowledge base wired into
the composition root** · **run persistence** · the **turn-loop REST API** · a **corpus-backed branch
oracle** · a **full-novel ingest CLI** · the **full-scenario e2e** · an **API contract check** · one
additive **`/play`** route.

### Verified LIVE over HTTP with no API key (not merely tested)
`GET /characters` → 5 cast · `POST /play` → turn with citations, `withheld=3`, **no consequence in the
payload** · `POST /act "I go finish the priest tonight"` → interpreted, ch1→ch2, withheld 3→2, four
reaction directives · `POST /act "I fly to Cuba and start a new life"` → **422**, unified envelope,
offered labels in `context` · `POST /replay-as deborah` → **withheld 6 and 5 where Dexter saw 2**.
The real novel ingests to **612 facts / 27 chapters**, canon lane == vector lane, guard gating
monotonically (ch1 23/612 → ch27 612/612).

### Five defects the green suite could not see — all found by independent review
1. **A dead `except` clause.** `bootstrap.py` caught `DocumentIngestionError`; `seed_canon` raises
   `DemoSeedError` — a *sibling*, not a subclass. A drifted anchor crashed `build_container()`, and
   `story-engine reconcile` (which calls it) was unreachable in exactly the case it repairs.
2. **A silently-naive timestamp**, written 20 lines below this repo's own comment warning that
   SQLAlchemy drops `tzinfo`.
3. **Two incompatible error envelopes for one 422**, on the branch a judge is most likely to trigger.
4. **Natural-language input wholly non-functional in the keyless demo** — scripted mode 422'd on every
   typed action, so "runs with no API key" held only for numeric picks.
5. **The graph lane is structurally empty on the demo fork** (all facts carry `object_literal`) —
   found by the new e2e, *reported rather than papered over*, logged in `BACKLOG.md` with a fix path.

### Decisions recorded in `DECISIONS.md`
OpenAI as provider with `scripted` kept as a first-class keyless path · cost metered honestly (an
unpriced model reports `0.0` and warns rather than inventing a number) · **the input is named
"natural-language intent", never "free-form"** — it maps onto a constrained action set, and the
overclaim would migrate from the pitch into the code · **canon-first / vector-second** ingest
atomicity with `reconcile()` and no compensating delete against an append-only store · the corpus
oracle ships **default-off**.

### Honest state of M4
The oracle is **real** — 7 works / 89 chapters / 5 branch points, each with a genuine `wattpad:<id>`.
The corpus is **thin**: every branch point is `support: 1`, and only **1 of the demo's 4 anchored
chapters** gets a mined alternate. Everything else stays authored with `source_work_id=None`, so mined
and authored are distinguishable at a glance. Nothing fabricates provenance.

### Next session — start here
1. **Merge decision.** The branch is not merged and not pushed to `main`. Review, then decide.
2. **M8** — traits and goals on the character record. Small, closes a MUST.
3. **M7** — the §5.5 verifier: *intentional divergence* vs *accidental contradiction*.
4. **The graph gap** (`BACKLOG.md`) — give demo anchors real `object_id` relations so the demo fork
   projects edges; `PlaythroughService._fact_for` writes `object_literal` unconditionally too.
5. **A real embedder** behind `EmbedderPort` — `HashingEmbedder` is near-random on natural language.
6. **Databricks** vector/memory integration is specced in `BACKLOG.md` — post-demo, and it must keep
   the guard as a PRE-filter or it is a spoiler side-channel.

---

## Session E — 2026-07-25 (scope lock → novel ingestion → **a working demo**)

**Branch:** `main`. Both parallel worktrees were merged and removed; the session then locked the demo
scope in writing and built the first task from it.

### The one thing to read next
**`demo.md`** — the scope fence. Nine demo beats, ordered tasks T0–T10, a pre-decided cut ladder, and an
explicit not-building list. Estimated **~18 h of work against ~14 h of runway**; the cut ladder exists
because that gap is real and should not be re-discovered at 3 a.m.

### What I did
1. **Cleaned the worktrees.** Removed `reddit-fanfic-scraper` and deregistered `knowledge-base`; pulled
   `main` to `d1952c8` (PR #4). Both worktrees had been committed into `main` as **mode 160000 gitlinks**
   — git recorded a bare commit-SHA pointer because it saw a nested `.git`, which is why the tree read
   dirty after removal. Untracked both and added `.claude/worktrees/` to `.gitignore` so it cannot recur.
   ⚠ The `knowledge-base` *directory* is still on disk: a live Claude session (pid 7456) holds a file
   handle. Cosmetic — git ignores it. `rm -rf .claude/worktrees/knowledge-base` once that session closes.
2. **Locked the scope** in `demo.md`, and folded T0–T10 into `BACKLOG.md` as the ordered queue.
3. **Built INGEST-01** — novel PDF → chapter-addressed, citable text. See below.
4. **Assessed three reference repos** (notebook-lm-clone, hermes-agent, and the maintainer's GitHub
   stars) and recorded what to take vs leave in `BACKLOG.md`.

### INGEST-01 — what was built, and the three upstream defects fixed
Adapted from `patchy631/ai-engineering-hub/notebook-lm-clone`. **License is MIT** (© 2024 patchy631) —
verified by reading `LICENSE` at the repo **root**; the prior `BACKLOG.md` warning that no license was
stated had only checked the subdirectory. That claim is now corrected in place.

- `domain/chunking.py` — pure, stdlib-only, overlapping sentence-aligned spans.
- `adapters/outbound/ingestion/pdf_document_source.py` — PyMuPDF reader + chapter detection.
- `ports/document_source.py`, `domain/models/document.py`, `DocumentIngestionError`.

**Defect 1 — silent data loss.** Upstream advanced with `start = max(start + chunk_size - overlap, end)`,
which jumps *past* `end` whenever the sentence snap retreats further than the overlap covers, dropping
those characters entirely. A dropped span is a fact that exists in the novel and can never be cited.
The trigger condition is exactly `start + chunk_size - overlap > end` — worth knowing, because the first
proof fixture (84-char sentences, 20-char overlap) did **not** trigger it and the test correctly failed
until the fixture was corrected. Short sentences relative to the window are what make it fire, and prose
is full of them.

**Defect 2 — quote/offset disagreement.** Upstream stripped the chunk text but recorded the *unstripped*
offsets, so `text[char_start:char_end] != quote`. A citation that cannot resolve to its own coordinates
is not a citation.

**Defect 3 — page-relative offsets.** Changed to chapter-relative. Decisive, not cosmetic: the spoiler
guard gates on **chapter** (`visible_to(fork, knower, chapter)`), and a page number cannot answer
"has this been revealed yet?".

**Design call worth keeping:** a PDF with no detectable chapter headings **raises** rather than degrading
to a single chapter. Stamping every fact `chapter=1` leaves the guard running and its tests green while
silently making the entire novel visible to every character from turn one — a green-suite failure of the
headline claim. `allow_single_chapter=True` is the explicit opt-in.

**Rejected:** upstream's retrieval path. `vector_db.search(query_vector, top_k)` applies no epistemic
filter, so wiring it in would create a second unguarded read path beside `store.visible_to()`.

### Then the demo got built (session 7b, same day)
**`uv run story-engine play --auto --turns 5 --replay-as deborah`** plays five choices against the
real novel and closes on the replay beat. **No API key needed** — beats are replayed from
`ScriptedLLM`, so a stage demo cannot die to a timeout or an unlucky sample.

- **PROP-01 — knowledge propagation.** `knower_scope` is derived from `Scene.witnesses`. The
  invariant: **monotonic** — may add a knower or move an acquisition earlier, never remove or delay
  one; enforced in the domain *and again* at the store boundary, because losing a knower is silent at
  read time. Two traps, both tested: an **untracked fact stays untracked** (`knower_scope is None`
  means visible-to-all, so attaching witnesses would *narrow* it — the inverse of learning), and
  **earliest acquisition wins**. Learning is not routed through `supersede`: the claim didn't change.
- **PLAY-01 — the turn loop.** `PlaythroughService`. Exactly one model call per turn and it decides
  nothing; every transition is computed in code first. `replay_as` is a re-render, not a rewrite.
- **DEMO-01 — playable.** Canon seeded from the PDF with quotes **sliced at seed time**, each anchor
  carrying a sentinel so drifted offsets fail loudly rather than citing the wrong paragraph.
- **The prose is authored** (`resources/dexter_demo_script.py`), keyed by
  `{knower}:{chapter}:{visible_fact_count}` — the key names *who is looking and how much they may
  see*, which is the axis the demo turns on. A test asserts all 12 beats are covered, because a gap
  wouldn't raise: it would silently degrade the one beat nobody rehearsed.
- **T10 — the harness bug is fixed.** `tests/conftest.py` now applies `unit`/`integration`/`e2e` from
  the directory a test lives in, and `unit` is registered. Before this, every `pytest -m unit`
  verification in `feature_list.json` selected **nothing** and no product feature could ever flip.

### Two defects found by *running* it, not reading it
1. **The narrator recited the player's own choices.** The prompt renders known facts and upcoming
   options as the same `- ` bullets, so the fallback's line scan read the menu as memory — directly
   under a prompt instruction never to name them. Fixed by scoping the scan to the knowledge block.
2. **The table of contents became chapter 1.** The real novel opens with "Chapter 1 thru Chapter 27",
   which matched the heading pattern and shifted **every** chapter by one. The guard gates on chapter,
   so that quietly moved every reveal boundary in the book — while all synthetic fixtures stayed green,
   because none of them had a table of contents.

### And then the cast started reacting (session 7c, same day)
**M6 — derived directives.** The renderer now gets a line for every *other* cast member:
`Sergeant Doakes — tension toward dexter: 2/5. Does NOT know: <clauses>.`
Added `prompts/render_scene/v2.jinja`; **v1 kept intact** per `prompts/README.md`.

- **Computed at render time, never stored.** Storing rich state for the protagonist and thin
  directives for everyone else would hardcode a hierarchy and turn S3 into a rewrite.
- **The anti-leak property is structural, not instructional.** A directive is
  `actor_facts − their_facts`, so it can only ever name facts the actor already knows — it is
  *incapable* of surfacing a third party's secret, rather than merely instructed not to. Asserted on
  the real assembled prompt: after Doakes learns the secret, Deborah's replay prompts still never
  contain "Dark Passenger".
- **Tension is derived, not authored.** Live run: Doakes **2/5**, Rita **3/5** — Doakes reads
  *closer* to Dexter because he was in the parking lot. Nobody edited a character sheet.

### State at clock-out
`make check` **GREEN**, **497 tests**, exit 0. `feature_list.json`: **33/40 passing**.
Working tree clean. Four commits: `a7077a5`, `215e173`, `00550e8`, `8dfb0ea`.

**M1, M2, M3, M5, M6, S3 flipped** — each earned by its own re-pointed verification command.

**M7 and M8 deliberately left false even though their commands now pass** — a green command written
by the same session is not evidence the spec is met:
- **M8** — uniform schema is real; **traits and goals still do not exist** on the character record.
- **M7** — the receipt works; **§5.5's verifier does not exist**, so nothing separates intentional
  divergence from accidental contradiction. "Consistency enforced" is not yet true.

### Next step — start here
1. **M4 / T5 — bind the Branch Oracle to real mined fan fiction.** *The biggest honesty gap.* §5.2
   and the pitch both claim choices come from divergences fan fiction actually wrote; they come from
   an authored table in `resources/dexter_demo.py`. Only the `source_work_id` values are genuine.
   **Blocked on data:** `data/` is empty (the corpus lived in the deleted worktree), so step one is
   re-running `story-engine harvest "Dexter" --kind novel --show-branches` — that needs network.
   Anything that stays authored must keep `source_work_id=None` so the distinction stays auditable.
2. **M8's traits and goals** — small, and it closes a MUST.
3. **M7's verifier** (§5.5) — the distinction, not a blanket contradiction flag. A verifier that
   flagged every divergence would be useless here, because deliberately breaking canon is the genre.
4. **T9 — the frontend.** Terminal-only today. Its `CanonClient` still targets the superseded
   single-flip contract (`getMoments`/`postDivergence`/`postRegenerate`) while the backend serves a
   turn loop. Biggest *presentability* win; also the biggest job.

### Still open
- **D-2 — snap-to-branch vs true free-form.** Recommend snap-to-branch. Unchanged.
- **D-3 — novel vs screen canon** (OD-2). The demo uses **novel** names; fan fiction is mostly screen.
  This bites the moment M4 starts.
- **A real embedder.** Measured on the full novel: verbatim recall@5 8/8, but natural-language
  retrieval is near-random, exactly as `HashingEmbedder`'s docstring predicts. The guard held
  perfectly (0 leaked of 20 hits at ch3). `fastembed` behind `EmbedderPort` is the fix.
- **`research/Pocket FM Hack/` is a nested git repo** and stays untracked. Do **not** `git add` it —
  that is precisely how the two worktrees became mode-160000 gitlinks that this session had to unpick.
- **D-1 is CLOSED** — the PDF is at `data/external/Darkly-Dreaming-Dexter-1.pdf`.

### Still open
- **D-2 — snap-to-branch vs true free-form.** Recommend snap-to-branch. Unchanged.
- **D-3 — novel vs screen canon** (OD-2). The demo uses **novel** names; fan fiction is mostly screen.
- **A real embedder.** Measured on the full novel: verbatim recall@5 8/8, but natural-language
  retrieval is near-random, exactly as `HashingEmbedder`'s own docstring predicts. The guard held
  perfectly (0 leaked of 20 hits at ch3). `fastembed` behind `EmbedderPort` is the fix.
- **D-1 is CLOSED** — the PDF is at `data/external/Darkly-Dreaming-Dexter-1.pdf`.

---

## Session D — 2026-07-25 (IV&V audit of the KNOWLEDGE BASE → two product blockers fixed)

**Branch:** `worktree-knowledge-base`. Independent verification pass over the knowledge base, then
remediation of the defects that blocked the product. Eight defects were reproduced with executable
probes **while `make check` was green**.

### The one thing to read next
**`tests/e2e/test_product_flow_e2e.py`** — it walks the whole product scenario (character select ->
per-character memory -> citation receipt -> guarded semantic recall -> player choice forks the story
-> replay as another character -> restart) against a real on-disk database. It is written against
`project_context.md` rather than against the implementation, which is why it found what the existing
green suite did not.

### The two PRODUCT blockers, both fixed
1. **Per-knower acquisition time.** `Fact.knower_scope` was a timeless `frozenset[str]`, and
   `is_visible_to` gated EVERY knower on the audience's `revealed_at` — so a character could not know
   anything before the audience did. All five cast members received identical packets; M5 and S3 were
   unbuildable. Now `tuple[Awareness, ...]` (knower + the chapter they learned it) with `AUDIENCE` as
   an ordinary knower. Call sites pass a `{knower: chapter}` mapping.
2. **Fork lineage.** `fork_id` was an opaque partition key, so a player's branch held their one choice
   and none of the novels. Added the `canon_fork` table plus `register_fork`/`get_fork`/`lineage`;
   `all_facts` resolves fork -> parent -> ... -> root with a divergence cap and nearer-fork shadowing.
   An unregistered fork still resolves as a root, so existing callers are unaffected.

### Critical defects fixed in the same code paths
- The vector lane ignored `FactStatus`, so a QUARANTINED fact was retrievable by similarity while the
  canon store correctly hid it. There were **two** implementations of one security predicate and the
  copy had dropped a clause; it is now one function, `domain.models.canon.is_visible`, shared by
  `Fact` and the vector store.
- `supersede()` skipped every domain validator and could write a row that made the whole fork
  permanently unreadable, with no delete path to repair it. It re-validates through `Fact` now.
- Double supersession left two live successors (violating documented I-2/I-8) — now rejected.
- `as_of()` had no tie-break on equal `valid_from` — now a total order.
- Vector `add()` was not idempotent; `remove()` did not exist.

### State
`make check` GREEN. KB tests 110 -> 138 before merging main. Every fix above carries a regression test
that names the defect it prevents.

### Next step
**`AUD-H5` is the highest-value open item: the KB still has zero production callers.** `bootstrap.py`
wires none of `SqliteCanonStore` / `SqliteVectorStore` / `WorkingMemory` / `HashingEmbedder`, and no
API route or CLI command reaches canon. `AUD-H1` (canon-vector sync) is now cheap because
`VectorStorePort.remove()` exists; only the ingest service pairing the two writes is missing.

### Known gaps, stated plainly
- `CanonEntity` / `Scene` / `Presence` / `Commitment` / `Flag` / `Source` still have no persistence
  and no source consumers.
- `knower_scope` is populated by hand; nothing derives it from `Scene.witnesses` yet (KB-13's
  propagation half), so knowledge does not compound across turns on its own.
- Test-quality items `AUD-T1`, `AUD-T2`, `AUD-T5`, `AUD-T7`, `AUD-T11`, `AUD-T13` are deferred, not
  done — the flagship leak test still uses a tautological oracle, and 4 of the 9 documented
  invariants (I-6, I-7, I-8, I-9) have no test. Do not read a green gate as full assurance.
- **Note for the EXT-1 hand-off:** Session C reports every `premise_group` has `size: 1`. The KB side
  is unaffected — forks do not assume multi-member groups — but M4's branch-oracle work should read
  that note first.

---

## Session C — 2026-07-25 (IV&V audit of the scraper → 4 bugs found and fixed)

**Framing:** An **independent verification & validation pass** over the EXT-1 scraper, run under the
explicit posture *"assume the scraper is incorrect until evidence proves otherwise."* This was a
**verification session, not a feature session** — no new scraper capability was added, by design.
Four real defects were found, proven with executable probes, and fixed.

`make check` is **GREEN** (exit 0, **286 passed**, up from 237). Stable across 5 consecutive runs
(3 sequential + 2 randomized order). All 9 feature verification commands re-run: **all PASS**.

### The one thing to read next
**`docs/EXT-1-scraper-output-contract.md`** — now corpus schema **1.2**. The new `chapters_dropped`
block is the change that matters to the knowledge-base consumer.

### What I did
**Audited first, fixed second.** Read the contract + design spec, mapped every module to its tests, then
ran the real pipeline and inspected the artifact rather than trusting the docs or the green gate.

**Four defects — each proven by running code, not by reading it:**

1. **`strip_boilerplate` was deleting real narrative prose.** Every call-to-action word is also an
   ordinary English verb, and the patterns matched any line merely *starting* with one. Five realistic
   lines destroyed, e.g. `"Like a knife, the cold cut through him."` / `"Follow the blood, he thought."`.
   The `read on <host>` pattern was unanchored, so `"He read on Wattpad about the case"` also died.
   **This was corrupting corpus text** — the knowledge base's direct input. 35 tests covered this module
   and none fed prose starting with a common verb.
2. **Chapters were silently dropped, leaving works truncated with no marker.** Live evidence:
   `wattpad:864850` shipped **starting at chapter 2** (chapter 1 gone); `390229723` had gaps at indices
   6 and 11. Index gaps are indistinguishable from an author's own numbering, so a consumer could not
   tell a truncated work from a complete one.
3. **The on-disk manifest contradicted the CLI.** `jsonl_sink.py` recomputed branch points with its own
   default ceiling, ignoring `--max-branch-options`. Proven: the console printed 2 options while the
   artifact — what the KB actually ingests — contained 3.
4. **`<script>`/`<style>` bodies leaked into prose.** Found by a *new* test: stripping tags leaves the
   *contents* of those elements behind as if it were story text.

**Fixes (all landed, gate green):**

| # | Fix | Files |
|---|---|---|
| 1 | CTA patterns now require `please` or a second reader-directed marker; `read on <host>` requires an explicit continuation object (`the rest`/`more`) | `domain/fanfic_quality.py` |
| 2 | `chapters_dropped {non_prose, duplicate, is_partial}` per record; **schema 1.1 → 1.2** (additive) | `models/fanfic.py`, `services/fanfic_harvest.py`, `jsonl_sink.py` |
| 3 | `max_branch_options` threaded through `CorpusSinkPort` — the sink no longer recomputes | `ports/corpus_sink.py`, `jsonl_sink.py`, `services/fanfic_harvest.py` |
| 4 | script/style/comment bodies removed before tag stripping | `fanfic/http_util.py` |

**Test suite: 237 → 286.**
- **New `tests/unit/adapters/test_http_util.py` (22 tests).** The retry engine — every scraper request
  goes through it — had **zero** tests. Now covers retryable vs non-retryable statuses, attempt
  exhaustion, network-error typing, and exponential backoff.
- **Fixed a false positive:** `test_respects_max_stories` asserted `len(stories) <= 2`, which a harvester
  returning **zero** stories also satisfies. Now `== 2`.
- **New classes:** `TestMultiChapterIntegrity`, `TestMultiSourceResilience`, `TestTruncationProvenance`,
  `TestBoilerplateDoesNotEatProse`.
- **Root cause of the blind spot:** service fixtures defaulted to `chapters=1` per work, making an entire
  bug class *structurally unreachable* by the suite. Real works are multi-chapter — the live Dexter
  corpus is 43 chapters across 4 works.

### State
- **Committed:** `2a25444` "regular updates" (16 files, +715/−145). Includes this session's work **and**
  5 files staged by a prior session (`AGENTS.md`, `CLAUDE.md`, `feature_list.json`, `init.sh`,
  the previous `session_handoff.md`).
- **Corpus schema is now 1.2.** 1.0/1.1 readers are unaffected — the change is additive.
- Live re-harvest confirms the fix end-to-end:
  `864850 → {'non_prose': 1, 'duplicate': 0, 'is_partial': True}`.

### Next step (how to resume)
1. `./init.sh` — confirms the gate; now also prints the corpus schema version + local corpora.
2. **The scraper is DONE for hackathon purposes. Do not invest further here.** It produces the 2–4 choice
   set the playable layer needs. Move to product features — **M8 first**.
3. **Hand to the KB team (one message, saves them an afternoon):** every `premise_group` in the real
   Dexter harvest has `size: 1` and every branch point `support: 1`. The *"N independent humans branched
   off the same canon node"* story does **not** hold at this corpus scale — one author per decision
   point. The demo is unaffected (canon + one alternate = a legal choice), but code written assuming
   multi-member groups will get empty results.
4. **Open, deliberately not fixed** — see `BACKLOG.md` IV&V section: prose-gate thresholds (F-7),
   `alias_expander.py` still at 0 tests, Wattpad `search()` pagination untested, `Retry-After` ignored.

---

## Session A — 2026-07-25 (product definition; owned by the product / knowledge-base session)

> Preserved verbatim from that session's clock-out.

**Framing:** The hackathon brief arrived. This was an **elicitation session, not a build session** — the
objective was to get the product out of the user's head and into a concrete spec. **No product code was
written, by design.** `make check` is GREEN (exit 0, 7 passed).

### The one thing to read next
**`project_context.md`** — the single source of truth for what we are building and why. It declares its own
supersessions (§12) and beats any other doc in this repo, including the friend-authored PRD and
`_PROBLEM VERDICT`. Decision provenance (13 decisions with rejected alternatives + a corrections table):
**`docs/2026-07-25-product-definition-session.md`**.

### The product, in one line
A playable branching layer over the **Dexter novels** — pick a character, play forward through choices mined
from **fan-fiction**, with every character remembering only what they actually learned.
Track: **P1 Story Time Machine + Infinite Story Universe**. Runway: 24–36h, 2–4 people.

### What I did
- **Closed INIT-01.** Established the brief is a *menu* (~40 statements / 6 tracks) — so this was a selection
  and narrowing decision, not a copy-paste. Patched `CLAUDE.md` + `AGENTS.md` (mirror in sync); verification
  command re-run and passing.
- **Resolved the repo's central conflict**: `_PROBLEM VERDICT` said build for the *creator*; the friend's PRD
  built for the *listener*. Settled **Player primary, creator is a slide** — an explicit override of the
  vault's own recommendation, recorded as such so it is not mistaken for an oversight.
- **Wrote `project_context.md`** (13 §): problem, exact core loop, glossary, corpus, MUST/SHOULD/OUT,
  demo proof, 17 settled decisions, 6 open items with owners, supersessions.
- **Wrote the session decision record** in a new top-level `docs/`.
- **Seeded the product phase** in `feature_list.json`: M1–M8 (MUST) + S1–S3 (SHOULD), each with a verification
  command, all `passes:false`.
- **Fixed the gate:** `.claude/worktrees` added to ruff `extend-exclude` — parallel worktrees are separate
  checkouts that run their own `make check`; linting them from the parent failed our gate on their code.

### Ideas established that session
1. **Fan-fiction is the branch oracle** — a third path past the dead end where hand-authored branches are
   unaffordable (Until Dawn) and generated branches are incoherent (AI Dungeon).
2. **Intentional divergence ≠ accidental contradiction.** Fan-fiction breaks canon *on purpose*; a verifier
   that flags every divergence is useless. This distinction *is* the product.
3. **Protagonist-ness is a rendering choice, not a stored property** — which makes Infinite Story Universe
   nearly free and unlocks the closing demo beat: replay the same branch as Debra.

### Warnings from that session (still current — heed these)
- **The git index is shared across parallel sessions.** Staging is not a safe hold; only an uncommitted
  working tree is. Coordinate before staging.
- **Never pipe `make check` into `tail`/`head`** — you get the *filter's* exit code, so a red gate reads as
  green. Redirect to a file and check `$?`.
- **OD-2 is a real trap:** the KB is novel-based, Dexter fan-fiction is largely screen-based. (Session B has
  now made this decidable — see below.)

### Session A's next step
**M8 — the uniform character state schema.** Build it first: it is the only decision expensive to retrofit,
and M5 + S3 both depend on it. Spec: `project_context.md` §4.4.

---

## Session B — 2026-07-25 (EXT-1: fan-fiction scraper → Branch Oracle)

**Branch:** `worktree-reddit-fanfic-scraper` · worktree `.claude/worktrees/reddit-fanfic-scraper`
**Commit:** `d51ed29`, rebased onto main (1 ahead, 0 behind). **NOT pushed. NOT merged to main.**
**Gate:** `make check` GREEN, exit code verified — ruff + ruff-format + mypy strict (68 files) + **237 tests**.
**Features:** `FANFIC-01 … FANFIC-06` all pass, each by its own `verification` command.

### What this branch is
**EXT-1** in `project_context.md` §9 — the ingestion dependency Session A was blocked on (its OD-3 was the
"highest-risk unknown in the project"). Read `project_context.md` first, then
`docs/EXT-1-scraper-output-contract.md`.

Per §5.2 the deliverable is **branch structure, not prose volume**: fan fiction supplies *what the options
are* and is **never quoted, reproduced, or used as generated prose**. A 918-word abandoned fic carries as much
branch signal as a 35-chapter saga. **Do not "improve" this by chasing corpus size.**

### What was delivered
| ID | Thing | Evidence |
|---|---|---|
| FANFIC-01/02/03 | Scraper: discover → judge relevance → gate prose → dedup → persist | Titanic 10 works; Dexter 4 works / 43 chapters / 55,769 words. Precision spot-check 6/6 Dexter, 8/8 Titanic |
| FANFIC-04 | **Branch Oracle** — canon decision points with 2–4 player-facing options (§4 step 3) | Titanic `character_survives:jack` support=3 → **4 options from 3 independent authors** |
| FANFIC-05 | **OD-2 canon discriminator** — wiki entity vocabulary (deliberately *not* a canon KB) | 314 Dexter entities: **novel 68 / screen 223 / both 9 / unknown 14** |
| FANFIC-06 | **EXT-1 output contract** (closes OD-3) | `docs/EXT-1-scraper-output-contract.md` |

Two sources behind one port: **Wattpad** (primary; blurbs + popularity, no canon marker) and **AO3 via
HuggingFace** (longer works, and the only source whose labels split canons). Reddit was ruled out on
measurement, not taste.

### Two findings that need a HUMAN DECISION — do not let these get lost
1. **§6.3's cast names are SCREEN names.** In the novels: **Debra → `Deborah Morgan`, Doakes →
   `Albert Doakes`, LaGuerta → `Migdia LaGuerta`.** Brian's moniker is `Ice Truck Killer` (screen) vs
   `Tamiami Butcher/Slasher` (novel). §6.1 says the KB is built from the **novels**, so either the cast names
   change or §6.1 does. Decide with the data in `data/raw/wiki_index/dexter/`.
2. **Our best Dexter branch is screen-canon.** *Set Free* ("Dexter doesn't kill Brian") is built on the
   killing-table framing. Under §6.1 it references a scene the novels may not have — the OD-2 corruption path,
   now visible instead of latent.

### The one ask on the knowledge-base side
A branch can name the **entities** it turns on but cannot cite a **scene**, because scene identity lives in
the Canon Kernel's `Scene` model. **Expose a resolvable canon-moment id** — minimally
`(chapter, order_in_chapter)` or a documented `Scene.id` — and the scraper can emit
`diverges_from: <scene ref>`, making the oracle queryable *by canon moment*, which is what §4 step 3 needs.
Largest remaining integration gap; see the contract doc §6.

### Known gaps (honest; none are blockers)
- `--kind` is effectively **required** for ambiguous titles: without it "Titanic" resolves to the ship and
  "Dexter" to a warship (`USS Dexter`).
- **Only exact dedup** (SHA-256 over normalised text). Near-duplicate reposts survive; MinHash was assessed
  and deliberately skipped at this corpus scale.
- AO3: dataset licence is **NONE**; no Hits/Kudos, so `--include-ao3` auto-relaxes the read/vote floors to 0.
  Dexter yield there is ~20 works in 64,000 rows — **do not plan a demo on AO3 Dexter volume**.
- `prose_quality`'s `paragraph_structure` component scored 1.00 on 13 of 14 real works — effectively a
  constant on Wattpad data. Revisit once AO3 data lands.
- The mature-content flag is the **host's self-report** and is unreliable (a `mature:false` work had an
  explicit blurb). Do not rely on it for a player-facing surface.
- Harvests are **not idempotent** — host ranking shifts, and the corpus file is overwritten. Snapshot if you
  need reproducibility.

### Harness fixes made while closing out (verified, not assumed)
- **`init.sh` was reporting a red gate as success.** It ended in
  `make check || echo "not green yet (expected during initialization)"`, so with `set -euo pipefail` the `||`
  swallowed the failure and `init.sh` exited 0 on a RED gate — the same failure mode as piping `make check`
  into `grep`. Now it prints `consistency: GREEN`, or prints `consistency: RED` to stderr and **exits with the
  gate's status**. Proven both ways: exit 0 green; exit 2 with a temporary syntax error injected.
- **`feature_list.json` order encodes priority, and it was pointing the next session at the wrong task.**
  `init.sh`'s "next feature (WIP=1)" query takes the first `passes:false` entry, which was `HARDEN-05` — whose
  own evidence says *"Do not start before M1-M8"*. Deferred work moved to the end, so it now surfaces **M8**,
  matching `PROGRESS.md`.
- **`CLAUDE.md` + `AGENTS.md`** (kept in sync) now point at the EXT-1 contract and list the three ingestion
  commands, plus the "check the gate by exit code" rule.
- **Checked, and NOT broken:** `INIT-01`'s verification (`! grep -q ... CLAUDE.md`) passes correctly — exit 0
  in bash. An earlier report that it failed was an artifact of running it through `subprocess(shell=True)`,
  which uses `cmd.exe` on Windows where `!` is not a negation operator. Do not "fix" it.

---

## NEXT SESSION — end-to-end testing, code review, full verification, THEN merge

Maintainer's plan. **Nothing merges to main until steps 1–3 pass.**

### 1. End-to-end testing (live network)
```bash
cd ".claude/worktrees/reddit-fanfic-scraper"

make check > /tmp/check.log 2>&1; echo "exit=$?"    # MUST be exit=0. Never pipe to grep/tail.

# Branch Oracle — the demo-critical path
uv run story-engine branches "Titanic" --kind movie --max-stories 10
uv run story-engine harvest  "Dexter"  --kind novel --max-stories 10 --show-branches

# Canon discriminator
uv run story-engine wiki-index "Dexter" --limit-per-kind 150

# Second source (slow: ~50 requests / ~2 min; relaxes read/vote floors)
uv run story-engine harvest "Harry Potter" --kind novel --include-ao3 --max-stories 5
```
Then inspect `data/raw/fanfic/<slug>/{stories.jsonl,manifest.json}` and
`data/raw/wiki_index/<slug>/{entities.jsonl,manifest.json}`. **Check each manifest's `story_count` against the
file's line count** — that mismatch is the interrupted-run detector.

Windows note: the console is cp1252 and dies on non-ASCII. Use `PYTHONIOENCODING=utf-8`, and in scripts
`sys.stdout.reconfigure(encoding="utf-8")`.

### 2. Code review — risk is NOT evenly distributed; review in this order
1. `domain/fanfic_premise.py` — the Branch Oracle. Grouping is **precedence, not union**, and survival keys on
   **one** entity. Both are load-bearing: union-keying shatters the group that proves the concept.
2. `domain/fanfic_quality.py` — the admission policy. Tag-key vs word-boundary matching fixed two *opposite*
   live misclassifications; the regression tests name the real cases.
3. `adapters/outbound/wiki/canon_basis.py` — the OD-2 classifier, highest consequence if wrong.
4. `adapters/outbound/fanfic/hf_ao3.py` — bounded/resumable scan; verify cache + offset persistence.
5. `domain/prose_score.py` — six bounded components; weights were deliberately **not** tuned to force a
   preferred ranking (that would overfit 14 works).

Suggested: `/code-review`, or the `pr-review-toolkit` agents. **`silent-failure-hunter` is the best fit** —
this code has many deliberate "degrade rather than abort" paths (a dead host, an unavailable chapter, a failed
alias expansion), and every one should log loudly rather than pass silently. Confirm that.

### 3. Full verification
- `make check` green **by exit code**, not by reading output.
- Re-run each `FANFIC-01…06` `verification` command from `feature_list.json` individually.
- Confirm **no `data/` artifact is staged** — it is gitignored and the corpus must never be committed.
- Confirm `docs/EXT-1-scraper-output-contract.md` still matches the code. Its §7 says **the code is
  authoritative and a mismatch is a bug in the doc.**

### 4. Only then: merge to main
Already rebased onto main, so it should fast-forward. **Ask the maintainer before pushing or merging.**

### Do NOT re-litigate these — measured, and recorded in `DECISIONS.md`
- Reddit does not hold fandom fan-fiction prose: fandom subs have a **median selftext of 141–620 chars**, and
  r/FanFiction Rule 1 bans posting fic text. AO3 and fanfiction.net are Cloudflare-walled.
- Wikipedia disambiguates films **by year** (`Titanic (1997 film)`), so no suffix list can reach them — the
  title must be *resolved* via search.
- Wikimedia **403s** any User-Agent lacking a contactable URL/email, which silently kills alias expansion.
  Set `STORY_ENGINE_CONTACT`.
- Read `docs/superpowers/specs/2026-07-25-fanfic-harvest-design.md` before changing any source or threshold —
  it holds the measurements, so you neither re-derive nor contradict them.
