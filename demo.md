# DEMO.md — the scope lock

> **Status:** ACTIVE · **Written:** 2026-07-25 · **Runway at time of writing: ~14 hours**
>
> **This file is a fence, not a wishlist.** It lists the things we build and *nothing else*. If a task is
> not on this page, it is not happening before the demo. Adding to it requires deleting something else.
>
> Scope authority: `project_context.md` remains the source of truth for *what the product is and why*.
> This file is the source of truth for *what we ship in the next 14 hours*. Where this file narrows
> `project_context.md`, the narrowing is deliberate and recorded in §6.

---

## 0. Run it

```bash
# The full rehearsed path: five choices as Dexter, then the same branch as Deborah.
uv run story-engine play --auto --turns 5 --replay-as deborah

# Play it yourself (prompts for each choice).
uv run story-engine play --as dexter --turns 5 --replay-as deborah
```

**No API key is needed.** Beats are replayed from `ScriptedLLM`, so the demo cannot be broken on
stage by a timeout, a rate limit, or an unlucky sample. Canon is seeded live from
`data/external/Darkly-Dreaming-Dexter-1.pdf`, so every receipt shown is the book's own words.

**What to watch.** Run it as Dexter, then read the replay. Turn 0 as **Dexter** narrates the Dark
Passenger and Harry's code with *3 facts withheld*. Turn 0 of **the same branch** as **Deborah**
reads *"stands at the edge of the moment with nothing to go on"* with *10 facts withheld*. That gap
is the product.

---

## 1. The demo, beat by beat

This is the whole artifact. Every task in §3 exists to serve one of these beats.

| # | Beat | What the judge sees |
|---|---|---|
| 1 | **Shelf** | The Dexter novel, on screen, with a real fact count from a real ingested book. |
| 2 | **Cast** | Five characters. Player picks one — say Dexter. |
| 3 | **Scene** | The current scene, rendered from *that character's* filtered view. |
| 4 | **Act** | Player types what they want to do, free-form. |
| 5 | **Branch** | The system grounds that intent in a divergence real fan-fiction actually wrote. |
| 6 | **Ripple** | Every cast member updates. **Those present learn it. Those absent do not.** |
| 7 | **Compound** | Repeat 3–6. State at step N correctly reflects choices 1…N−1. |
| 8 | **Receipt** | "Every fact is checked" — show the canon fact and where in the novel it came from. |
| 9 | **The closer** | Replay the *same branch* as Debra. She visibly does not know what the room just watched happen. |

**Beat 6 is the product.** Beats 1–5 set it up, 7–8 substantiate it, 9 lands it. If we are choosing what to
polish, we polish 6 and 9.

---

## 2. What already exists (do not rebuild)

Confirmed by reading the code on 2026-07-25, not by trusting the docs.

| Asset | Where | State |
|---|---|---|
| **Canon Kernel** — tri-temporal `Fact` rows, forks + lineage, atomic supersession | `adapters/outbound/persistence/canon_store.py` | ✅ built, 286 tests |
| **Graph projection** — derived adjacency, cycle-safe BFS, guard applied at construction | `domain/graph.py` | ✅ built |
| **Vector lane** — semantic recall, guard as **pre**-filter, `EmbedderPort` | `persistence/vector_store.py`, `embedding/hashing_embedder.py` | ✅ built |
| **Working memory** — bounded per-character packet, character is a **parameter** | `services/working_memory.py` | ✅ built |
| **Spoiler guard** — ONE predicate, three consumers | `domain.models.canon.is_visible` | ✅ built |
| **Fan-fic scraper + Branch Oracle + wiki entity index** | `services/fanfic_harvest.py`, `domain/fanfic_premise.py` | ✅ built, IV&V'd |
| **Frontend shell** — 6 screens, shadcn, i18n, Playwright | `frontend/` | ⚠ built to the *superseded* PRD, on mock data |

### The one architectural rule that protects the demo

There is **one store and two derived lanes** — not three databases. The canon store is the single source of
truth; the graph and the vector index are projections over it. All three read paths route through the same
guard predicate.

**Do not add a fourth read path.** An unguarded lane beside a guarded store is a spoiler side-channel, and
graph traversal is exactly how you would reach a withheld fact. This is what breaks beat 6 live on stage.

**Corollary — do not give each character its own memory store.** Per-character memory already exists as a
*filtered view* over one world state (`Fact.knower_scope` + `store.visible_to()`). Five separate stores would
violate `project_context.md` §4.4 and turn beat 9 from a toggle into a rewrite.

