# Monet

LLM-powered iterative SVG art generator. Give it a prompt, and an LLM will draw it — one layer at a time — by writing SVG elements, rendering the canvas, looking at what it made, and iterating.

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

You'll need at least one API key. Create a `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
```

## Usage

```bash
# Basic usage (defaults to Anthropic Claude)
uv run monet "a sunset over the ocean"

# Use Gemini instead
uv run monet "a cat on a windowsill" -p gemini

# All options
uv run monet "abstract geometry" \
  -p gemini \
  -m gemini-2.5-pro \
  --max-iterations 20 \
  --width 600 --height 600 \
  --background "#000000" \
  -o ./my_art/ \
  --thinking \
  -v
```

Output goes to `output/<timestamp>_<slug>/` with:
- `iter-001.svg`, `iter-001.png`, ... — each iteration's canvas
- `final.svg`, `final.png` — the finished piece (PNG at 2x resolution)
- `artist-log.txt` — the LLM's artistic notes and planning from each iteration

## Examples

| Prompt | Result |
|--------|--------|
| *"a pond of water lilies in the style of Claude Monet"* | ![lilies](examples/lilies.png) |
| *"a self-portrait of your inner experience"* | ![self-portrait](examples/self-portrait.png) |

## How it works

Each iteration, the LLM sees the current canvas as an image and outputs new SVG elements to layer on top. It keeps its own "artist notes" as a scratchpad for planning across iterations. The loop runs until the LLM signals it's done or hits the max iteration count.

## License

MIT
