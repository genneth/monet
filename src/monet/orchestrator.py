from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from .canvas import SvgCanvas
from .config import DEFAULT_EXPORT_SCALE, DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_THINKING_BUDGET
from .prompt import build_system_prompt
from .providers.base import DrawingRequest, DrawingResponse, LLMProvider
from .renderer import render_svg_to_png, render_svg_to_png_base64, save_png, save_svg
from .response_parser import ParsedResponse, parse_response

log = logging.getLogger(__name__)

PLANNING_INSTRUCTION = """\
This is iteration 0 — the planning phase. Study the blank canvas dimensions and think through \
your artistic approach before drawing anything.

Plan the following:

1. **Composition** — Layout, focal points, foreground vs background, how you'll use the canvas space
2. **Color palette** — Specific hex colors and their roles in the piece
3. **Iteration sequence** — What to draw in early, middle, and late iterations, pacing relative to \
the {max_iterations} drawing iterations you'll have
4. **SVG techniques** — Which SVG features to use (gradients, filters, clip paths, paths, shapes, \
text, etc.) and where
5. **Potential challenges** — Tricky aspects of the subject and how to handle them in SVG

Output ONLY `<notes>` and `<status>continue</status>`. Do NOT output `<svg-elements>`, `<defs>`, \
or `<background>` — this is planning only."""


@dataclass
class DrawingSession:
    prompt: str
    provider: LLMProvider
    canvas: SvgCanvas
    output_dir: Path
    max_iterations: int = 25
    thinking_enabled: bool = False
    thinking_budget: int = DEFAULT_THINKING_BUDGET
    iteration: int = field(default=0, init=False)
    notes_history: list[str] = field(default_factory=list, init=False)
    total_input_tokens: int = field(default=0, init=False)
    total_output_tokens: int = field(default=0, init=False)
    total_thinking_tokens: int = field(default=0, init=False)
    total_cache_read_tokens: int = field(default=0, init=False)
    total_cache_creation_tokens: int = field(default=0, init=False)


class SessionLogger:
    """Unified logger that writes to both a file and stderr (via logging)."""

    def __init__(self, path: Path, verbose: bool):
        self._path = path
        self._verbose = verbose
        # Truncate log file at start of session
        self._path.write_text("", encoding="utf-8")

    def write(self, msg: str) -> None:
        """Write to the log file, and to stderr if verbose."""
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        if self._verbose:
            log.info(msg)

    def log_session_start(self, session: DrawingSession) -> None:
        self.write(f"Prompt: {session.prompt}")
        self.write(f"Provider: {session.provider.name} (model: {session.provider.default_model})")
        self.write(f"Canvas: {session.canvas.width}x{session.canvas.height}, bg={session.canvas.background}")
        self.write(f"Max iterations: {session.max_iterations}")
        if session.thinking_enabled:
            self.write(f"Thinking: enabled (budget: {session.thinking_budget})")
        self.write("")

    def log_iteration_start(self, iteration: int) -> None:
        self.write(f"{'=' * 60}")
        self.write(f"== Iteration {iteration}")
        self.write(f"{'=' * 60}")

    def log_api_response(self, response: DrawingResponse) -> None:
        # Provider debug messages (cache status, etc.)
        for msg in response.provider_log:
            self.write(f"[provider] {msg}")
        self.write(f"Model: {response.model}")
        parts = [
            f"in={response.input_tokens}",
            f"out={response.output_tokens}",
        ]
        if response.cache_read_tokens:
            parts.append(f"cache_read={response.cache_read_tokens}")
        if response.cache_creation_tokens:
            parts.append(f"cache_create={response.cache_creation_tokens}")
        if response.thinking_tokens:
            parts.append(f"thinking={response.thinking_tokens}")
        self.write(f"Tokens: {', '.join(parts)}")

    def log_parsed_response(self, parsed: ParsedResponse) -> None:
        if parsed.notes:
            self.write(f"\nArtist notes:\n{parsed.notes}\n")
        if parsed.background:
            self.write(f"Background changed to {parsed.background}")
        if parsed.replace_layer_id:
            self.write(f"Replace layer: {parsed.replace_layer_id}")
        if parsed.svg_elements:
            # Count elements and estimate complexity
            element_count = len(re.findall(r"<(?!/)[a-zA-Z]", parsed.svg_elements))
            has_defs = bool(parsed.defs_elements and parsed.defs_elements.strip())
            self.write(f"New SVG: ~{element_count} elements" + (" + defs" if has_defs else ""))
        elif not parsed.replace_layer_id:
            self.write("WARNING: No SVG elements in response")
        self.write(f"Status: {parsed.status}")

    def log_canvas_update(self, msg: str) -> None:
        self.write(msg)

    def log_session_end(self, session: DrawingSession) -> None:
        self.write("")
        self.write(f"{'=' * 60}")
        self.write("== Session complete")
        self.write(f"{'=' * 60}")
        self.write(f"Iterations: {session.iteration}")
        self.write(f"Layers: {session.canvas.get_layer_summary()}")
        self.write(
            f"Total tokens: in={session.total_input_tokens}"
            f", out={session.total_output_tokens}"
            + (f", thinking={session.total_thinking_tokens}" if session.total_thinking_tokens else "")
        )
        if session.total_cache_read_tokens:
            self.write(f"Total cache read tokens: {session.total_cache_read_tokens}")
        if session.total_cache_creation_tokens:
            self.write(f"Total cache creation tokens: {session.total_cache_creation_tokens}")
        self.write(f"Output: {session.output_dir}")


