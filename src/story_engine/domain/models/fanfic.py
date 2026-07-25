"""Fan-fiction corpus models.

The typed shape of a harvested fan-fiction work, independent of which host it came from. Populated
at the adapter boundary (see `adapters/outbound/fanfic/`) so unvalidated third-party JSON never
reaches the core. See docs/superpowers/specs/2026-07-25-fanfic-harvest-design.md.
"""

from enum import StrEnum

from pydantic import Field, computed_field

from story_engine.domain.base import DomainModel


class FanficSource(StrEnum):
    """Host a work was harvested from."""

    WATTPAD = "wattpad"
    AO3 = "ao3"
    REDDIT = "reddit"
    LOCAL = "local"


class FandomQuery(DomainModel):
    """A fandom to harvest, plus the thresholds a work must clear to be kept.

    `aliases` carries the expanded surface for the fandom — title variants, character names, and
    universe terms. Universe terms ("Anaklusmos", "celestial bronze") are the highest-precision
    signals because nobody outside the fandom writes them.
    """

    name: str = Field(min_length=2, max_length=120)
    aliases: tuple[str, ...] = ()
    min_words: int = Field(default=500, ge=0)
    min_quotes_per_1k: float = Field(default=5.0, ge=0.0)
    min_reads: int = Field(default=0, ge=0)
    min_votes: int = Field(default=0, ge=0)
    min_alias_hits: int = Field(default=2, ge=1)
    allow_mature: bool = Field(
        default=False,
        description="Keep works the host flags as mature. Off by default.",
    )
    languages: tuple[str, ...] = ("en",)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def search_terms(self) -> tuple[str, ...]:
        """Distinct, lowercased terms to match against, name first."""
        seen: dict[str, None] = {}
        for term in (self.name, *self.aliases):
            cleaned = term.strip().lower()
            if cleaned:
                seen.setdefault(cleaned, None)
        return tuple(seen)


class PremiseTrope(StrEnum):
    """A recognized what-if premise facet.

    Fan fiction clusters around a small, recurring set of divergences from canon. These are the
    facets the lexical detector in `domain/fanfic_premise.py` can prove from a title/blurb; the
    order of the members is not significant (precedence lives in that module).
    """

    CHARACTER_SURVIVES = "character_survives"
    TRANSMIGRATION = "transmigration"
    CROSSOVER = "crossover"
    READER_INSERT = "reader_insert"
    PAIRING = "pairing"
    TIME_DISPLACEMENT = "time_displacement"
    CONTINUATION = "continuation"
    LOVE_TRIANGLE = "love_triangle"
    FOUND_FAMILY = "found_family"
    ORIGINAL_CHARACTER = "original_character"
    ALTERNATE_UNIVERSE = "alternate_universe"
    CHARACTER_DEATH = "character_death"


