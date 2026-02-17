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
| *"ginger cat in the style of picasso"* | ![picasso-cat](examples/picasso-cat.png) |

## Cost estimates

A typical artwork takes 10-15 drawing iterations, plus a planning iteration (iteration 0) that always uses extended thinking. Each drawing iteration sends system prompt + art prompt + growing artist notes + canvas image, and receives ~1000-1500 output tokens of SVG and notes.

Estimates below are for a **15-iteration session** (16 API calls total) including the planning overhead. Gemini estimates assume no caching (implicit caching is available but hit rates are unreliable). Anthropic estimates include incremental prompt caching — each iteration reads the previous call's cached prefix (~46% input cost savings).

### Gemini (no caching)

| Model | Input | Output | Total | Notes |
|-------|-------|--------|-------|-------|
| **Gemini 2.5 Flash** | ~$0.01 | ~$0.06 | **~$0.07** | Cheapest option. |
| **Gemini 3 Flash Preview** | ~$0.02 | ~$0.07 | **~$0.09** | Default Gemini model. |
| **Gemini 2.5 Pro** | ~$0.06 | ~$0.24 | **~$0.29** | Better quality, still reasonable. |
| **Gemini 3 Pro Preview** | ~$0.09 | ~$0.28 | **~$0.37** | Best Gemini quality. |

### Anthropic (with incremental caching)

| Model | Input | Output | Total | Notes |
|-------|-------|--------|-------|-------|
| **Claude Haiku 4.5** | ~$0.04 | ~$0.12 | **~$0.15** | Fast and cheap. |
| **Claude Sonnet 4.6** | ~$0.11 | ~$0.35 | **~$0.46** | Default model. |
| **Claude Opus 4.6** | ~$0.18 | ~$0.59 | **~$0.76** | Best quality. Under $1 per artwork. |

With `--thinking` enabled, expect 2-3x the output token cost due to thinking tokens. Extended thinking generally produces better spatial reasoning and more coherent compositions.

Gemini models have a generous free tier for low-volume usage.

## How it works

Each iteration, the LLM sees the current canvas as an image and outputs new SVG elements to layer on top. It keeps its own "artist notes" as a scratchpad for planning across iterations. The loop runs until the LLM signals it's done or hits the max iteration count.

## License

MIT
