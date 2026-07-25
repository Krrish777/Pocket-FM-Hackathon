"""`story-engine play` — the demo, playable from a terminal.

An inbound adapter and nothing more: it seeds the fork, wires the same `PlaythroughService` the API
would use, and prints turns. No narrative logic lives here.

The closing beat is `--replay-as`: the same completed branch, re-rendered from another character's
view. Watching Deborah narrate a scene she was never in, without the thing she never learned, is
the demo (`project_context.md` §8.1).
"""

import logging
from pathlib import Path

import typer
from sqlmodel import SQLModel, create_engine

from story_engine.adapters.outbound.file_prompt_store import FilePromptStore
from story_engine.adapters.outbound.ingestion.pdf_document_source import (
    PdfDocumentSource,
)
from story_engine.adapters.outbound.persistence.canon_store import SqliteCanonStore
from story_engine.adapters.outbound.scripted_llm import ScriptedLLM
from story_engine.adapters.outbound.scripted_oracle import ScriptedBranchOracle
from story_engine.domain.models.play import Playthrough
from story_engine.resources.dexter_demo import CAST, FORK_ID
from story_engine.services.demo_seed import DEFAULT_NOVEL, demo_branches, seed_canon
from story_engine.services.playthrough import PlaythroughService
from story_engine.services.working_memory import WorkingMemory

logger = logging.getLogger(__name__)

RULE = "-" * 72


def _build(db: Path, novel: Path, *, seed: bool) -> PlaythroughService:
    engine = create_engine(f"sqlite:///{db}")
    SQLModel.metadata.create_all(engine)
    store = SqliteCanonStore(engine)

    if seed:
        facts = seed_canon(store, PdfDocumentSource(), novel)
        typer.echo(f"Seeded {len(facts)} canon facts from {novel.name}.")

    return PlaythroughService(
        store=store,
        memory=WorkingMemory(store),
        oracle=ScriptedBranchOracle(demo_branches()),
        llm=ScriptedLLM(),
        prompts=FilePromptStore("prompts"),
    )


def _show(run: Playthrough) -> None:
    """Print the latest turn: the scene, its receipt, and what was kept back."""
    turn = run.turns[-1]
    typer.echo(f"\n{RULE}")
    typer.echo(
        f"TURN {turn.index}  ·  chapter {turn.chapter}  ·  "
        f"as {CAST.get(turn.protagonist, turn.protagonist)}"
    )
    typer.echo(RULE)
    typer.echo(f"\n{turn.scene}\n")

    if turn.citations:
        typer.echo("RECEIPT — every fact is checked, and here is the source:")
        for citation in turn.citations:
            typer.echo(
                f"  [{citation.source_id} ch{citation.chapter}] "
                f'"{citation.quote[:90].strip()}..."'
            )

    # Surfaced, never swallowed: over-withholding is a reported metric, a leak is a build failure.
    typer.echo(f"\nWithheld from this view: {turn.withheld_count} fact(s).")


def register(app: typer.Typer) -> None:
    """Attach the `play` command to the CLI app."""

    @app.command()
    def play(
        character: str = typer.Option(
            "dexter", "--as", help=f"Who to play. One of: {', '.join(CAST)}"
        ),
        replay_as: str = typer.Option(
            "", "--replay-as", help="After the run, re-render it as this character."
        ),
        auto: bool = typer.Option(
            False,
            "--auto",
            help="Take the first option every turn (for a scripted demo).",
        ),
        turns: int = typer.Option(
            5, "--turns", min=1, max=10, help="How many choices."
        ),
        db: Path = typer.Option(Path("data/interim/demo.db"), "--db"),
        novel: Path = typer.Option(DEFAULT_NOVEL, "--novel"),
        fresh: bool = typer.Option(
            True, "--fresh/--resume", help="Start from a clean fork."
        ),
    ) -> None:
        """Play the Dexter branch: choose, watch the world react, then replay as someone else."""
        logging.basicConfig(
            level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s"
        )

        if character not in CAST:
            raise typer.BadParameter(
                f"unknown character {character!r}; pick one of {list(CAST)}"
            )

        db.parent.mkdir(parents=True, exist_ok=True)
        if fresh and db.exists():
            db.unlink()

        service = _build(db, novel, seed=fresh or not db.exists())
        run = service.begin(fork_id=FORK_ID, protagonist=character, chapter=1)
        _show(run)

        for _ in range(turns):
            options = run.turns[-1].choices
            if not options:
                typer.echo("\nThe run has reached the end of its branches.")
                break

            typer.echo("\nWhat do you do?")
            for position, option in enumerate(options, start=1):
                origin = (
                    f"  (from fan fiction {option.source_work_id})"
                    if option.source_work_id
                    else ""
                )
                typer.echo(f"  {position}. {option.label}{origin}")

            if auto:
                pick = 1
                typer.echo(f"  > {pick} (auto)")
            else:
                pick = typer.prompt("  >", type=int, default=1)
            if not 1 <= pick <= len(options):
                raise typer.BadParameter(f"pick 1-{len(options)}")

            run = service.advance(run, options[pick - 1].id)
            _show(run)

        if replay_as:
            if replay_as not in CAST:
                raise typer.BadParameter(f"unknown character {replay_as!r}")
            typer.echo(f"\n\n{RULE}")
            typer.echo(
                f"THE SAME BRANCH, RE-RENDERED AS {CAST[replay_as].upper()}\n"
                f"Same events, same choices. Only what she is entitled to know has changed."
            )
            typer.echo(RULE)
            replay = service.replay_as(run, replay_as)
            for turn in replay.turns:
                typer.echo(f"\n[turn {turn.index}, ch{turn.chapter}] {turn.scene}")
                typer.echo(f"  withheld from this view: {turn.withheld_count} fact(s)")
