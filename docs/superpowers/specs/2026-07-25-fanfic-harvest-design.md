# Fanfic Harvest — Fandom-Targeted Fan-Fiction Corpus Builder

- **Date:** 2026-07-25
- **Status:** approved by maintainer (explicit hand-over), built same session
- **Branch:** `worktree-reddit-fanfic-scraper`
- **Feature ID:** `FANFIC-01`

## 1. Purpose

Given a **fandom** (a novel, film, or series — e.g. "The Witcher", "Percy Jackson"), produce a
local, deduplicated corpus of **fan-fiction prose with chapter structure**, to serve as the base
canon and what-if reference material for the **P1 · Infinite Story Universe** demo (side characters
gain persistent memory and become protagonists of their own arcs without breaking continuity).

## 2. Evidence that shaped this design

All figures measured live on 2026-07-25, not assumed.

### 2.1 Reddit does not hold fandom fan-fiction prose

Prose density, n=100 recent posts per subreddit via the Arctic Shift archive
(`%` = posts whose selftext exceeds 2,000 chars):

| Subreddit | median chars | >2000 chars | dominant flairs |
|---|---|---|---|
| r/HFY | 13,253 | **96%** | `OC-Series`, `OC-OneShot` |
| r/redditserials | 10,799 | 77% | `Science Fiction`, `Fantasy` |
| r/shortstories | 7,343 | 77% | `Horror`, `Realistic Fiction` |
| r/FanFiction | **463** | **8%** | `Lost Fic`, `Discussion`, `Recs Wanted` |
| r/HPfanfiction | 401 | **3%** | `Request`, `Find That Fic` |
| r/Dramione | 236 | **0%** | `Recs Wanted`, `Help me ID this fic` |

The inversion that matters: **fandom subs carry fandom signal but no prose; prose subs carry prose
but no fandom signal.** Cross-sections are near-empty (r/shortstories + "Percy Jackson" = 6 hits;
r/redditserials = 0). r/FanFiction Rule 1 bans fic text on the front page and excerpts beyond two
sentences. A Reddit-only fandom fanfic scraper returns "does anyone remember the fic where…" and
ships nothing.

### 2.2 Host reachability from this machine

| Host | Status | Verdict |
|---|---|---|
| **Wattpad** (`api/v3/stories`, `apiv2/storytext`) | **200, JSON, no auth** | **PRIMARY** |
| SpaceBattles / SufficientVelocity / RoyalRoad | 200 | future secondary |
| Arctic Shift (Reddit mirror) | 200 | optional supplement |
| AO3 | 403 Cloudflare "Shields are up!" | blocked |
| fanfiction.net / fictionpress | 403 Cloudflare JS challenge | blocked |
| reddit.com direct | 403 `snooserv` anti-bot | API needs approval |

### 2.3 Wattpad is the answer — verified end to end

- `GET /api/v3/stories?query=witcher+geralt+fanfiction` → **369 stories**, tags include
  `fanfiction`, `ciri`, `dandelion`, `anyachalotra`
- Story objects carry `parts[]` (id + title per chapter), `numParts`, `readCount`, `voteCount`,
  `completed`, `language`, `mature`, `tags`, `categories`, `nextUrl`
- `GET /apiv2/storytext?id=<partId>` → **18,227 chars of real Witcher fanfic prose**
- Chapter structure therefore comes free — no title-regex inference needed

### 2.4 Measured prose-vs-discussion thresholds (stdlib only)

| Feature | prose subs | discussion subs | discriminative |
|---|---|---|---|
| word count | 1,677–2,316 | 100–125 | ✅ massive |
| **quote marks / 1k words** | 23–32 | **0.0** | ✅ perfect separation |
| `-ed` tokens / 1k words | 48–49 | 17–21 | ✅ ~2.5× |
| median paragraph words | 21.8 | 46.5 | ❌ **inverted** — do not use |

Gate: `words >= 500` AND `quotes_per_1k >= 5`, with past-tense density as tiebreak. Dialogue
punctuation is the single best signal, because prose breaks paragraphs on speech and discussion
posts are one long block.

## 3. Architecture

Hexagonal, per `.claude/rules/structure.md`. HTTP lives only in the adapter; all scoring is pure.

