"""Story Engine CLI (inbound adapter, Typer).

Thin: parse args → build the container → call the SAME service the API uses. Entry point declared in
pyproject `[project.scripts]` (`story-engine = "story_engine.cli.main:main"`).
"""

import logging
from pathlib import Path
from statistics import median

import typer

from story_engine.adapters.outbound.fanfic.alias_expander import WikipediaAliasExpander
from story_engine.adapters.outbound.fanfic.hf_ao3 import HuggingFaceAO3Source
from story_engine.adapters.outbound.fanfic.jsonl_sink import (
    DEFAULT_CORPUS_ROOT,
    JsonlCorpusSink,
)
from story_engine.adapters.outbound.fanfic.wattpad import WattpadSource
from story_engine.adapters.outbound.wiki.fandom_wiki import FandomWikiSource
from story_engine.adapters.outbound.wiki.jsonl_index_sink import (
    DEFAULT_INDEX_ROOT,
    JsonlWikiIndexSink,
)
from story_engine.bootstrap import build_container
from story_engine.domain.models.wiki_index import WikiEntityKind
from story_engine.ports.fanfic_source import FanficSourcePort
from story_engine.services.fanfic_harvest import FanficHarvester, HarvestReport
from story_engine.services.wiki_index_harvest import DEFAULT_KINDS, WikiIndexHarvester

app = typer.Typer(help="Story Engine CLI", no_args_is_help=True)

# AO3 rows carry no reliable Hits/Kudos, so the popularity floors that protect the Wattpad corpus
# from joke fics reject every AO3 work outright. Including AO3 therefore relaxes the floors — a
# deliberate, reported trade rather than a silent one.
_AO3_SCAN_ROWS = 5_000
_AO3_CACHE_DIR = Path("data/interim/hf_ao3")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )


def _build_sources(include_ao3: bool) -> tuple[FanficSourcePort, ...]:
    """Assemble the host adapters for a harvest, Wattpad first."""
    sources: list[FanficSourcePort] = [WattpadSource()]
    if include_ao3:
        sources.append(
            HuggingFaceAO3Source(
                max_scan_rows=_AO3_SCAN_ROWS,
                cache_dir=_AO3_CACHE_DIR,
                request_delay=1.0,
            )
        )
    return tuple(sources)


def _echo_report(report: HarvestReport) -> None:
    """Print the harvest tally, including every rejection reason."""
    scores = report.prose_quality_scores
    typer.echo("")
    typer.echo(f"Fandom             : {report.fandom}")
    typer.echo(f"Aliases used       : {report.aliases_used}")
    typer.echo(f"Candidates seen    : {report.candidates_seen}")
    typer.echo(f"Rejected (fandom)  : {report.relevance_rejected}")
    typer.echo(f"Rejected (prose)   : {report.prose_rejected}")
    typer.echo(f"Rejected (quality) : {report.quality_rejected}")
    typer.echo(f"Duplicates dropped : {report.duplicates_dropped}")
    typer.echo(f"Works kept         : {report.stories_kept}")
    typer.echo(f"Chapters kept      : {report.chapters_kept}")
    typer.echo(f"Total words        : {report.total_words:,}")
    if scores:
        typer.echo(f"Prose quality      : median {median(scores):.1f} of {len(scores)}")
    typer.echo(f"Premise groups     : {len(report.premise_groups)}")
    typer.echo(f"Branch points      : {len(report.branch_points)}")
    typer.echo(f"Written to         : {report.sink_location or '(nothing kept)'}")


def _echo_branch_points(report: HarvestReport) -> None:
    """Print the Branch Oracle: one canon decision point per block, with its options."""
    if not report.branch_points:
        typer.echo("\nNo branch points detected.")
        return
    typer.echo("")
    for point in report.branch_points:
        typer.echo(f"=== {point.key}  (support={point.support})")
        typer.echo(f"    DECISION: {point.decision_point}")
        for option in point.options:
            marker = "CANON " if option.is_canon else f"alt x{option.support}"
            typer.echo(f"      [{marker}] {option.label}")


