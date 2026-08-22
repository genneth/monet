---
name: monet
description: Create or iteratively refine original SVG artwork with Monet's file-backed action-look loop. Use for drawing and generative-art requests in this repository; do not use for ordinary application icons or maintenance of existing product SVG assets unless the user explicitly asks to use Monet.
---

# Monet

Create the artwork through repeated SVG edits, deterministic renders, and visual inspection. Treat the prompt as a starting point; let revision discover the work's specific logic.

Before drawing, read [references/artistic-guide.md](references/artistic-guide.md).

## Workflow

1. Choose a concise, descriptive title of roughly 2–6 words. Start a session with `uv run monet new "<prompt>" --title "<title>"`. Set dimensions and background when appropriate. Use the absolute paths in the returned JSON for every later action.
2. Inspect the blank `current.png`. In `artist-notes.md`, note the initial composition and palette, then imagine how a viewer's attention might unfold: what they notice, infer, question, and return to. Write a proposition, not a fixed blueprint or symbol glossary.
3. Write raw SVG elements—without an outer `<svg>` wrapper—to the returned `next_layer` path. Put gradients, filters, patterns, symbols, masks, and clip paths in the matching `next_defs` file. Prefix every definition ID with that layer's iteration number, such as `iter003-water-glow`.
4. Run `uv run monet render <session>`. If validation fails, fix the layer and retry; the last successful `current.svg` and `current.png` remain intact.
5. Inspect the returned `current_png` with the host's local image-viewing capability. Record the strongest observation, then respond by adding, revising, or removing work. Before polishing, test one meaningful alternative to a major choice.
6. Keep `artist-notes.md` useful for resuming: record what works, the current observation and next consequence, important IDs, and meaningful rejected directions. Do not turn it into a transcript.
7. When the image is complete, write a single-paragraph, 3–5 sentence artist statement of at most 80 words to `artist-statement.txt`, then run `uv run monet finish <session>`. Inspect the final PNG before reporting completion.

Use `uv run monet status <session>` to resume or recover paths. Use `uv run monet background <session> <color>` to change the background through the same validated render path.

When the work is another attempt in an existing series, inspect `output/series/` and use `--output` to place it beside the related attempts with the next ordered prefix. Make the attempt name describe the distinguishing approach, not the full prompt.

When the image first feels complete, treat it as halfway. Spend a comparable number of further render-and-inspect passes testing alternatives, revising, and removing; transform existing work more often than you add layers. Then apply the second-look review in the artistic guide and stop when further changes would be merely cosmetic.