```
domain/models/fanfic.py       FandomQuery, StoryRef, Chapter, HarvestedStory   (pure Pydantic)
domain/fanfic_quality.py      prose gate, relevance, boilerplate strip, dedup key  (pure, stdlib)
ports/fanfic_source.py        FanficSourcePort (Protocol)
adapters/outbound/fanfic/
    wattpad.py                WattpadSource — httpx, the only vendor/IO module
    alias_expander.py         WikipediaAliasExpander — redirects → alias set
services/fanfic_harvest.py    FanficHarvester — orchestrates expand→search→gate→fetch→dedup
cli/main.py                   `harvest` command
```

### 3.1 Data flow

```
fandom name
  │
  ├─ 1. EXPAND    Wikipedia prop=redirects → aliases + universe terms ("Anaklusmos")
  │
  ├─ 2. SEARCH    Wattpad api/v3/stories, one query per alias, paginated
  │
  ├─ 3. RANK      relevance = tag/title/description alias overlap (>=2 distinct aliases)
  │               quality   = reads/votes/completeness floor
  │
  ├─ 4. FETCH     apiv2/storytext per part, concurrency-capped
  │
  ├─ 5. CLEAN     ftfy-style mojibake fix, strip A/N + disclaimer boilerplate
  │
  ├─ 6. GATE      words >= 500 AND quotes_per_1k >= 5
  │
  ├─ 7. DEDUP     SHA-256 of normalized text (exact); near-dup deferred
  │
  └─ 8. PERSIST   JSONL → data/raw/fanfic/<fandom>/ (gitignored)
```

### 3.2 Why relevance is lexical, not semantic

Fandom aliases are rare proper nouns. Requiring **two distinct alias hits** kills false positives
from a passing "Percy" while keeping recall. Dense embeddings blur exactly the distinctions that
matter here, and `all-MiniLM-L6-v2`'s 256-token window is far shorter than a 13,000-char story.
Embeddings and LLM classifiers are deliberately excluded.

## 4. Error handling

- Typed errors in `shared/errors.py`: `HarvestError` (base) → `SourceUnavailableError`.
- Per-story failures are logged and skipped so one bad chapter can't abort a run; the run reports
  counts. Never a bare `except`.
- HTTP: explicit timeout, retry with backoff on 429/5xx, concurrency cap.

## 5. Data posture (maintainer decision)

Local-only, `data/raw/*` already gitignored. Store source id + permalink + author with every record
so everything stays attributable and deletable. Corpus is **demo canon / retrieval input, never
training data**. On stage: "we index public serialized fiction," not "we scraped."

Recorded risk: Wattpad's ToS is not a licence to redistribute; nothing here may be republished.
Reddit's own terms bar ML-training use without permission and its API now requires manual approval
under the Responsible Builder Policy — which is why Reddit is *not* the primary source.

**Audio-specific blocker, for whoever adds a Reddit adapter later.** r/HFY Rule 5 and the
r/TheCrypticCompendium / r/Odd_directions IP rules explicitly forbid converting posted stories into
audio or ebook form without the author's stated permission. Since this project's product surface is
audio storytelling, a Reddit-sourced corpus is a licensing blocker rather than a footnote. Wattpad
sourcing does not carry this specific rule, but carries no redistribution right either.

## 6. Verification

`FANFIC-01` passes when a real run yields ≥10 relevance-passing multi-chapter stories with prose for
a named fandom, and `make check` is green.

```bash
uv run story-engine harvest "The Witcher" --max-stories 10
```

## 7. Deliberately out of scope

Offsite AO3/FFN scraping (Cloudflare-walled), headless browsers, MinHash near-dup, embeddings,
LLM relevance classification, Reddit as a prose source, the 3.8 TB Reddit torrent dumps (taken down
at Reddit's request 2026-07-24).

## 8. Tension recorded

`_PROBLEM VERDICT (evidence-selected).md` argues for a **verifier** over a generator and scores
Infinite Story Universe ★★ against Plot Hole Hunter / Story Time Machine ★★★. Infinite Story
Universe is not on that document's kill list, so this is consistent — but the corpus earns its
keep only if it feeds a continuity claim, not raw generation. Long multi-chapter fanfic with large
ensembles is also ideal adversarial input for a continuity verifier, so both faces stay open.
