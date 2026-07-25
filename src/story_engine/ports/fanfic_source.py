"""Fan-fiction source port — the seam between harvesting and any particular host.

Two capabilities, deliberately kept in one cohesive port because no consumer needs search without
fetch: discover works matching a fandom, then fetch a work's prose. Host SDKs and HTTP live only in
`adapters/outbound/fanfic/`.
"""

from typing import Protocol

from story_engine.domain.models.fanfic import Chapter, FandomQuery, StoryRef


class FanficSourcePort(Protocol):
    """Discover and fetch fan-fiction works from a host."""

    source_name: str
    """The host this adapter serves, matching the `FanficSource` value it stamps on refs."""

    def search(self, query: FandomQuery, *, limit: int) -> tuple[StoryRef, ...]:
        """Return up to `limit` candidate works for the fandom, metadata only."""
        ...

    def fetch_chapters(
        self, ref: StoryRef, *, max_chapters: int
    ) -> tuple[Chapter, ...]:
        """Return up to `max_chapters` chapters of prose for a work, in reading order."""
        ...


class AliasExpanderPort(Protocol):
    """Expand a fandom name into its alias surface (title variants, characters, universe terms)."""

    def expand(self, fandom: str, *, limit: int, kind: str = "auto") -> tuple[str, ...]:
        """Return up to `limit` distinct aliases for `fandom`, excluding the name itself.

        `kind` (`movie`/`novel`/`series`/`auto`) disambiguates an ambiguous title — without it,
        "Titanic" resolves to the ship rather than the film.
        """
        ...
