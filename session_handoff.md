# Session Handoff

> The single per-session **clock-out** note. Overwrite at the end of each session. At session start, read
> this first, then `PROGRESS.md` and `DECISIONS.md`. Keep it short.

## Last session — 2026-07-25 (session 5, THE BRIEF LANDED → problem statement selected)

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

### Ideas established this session that neither prior doc had
1. **Fan-fiction is the branch oracle** — a third path past the dead end where hand-authored branches are
   unaffordable (Until Dawn) and generated branches are incoherent (AI Dungeon). Branches pre-authored by the
   crowd, free, audience-filtered, dense at the moments that matter.
2. **Intentional divergence ≠ accidental contradiction.** Fan-fiction breaks canon *on purpose*; a verifier
   that flags every divergence is useless. This distinction *is* the product.
3. **Protagonist-ness is a rendering choice, not a stored property** — which makes Infinite Story Universe
   nearly free and unlocks the closing demo beat: replay the same branch as Debra, who visibly does not know
   what the audience just watched happen.

### Next step (resume here)
**M8 — the uniform character state schema.** Build it first: it is the only decision expensive to retrofit,
and M5 + S3 both depend on it. Spec: `project_context.md` §4.4. In parallel, chase **OD-3** (the EXT-1 scraper
output contract) — it is the highest-risk unknown and blocks M1/M4.

### Warnings for whoever picks this up
- **The git index is shared across parallel sessions.** I staged 4 files for review; a parallel session then
  committed the entire index as `8d70e1b` "regular updates" (164 files). Staging is not a safe hold — only an
  uncommitted working tree is. Coordinate before staging.
- **Never pipe `make check` into `tail`/`head`** — you get the filter's exit code, and a red gate reads as
  green. It bit me this session. Redirect to a file, check `$?`.
- **OD-2 is a real trap:** our KB is novel-based, Dexter fan-fiction is largely screen-based. Decide it before
  ingesting anything, don't discover it at hour 20.

### State at clock-out
`make check` GREEN (exit 0, 7 passed) · INIT-01…05 + HARDEN-01…04 pass · HARDEN-05 deferred below product work ·
all M/S features `passes:false` · **uncommitted, awaiting the maintainer's permission to commit.**
## Last session — 2026-07-25 (session 5, IN-EVENT: fan-fiction scraper)

**Framing:** First in-event session. The brief LANDED and lives in the `Pocket FM Hack` vault
(`_PROBLEM STATEMENT (official).md`, `_PROBLEM VERDICT (evidence-selected).md`) — **not yet copied into
`CLAUDE.md`, so INIT-01 is still failing.** Chosen surface: **P1 · Infinite Story Universe**. Maintainer
scoped this session to exactly one deliverable: *a scraper that takes a novel/film and saves its relevant
fan fiction.* The knowledge base and the scraper→KB wiring are explicitly a **different branch, next session**.

**Where the work is:** worktree `.claude/worktrees/reddit-fanfic-scraper`, branch
`worktree-reddit-fanfic-scraper`. **Nothing committed** (permission not given).

**What I did (all verified):**
- **Measured before building.** 4 parallel research agents + live network probes. Finding that redirected the
  build: **Reddit does not hold fandom fanfic prose** (fandom subs median selftext 141–620 chars; r/FanFiction
  Rule 1 bans fic text), and **AO3 + fanfiction.net are Cloudflare-blocked**. **Wattpad is reachable keyless
  and has both fandom search and full chapter prose.** Full evidence tables:
  `docs/superpowers/specs/2026-07-25-fanfic-harvest-design.md`.
- **Built `FANFIC-01`** hexagonally: pure `domain/fanfic_quality.py` + `domain/models/fanfic.py`;
  `FanficSourcePort`/`AliasExpanderPort`/`CorpusSinkPort`; `WattpadSource`, `WikipediaAliasExpander`,
  `JsonlCorpusSink`, shared `http_util`; `FanficHarvester` service; `story-engine harvest` CLI. 37 feature tests.
- **`make check` GREEN** — ruff + format + mypy strict (55 files) + **44 tests**.
- **`FANFIC-02` verified live:** `harvest "The Witcher"` → 18 aliases, 1 work / 3 chapters / **4,073 words** of
  real Witcher prose → `data/raw/fanfic/the-witcher/{stories.jsonl,manifest.json}` (gitignored).
- **Two bugs the first live run exposed, both fixed:** Wikimedia 403s any UA lacking a contactable URL/email
  (silently killing alias expansion) → `STORY_ENGINE_CONTACT`; and `min_alias_hits=2` was unsatisfiable with a
  one-term query, rejecting 20/20 → `required_alias_hits()` clamps to the available surface.

## Session 5c — Branch Oracle, OD-2 discriminator, EXT-1 contract (3 parallel agents)
`project_context.md` landed on main mid-session and is the SSOT. It reframed the deliverable: section 5.2 says
fan fiction is "a source of branch structure only", never reproduced as prose. **We are EXT-1** in its section 9,
whose contract was UNDEFINED and flagged the highest-risk integration.