---

## 3. What we build

Ordered by dependency. Estimates are build time, not wall-clock.

### T0 · Regenerate data — 30 min
`data/` contains only `.gitkeep`. The Dexter corpus and the 314-entity wiki index lived in the scraper
worktree (gitignored, now deleted). Re-run:

```bash
uv run story-engine harvest    "Dexter" --kind novel --show-branches
uv run story-engine wiki-index "Dexter"
```

Blocks: T5. Regenerable in minutes — a step, not a loss.

### T1 · LLM adapter + first prompt — 1.5 h
Nothing in this repo can render a sentence today. Only `stub_llm.py` exists; `prompts/` holds a README.

- Real adapter behind the existing `LLMPort` (`ports/llm.py`) in `adapters/outbound/` — logs tokens + cost,
  always sets `max_tokens`. Add the SDK dep to `pyproject.toml`.
- `prompts/render_scene/v1.jinja` — prompts are versioned assets, never string literals (hard constraint #4).

Blocks: everything that produces text. **Widest-reach unblocker on the list — do it first.**

### T2 · Novel ingestion — 3 h · *runs parallel to T1*
PDF → chapters → chunks → `Fact` rows carrying `Provenance(source_id, chapter, char_span, verbatim)`.

- **Reference:** `patchy631/ai-engineering-hub/notebook-lm-clone` (see `BACKLOG.md:199–237`).
  **TAKE:** PyMuPDF page-accurate parsing, and citation metadata threaded through chunking into retrieval
  results. Page-accurate extraction is exactly how a citation survives back to source — it *is* the receipt.
  **LEAVE:** Zep (no epistemic scope — we already built the better-fitted layer), Milvus, Streamlit, Kokoro.
  ⚠ **No stated license.** Maintainer has accepted this risk for a non-distributed hackathon artifact.
- Write through a single `CanonIngestService` that pairs the canon-store write and the vector-index write as
  **one unit of work** (already specced, `BACKLOG.md:51`). Two independent writes drift.

Serves beats 1, 3, 8. **Open: the PDF path is not yet known — see §7.**

### T3 · Knowledge propagation — ✅ **DONE (session 7)** ⚠ *was the load-bearing task*
Built as `domain/propagation.py` + `CanonStorePort.record_learning`. 24 tests. The invariant that
governs it: **propagation is monotonic** — it may add a knower or move an acquisition earlier, never
remove a knower or delay one, and it is enforced at the store boundary as well as in the domain,
because losing a knower is silent at read time. An **untracked fact stays untracked**: attaching a
scene's witnesses to a fact everyone can see would *narrow* it, which is the inverse of learning.

<details><summary>original plan</summary>

Derive `knower_scope` from `Scene.witnesses` so knowledge compounds across turns. KB-13's unbuilt half.

Present at the scene → learns it. Absent → does not, until told or able to infer.

This single task is simultaneously the ripple (beat 6), the butterfly effect (beat 7), per-character memory,
and the setup for the closer (beat 9). It is `project_context.md` §4.2 — the stated acceptance condition for
the entire build.

**If exactly one thing gets built well today, it is this.**
</details>

### T4 · Turn loop — ✅ **DONE (session 7)**
`services/playthrough.py`. Five choices deep against a real store, with a restart, proving the
acceptance condition per character. Exactly one model call per turn, and it decides nothing.
Also delivered **T7** (the citation receipt) and **T8** (`replay_as`) — both fell out of the loop
rather than needing their own passes.

<details><summary>original plan</summary>

`PlaythroughService`: assemble character view → offer branch → apply choice to world state → recompute
witnesses → propagate → render next scene. One narration call per turn; state transitions deterministic in
code, never inferred by the model (§4.4).

Closes M2, M3, M6. Serves beats 2, 3, 7.
</details>


### T5 · Branch Oracle → canon moment binding — 2 h
The oracle mines divergence points but cannot yet cite a canon scene — our own contract says so. Bind mined
branch points to resolvable canon moment ids so the options at a decision point are *real* fan-fiction
divergences, not invented ones.

Closes M4. Serves beat 5.

### T6 · Free-form intent router (snap-to-branch) — 2 h
Player types anything. We ground it in a validated branch:

1. Embed the input — `EmbedderPort` and the vector store already exist.
2. Match against branch options mined at the current decision point.
3. **Above threshold** → route to that pre-validated branch. Free-form feel, engine on rails.
4. **Below threshold** → generate a candidate branch, verify against canon, *then* apply.

Step 4 is also OD-4's missing degradation path, which is needed regardless.

Serves beats 4–5. Pitch line: **"Say anything — we ground it in what fan-fiction actually wrote."**

### T7 · Receipt surface — 1 h
Display the canon fact a claim was checked against, plus its source location. Nearly free once T2 lands
provenance-carrying facts. Must distinguish **intentional divergence** (a consequence the player chose —
expected) from **accidental contradiction** (drift nobody chose — flagged). A verifier that flags every
divergence is useless here; deliberate canon-breaking is the genre.

Closes M7. Serves beat 8.

### T8 · Replay as another character — 45 min
Re-render the completed branch from Debra's view. Mechanism is near-free given the renderer already takes a
character as a parameter; only the toggle is work.

Serves beat 9 — **the strongest single beat available, and the cheapest.** Do not let it fall off the end.

### T9 · API + frontend rewire + rehearsal — 3 h
- Expose the turn loop; the frontend's `CanonClient` currently targets the superseded single-flip contract
  (`getMoments` / `postDivergence` / `postRegenerate`) while the backend serves `/episodes`.
- `NEXT_PUBLIC_USE_MOCK=false` flips mock → live at one seam. **Keep the mock working as the stage fallback.**
- Rehearse the run end to end at least twice.

### T10 · Fix the broken verification commands — 20 min
Several `feature_list.json` entries verify with `-m unit -k …`, which selects nothing (AUD-M3), so those
features can never flip to `passing` however good the code is. Repair the commands.

**Total: ~18 h against ~14 h of runway.** That gap is why §5 exists.

---

## 4. Critical path

```
T1 (LLM) ─┬─────────────────────────────► T4 (turn loop) ──► T9
T2 (novel)┘                             ↗
T3 (propagation) ───────────────────────┘
T0 (data) ──► T5 (oracle binding) ──────┘
                                          T6, T7, T8 attach to T4
```

T1 and T2 are independent — run them in parallel. **T3 is on the critical path and has no substitute.**

---

## 5. The cut ladder

When we fall behind, we drop from the top of this list. Decided now, in the cold, so it isn't decided at
3 a.m. in a panic.

| Order | Drop | Cost of dropping |
|---|---|---|
| 1 | S1 audio, S2 ripple graph | None — already SHOULD-tier |
| 2 | **Free-form (T6)** → bounded options | UI keeps a text box mapped to preset options. Loses interactivity, keeps the proof. |
| 3 | 10 choices → **5** | None. §4.1 already says 10 is a ceiling, not a target; §8 needs ≥5. |
| 4 | 5 characters → **2** (Dexter + Debra) | Small. Debra is non-negotiable — she is the closer. |
| 5 | Novel ingestion (T2) → seed canon from the **wiki index** instead | Receipt cites a wiki page rather than a novel page. Weaker, still a real receipt. Saves ~2 h. |

**Never cut:** T3 (propagation) · T4 (turn loop) · T8 (replay as Debra). Those three *are* the demo.

---

## 6. Explicitly NOT building

Restated so it is never re-litigated mid-build.

- **Self-improving agent loop.** Improves output across many runs; we have one five-minute demo. No judge can
  observe it and its cost is unbounded. Revisit after the demo path is green.
- **Per-character agents** (one LLM call per character). ~6× cost, no epistemic gain — the guarantee comes
  from what is absent from the assembled context, not from instructing a model to withhold (§4.4).
- **A separate graph database.** The graph is a projection. A service dependency also breaks the offline
  constraint.
- Creator surface · Plot Hole Hunter · multi-novel support · accounts, saves, sharing · auto-repair of
  flagged contradictions (flag only) · real Pocket FM catalog integration.

---

## 7. Open — blocking, needs a human answer

| # | Question | Blocks | Recommendation |
|---|---|---|---|
| **D-1** | **Where is the Dexter novel PDF?** Not in the repo — `data/` holds only `.gitkeep`. | T2 (3 h, long pole) | Provide the path, or we fall to cut-ladder #5 and seed canon from the wiki index. |
| **D-2** | **Snap-to-branch, or true free-form generation?** | T6 | **Snap-to-branch.** True free-form puts unvalidated generation on stage in the one demo whose thesis is that we solved incoherence. |
| **D-3** | Novel canon or screen canon (OD-2)? The wiki proves 3 of 5 cast members have different novel names — Debra→Deborah, Doakes→Albert, LaGuerta→Migdia. | T2, T5 | Decide, do not discover. Screen canon has far denser fan-fiction. |
