from __future__ import annotations

import base64
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv

from .canvas import SvgCanvas
from .config import (
    DEFAULT_BACKGROUND,
    DEFAULT_HEIGHT,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_PROVIDER,
    DEFAULT_WIDTH,
)
from .orchestrator import DrawingSession, SessionLogger, generate_artist_statement, run_drawing_session
from .providers.anthropic import AnthropicProvider
from .providers.base import LLMProvider
from .providers.gemini import GeminiProvider


def _slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-")


def _make_provider(provider_name: str, model: str | None) -> LLMProvider:
    if provider_name == "anthropic":
        return AnthropicProvider(model=model)
    elif provider_name == "gemini":
        return GeminiProvider(model=model)
    else:
        raise click.BadParameter(f"Unknown provider: {provider_name}")


def _setup_logging(verbose: bool) -> None:
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("monet").setLevel(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


class DefaultToDrawGroup(click.Group):
    """Click group that defaults to the 'draw' subcommand for bare invocations."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        # If the first arg isn't a known command or --help, prepend 'draw'
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["draw", *args]
        return super().parse_args(ctx, args)


@click.group(cls=DefaultToDrawGroup, invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Monet — LLM-powered iterative SVG art generator."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("prompt")
@click.option(
    "-p",
    "--provider",
    default=DEFAULT_PROVIDER,
    type=click.Choice(["anthropic", "gemini"]),
    help="LLM provider.",
)
@click.option("-m", "--model", default=None, help="Model name override.")
@click.option(
    "--max-iterations",
    default=DEFAULT_MAX_ITERATIONS,
    show_default=True,
    help="Maximum drawing iterations.",
)
@click.option("--width", default=DEFAULT_WIDTH, show_default=True, help="Canvas width.")
@click.option("--height", default=DEFAULT_HEIGHT, show_default=True, help="Canvas height.")
@click.option("--background", default=DEFAULT_BACKGROUND, show_default=True, help="Background color.")
@click.option("-o", "--output", default=None, type=click.Path(), help="Output directory.")
@click.option("-v", "--verbose", is_flag=True, help="Verbose logging.")
def draw(
    prompt: str,
    provider: str,
    model: str | None,
    max_iterations: int,
    width: int,
    height: int,
    background: str,
    output: str | None,
    verbose: bool,
) -> None:
    """Create art with an LLM. Provide an art PROMPT to get started."""
    load_dotenv()
    _setup_logging(verbose)

    # Output directory
    if output:
        output_dir = Path(output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(prompt)
        output_dir = Path("output") / f"{timestamp}_{slug}"

    # Build components
    llm = _make_provider(provider, model)
    canvas = SvgCanvas(width=width, height=height, background=background)

    session = DrawingSession(
        prompt=prompt,
        provider=llm,
        canvas=canvas,
        output_dir=output_dir,
        max_iterations=max_iterations,
    )

    final_path = run_drawing_session(session, verbose=verbose)
    click.echo(f"Final SVG: {final_path}")


@main.command()
@click.argument("output_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "-p",
    "--provider",
    default=DEFAULT_PROVIDER,
    type=click.Choice(["anthropic", "gemini"]),
    help="LLM provider.",
)
@click.option("-m", "--model", default=None, help="Model name override.")
@click.option("-v", "--verbose", is_flag=True, help="Verbose logging.")
def statement(
    output_dir: str,
    provider: str,
    model: str | None,
    verbose: bool,
) -> None:
    """Generate an artist's statement for a finished artwork in OUTPUT_DIR."""
    load_dotenv()
    _setup_logging(verbose)

    output_path = Path(output_dir)

    # Read final image
    final_png = output_path / "final.png"
    if not final_png.exists():
        raise click.ClickException(f"No final.png found in {output_path}")
    canvas_b64 = base64.standard_b64encode(final_png.read_bytes()).decode("ascii")

    # Read artist log as notes
    log_file = output_path / "artist-log.txt"
    if not log_file.exists():
        raise click.ClickException(f"No artist-log.txt found in {output_path}")
    log_text = log_file.read_text(encoding="utf-8")

    # Extract original prompt from first line (format: "Prompt: ...")
    original_prompt = "unknown"
    for line in log_text.splitlines():
        if line.startswith("Prompt: "):
            original_prompt = line[len("Prompt: ") :]
            break

    llm = _make_provider(provider, model)
    slog = SessionLogger(output_path / "_statement-log.txt", verbose)

    text, response = generate_artist_statement(
        provider=llm,
        canvas_png_base64=canvas_b64,
        notes_history=[log_text],
        original_prompt=original_prompt,
        slog=slog,
    )

    stmt_path = output_path / "artist-statement.txt"
    stmt_path.write_text(text, encoding="utf-8")
    click.echo(text)
    click.echo(f"\nSaved to {stmt_path}")


if __name__ == "__main__":
    main()