- **FANFIC-04 Branch Oracle** — `domain/fanfic_premise.py` + `domain/prose_score.py`. Mines canon decision
  points with 2-4 player-facing options. Live Titanic: `character_survives:jack` support=3 -> 4 options from
  3 independent authors. Option labels synthesized, never copied (test-enforced).
- **FANFIC-05 OD-2** — wiki entity vocabulary + novel/screen discriminator. 314 Dexter entities:
  novel 68 / screen 223 / both 9 / unknown 14. **Found that 3 of the 5 spec cast have different NOVEL names:
  Debra->Deborah Morgan, Doakes->Albert Doakes, LaGuerta->Migdia LaGuerta.**
- **FANFIC-06 EXT-1 contract** — `docs/EXT-1-scraper-output-contract.md`, closes OD-3.
- **AO3 source** — only source that distinguishes canon (`Dexter Series - Jeff Lindsay` vs `Dexter (TV)`).
  Traps: no Hits/Kudos so read/vote floors reject it (CLI auto-relaxes); dataset licence is NONE.
- **Full depth** — `--max-chapters` default 500; Dexter 13 -> 43 chapters / 55,769 words.
- **CLI** — `harvest` (new flags), `branches`, `wiki-index`.
- **Collision averted:** `worktree-knowledge-base` already owns `domain/models/canon.py` + 11 enums; our work
  re-pathed to `wiki_index.py` / `adapters/outbound/wiki/` and shares NO Python types with it.

## State
`make check` green (**237 tests**, mypy strict on 68 files). INIT-02…05, HARDEN-01…04, **FANFIC-01…06** pass.
HARDEN-05 deferred. **INIT-01 is closed by `project_context.md` section 12** but its grep verification still
points at the old CLAUDE.md marker — re-point it.

## Session 5b — analyst evaluator loop (same session, after the first handoff draft)
Ran the maintainer's requested loop on **Dexter (novel)** and **Titanic (movie)**, reviewing output as a
fan-fiction analyst and fixing what the data exposed. Six fixes, each driven by a specific misclassification:
1. **Round-robin alias search** (was exhausting term #1; 18 aliases discovered, 1 queried). Candidates 20 -> 40.
2. **Wikipedia-search title resolution + `--kind`.** Films disambiguate by YEAR, so suffix guessing could never
   reach `Titanic (1997 film)`. Before: "Dexter" -> `USS Dexter` (warship), "Titanic" -> the ship,
   "The Avengers" -> 1960s spy series. After: `Dexter Morgan`, `Caledon Hockley`, `TARS`.
3. **Alias noise filter + variant ranking** (dropped "List of box office records…", "Anti-Harry Potter
   community"; demoted typos like "Hairy potter" behind real entities).
4. **Tag-key + word-boundary alias matching.** Substring matching failed BOTH ways: tag `dextermorgan` missed
   the alias "Dexter Morgan", while "dexter" wrongly matched inside `dextercharming` (Ever After High).
5. **Explicit-declaration rule** — "…: A Dexter Fanfiction" is admitted on its own; adjacency required so
   "Dexter ▷ Scott Summers" (X-Men) stays out.
6. **Corpus-quality gates** — mature excluded by default, read/vote floors (killed a 54-read joke fic),
   sentence-level disclaimer + byline stripping (0 leaks corpus-wide afterwards).

**Result:** Titanic 10 works / 21 chapters / 23,830 words; Dexter 4 works / 13 chapters / 19,104 words.
Precision spot-check 6/6 Dexter, 8/8 inspected Titanic. 59 tests green, FANFIC-03 now passes.

## Next step (in priority order)
1. **Maintainer benchmark review.** The agreed loop: maintainer names a film/novel, inspects every generated
   file against their benchmark, sends corrections, iterate. Run `story-engine harvest "<title>"` and hand over
   `stories.jsonl` + `manifest.json`.
2. **INIT-01:** copy the official problem statement into `CLAUDE.md` and seed product features.
3. Near-duplicate dedup (MinHash) — only exact SHA-256 dedup exists today.
4. Ask before committing.

## How to resume
```bash
cd ".claude/worktrees/reddit-fanfic-scraper"
make check                                  # expect green, 59 tests
uv run story-engine harvest "Dexter" --kind novel  --max-stories 10 --max-chapters 4
uv run story-engine harvest "Titanic" --kind movie --max-stories 10 --max-chapters 4
# --kind is effectively REQUIRED: without it, "Titanic" resolves to the ship, not the film.
# then read data/raw/fanfic/<slug>/manifest.json and stories.jsonl
```
Read `docs/superpowers/specs/2026-07-25-fanfic-harvest-design.md` before changing sources or thresholds — it
holds the measurements, so you don't re-derive (or contradict) them.
