---
name: monet
description: Create or iteratively refine original SVG artwork with Monet's file-backed action-look loop. Use for drawing and generative-art requests in this repository; do not use for ordinary application icons or maintenance of existing product SVG assets unless the user explicitly asks to use Monet.
---

# Monet

Create the artwork through repeated SVG edits, deterministic renders, and visual inspection.

Before drawing, read [references/artistic-guide.md](references/artistic-guide.md). Read at most one additional profile when it fits the request:

- Read [references/painterly.md](references/painterly.md) for organic, atmospheric, impressionist, figurative, or painterly work.
- Read [references/systems.md](references/systems.md) for generative, geometric, plotter-like, modular, or high-density work.

## Workflow

1. Choose a concise, descriptive title of roughly 2–6 words. Start a session with `uv run monet new "<prompt>" --title "<title>"`. Set dimensions, background, and `--profile painterly|systems` when appropriate. Use the absolute paths in the returned JSON for every later action.
2. Inspect the blank `current.png`, then record a concise composition and palette plan in `artist-notes.md`.
3. Write raw SVG elements—without an outer `<svg>` wrapper—to the returned `next_layer` path. Put gradients, filters, patterns, symbols, masks, and clip paths in the matching `next_defs` file. Prefix every definition ID with that layer's iteration number, such as `iter003-water-glow`.
4. Run `uv run monet render <session>`. If validation fails, fix the layer and retry; the last successful `current.svg` and `current.png` remain intact.
5. Inspect the returned `current_png` with the host's local image-viewing capability. Decide from the image whether to add a new layer or revise an existing layer file, then render again.
6. Keep `artist-notes.md` useful for resuming the session: record what is working, the next intended change, and any important IDs or structural choices. Do not turn it into a transcript.
7. When the image is complete, write a single-paragraph, 3–5 sentence artist statement of at most 80 words to `artist-statement.txt`, then run `uv run monet finish <session>`. Inspect the final PNG before reporting completion.

Use `uv run monet status <session>` to resume or recover paths. Use `uv run monet background <session> <color>` to change the background through the same validated render path.

When the work is another attempt in an existing series, inspect `output/series/` and use `--output` to place it beside the related attempts with the next ordered prefix. Make the attempt name describe the distinguishing approach, not the full prompt.

Treat 8–15 successful renders as a useful range, not a quota. Stop when further changes would be marginal.
