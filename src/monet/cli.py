from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import click

from .config import DEFAULT_BACKGROUND, DEFAULT_HEIGHT, DEFAULT_PROFILE, DEFAULT_WIDTH, PROFILES
from .project import DrawingProject


def _emit(value: dict[str, Any]) -> None:
    click.echo(json.dumps(value, indent=2, sort_keys=True))


def _run(action: Callable[[], dict[str, Any]]) -> None:
    try:
        _emit(action())
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


def _open_project(path: Path) -> DrawingProject:
    return DrawingProject.open(path)


@click.group()
def main() -> None:
    """Monet — a file-backed iterative SVG canvas for coding agents."""


@main.command("new")
@click.argument("prompt")
@click.option("--title", help="Concise display title used in the session directory and manifest.")
@click.option("--width", default=DEFAULT_WIDTH, show_default=True, type=click.IntRange(min=1))
@click.option("--height", default=DEFAULT_HEIGHT, show_default=True, type=click.IntRange(min=1))
@click.option("--background", default=DEFAULT_BACKGROUND, show_default=True)
@click.option("--profile", default=DEFAULT_PROFILE, show_default=True, type=click.Choice(PROFILES))
@click.option("-o", "--output", type=click.Path(path_type=Path), help="Exact session directory to create.")
def new(
    prompt: str,
    title: str | None,
    width: int,
    height: int,
    background: str,
    profile: str,
    output: Path | None,
) -> None:
    """Create a new drawing session for PROMPT and render its blank canvas."""

    def action() -> dict[str, Any]:
        project = DrawingProject.create(
            prompt,
            title=title,
            width=width,
            height=height,
            background=background,
            profile=profile,
            output=output,
        )
        return project.status()

    _run(action)


@main.command()
@click.argument("session", type=click.Path(exists=True, file_okay=False, path_type=Path))
def render(session: Path) -> None:
    """Validate and render the layer files in SESSION."""

    def action() -> dict[str, Any]:
        project = _open_project(session)
        result = project.render()
        status = project.status()
        status["snapshot_svg"] = str(result.snapshot_svg_path)
        return status

    _run(action)


@main.command()
@click.argument("session", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("color")
def background(session: Path, color: str) -> None:
    """Set SESSION's background COLOR and render the result."""

    def action() -> dict[str, Any]:
        project = _open_project(session)
        result = project.set_background(color)
        status = project.status()
        status["snapshot_svg"] = str(result.snapshot_svg_path)
        return status

    _run(action)


@main.command()
@click.argument("session", type=click.Path(exists=True, file_okay=False, path_type=Path))
def status(session: Path) -> None:
    """Print SESSION's manifest and useful paths."""
    _run(lambda: _open_project(session).status())


@main.command()
@click.argument("session", type=click.Path(exists=True, file_okay=False, path_type=Path))
def finish(session: Path) -> None:
    """Validate SESSION, save final SVG/PNG artifacts, and close it."""

    def action() -> dict[str, Any]:
        project = _open_project(session)
        result = project.finish()
        status = project.status()
        status["snapshot_svg"] = str(result.snapshot_svg_path)
        return status

    _run(action)


if __name__ == "__main__":
    main()
