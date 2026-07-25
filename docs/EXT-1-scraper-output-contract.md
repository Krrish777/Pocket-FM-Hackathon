# EXT-1 — Fan-Fiction Scraper Output Contract

> **Purpose:** closes **OD-3** in [`project_context.md`](../project_context.md) §11, which states the EXT-1
> output contract "must be obtained, not guessed" and is "**Needed by: Immediately**". §9 calls EXT-1
> "the highest-risk integration in the project".
>
> **Owner:** this repo/branch (`worktree-reddit-fanfic-scraper`) — I am EXT-1.
> **Consumer:** the Canon Kernel / Branch Oracle side (`worktree-knowledge-base`).
> **Status:** CONFIRMED against the implementation on 2026-07-25. Corpus artifact is schema **1.1**;
> wiki-index artifact is schema **1.0**. Nothing here is inferred: unknowns are stated as unknown.

---

## 1. The four §9 questions, answered

`project_context.md` §9 lists four unchecked boxes. Answering them is this document's job.

| §9 question | Answer |
|---|---|
| **What it emits** | Files on disk. Two artifact families: (a) a **work corpus** — one JSON object per fan-fiction work, with metadata, provenance and prose; (b) **branch structure** — premise/divergence objects derived from those works. Not a database, not an API. |
| **Which canon it scrapes** | **Currently screen-leaning, and this is a live hazard.** Wattpad (the primary source) carries no novel-vs-screen marker at all. See §5 — this is OD-2 and it is NOT yet closed. |
| **Delivery mechanism** | Local files under `data/raw/` (gitignored), JSONL + a `manifest.json` per fandom. Consumer reads them directly; no service to call. |
| **Whether it links divergences back to specific canon moments** | **Partially — and closing this needs something from the consumer.** See §6. Today a divergence names its focal canon *entities*; it cannot cite a canon *scene* because scene identity is owned by the Canon Kernel. |

---

## 2. Why fan-fiction prose is delivered but must not be reproduced

`project_context.md` §5.2 constrains this precisely:

> "fan-fiction supplies *what the options are*. It is **not quoted, reproduced, or used as generated prose.
> It is a source of branch structure only.**"

The corpus therefore ships prose **for provenance and derivation only**. Consumers may read it to derive
structure and to satisfy §5.4's citation requirement. Consumers must **not** feed it to a model as prose to
imitate, nor surface it to a player. The scraper cannot enforce this; it is a contract term.

Corollary: **volume is not the goal.** A 918-word abandoned fic that establishes "Dexter doesn't kill Brian"
is a complete, high-value branch record. Corpus size is not a quality measure for this integration.

---

## 3. Artifact layout

```
data/raw/fanfic/<fandom-slug>/
    stories.jsonl      one JSON object per work, newline-delimited, UTF-8
    manifest.json      run-level metadata (see §3.2)
```

`<fandom-slug>` is the lowercased fandom name with non-alphanumerics collapsed to `-`
(e.g. `Dexter` → `dexter`, `The Witcher` → `the-witcher`).

JSONL, not a JSON array, so the consumer can stream one work at a time without loading the corpus.

### 3.1 `stories.jsonl` — per-work record

Settled fields (stable — safe to build against):

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Contract version; see §7. |
| `source` | string | Host the work came from: `wattpad`, `ao3`, `reddit`, `local`. |
| `source_id` | string | Host-native id. `(source, source_id)` is the **primary key**. |
| `title` | string | Work title as published. |
| `author` | string | Host username. Retained for attribution and deletion requests. |
| `url` | string | Canonical URL of the work — the citation target. |
| `description` | string | Author's blurb. **The richest branch-structure signal**; premises are usually stated here. |
| `tags` | string[] | Host tags, lowercased as published (hosts strip spaces: `dextermorgan`). |
| `language` | string | Two-letter code, best effort. |
| `completed` | bool | Host's completion flag. `false` means the branch is abandoned mid-story. |
| `mature` | bool | Host's mature flag. **Self-reported and unreliable** — see §5. |
| `reads`, `votes` | int | Host popularity counters. `0` where the host has no such concept (AO3). |
| `num_chapters_reported` | int | Chapter count the host claims, which may exceed chapters delivered. |
| `total_words` | int | Sum of delivered chapter word counts. |
| `relevance.alias_hits` | string[] | Which fandom aliases matched — the evidence this work belongs to this fandom. |
| `relevance.score` | int | Count of distinct alias hits. |
| `chapters[]` | object[] | `{index, source_id, title, word_count, text}`, in reading order. |

