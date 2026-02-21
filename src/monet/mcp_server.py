from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from .canvas import SvgCanvas
from .config import DEFAULT_BACKGROUND, DEFAULT_EXPORT_SCALE, DEFAULT_HEIGHT, DEFAULT_WIDTH
from .prompt import build_artistic_guidelines, build_canvas_description, build_statement_prompt
from .renderer import render_svg_to_png, save_png, save_svg

mcp = FastMCP("monet")


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


@dataclass
class Session:
    prompt: str
    canvas: SvgCanvas
    output_dir: Path
    iteration: int = 0
    finished: bool = False
    _log_lines: list[str] = field(default_factory=list, repr=False)

    def log(self, msg: str) -> None:
        self._log_lines.append(msg)

    def flush_log(self) -> None:
        with open(self.output_dir / "artist-log.txt", "a", encoding="utf-8") as f:
            for line in self._log_lines:
                f.write(line + "\n")
        self._log_lines.clear()


_session: Session | None = None


def _require_session() -> Session:
    if _session is None:
        raise ValueError("No active session. Call create_canvas first.")
    return _session


def _require_mutable_session() -> Session:
    s = _require_session()
    if s.finished:
        raise ValueError("Drawing is finished. Call create_canvas to start a new one.")
    return s


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-")


def _render_canvas_image(canvas: SvgCanvas) -> Image:
    png_bytes = render_svg_to_png(canvas.to_svg())
    return Image(data=png_bytes, format="png")


def _save_intermediates(session: Session) -> None:
    stem = f"iter-{session.iteration:03d}"
    svg_str = session.canvas.to_svg()
    save_svg(svg_str, session.output_dir / f"{stem}.svg")
    try:
        png_bytes = render_svg_to_png(svg_str)
        save_png(png_bytes, session.output_dir / f"{stem}.png")
    except Exception as e:
        session.log(f"WARNING: Could not save intermediate PNG: {e}")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool
def create_canvas(
    prompt: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    background: str = DEFAULT_BACKGROUND,
) -> tuple[str, Image]:
    """Start a new drawing session.

    This must be the first tool called. It initializes a blank canvas and returns
    artistic guidelines plus the blank canvas image. Use these guidelines to plan
    your artistic approach before calling add_layer.

    Args:
        prompt: What to draw — the artistic subject / concept.
        width: Canvas width in pixels (default 800).
        height: Canvas height in pixels (default 600).
        background: Background color as hex string (default "#FFFFFF").
    """
    global _session

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(prompt)
    output_dir = Path("output") / f"{timestamp}_{slug}"
    output_dir.mkdir(parents=True, exist_ok=True)

    canvas = SvgCanvas(width=width, height=height, background=background)
    _session = Session(prompt=prompt, canvas=canvas, output_dir=output_dir)

    # Initialize log
    (output_dir / "artist-log.txt").write_text("", encoding="utf-8")
    _session.log(f"Prompt: {prompt}")
    _session.log(f"Canvas: {width}x{height}, bg={background}")
    _session.log(f"Output: {output_dir}")
    _session.log("")
    _session.flush_log()

    canvas_desc = build_canvas_description(width, height)
    guidelines = build_artistic_guidelines()

    text = f"""\
# Drawing Session: {prompt}

You are an SVG artist. You create art by writing SVG elements on a canvas, iteratively refining \
your work. Each iteration, you see your current canvas as an image and add new SVG elements.

## Canvas
{canvas_desc}

## How to Use the Tools
- Call `add_layer` to add SVG elements as a new layer on top of existing ones.
- Provide raw SVG elements (no <svg> wrapper).
- For defs (gradients, filters, patterns), pass them in the `defs` parameter.
- CRITICAL: prefix every def ID with the layer number to avoid conflicts (e.g., "iter3-sunGradient").
- Use `set_background` to change the background color.
- Use `replace_layer` sparingly to fix mistakes in a previous layer.
- Use `view_canvas` to see the current state without making changes.
- Call `finish_drawing` when the piece is complete.

## Artistic Guidelines
{guidelines}

The blank canvas is ready. Plan your composition, then start adding layers."""

    return text, _render_canvas_image(canvas)


@mcp.tool
def add_layer(svg_elements: str, defs: str | None = None) -> tuple[str, Image]:
    """Add a new SVG layer on top of existing layers.

    Provide raw SVG elements (no <svg> wrapper). Optionally include defs for
    gradients, filters, patterns, etc. The layer is validated by rendering — if
    the SVG is invalid, the layer is rolled back and an error is returned.

    Args:
        svg_elements: Raw SVG elements to add (e.g., '<circle cx="100" cy="100" r="50" fill="red"/>').
        defs: Optional SVG defs content (gradients, filters, etc.). Prefix IDs with layer number.
    """
    session = _require_mutable_session()
    session.iteration += 1

    session.log(f"{'=' * 40}")
    session.log(f"== add_layer (iteration {session.iteration})")

    layer_id = session.canvas.add_layer(svg_elements, defs)

    # Validate render
    try:
        render_svg_to_png(session.canvas.to_svg())
    except Exception as e:
        # Roll back
        del session.canvas.layers[layer_id]
        if layer_id in session.canvas.defs:
            del session.canvas.defs[layer_id]
        session.iteration -= 1
        session.log(f"ROLLED BACK {layer_id}: {e}")
        session.flush_log()
        raise ValueError(f"Layer {layer_id} caused a render error and was rolled back: {e}. Fix the SVG and try again.")

    session.log(f"Added {layer_id}")
    _save_intermediates(session)
    session.flush_log()

    summary = f"Added {layer_id}. Layers: {session.canvas.get_layer_summary()}"
    return summary, _render_canvas_image(session.canvas)


