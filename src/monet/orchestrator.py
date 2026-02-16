from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .canvas import SvgCanvas
from .config import DEFAULT_EXPORT_SCALE, DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_THINKING_BUDGET
from .prompt import build_system_prompt
from .providers.base import DrawingRequest, LLMProvider
from .renderer import render_svg_to_png, render_svg_to_png_base64, save_png, save_svg
from .response_parser import parse_response

log = logging.getLogger(__name__)


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


def run_drawing_session(session: DrawingSession, verbose: bool = False) -> Path:
    session.output_dir.mkdir(parents=True, exist_ok=True)

    system_prompt = build_system_prompt(session.canvas.width, session.canvas.height, session.max_iterations)
    empty_streak = 0

    while session.iteration < session.max_iterations:
        session.iteration += 1
        log.info(f"--- Iteration {session.iteration} ---")

        # Render current canvas to PNG
        svg_string = session.canvas.to_svg()
        try:
            canvas_b64 = render_svg_to_png_base64(svg_string)
        except Exception as e:
            log.error(f"Failed to render canvas: {e}")
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
            log.error(f"API call failed: {e}")
            break

        # Track tokens
        session.total_input_tokens += response.input_tokens
        session.total_output_tokens += response.output_tokens
        session.total_thinking_tokens += response.thinking_tokens
        session.total_cache_read_tokens += response.cache_read_tokens
        session.total_cache_creation_tokens += response.cache_creation_tokens

        if verbose:
            log.info(
                f"Tokens — in: {response.input_tokens}, out: {response.output_tokens}"
                f", cache_read: {response.cache_read_tokens}"
                f", cache_create: {response.cache_creation_tokens}"
                + (f", thinking: {response.thinking_tokens}" if response.thinking_tokens else "")
            )

        # Parse response
        parsed = parse_response(response.raw_text)
        if parsed.notes:
            session.notes_history.append(parsed.notes)

        # Append to artist log
        log_path = session.output_dir / "artist-log.txt"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"== Iteration {session.iteration} ==\n")
            f.write(f"Tokens: in={response.input_tokens}, out={response.output_tokens}\n")
            if parsed.notes:
                f.write(f"\n{parsed.notes}\n")
            if parsed.svg_elements:
                element_count = parsed.svg_elements.count("<")
                f.write(f"\n[Added ~{element_count} SVG elements]\n")
            if parsed.replace_layer_id:
                f.write(f"[Replaced {parsed.replace_layer_id}]\n")
            if parsed.background:
                f.write(f"[Background -> {parsed.background}]\n")
            f.write(f"[Status: {parsed.status}]\n\n")

        if verbose and parsed.notes:
            log.info(f"Artist notes: {parsed.notes[:200]}...")

        # Update background if requested
        if parsed.background:
            session.canvas.background = parsed.background
            log.info(f"Background changed to {parsed.background}")

        # Handle layer replacement
        if parsed.replace_layer_id and parsed.replace_elements:
            try:
                session.canvas.replace_layer(parsed.replace_layer_id, parsed.replace_elements)
                log.info(f"Replaced {parsed.replace_layer_id}")
            except KeyError:
                log.warning(f"Cannot replace {parsed.replace_layer_id}: not found")

        # Add new layer
        if parsed.svg_elements:
            layer_id = session.canvas.add_layer(parsed.svg_elements, parsed.defs_elements or None)
            log.info(f"Added {layer_id}")

            # Verify the new SVG renders without errors
            new_svg = session.canvas.to_svg()
            try:
                render_svg_to_png(new_svg)
            except Exception as e:
                log.warning(f"Layer {layer_id} caused render error, removing: {e}")
                del session.canvas.layers[layer_id]
                if layer_id in session.canvas.defs:
                    del session.canvas.defs[layer_id]
                empty_streak += 1
            else:
                empty_streak = 0
        elif not parsed.replace_layer_id:
            log.warning("No SVG elements in response")
            empty_streak += 1
        else:
            empty_streak = 0

        if empty_streak >= 3:
            log.warning("3 consecutive iterations with no new content, stopping.")
            break

        # Save intermediate files
        current_svg = session.canvas.to_svg()
        iter_stem = f"iter-{session.iteration:03d}"
        save_svg(current_svg, session.output_dir / f"{iter_stem}.svg")
        try:
            png_bytes = render_svg_to_png(current_svg)
            save_png(png_bytes, session.output_dir / f"{iter_stem}.png")
        except Exception as e:
            log.warning(f"Could not save intermediate PNG: {e}")

        # Check if done
        if parsed.status == "done":
            log.info("Artist signaled done.")
            break
    else:
        log.info(f"Reached max iterations ({session.max_iterations}).")

    # Save final outputs at higher quality
    final_svg = session.canvas.to_svg()
    final_svg_path = session.output_dir / "final.svg"
    save_svg(final_svg, final_svg_path)

    try:
        final_png = render_svg_to_png(final_svg, scale=DEFAULT_EXPORT_SCALE)
        save_png(final_png, session.output_dir / "final.png")
    except Exception as e:
        log.warning(f"Could not save final PNG: {e}")

    # Summary
    log.info(
        f"Done! {session.iteration} iterations. "
        f"Total tokens — in: {session.total_input_tokens}, out: {session.total_output_tokens}"
        + (f", thinking: {session.total_thinking_tokens}" if session.total_thinking_tokens else "")
    )
    log.info(f"Output: {session.output_dir}")

    return final_svg_path
