"""Pure prose-quality and fandom-relevance rules.

No IO, no vendor SDKs — every function here is a deterministic text calculation, so the whole
admission policy is unit-testable offline. Thresholds are empirical: measured 2026-07-25 over 340
live posts across prose-dense and discussion-dense communities. See
docs/superpowers/specs/2026-07-25-fanfic-harvest-design.md §2.4.
"""

import hashlib
import re
import unicodedata

from story_engine.domain.models.fanfic import Chapter, FandomQuery, StoryRef

# Straight and curly double quotes, plus the CJK corner brackets some authors use for speech.
_QUOTE_CHARS = '"“”«»「」'
_QUOTE_RE = re.compile(f"[{re.escape(_QUOTE_CHARS)}]")
_PAST_TENSE_RE = re.compile(r"\b\w+ed\b", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_WORD_RE = re.compile(r"[a-z0-9]+")
_LEADING_ARTICLES = frozenset({"the", "a", "an"})
# "A Dexter Fanfiction", "[Dexter Fanfiction]", or the tag `dexterfanfiction` — a self-declaration.
_FANFIC_MARKER = r"(?:fan\W*fictions?|fan\W*fics?|fics?)"

# Author-note and cross-promotion boilerplate. Anchored per-line: these are conventionally their own
# line, and anchoring avoids eating dialogue that merely contains the words.
_BOILERPLATE_LINE_RES = (
    re.compile(r"^\s*a\s*/\s*n\s*[:.-]", re.IGNORECASE),
    re.compile(r"^\s*author'?s?\s+note\s*[:.-]", re.IGNORECASE),
    re.compile(r"^\s*(?:disclaimer|warning)\s*[:.-]", re.IGNORECASE),
    re.compile(r"^\s*i\s+(?:do\s+not|don'?t)\s+own\b", re.IGNORECASE),
    re.compile(
        r"\bread\s+(?:the\s+rest\s+)?on\s+(?:ao3|archive|ffn|wattpad)\b", re.IGNORECASE
    ),
    re.compile(r"^\s*(?:first|prev(?:ious)?|next|start)\s*[|/]", re.IGNORECASE),
    re.compile(
        r"^\s*(?:please\s+)?(?:vote|comment|follow|subscribe|like)\b", re.IGNORECASE
    ),
    re.compile(r"^\s*(?:edit|update)\s*[:.-]", re.IGNORECASE),
    re.compile(r"^\s*\[?(?:posted|cross-?posted)\s+(?:from|to)\b", re.IGNORECASE),
    # Title pages: a byline line, or a bare "<Something> Fanfiction" credit line.
    re.compile(r"^\s*(?:by|written\s+by)\s*[:\-]\s*\S", re.IGNORECASE),
    re.compile(r"^\s*[\w '\-]{0,60}fan\s*fiction\s*$", re.IGNORECASE),
)

# Disclaimers are often mid-line, sharing a line with other text, so they are removed at sentence
# granularity rather than by dropping the whole line (which would take prose with it).
_DISCLAIMER_SENTENCE_RE = re.compile(
    r"[^.!?\n]*\b(?:"
    r"i\s+(?:do\s+not|don'?t|dont)\s+own"
    r"|(?:all\s+)?rights?\s+(?:reserved|belong)"
    r"|i\s+only\s+own\s+(?:the\s+)?(?:plot|oc|ocs|characters?)"
    r"|based\s+(?:mainly\s+)?(?:on|after)\s+the\s+(?:film|movie|book|show|series)\b"
    r"|belongs?\s+to\s+(?:their|its|the)\s+respective\s+owners?"
    r")\b[^.!?\n]*[.!?]*",
    re.IGNORECASE,
)
_INLINE_SPACE_RE = re.compile(r"[ \t]+")


def quotes_per_1k_words(text: str) -> float:
    """Return dialogue-quote characters per 1,000 words.

    The strongest single prose signal measured: real prose runs 23-32, discussion posts a median of
    exactly 0.0, because narrative breaks paragraphs on speech while discussion is one long block.
    """
    words = len(text.split())
    if words == 0:
        return 0.0
    return len(_QUOTE_RE.findall(text)) * 1000.0 / words


def past_tense_per_1k_words(text: str) -> float:
    """Return `-ed` tokens per 1,000 words — a ~2.5x prose/discussion tiebreak."""
    words = len(text.split())
    if words == 0:
        return 0.0
    return len(_PAST_TENSE_RE.findall(text)) * 1000.0 / words


def is_prose(text: str, *, min_words: int, min_quotes_per_1k: float) -> bool:
    """Return True if `text` reads as narrative prose rather than discussion.

    Deliberately excludes first-person ratio (no separation) and mean paragraph length (it runs
    backwards — discussion posts are single long blocks).
    """
    if len(text.split()) < min_words:
        return False
    return quotes_per_1k_words(text) >= min_quotes_per_1k


def strip_boilerplate(text: str) -> str:
    """Drop author notes, disclaimers, bylines, and cross-promotion, preserving prose.

    Works at two granularities, because live data showed both shapes: whole boilerplate LINES
    ("A/N: sorry for the late update"), and disclaimer SENTENCES buried mid-line ("This is based on
    the film. I DO NOT OWN TITANIC! I only own the plot."), which a line-anchored rule misses.
    """
    kept = [
        line
        for line in text.splitlines()
        if not any(pattern.search(line) for pattern in _BOILERPLATE_LINE_RES)
    ]
    without_disclaimers = _DISCLAIMER_SENTENCE_RE.sub(" ", "\n".join(kept))
    # Collapse the whitespace the substitutions leave behind, without losing paragraph breaks.
    lines = [
        _INLINE_SPACE_RE.sub(" ", line).strip()
        for line in without_disclaimers.splitlines()
    ]
    return "\n".join(lines).strip()


def normalize_text(text: str) -> str:
    """Return a canonical form for comparison: NFKC, lowercased, whitespace-collapsed."""
    folded = unicodedata.normalize("NFKC", text).lower()
    return _WHITESPACE_RE.sub(" ", folded).strip()


def content_fingerprint(text: str) -> str:
    """Return a SHA-256 hex digest of the normalized text, for exact-duplicate detection."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def _alias_key(value: str) -> str:
    """Collapse a string to its alphanumeric core, for comparing against space-stripped tags."""
    return _NON_ALNUM_RE.sub("", value.lower())


def _alias_keys(term: str) -> set[str]:
    """Return the tag-comparable forms of `term`, with and without a leading article.

    Hosts' tags drop articles: the tag `bayharborbutcher` must satisfy the Wikipedia-derived alias
    "The Bay Harbor Butcher".
    """
    words = _WORD_RE.findall(term.lower())
    if not words:
        return set()
    keys = {"".join(words)}
    if len(words) > 1 and words[0] in _LEADING_ARTICLES:
        keys.add("".join(words[1:]))
    return keys


def _phrase_pattern(term: str) -> re.Pattern[str] | None:
    """Compile a word-boundary pattern for `term`, tolerating missing separators."""
    words = _WORD_RE.findall(term.lower())
    if not words:
        return None
    # `\W*` between words matches both "dexter morgan" and "dextermorgan"; the `\b` anchors stop
    # "dexter" from matching inside "dextercharming".
    return re.compile(r"\b" + r"\W*".join(re.escape(w) for w in words) + r"\b")


def alias_hits(ref: StoryRef, query: FandomQuery) -> tuple[str, ...]:
    """Return the distinct fandom aliases present in a work's metadata.

    Matching is lexical because fandom terms are rare proper nouns ("Anaklusmos", "Dexter Morgan") —
    the case where exact matching is high-precision and dense embeddings blur the signal. Two
    boundary rules, both learned from misclassified live data:

    * **Tags are matched as whole normalized keys.** Hosts strip spaces, so the tag `dextermorgan`
      must satisfy the alias "Dexter Morgan" — otherwise unmistakable fanfic is rejected.
    * **Title and description are matched on word boundaries.** Plain substring matching let
      "dexter" hit inside "dextercharming" (an *Ever After High* character), admitting the wrong
      fandom entirely.
    """
    tag_keys = {_alias_key(tag) for tag in ref.tags}
    text = f"{ref.title} {ref.description}".lower()
    found: list[str] = []
    for term in query.search_terms:
        keys = _alias_keys(term)
        if not keys:
            continue
        if keys & tag_keys:
            found.append(term)
            continue
        pattern = _phrase_pattern(term)
        if pattern is not None and pattern.search(text):
            found.append(term)
    return tuple(found)


def required_alias_hits(query: FandomQuery) -> int:
    """Return how many distinct aliases a work must mention, given what's available.

    Clamped to the size of the alias surface. Without this, a fandom whose alias expansion failed
    has exactly one search term, `min_alias_hits=2` becomes unsatisfiable, and every candidate is
    rejected — a silent total-recall failure observed on the first live run.
    """
    return max(1, min(query.min_alias_hits, len(query.search_terms)))


def declares_fandom(ref: StoryRef, query: FandomQuery) -> bool:
    """Return True if the work explicitly labels itself as fan fiction OF this fandom.

    Titles like "Rita Makes Up Her Mind: A Dexter Fanfiction" or the tag `dexterfanfiction` state
    their fandom outright — stronger evidence than a second incidental alias, and the alias-count
    rule alone was rejecting them. Adjacency is required: "Dexter ▷ Scott Summers" (an X-Men work
    with a character named Dexter) must still be rejected.
    """
    words = _WORD_RE.findall(query.name.lower())
    if not words:
        return False
    name = r"\W*".join(re.escape(w) for w in words)
    haystack = f"{ref.title} {ref.description} {' '.join(ref.tags)}".lower()
    return bool(
        re.search(rf"\b{name}\W*{_FANFIC_MARKER}\b", haystack)
        or re.search(rf"\b{_FANFIC_MARKER}\W*{name}\b", haystack)
    )


def is_relevant(ref: StoryRef, query: FandomQuery) -> bool:
    """Return True if the work clears the fandom-relevance and popularity floors.

    Admitted either by several distinct alias hits (which suppresses incidental first-name
    mentions) or by an explicit self-declaration of the fandom.
    """
    if ref.mature and not query.allow_mature:
        return False
    if ref.reads < query.min_reads or ref.votes < query.min_votes:
        return False
    if query.languages and ref.language not in query.languages:
        return False
    if declares_fandom(ref, query):
        return True
    return len(alias_hits(ref, query)) >= required_alias_hits(query)


def admit_chapter(chapter: Chapter, query: FandomQuery) -> bool:
    """Return True if a fetched chapter should be kept in the corpus."""
    return is_prose(
        chapter.text,
        min_words=query.min_words,
        min_quotes_per_1k=query.min_quotes_per_1k,
    )