@mcp.tool
def replace_layer(layer_id: str, svg_elements: str, defs: str | None = None) -> tuple[str, Image]:
    """Replace an existing layer's content.

    Use sparingly — only to fix mistakes. The layer must already exist.

    Args:
        layer_id: The layer to replace (e.g., "layer-3").
        svg_elements: New SVG elements for this layer.
        defs: Optional new defs for this layer.
    """
    session = _require_mutable_session()

    session.log(f"== replace_layer {layer_id}")

    # Save old state for rollback
    old_elements = session.canvas.layers.get(layer_id)
    old_defs = session.canvas.defs.get(layer_id)

    try:
        session.canvas.replace_layer(layer_id, svg_elements, defs)
    except KeyError:
        raise ValueError(f"Layer '{layer_id}' does not exist. Current layers: {session.canvas.get_layer_summary()}")

    # Validate render
    try:
        render_svg_to_png(session.canvas.to_svg())
    except Exception as e:
        # Roll back
        session.canvas.layers[layer_id] = old_elements
        if old_defs is not None:
            session.canvas.defs[layer_id] = old_defs
        elif layer_id in session.canvas.defs:
            del session.canvas.defs[layer_id]
        session.log(f"ROLLED BACK replace {layer_id}: {e}")
        session.flush_log()
        raise ValueError(
            f"Replacing {layer_id} caused a render error and was rolled back: {e}. Fix the SVG and try again."
        )

    session.log(f"Replaced {layer_id}")
    _save_intermediates(session)
    session.flush_log()

    summary = f"Replaced {layer_id}. Layers: {session.canvas.get_layer_summary()}"
    return summary, _render_canvas_image(session.canvas)


@mcp.tool
def set_background(color: str) -> tuple[str, Image]:
    """Change the canvas background color.

    Args:
        color: Hex color string (e.g., "#1a1a2e").
    """
    session = _require_mutable_session()
    session.canvas.background = color
    session.log(f"Background changed to {color}")
    session.flush_log()
    return f"Background set to {color}.", _render_canvas_image(session.canvas)


@mcp.tool
def view_canvas() -> tuple[str, Image]:
    """View the current canvas without making changes.

    Returns the rendered canvas image and a summary of all layers.
    """
    session = _require_session()
    summary = f"Canvas {session.canvas.width}x{session.canvas.height}, bg={session.canvas.background}\n"
    summary += f"Layers: {session.canvas.get_layer_summary()}"
    if session.finished:
        summary += "\n(Drawing is finished)"
    return summary, _render_canvas_image(session.canvas)


@mcp.tool
def finish_drawing() -> tuple[str, Image]:
    """Finish the drawing and save final high-resolution outputs.

    Saves final.svg and final.png (at 2x resolution). After finishing, the canvas
    can still be viewed but not modified. Call create_canvas to start a new drawing.
    """
    session = _require_mutable_session()
    session.finished = True

    final_svg = session.canvas.to_svg()
    save_svg(final_svg, session.output_dir / "final.svg")

    final_png = render_svg_to_png(final_svg, scale=DEFAULT_EXPORT_SCALE)
    save_png(final_png, session.output_dir / "final.png")

    session.log("")
    session.log(f"{'=' * 40}")
    session.log("== Drawing finished")
    session.log(f"Iterations: {session.iteration}")
    session.log(f"Layers: {session.canvas.get_layer_summary()}")
    session.log(f"Output: {session.output_dir}")
    session.flush_log()

    statement_prompt = build_statement_prompt()

    summary = (
        f"Drawing complete! Saved to {session.output_dir}\n"
        f"Iterations: {session.iteration}\n"
        f"Layers: {session.canvas.get_layer_summary()}\n\n"
        f"## Artist Statement\n\n"
        f"{statement_prompt}\n\n"
        f"Please write an artist's statement for this piece, then call "
        f"`save_artist_statement` with the text."
    )
    return summary, Image(data=final_png, format="png")


@mcp.tool
def save_artist_statement(statement: str) -> str:
    """Save an artist's statement for the finished drawing.

    Call this after finish_drawing to save gallery-style prose describing
    the artwork. The statement is written to artist-statement.txt in the
    output directory.

    Args:
        statement: The artist's statement text (plain prose, no markup).
    """
    session = _require_session()
    if not session.finished:
        raise ValueError("Drawing is not finished yet. Call finish_drawing first.")

    path = session.output_dir / "artist-statement.txt"
    path.write_text(statement, encoding="utf-8")

    session.log(f"Artist statement saved ({len(statement)} chars)")
    session.flush_log()

    return f"Artist statement saved to {path}"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