class PremiseSignature(DomainModel):
    """The what-if premise a work is built on, derived lexically from its title and blurb.

    `key` is the grouping identity — deliberately narrow (one dominant trope plus the canon
    entities it acts on) so that works sharing a key really do branch off the same canon decision
    point. `tropes` keeps every facet that fired, so a caller can regroup more loosely.
    """

    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    tropes: tuple[PremiseTrope, ...] = ()
    focal_entities: tuple[str, ...] = ()
    evidence: tuple[str, ...] = Field(
        default=(),
        description=(
            "Verbatim blurb snippets that triggered detection. Provenance for auditing only — "
            "never rendered to a player and never used as prose (project_context.md §5.2)."
        ),
    )
    decision_point: str = Field(
        default="",
        description="The canon decision this work diverges from, phrased canon-side.",
    )
    alternate_path: str = Field(
        default="", description="The path this work takes instead of canon."
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_classified(self) -> bool:
        """True if any premise trope was detected."""
        return bool(self.tropes)


class BranchOption(DomainModel):
    """One discrete option at a canon decision point — a player-facing choice.

    `label` is synthesized from the premise taxonomy, never copied from a work's text: fan fiction
    supplies *what the options are*, not any reproduced prose (project_context.md §5.2).
    """

    label: str = Field(min_length=1)
    detail: str = ""
    is_canon: bool = Field(
        default=False,
        description="True for the option that lets canon stand — the intentional-divergence "
        "baseline of project_context.md §5.5.",
    )
    tropes: tuple[PremiseTrope, ...] = ()
    support: int = Field(
        default=0, ge=0, description="Number of harvested works taking this path."
    )
    sources: tuple[str, ...] = ()
    source_titles: tuple[str, ...] = ()


class BranchPoint(DomainModel):
    """A canon decision point plus the 2-4 discrete options observed diverging from it.

    This is the Branch Oracle unit (project_context.md §5.2/§4): one decision, a canon-stands
    option, and the alternate paths independent fan authors actually took. Every divergence here is
    *intentional* (a chosen consequence), never an accidental contradiction (§5.5).
    """

    key: str = Field(min_length=1)
    decision_point: str = Field(min_length=1)
    tropes: tuple[PremiseTrope, ...] = ()
    focal_entities: tuple[str, ...] = ()
    options: tuple[BranchOption, ...] = ()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def option_count(self) -> int:
        """Number of options offered, including the canon-stands option."""
        return len(self.options)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def support(self) -> int:
        """Total harvested works backing the non-canon options."""
        return sum(o.support for o in self.options if not o.is_canon)


class PremiseGroup(DomainModel):
    """Works that share one premise — N human-authored branches off one canon decision point."""

    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    tropes: tuple[PremiseTrope, ...] = ()
    members: tuple[str, ...] = Field(
        default=(), description="`<source>:<source_id>` handles of the member works."
    )
    member_titles: tuple[str, ...] = ()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def size(self) -> int:
        """Number of works in the group."""
        return len(self.members)


class ProseComponent(DomainModel):
    """One bounded, explainable term of the prose-quality score."""

    name: str = Field(min_length=1)
    value: float = Field(ge=0.0, le=1.0, description="Normalized component score.")
    weight: float = Field(ge=0.0, le=1.0, description="Contribution to the total.")
    detail: str = Field(default="", description="The raw measurement, for auditing.")


class ProseQuality(DomainModel):
    """A deterministic, explainable writing-quality score in [0, 100].

    Every component is normalized to [0, 1] and the weights sum to 1, so `score` is a weighted
    mean scaled by 100. Nothing here judges *relevance* — that is `alias_hits`' job.
    """

    score: float = Field(ge=0.0, le=100.0)
    components: tuple[ProseComponent, ...] = ()
    word_count: int = Field(default=0, ge=0)


class ChapterRef(DomainModel):
    """An opaque, host-agnostic handle to one chapter, discovered during search.

    Carrying these on the `StoryRef` lets `fetch_chapters` pull prose without a second metadata
    round-trip, while keeping the host's id scheme opaque to the core.
    """

    source_id: str = Field(min_length=1)
    index: int = Field(ge=1)
    title: str = ""


class StoryRef(DomainModel):
    """Host-side metadata for a work, before its prose is fetched."""

    source: FanficSource
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=500)
    author: str = ""
    url: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()
    chapter_refs: tuple[ChapterRef, ...] = ()
    num_chapters: int = Field(default=0, ge=0)
    reads: int = Field(default=0, ge=0)
    votes: int = Field(default=0, ge=0)
    completed: bool = False
    mature: bool = False
    language: str = "en"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def haystack(self) -> str:
        """Lowercased title + description + tags, for alias matching."""
        return " ".join((self.title, self.description, " ".join(self.tags))).lower()


class Chapter(DomainModel):
    """One fetched chapter of prose."""

    index: int = Field(ge=1, description="1-based position within the work.")
    source_id: str = Field(min_length=1)
    title: str = ""
    text: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def word_count(self) -> int:
        """Number of whitespace-separated words in the prose."""
        return len(self.text.split())


class HarvestedStory(DomainModel):
    """A work plus its fetched chapters and the score that admitted it."""

    ref: StoryRef
    chapters: tuple[Chapter, ...] = ()
    alias_hits: tuple[str, ...] = ()
    premise: PremiseSignature | None = None
    prose_quality: ProseQuality | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def handle(self) -> str:
        """Stable `<source>:<source_id>` identity for this work."""
        return f"{self.ref.source}:{self.ref.source_id}"

    @property
    def prose_text(self) -> str:
        """All kept chapters joined, the unit the prose-quality score is measured over.

        A plain property, not a `computed_field`: serializing it would duplicate the entire corpus
        inside every dump.
        """
        return "\n\n".join(c.text for c in self.chapters)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_words(self) -> int:
        return sum(c.word_count for c in self.chapters)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def relevance_score(self) -> int:
        """Count of distinct fandom aliases found in the work's metadata."""
        return len(self.alias_hits)
