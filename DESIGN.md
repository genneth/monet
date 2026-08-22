# Monet design

## Principle

Monet owns deterministic drawing state; the agent harness owns intelligence.

There is no embedded model provider, response protocol, or conversational state. The action–look loop is composed from ordinary Codex capabilities:

```text
Codex skill → edit layer file → Monet render → inspect PNG → repeat
```

## Components

- `src/monet/canvas.py` assembles ordered SVG layers and their definitions.
- `src/monet/renderer.py` converts SVG to PNG with `resvg-py`.
- `src/monet/project.py` owns the session manifest, file discovery, validated renders, snapshots, and finalization.
- `src/monet/cli.py` exposes stateless JSON-producing commands for agent and human callers.
- `.agents/skills/monet/` teaches Codex the artistic action–look workflow.

## Persistence contract

`session.json` is versioned and records the concise title, full prompt, canvas configuration, lifecycle status, render count, timestamps, selected artistic profile, and the most recent render error. It does not duplicate layer contents.

Files matching `layers/NNN.svg` are loaded in numeric order. `layers/NNN.defs.svg` is optional and contributes definitions for that layer. Other files in `layers/` are ignored.

Every successful `render` writes an immutable numbered SVG snapshot and updates `current.svg/png`. SVG construction and PNG conversion complete before any current or snapshot artifact is replaced. A failed render updates only `last_error` in the manifest. PNG history is deliberately omitted because the SVG snapshot is reproducible and much smaller.

`finish` requires at least one layer, performs a fresh validation render, writes final artifacts, and changes the manifest status to `finished`. Finished sessions reject further render or background operations.

## Compatibility

The CLI and on-disk format are the compatibility boundary. Another agent harness can drive the same edit–render–inspect loop without importing Monet internals. If a future client genuinely requires typed remote tools, an optional MCP adapter can call `DrawingProject`; it must not introduce separate session behavior.

## Commands

```bash
uv run monet new "prompt"
uv run monet render <session>
uv run monet background <session> <color>
uv run monet status <session>
uv run monet finish <session>
```

Commands emit JSON with absolute artifact paths so callers do not need to infer workspace-relative locations.
