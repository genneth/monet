# Monet

Monet is a file-backed SVG canvas for iterative artwork with Codex. Codex writes a layer, Monet renders it, Codex looks at the result, and the loop continues until the piece is complete.

Monet contains no LLM client or autonomous agent loop. Intelligence, planning, and image inspection belong to the surrounding agent harness; Monet provides deterministic canvas assembly, rendering, validation, history, and final exports.

## Setup

Monet requires Python 3.14+ and [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

The repository includes a Codex skill at `.agents/skills/monet`. From this repository, ask Codex to create an artwork; the skill guides the complete action–look workflow.

## Manual workflow

Create a session:

```bash
uv run monet new "a sunset over the ocean" --title "Afterlight" --profile painterly
```

The command returns JSON containing absolute paths for the session, blank canvas, notes, and next layer. Write raw SVG elements to `next_layer`, with any definitions in `next_defs`, then render:

```bash
uv run monet render /absolute/path/to/output/session
```

Inspect `current.png`, add or revise layer files, and render again. Existing layers can be changed directly; render snapshots record every successful visual state independently of layer numbering.

Other commands:

```bash
uv run monet status <session>
uv run monet background <session> "#101820"
uv run monet finish <session>
```

`finish` validates the current layer files, writes `final.svg` and a 2× `final.png`, then marks the session immutable.

## Session format

```text
output/<year>/<month>/<day>_<time>_<title>/
├── session.json
├── artist-notes.md
├── artist-statement.txt       # written by the agent when complete
├── layers/
│   ├── 001.svg               # raw SVG elements
│   ├── 001.defs.svg          # optional definitions for layer 001
│   └── 002.svg
├── renders/
│   ├── 001.svg
│   └── ...
├── current.svg
├── current.png
├── final.svg
└── final.png
```

Layer files are the source of truth. Numbered SVG snapshots preserve successful source states without accumulating a PNG for every iteration. If a render fails, Monet records the error in `session.json` and leaves the last successful `current.svg` and `current.png` untouched. A session can be resumed from any process with `monet status`.

Related experiments can live under `output/series/<series-name>/` by passing an exact `--output` path. Use ordered attempt names such as `03--luminous-watercolor` so the relationship and distinguishing approach remain visible in the filesystem.

## Development

```bash
uv run pytest
uv run ruff check .
```

See [DESIGN.md](DESIGN.md) for the code-level contract.

## Examples

These are selected from 56 historical runs, now grouped into 11 related series
and a set of standalone works. Captions preserve the creating model and date
where the run recorded them; “model unrecorded” is deliberate rather than a
guessed attribution. Every image below is the actual SVG source.

| | | | |
|---|---|---|---|
| [<img src="examples/showcase/2026-02-16--water-lilies--gemini-3-flash.png" alt="Water lilies by Gemini 3 Flash" width="240">](examples/showcase/2026-02-16--water-lilies--gemini-3-flash.svg)<br>**Water Lilies**<br>Gemini 3 Flash · 16 Feb 2026 | [<img src="examples/showcase/2026-02-16--picasso-cat--gemini-3-pro.png" alt="Picasso cat by Gemini 3 Pro" width="240">](examples/showcase/2026-02-16--picasso-cat--gemini-3-pro.svg)<br>**Picasso Cat**<br>Gemini 3 Pro · 16 Feb 2026 | [<img src="examples/showcase/2026-02-17--girl-with-a-pearl-earring--gemini-3-flash.png" alt="Girl with a Pearl Earring after Picasso by Gemini 3 Flash" width="240">](examples/showcase/2026-02-17--girl-with-a-pearl-earring--gemini-3-flash.svg)<br>**Girl with a Pearl Earring, after Picasso**<br>Gemini 3 Flash · 17 Feb 2026 | [<img src="examples/showcase/2026-02-17--toddler-quants--gemini-3-flash.png" alt="Toddler Quants after Miro by Gemini 3 Flash" width="240">](examples/showcase/2026-02-17--toddler-quants--gemini-3-flash.svg)<br>**Toddler Quants, after Miró**<br>Gemini 3 Flash · 17 Feb 2026 |
| [<img src="examples/showcase/2026-02-18--purple-fuzzy-cat--gemini-3-flash.png" alt="Purple fuzzy cat by Gemini 3 Flash" width="240">](examples/showcase/2026-02-18--purple-fuzzy-cat--gemini-3-flash.svg)<br>**Purple Fuzzy Cat**<br>Gemini 3 Flash · 18 Feb 2026 | [<img src="examples/showcase/2026-02-18--pen-plotter-self-portrait--gemini-3-flash.png" alt="Pen-plotter self-portrait by Gemini 3 Flash" width="240">](examples/showcase/2026-02-18--pen-plotter-self-portrait--gemini-3-flash.svg)<br>**Pen-plotter Self-Portrait**<br>Gemini 3 Flash · 18 Feb 2026 | [<img src="examples/showcase/2026-02-21--matisse-tropical-garden--model-unrecorded.png" alt="Matisse tropical garden by an unrecorded model" width="240">](examples/showcase/2026-02-21--matisse-tropical-garden--model-unrecorded.svg)<br>**Tropical Garden**<br>Model unrecorded · 21 Feb 2026 | [<img src="examples/showcase/2026-02-22--lexus-lc500-study--model-unrecorded.png" alt="Lexus LC 500 study by an unrecorded model" width="240">](examples/showcase/2026-02-22--lexus-lc500-study--model-unrecorded.svg)<br>**Lexus LC 500 Study**<br>Model unrecorded · 22 Feb 2026 |
| [<img src="examples/showcase/2026-03-22--spot-painting--claude-opus-4-6.png" alt="Spot painting by Claude Opus 4.6" width="240">](examples/showcase/2026-03-22--spot-painting--claude-opus-4-6.svg)<br>**Spot Painting**<br>Claude Opus 4.6 · 22 Mar 2026 | [<img src="examples/showcase/2026-04-27--great-wave--model-unrecorded.png" alt="Great Wave study by an unrecorded model" width="240">](examples/showcase/2026-04-27--great-wave--model-unrecorded.svg)<br>**Great Wave**<br>Model unrecorded · 27 Apr 2026 | [<img src="examples/showcase/2026-06-14--pop-art-landscape--claude-opus-4-8.png" alt="Pop-art landscape by Claude Opus 4.8" width="240">](examples/showcase/2026-06-14--pop-art-landscape--claude-opus-4-8.svg)<br>**Pop-art Landscape**<br>Claude Opus 4.8 · 14 Jun 2026 | [<img src="examples/showcase/2026-06-24--kandinsky-constructivist-ink--gemini-2-pro.png" alt="Constructivist ink by Gemini 2 Pro" width="240">](examples/showcase/2026-06-24--kandinsky-constructivist-ink--gemini-2-pro.svg)<br>**Constructivist Ink**<br>Gemini 2.0 Pro · 24 Jun 2026 |
| [<img src="examples/showcase/2026-06-24--feininger-marine--claude-opus-4-6.png" alt="Feininger marine by Claude Opus 4.6" width="240">](examples/showcase/2026-06-24--feininger-marine--claude-opus-4-6.svg)<br>**Feininger Marine**<br>Claude Opus 4.6 · 24 Jun 2026 | [<img src="examples/showcase/2026-07-02--self-portrait--gemma-4.png" alt="Self-portrait by Gemma 4" width="240">](examples/showcase/2026-07-02--self-portrait--gemma-4.svg)<br>**Self-Portrait**<br>Gemma 4 · 2 Jul 2026 | [<img src="examples/showcase/2026-08-22--water-lilies--sol-5-6.png" alt="Water lilies by Sol 5.6" width="240">](examples/showcase/2026-08-22--water-lilies--sol-5-6.svg)<br>**Water Lilies**<br>Sol 5.6 · 22 Aug 2026 | [<img src="examples/showcase/2026-08-22--picasso-cat--sol-5-6.png" alt="Picasso cat by Sol 5.6" width="240">](examples/showcase/2026-08-22--picasso-cat--sol-5-6.svg)<br>**Picasso Cat**<br>Sol 5.6 · 22 Aug 2026 |

The [August 2026 Sol study](examples/sol-5.6/) records all three blind trials,
including the exact reused prompts and the pen-plotter self-portrait that was
not selected for the main gallery. The repository also retains the
[earlier hand-selected PNG set](examples/selected/).

## License

MIT