`chapters[].index` is the work's own 1-based ordering and **may contain gaps**, because non-prose parts
(forewords, author notes) are filtered out while the original ordering is preserved. Do not assume
`index == position in array`.

**Schema 1.1 additions — CONFIRMED.** Every 1.0 field above is unchanged, so a 1.0 reader keeps working.
Both new blocks are nullable: `null` means the producer did not compute them, which is different from
"computed and found nothing".

| Field | Type | Meaning |
|---|---|---|
| `premise` | object \| null | `{key, label, tropes[], focal_entities[], decision_point, alternate_path, evidence[]}` — the Branch Oracle signature for this work. `decision_point` is the canon-side question ("Whether Brian dies, as canon has it"); `alternate_path` is what this work did instead ("Spare Brian — Brian lives, building a family"). Unclassifiable works get `key="unclassified"` and `alternate_path="UNVERIFIED — no divergence detectable from the blurb"` rather than being dropped. |
| `prose_quality` | object \| null | `{score, word_count, components[{name,value,weight,detail}]}`. `score` is `100 × Σ(wᵢ·cᵢ)`, each component bounded `[0,1]`, weights summing to 1. Ranking aid, **not** a relevance signal. |

`canon_basis` is **not yet emitted on corpus records** — see §5. Where canon basis is available today it lives
in the wiki-index artifact (§3.3) and, for AO3-sourced works, in the raw host labels carried on `tags`
(`ao3_fandom:<raw Fandom>`, `ao3_characters:<raw Characters>`).

### 3.3 Manifest branch-structure blocks (schema 1.1)

The manifest is where the **player-facing unit** lives, because branch points are corpus-level, not
per-work:

| Block | Meaning |
|---|---|
| `branch_points[]` | `{key, decision_point, tropes[], focal_entities[], support, options[]}`. Each `options[]` entry is `{label, is_canon, support, sources[]}`. Exactly one option has `is_canon: true` — the "let canon stand" baseline. **This is the 2–4 choice set `project_context.md` §4 step 3 consumes.** |
| `premise_groups[]` | `{key, label, size, members[], member_titles[]}` — works sharing one canon decision point, i.e. N independent human branches off one node. `members[]` holds `<source>:<source_id>` handles. |
| `prose_quality` | `{scored_works, min, median, max, scale}`. |
| `ordering` | `"prose_quality_score_desc"` or `"harvest_order"`, determined by **inspecting** the file rather than trusting a flag. |
| `branch_oracle_note` | States the §5.2 constraint in the artifact itself. |

**Option labels are synthesized from the premise taxonomy and are never copied from author text** — a unit
test asserts no option label appears in its source blurb. Verbatim snippets appear only in
`premise.evidence`, documented as audit provenance for §5.4 citations.

Worked example (real output, Titanic, 10 works):

```
character_survives:jack   support=3
  decision_point: "Whether Jack dies, as canon has it"
    is_canon=true   "Let canon stand — Jack dies"
    is_canon=false  "Spare Jack — Jack lives, carrying on past the canon ending"
    is_canon=false  "Spare Jack — Jack lives, carrying on past the canon ending, building a family"
    is_canon=false  "Spare Jack — Jack lives, displaced in time"
```

Three independently authored works, one canon decision point, four legal options.

### 3.4 Wiki entity-vocabulary artifact (separate, schema 1.0)

```
data/raw/wiki_index/<fandom-slug>/
    entities.jsonl
    manifest.json          artifact_kind: "wiki_entity_vocabulary"
```

**This is NOT a canon knowledge base and must not be ingested as canon facts.** Values are recorded as
*observations* with provenance ("observed on page X"), never as assertions. Per record:
`schema_version`, `natural_key` (`<source>:<fandom-slug>:<kind>:<lowercased name>`, stable across runs —
deliberately **not** an `id`), `canonical_name`, `aliases[]`, `type`, `status`, `canon_basis`,
`canon_basis_evidence[]`, `summary`, `prominence`, `relationships[]`, `attributes[]`, `provenance[]`.

`id` and `fork_id` are **deliberately absent** — identity and fork semantics belong to the consumer
(§11 OD-1) and this producer will not prejudge them. `relationships[].target` is an **unresolved name
string**, not a reference; resolve it with the Canon Kernel's own `CanonEntity.matches_name()`.

### 3.2 `manifest.json` — per-run record

`schema_version`, `fandom`, `harvested_at` (UTC ISO-8601), `story_count`, `chapter_count`, `total_words`,
`sources[]`, `corpus_file`, `usage_note`. The manifest is the integrity check: if `story_count` disagrees
with the line count of `stories.jsonl`, the run was interrupted — treat the corpus as suspect.