@app.command()
def generate(series_id: str, beat: str) -> None:
    """Generate the next episode for a series from a target beat."""
    container = build_container()
    episode = container.episode_generator.generate(series_id, beat=beat)
    typer.echo(episode.title)


@app.command()
def harvest(
    fandom: str = typer.Argument(
        ..., help="Novel, film, or series to harvest fan fiction for."
    ),
    kind: str = typer.Option(
        "auto",
        help="movie | novel | series | auto. Effectively REQUIRED for ambiguous titles: "
        "without it 'Titanic' resolves to the ship and 'Dexter' to a warship.",
    ),
    max_stories: int = typer.Option(25, help="Maximum works to keep."),
    max_chapters: int = typer.Option(
        500,
        help="Maximum chapters to fetch per work. Default is effectively 'all' — hosts return "
        "every part, so a low cap silently truncates long works.",
    ),
    min_words: int = typer.Option(
        500, help="Minimum words for a chapter to count as prose."
    ),
    min_quotes_per_1k: float = typer.Option(
        5.0, help="Minimum dialogue-quote density per 1k words."
    ),
    min_alias_hits: int = typer.Option(
        2, help="Distinct fandom aliases a work must mention to be considered relevant."
    ),
    min_reads: int = typer.Option(
        100,
        help="Minimum read count on the host — a popularity floor against joke fics.",
    ),
    min_votes: int = typer.Option(5, help="Minimum vote count on the host."),
    min_prose_quality: float | None = typer.Option(
        None,
        help="Drop works scoring below this (0-100). Unset by default: ranking, not filtering.",
    ),
    rank_by_quality: bool = typer.Option(
        True,
        "--rank-by-quality/--no-rank-by-quality",
        help="Order kept works best-first.",
    ),
    max_branch_options: int = typer.Option(
        4, min=2, help="Maximum options per branch point (canon baseline included)."
    ),
    allow_mature: bool = typer.Option(
        False,
        "--allow-mature",
        help="Include works the host flags as mature. Excluded by default. NOTE: the host flag is "
        "self-reported and unreliable.",
    ),
    include_ao3: bool = typer.Option(
        False,
        "--include-ao3",
        help="Also scan the HuggingFace AO3 corpus. Longer works and it distinguishes novel from "
        "screen canon, but it has no read/vote data, so this relaxes those floors to 0.",
    ),
    show_branches: bool = typer.Option(
        False, "--show-branches", help="Print the branch points after the summary."
    ),
    out: Path = typer.Option(DEFAULT_CORPUS_ROOT, help="Corpus output root."),
) -> None:
    """Harvest a fan-fiction corpus for a novel or film and write it locally as JSONL."""
    _configure_logging()
    if include_ao3 and (min_reads > 0 or min_votes > 0):
        typer.echo(
            "note: --include-ao3 relaxes --min-reads/--min-votes to 0 "
            "(AO3 rows carry no reliable Hits/Kudos, so the floors would reject every AO3 work)"
        )
        min_reads = 0
        min_votes = 0

    harvester = FanficHarvester(
        sources=_build_sources(include_ao3),
        alias_expander=WikipediaAliasExpander(),
        sink=JsonlCorpusSink(out),
    )
    _, report = harvester.harvest(
        fandom,
        max_stories=max_stories,
        max_chapters_per_story=max_chapters,
        min_words=min_words,
        min_quotes_per_1k=min_quotes_per_1k,
        min_alias_hits=min_alias_hits,
        min_reads=min_reads,
        min_votes=min_votes,
        allow_mature=allow_mature,
        kind=kind,
        min_prose_quality=min_prose_quality,
        rank_by_quality=rank_by_quality,
        max_branch_options=max_branch_options,
    )
    _echo_report(report)
    if show_branches:
        _echo_branch_points(report)


