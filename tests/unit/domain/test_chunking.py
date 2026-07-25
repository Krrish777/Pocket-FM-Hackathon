"""Chunking must not lose text and must stay citable.

The two properties asserted hardest here — total coverage and quote/span agreement — are the two
the upstream implementation got wrong. Both failures are silent: nothing raises, the chunk count
looks reasonable, and the loss only surfaces later as a fact that cannot be cited. So they are
tested as *properties over the whole output*, not as spot checks on chunk zero.
"""

from itertools import pairwise

import pytest

from story_engine.domain.chunking import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_OVERLAP,
    TextSpan,
    chunk_text,
)


def _prose(sentences: int) -> str:
    """Build prose whose sentence ends land off the window grid, so the snap actually fires."""
    return " ".join(
        f"Sentence {i} carried a little more weight than the one before it, and it ended here."
        for i in range(sentences)
    )


def _covered_indices(text: str, spans: list[TextSpan]) -> set[int]:
    covered: set[int] = set()
    for span in spans:
        covered.update(range(span.char_start, span.char_end))
    return covered


def _content_indices(text: str) -> set[int]:
    """Every non-whitespace position — the characters that must survive chunking.

    Spans trim whitespace at their *edges* but keep it inside, so coverage is asserted as a
    superset: no content character may be dropped, while interior spacing is free to be covered.
    """
    return {i for i, char in enumerate(text) if not char.isspace()}


@pytest.mark.parametrize(
    "chunk_size,overlap", [(100, 20), (250, 50), (1000, 200), (37, 0)]
)
def test_every_character_is_covered(chunk_size: int, overlap: int) -> None:
    """No character is ever skipped — the regression for the upstream advance bug.

    Upstream advanced with `max(start + chunk_size - overlap, end)`, which jumps *past* `end`
    whenever the boundary snap pulled `end` backwards, silently dropping everything between.
    """
    text = _prose(60)

    spans = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    assert _content_indices(text) <= _covered_indices(text, spans)


def test_upstream_advance_rule_would_drop_characters() -> None:
    """Executable proof the upstream rule loses text, so the fix is not cargo-culted.

    Reproduces only the advance arithmetic, then shows a gap opens between consecutive windows.

    The bug is conditional, and the condition is worth stating: a gap appears exactly when
    `start + chunk_size - overlap > end`, i.e. when the sentence snap pulls `end` back *further
    than the overlap covers*. Short sentences relative to the window are what trigger it — with
    84-character sentences and a 20-character overlap the snap only retreats 16 and the overlap
    absorbs it, dropping nothing. Prose is full of short sentences, so this fires in practice.
    """
    text = " ".join(
        f"Thought number {i} closed on this note." for i in range(60)
    )  # ~38 chars each
    chunk_size, overlap = 120, 5

    upstream_covered: set[int] = set()
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = max(text.rfind(c, start, end) for c in (".", "\n"))
            if boundary > start + chunk_size * 0.5:
                end = boundary + 1
        upstream_covered.update(range(start, end))
        next_start = max(start + chunk_size - overlap, end)  # the upstream rule
        if next_start >= len(text):
            break
        start = next_start

    dropped = _content_indices(text) - upstream_covered
    assert dropped, "expected the upstream rule to drop characters; it did not"

    ours = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    assert not (_content_indices(text) - _covered_indices(text, ours))


@pytest.mark.parametrize("chunk_size,overlap", [(100, 20), (250, 50), (1000, 200)])
def test_quote_matches_its_span(chunk_size: int, overlap: int) -> None:
    """A citation must resolve back to its own coordinates, or it is not a citation."""
    text = _prose(40)

    for span in chunk_text(text, chunk_size=chunk_size, overlap=overlap):
        assert text[span.char_start : span.char_end] == span.quote


def test_spans_are_ordered_forward_and_never_empty() -> None:
    """`Provenance` rejects a non-advancing span and an empty quote — never emit either."""
    spans = chunk_text(_prose(40), chunk_size=120, overlap=30)

    assert spans
    for span in spans:
        assert span.char_end > span.char_start
        assert span.quote.strip()
    for earlier, later in pairwise(spans):
        assert later.char_start > earlier.char_start


def test_consecutive_spans_share_context() -> None:
    """Overlap exists so a fact straddling a window edge survives intact somewhere."""
    text = _prose(40)

    spans = chunk_text(text, chunk_size=200, overlap=80)

    assert len(spans) > 1
    # Each span starts at or before its predecessor's end: touching or overlapping, never a gap.
    for earlier, later in pairwise(spans):
        assert later.char_start <= earlier.char_end


def test_snaps_to_a_sentence_boundary() -> None:
    """A chunk should end on a completed thought rather than mid-word."""
    text = "The first thought ended cleanly. " + ("padding " * 40) + "tail."

    spans = chunk_text(text, chunk_size=60, overlap=10)

    assert spans[0].quote.endswith(".")


def test_a_short_text_is_a_single_span() -> None:
    text = "Dexter kept the slides in a rosewood box."

    spans = chunk_text(text, chunk_size=DEFAULT_CHUNK_SIZE, overlap=DEFAULT_OVERLAP)

    assert spans == [TextSpan(char_start=0, char_end=len(text), quote=text)]


@pytest.mark.parametrize("text", ["", "   ", "\n\n\t  \n"])
def test_contentless_text_yields_no_spans(text: str) -> None:
    """Whitespace is not citable, so it must not become a span with an empty quote."""
    assert chunk_text(text) == []


@pytest.mark.parametrize(
    "chunk_size,overlap",
    [(0, 0), (-1, 0), (100, -1), (100, 100), (100, 200)],
)
def test_unusable_parameters_fail_loudly(chunk_size: int, overlap: int) -> None:
    """An overlap at or above the window size cannot advance — refuse rather than hang."""
    with pytest.raises(ValueError):
        chunk_text(_prose(5), chunk_size=chunk_size, overlap=overlap)