---

## 4. Guarantees, and explicit non-guarantees

**Guaranteed:**
- Every record carries `source`, `source_id`, `url`, `author` — so any passage is traceable and deletable,
  satisfying the provenance requirement in §5.1 and the citation requirement in §5.4.
- `(source, source_id)` is unique within a corpus file.
- Exact-duplicate chapter text is removed (SHA-256 over normalised text).
- Non-prose parts (forewords, disclaimers, bylines, author notes) are stripped before delivery.
- UTF-8 throughout.

**NOT guaranteed — design around these:**
- **No near-duplicate detection.** Reposts and chapter-in-full-work overlaps survive. (MinHash was assessed
  and deliberately skipped at current corpus scale.)
- **Not idempotent across runs.** Host search ranking shifts, so a re-run may return a different set. The
  corpus file is overwritten. Snapshot it if reproducibility matters.
- **Chapter coverage may be partial** — capped by the caller. Compare `total_words` against
  `num_chapters_reported`.
- **No completeness claim.** For any fandom the scraper returns what the reachable hosts surface, not the
  population. Measured example: the entire Wattpad Dexter fandom is **6 relevant works**.

---

## 5. Open hazards the consumer must know

**OD-2 — novel vs screen canon. NOT CLOSED.** `project_context.md` §6.4 states the knowledge base is built
from the **novels** while Dexter fan-fiction is predominantly **screen**-based, and calls this "a silent
corruption path". Current status:
- Wattpad exposes **no** canon marker. Works harvested from it are effectively canon-unknown.
- AO3 metadata *does* distinguish canons in its `Fandom` string (it uses forms like
  `Harry Potter - J. K. Rowling` vs `Teen Wolf (TV)`), so the AO3 source may be able to classify.
- A wiki-derived novel-vs-screen discriminator is under construction.
Until `canon_basis` is populated and trusted, **the consumer must assume `unknown` and must not treat a
branch as novel-canon-safe.**

**Mature-content flag is unreliable.** `mature` is the host's self-report. A harvested Titanic work with
`mature: false` had a sexually explicit blurb. Do not rely on this field for a player-facing surface.

**Screen-canon entity names differ from novel names.** §6.3 warns character details diverge between novel and
screen. Names in `relevance.alias_hits` derive from Wikipedia/host tags, so they may be screen forms. Resolve
them through the Canon Kernel's own entity resolution; do not treat them as canonical.

---

## 6. What EXT-1 needs FROM the consumer (two-way dependency)

§9's fourth question — does the scraper link divergences to specific canon moments? — cannot be fully
answered by me alone, and this is the one place the contract is genuinely bidirectional.

A branch record can name the canon **entities** it turns on (e.g. `Brian Moser`, `Dexter Morgan`). It cannot
emit a canon **scene** reference, because scene identity lives in the Canon Kernel: the parallel branch
defines `Scene` with `id`, `fork_id`, `chapter: ChapterIndex`, `order_in_chapter`, and a `witnesses` set.

**Request:** expose a stable, resolvable identifier for canon moments — minimally
`(chapter, order_in_chapter)` or a documented `Scene.id` scheme — plus a name-resolution entry point
(the existing `CanonEntity.matches_name()` is exactly right). Given those, the scraper can emit
`diverges_from: <scene ref>` per branch and the Branch Oracle becomes directly queryable by canon moment,
which is what §4 step 3 needs.

**Until then:** branch records are keyed by entity and premise only, and the consumer must do the
moment-matching. This is the single largest remaining integration gap.

---

## 7. Versioning

`schema_version` / `CORPUS_SCHEMA_VERSION` lives in
`src/story_engine/adapters/outbound/fanfic/jsonl_sink.py` and is the authority.

- **Patch/minor** — additive fields only. Consumers must ignore unknown fields.
- **Major** — a field is removed, renamed, or changes meaning. Requires updating this document in the same
  change.

If this document and the code disagree, **the code is authoritative and this document is a bug.**

---

## 8. Reproducing a corpus

```bash
# --kind is effectively REQUIRED: without it "Titanic" resolves to the ship, not the film,
# and "Dexter" resolves to a warship (USS Dexter).
uv run story-engine harvest "Dexter"  --kind novel --max-stories 10
uv run story-engine harvest "Titanic" --kind movie --max-stories 10
```

Design rationale, measurements, and the evidence behind every threshold are in
[`docs/superpowers/specs/2026-07-25-fanfic-harvest-design.md`](superpowers/specs/2026-07-25-fanfic-harvest-design.md).
Read it before changing sources or thresholds.