def run_drawing_session(session: DrawingSession, verbose: bool = False) -> Path:
    session.output_dir.mkdir(parents=True, exist_ok=True)

    slog = SessionLogger(session.output_dir / "artist-log.txt", verbose)
    slog.log_session_start(session)

    system_prompt = build_system_prompt(session.canvas.width, session.canvas.height, session.max_iterations)
    empty_streak = 0

    # --- Iteration 0: Planning phase (always uses thinking) ---
    slog.log_iteration_start(0)
    slog.write("Planning phase — thinking through artistic approach...")

    try:
        plan_svg = session.canvas.to_svg()
        plan_b64 = render_svg_to_png_base64(plan_svg)

        plan_request = DrawingRequest(
            system_prompt=system_prompt,
            canvas_png_base64=plan_b64,
            original_prompt=session.prompt,
            iteration=0,
            layer_summary=session.canvas.get_layer_summary(),
            notes_history=[],
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            iteration_message=PLANNING_INSTRUCTION.format(max_iterations=session.max_iterations),
            thinking_enabled=True,
            thinking_budget=session.thinking_budget,
        )

        plan_response = session.provider.send_drawing_request(plan_request)

        # Track tokens
        session.total_input_tokens += plan_response.input_tokens
        session.total_output_tokens += plan_response.output_tokens
        session.total_thinking_tokens += plan_response.thinking_tokens
        session.total_cache_read_tokens += plan_response.cache_read_tokens
        session.total_cache_creation_tokens += plan_response.cache_creation_tokens

        slog.log_api_response(plan_response)

        plan_parsed = parse_response(plan_response.raw_text)
        if plan_parsed.notes:
            session.notes_history.append(f"[Artistic Plan]\n{plan_parsed.notes}")
        slog.log_parsed_response(plan_parsed)

        # Warn if the LLM produced SVG during planning
        if plan_parsed.svg_elements:
            slog.write("WARNING: Planning phase produced SVG elements — ignoring them.")
        if plan_parsed.defs_elements:
            slog.write("WARNING: Planning phase produced defs — ignoring them.")
        if plan_parsed.background:
            slog.write("WARNING: Planning phase changed background — ignoring it.")
    except Exception as e:
        slog.write(f"WARNING: Planning phase failed ({e}), continuing without plan.")

    while session.iteration < session.max_iterations:
        session.iteration += 1
        slog.log_iteration_start(session.iteration)

        # Render current canvas to PNG
        svg_string = session.canvas.to_svg()
        try:
            canvas_b64 = render_svg_to_png_base64(svg_string)
        except Exception as e:
            slog.write(f"ERROR: Failed to render canvas: {e}")
            break

        # Build and send request
        request = DrawingRequest(
            system_prompt=system_prompt,
            canvas_png_base64=canvas_b64,
            original_prompt=session.prompt,
            iteration=session.iteration,
            layer_summary=session.canvas.get_layer_summary(),
            notes_history=list(session.notes_history),
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            thinking_enabled=session.thinking_enabled,
            thinking_budget=session.thinking_budget,
        )

        try:
            response = session.provider.send_drawing_request(request)
        except Exception as e:
            slog.write(f"ERROR: API call failed: {e}")
            break

        # Track tokens
        session.total_input_tokens += response.input_tokens
        session.total_output_tokens += response.output_tokens
        session.total_thinking_tokens += response.thinking_tokens
        session.total_cache_read_tokens += response.cache_read_tokens
        session.total_cache_creation_tokens += response.cache_creation_tokens

        slog.log_api_response(response)

        # Parse response
        parsed = parse_response(response.raw_text)
        if parsed.notes:
            session.notes_history.append(parsed.notes)

        slog.log_parsed_response(parsed)

        # Update background if requested
        if parsed.background:
            session.canvas.background = parsed.background

        # Handle layer replacement
        if parsed.replace_layer_id and parsed.replace_elements:
            try:
                session.canvas.replace_layer(parsed.replace_layer_id, parsed.replace_elements)
                slog.log_canvas_update(f"Replaced {parsed.replace_layer_id}")
            except KeyError:
                slog.log_canvas_update(f"WARNING: Cannot replace {parsed.replace_layer_id}: not found")

        # Add new layer
        if parsed.svg_elements:
            layer_id = session.canvas.add_layer(parsed.svg_elements, parsed.defs_elements or None)
            slog.log_canvas_update(f"Added {layer_id}")

            # Verify the new SVG renders without errors
            new_svg = session.canvas.to_svg()
            try:
                render_svg_to_png(new_svg)
            except Exception as e:
                slog.log_canvas_update(f"WARNING: {layer_id} caused render error, removing: {e}")
                del session.canvas.layers[layer_id]
                if layer_id in session.canvas.defs:
                    del session.canvas.defs[layer_id]
                empty_streak += 1
            else:
                empty_streak = 0
        elif not parsed.replace_layer_id:
            empty_streak += 1
        else:
            empty_streak = 0

        if empty_streak >= 3:
            slog.write("STOPPING: 3 consecutive iterations with no new content.")
            break

        # Save intermediate files
        current_svg = session.canvas.to_svg()
        iter_stem = f"iter-{session.iteration:03d}"
        save_svg(current_svg, session.output_dir / f"{iter_stem}.svg")
        try:
            png_bytes = render_svg_to_png(current_svg)
            save_png(png_bytes, session.output_dir / f"{iter_stem}.png")
        except Exception as e:
            slog.write(f"WARNING: Could not save intermediate PNG: {e}")

        # Check if done
        if parsed.status == "done":
            slog.write("Artist signaled done.")
            break
    else:
        slog.write(f"Reached max iterations ({session.max_iterations}).")

    # Save final outputs at higher quality
    final_svg = session.canvas.to_svg()
    final_svg_path = session.output_dir / "final.svg"
    save_svg(final_svg, final_svg_path)

    try:
        final_png = render_svg_to_png(final_svg, scale=DEFAULT_EXPORT_SCALE)
        save_png(final_png, session.output_dir / "final.png")
    except Exception as e:
        slog.write(f"WARNING: Could not save final PNG: {e}")

    slog.log_session_end(session)

    return final_svg_path
