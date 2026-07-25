"""Story Engine CLI (inbound adapter, Typer).

Thin: parse args → build the container → call the SAME service the API uses. Entry point declared in
pyproject `[project.scripts]` (`story-engine = "story_engine.cli.main:main"`).
"""

import typer

from story_engine.bootstrap import build_container

app = typer.Typer(help="Story Engine CLI", no_args_is_help=True)


@app.command()
def generate(series_id: str, beat: str) -> None:
    """Generate the next episode for a series from a target beat."""
    container = build_container()
    episode = container.episode_generator.generate(series_id, beat=beat)
    typer.echo(episode.title)


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
