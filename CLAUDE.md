# Monet — LLM-Powered Iterative SVG Art Generator

## Quick Reference

- **Run**: `uv run monet "your prompt here" -v`
- **Test**: `uv run pytest tests/`
- **Install deps**: `uv sync`

## Architecture

Stateless draw-look loop: each iteration renders the canvas to PNG, sends it to an LLM with artist notes, parses XML-tagged response for new SVG elements, and appends them as a layer. No conversation history accumulates — continuity comes from the rendered image + artist notes only.

## Project Layout

- `src/monet/canvas.py` — SVG document state (layers, defs)
- `src/monet/renderer.py` — SVG → PNG via CairoSVG
- `src/monet/response_parser.py` — Parse LLM XML-tagged responses
- `src/monet/prompt.py` — System prompt construction
- `src/monet/providers/` — LLM provider interface + Anthropic/Gemini implementations
- `src/monet/orchestrator.py` — Core draw-look loop
- `src/monet/cli.py` — Click CLI entry point
- `src/monet/config.py` — Defaults

## Conventions

- Python 3.14+, type hints throughout
- Use `from __future__ import annotations` in all modules
- Dataclasses for data containers
- CairoSVG for rendering (requires system cairo library)
- XML-tagged response format (not JSON) for LLM output
- Layer IDs: `layer-N`, defs IDs: `iter{N}-name` to avoid conflicts