@app.command()
def branches(
    fandom: str = typer.Argument(
        ..., help="Novel, film, or series to mine branches for."
    ),
    kind: str = typer.Option("auto", help="movie | novel | series | auto."),
    max_stories: int = typer.Option(25, help="Maximum works to mine."),
    max_branch_options: int = typer.Option(
        4, min=2, help="Max options per branch point."
    ),
    include_ao3: bool = typer.Option(
        False, "--include-ao3", help="Also scan the HuggingFace AO3 corpus."
    ),
    out: Path = typer.Option(DEFAULT_CORPUS_ROOT, help="Corpus output root."),
) -> None:
    """Show the Branch Oracle: canon decision points and the alternate paths fan fiction took.

    Fan fiction supplies WHAT the options are; option labels are synthesized from the premise
    taxonomy and no harvested prose is reproduced (project_context.md 5.2).
    """
    _configure_logging()
    harvester = FanficHarvester(
        sources=_build_sources(include_ao3),
        alias_expander=WikipediaAliasExpander(),
        sink=JsonlCorpusSink(out),
    )
    _, report = harvester.harvest(
        fandom,
        max_stories=max_stories,
        kind=kind,
        min_reads=0 if include_ao3 else 100,
        min_votes=0 if include_ao3 else 5,
        max_branch_options=max_branch_options,
    )
    _echo_branch_points(report)
    typer.echo("")
    typer.echo(
        f"{len(report.premise_groups)} premise groups from {report.stories_kept} works"
    )


@app.command("wiki-index")
def wiki_index(
    fandom: str = typer.Argument(
        ..., help="Fandom whose wiki to index, e.g. 'Dexter'."
    ),
    limit_per_kind: int = typer.Option(150, help="Maximum entities to keep per kind."),
    min_summary_words: int = typer.Option(
        0, help="Drop entities whose lead prose is shorter than this."
    ),
    kinds: str = typer.Option(
        "",
        help="Comma-separated entity kinds (character,location,event,organization,other). "
        "Empty uses the default set.",
    ),
    subdomain: str = typer.Option(
        "", help="Override the wiki subdomain, e.g. 'riordan' for Percy Jackson."
    ),
    out: Path = typer.Option(DEFAULT_INDEX_ROOT, help="Index output root."),
) -> None:
    """Build a wiki ENTITY VOCABULARY plus a novel-vs-screen canon discriminator.

    This is deliberately NOT a canon knowledge base: values are recorded as observations with
    provenance, never as canon facts. `canon_basis: screen` is a review flag, not a verdict —
    absence of a novel page is not absence from the novels.
    """
    _configure_logging()
    selected = DEFAULT_KINDS
    if kinds.strip():
        selected = tuple(
            WikiEntityKind(token.strip().lower())
            for token in kinds.split(",")
            if token.strip()
        )
    overrides = {fandom: subdomain} if subdomain.strip() else None

    harvester = WikiIndexHarvester(
        source=FandomWikiSource(subdomain_overrides=overrides),
        sink=JsonlWikiIndexSink(out),
    )
    _, report = harvester.harvest(
        fandom,
        kinds=selected,
        limit_per_kind=limit_per_kind,
        min_summary_words=min_summary_words,
    )
    typer.echo("")
    typer.echo(f"Wiki               : {report.wiki_url}")
    typer.echo(f"Pages discovered   : {report.pages_discovered}")
    typer.echo(f"Pages unusable     : {report.pages_unusable}")
    typer.echo(f"Entities parsed    : {report.entities_parsed}")
    typer.echo(f"Dropped (thin)     : {report.entities_dropped_thin}")
    typer.echo(f"Duplicates merged  : {report.duplicates_merged}")
    typer.echo(f"Entities kept      : {report.entities_after_merge}")
    typer.echo(
        f"Canon basis        : novel {report.novel_only} · screen {report.screen_only} · "
        f"both {report.both_canons} · unknown {report.unknown_basis}"
    )
    typer.echo(f"Relationships      : {report.relationships}")
    typer.echo(f"Attributes         : {report.attributes}")
    typer.echo(f"Unresolved targets : {report.unresolved_targets}")
    typer.echo(f"Written to         : {report.sink_location or '(nothing kept)'}")


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
