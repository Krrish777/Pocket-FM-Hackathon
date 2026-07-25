# Session Handoff

> The single per-session **clock-out** note. At session start read this first, then `PROGRESS.md` and
> `DECISIONS.md`. Two sessions ran in parallel on 2026-07-25 and both clocked out here: **Session A**
> (product definition) and **Session B** (EXT-1 scraper). **Session B is the most recent.**

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

## Session B — 2026-07-25 (EXT-1: fan-fiction scraper → Branch Oracle) ← MOST RECENT

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
