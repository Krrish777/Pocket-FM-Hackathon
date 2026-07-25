"""Pure text chunking for source-document ingestion — overlapping spans that stay citable.

Adapted from the ingestion pipeline in `patchy631/ai-engineering-hub/notebook-lm-clone`
(MIT, © 2024 patchy631), which supplied the shape: walk the text in fixed-size windows, snap
each window back to a sentence boundary so a chunk does not end mid-thought, and carry the
character offsets forward so a retrieved chunk can name where it came from.

Three behaviours were changed, and the reasons are the point of this module:

1. **No character is ever skipped.** Upstream advanced with
   `start = max(start + chunk_size - overlap, end)`. When the boundary snap pulls `end`
   *backwards* — the common case, since that is what the snap is for — the next `start` lands
   *past* `end` and the characters between them are never emitted. With `chunk_size=1000,
   overlap=200` and a snap to 700, characters 700-800 vanish. For a notebook assistant that is a
   quality shrug; here a dropped span is a fact that exists in the novel and can never be cited,
   so the receipt (`project_context.md` §5.4) silently cannot be produced. We advance with
   `start = max(end - overlap, start + 1)`, which can never exceed `end`, so consecutive spans
   always touch or overlap. `test_every_character_is_covered` is the regression.

2. **The quote matches its own span.** Upstream stripped the chunk text but recorded the
   *unstripped* offsets, so `text[char_start:char_end] != quote` whenever a window began or ended
   on whitespace. A citation that does not resolve back to its own coordinates is not a citation.
   Trimming adjusts the offsets with it, giving the invariant asserted by
   `test_quote_matches_its_span`.

3. **Offsets are relative to one addressable unit** (a chapter), never reset per page. Upstream
   restarted at 0 on every PDF page, making an offset meaningless without knowing the page.
   `Provenance` addresses by `(source_id, chapter, char_start, char_end)`, so the caller passes
   whole-chapter text and every offset resolves against it.

Stdlib only and free of IO by design: this is where the citation guarantee lives, so it must be
exhaustively testable without a PDF, a network, or a model.
"""

from dataclasses import dataclass

DEFAULT_CHUNK_SIZE = 1000
"""Characters per window before the boundary snap."""

DEFAULT_OVERLAP = 200
"""Characters of context each window shares with its predecessor.

Overlap exists so a fact straddling a window edge survives in at least one intact chunk.
"""

_MIN_BOUNDARY_RATIO = 0.5
"""How far into a window a sentence boundary must fall to be worth snapping to.

Snapping to a boundary near the window start would emit a sliver and re-read almost everything,
so a boundary is only honoured in the back half.
"""

_BOUNDARY_CHARS = (".", "\n")
"""Characters treated as the end of a thought, in priority-free order — the latest one wins."""


@dataclass(frozen=True, slots=True)
class TextSpan:
    """A citable slice of a source text.

    The offsets are relative to the text handed to `chunk_text`, and `quote` is stored verbatim so
    a citation renders without re-reading the source. These map directly onto `Provenance`.

    Invariant, guaranteed by construction: `source[char_start:char_end] == quote`.
    """

    char_start: int
    char_end: int
    quote: str


def chunk_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[TextSpan]:
    """Split text into overlapping, sentence-aligned spans that cover it completely.

    Args:
        text: The unit being chunked — normally one chapter, since `Provenance` addresses by
            chapter and the returned offsets are relative to this string.
        chunk_size: Target characters per span, before snapping to a sentence boundary.
        overlap: Characters each span shares with the one before it.

    Returns:
        Spans in ascending order. Consecutive spans touch or overlap, so every non-whitespace
        character of `text` appears in at least one span. Empty when `text` has no content.

    Raises:
        ValueError: If `chunk_size` is below 1, or `overlap` is negative or not smaller than
            `chunk_size` — an overlap at or above the window size cannot advance.
    """
    if chunk_size < 1:
        raise ValueError(f"chunk_size must be at least 1, got {chunk_size}")
    if overlap < 0:
        raise ValueError(f"overlap must not be negative, got {overlap}")
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap must be smaller than chunk_size, got {overlap} >= {chunk_size}"
        )

    length = len(text)
    spans: list[TextSpan] = []
    start = 0

    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            end = _snap_to_boundary(text, start, end, chunk_size)

        span = _trim(text, start, end)
        if span is not None:
            spans.append(span)

        if end >= length:
            break
        # Never past `end`: that is what guarantees consecutive spans leave no gap.
        start = max(end - overlap, start + 1)

    return spans


def _snap_to_boundary(text: str, start: int, end: int, chunk_size: int) -> int:
    """Pull `end` back to just after the last sentence boundary, if one falls late enough."""
    latest = max(text.rfind(char, start, end) for char in _BOUNDARY_CHARS)
    if latest > start + chunk_size * _MIN_BOUNDARY_RATIO:
        return latest + 1  # include the boundary character itself
    return end


def _trim(text: str, start: int, end: int) -> TextSpan | None:
    """Shrink a span past surrounding whitespace, moving its offsets with it.

    Returns None when nothing but whitespace is left — an empty quote is not citable, and
    `Provenance.quote` rejects it anyway.
    """
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start >= end:
        return None
    return TextSpan(char_start=start, char_end=end, quote=text[start:end])
