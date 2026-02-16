from __future__ import annotations

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
    DEFAULT_THINKING_BUDGET,
    DEFAULT_WIDTH,
)
from .orchestrator import DrawingSession, run_drawing_session
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


@click.command()
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
@click.option("--thinking", is_flag=True, help="Enable extended thinking.")
@click.option(
    "--thinking-budget",
    default=DEFAULT_THINKING_BUDGET,
    show_default=True,
    help="Thinking token budget.",
)
def main(
    prompt: str,
    provider: str,
    model: str | None,
    max_iterations: int,
    width: int,
    height: int,
    background: str,
    output: str | None,
    verbose: bool,
    thinking: bool,
    thinking_budget: int,
) -> None:
    """Create art with an LLM. Provide an art PROMPT to get started."""
    load_dotenv()

    # Set up logging
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
    )
    log = logging.getLogger("monet")
    log.setLevel(level)

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

    log.info(f"Prompt: {prompt}")
    log.info(f"Provider: {llm.name} ({model or llm.default_model})")
    log.info(f"Canvas: {width}x{height}, bg={background}")
    log.info(f"Output: {output_dir}")
    if thinking:
        log.info(f"Thinking enabled (budget: {thinking_budget})")

    session = DrawingSession(
        prompt=prompt,
        provider=llm,
        canvas=canvas,
        output_dir=output_dir,
        max_iterations=max_iterations,
        thinking_enabled=thinking,
        thinking_budget=thinking_budget,
    )

    final_path = run_drawing_session(session, verbose=verbose)
    click.echo(f"Final SVG: {final_path}")


if __name__ == "__main__":
    main()
