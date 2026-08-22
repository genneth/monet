# Artistic guide

Monet builds one SVG document from ordered layer files. Each successful state should embody a meaningful visual decision, but the final work need not preserve every earlier choice.

## Responsiveness to attention

Aim for thickness: a work that yields more as attention continues, not one that merely contains more stuff. Imagine the viewer as an active mind whose attention, expectations, and inferences the work can reward or unsettle.

- Shape a sequence: what will the viewer notice, infer, question, and return to?
- Repeat and transform a few motifs; make major elements relate rather than merely accumulate.
- Leave room for the viewer. Do not explain every symbol or close every space.
- Let inspection overturn choices, and protect productive oddities from generic polish.

Minimal work can be thick; elaborate work can be exhausted at a glance.

## Build order

Work roughly from atmosphere to structure while allowing visual discoveries to revise the plan:

1. Establish mood, light, and the large tonal fields.
2. Place the major forms and compositional masses.
3. Add depth through overlap, scale, edge quality, and atmospheric perspective.
4. Develop focal areas with greater contrast, sharpness, or internal detail.
5. Unify the palette with restrained glazes, reflected color, or repeated motifs.
6. Finish with only the highlights, texture, removals, and corrections the image actually needs.

## SVG strengths

- Prefer gradients, transparency, masks, clipping, and deliberate geometry over imitating raster paint literally.
- Use blur for depth and atmosphere, not as a substitute for form.
- Layer translucent colors so the renderer performs optical mixing.
- Use curved paths for organic boundaries and groups with local transforms for complex assemblies.
- Keep the focal hierarchy visible at the final viewing size. Complexity that collapses into mush is wasted.
- Ground objects with contact shadows, cast shadows, reflections, or environmental overlap.

## Layer discipline

- Add only what the next visual decision requires. Do not cover the accumulated piece with a new opaque full-canvas rectangle.
- Put definitions in the matching `.defs.svg` file and give every ID a unique `iterNNN-` prefix.
- Rotate around an explicit center: `rotate(angle cx cy)`.
- When revising an old layer, inspect dependent definition IDs before changing or removing them.
- External image URLs make sessions non-deterministic; prefer native SVG elements or local data only when the user supplies it.

## Visual review

After every render, judge the image rather than the source code. Check composition at full view, then inspect the focal area for artifacts. Look specifically for accidental tangencies, ungrounded forms, invisible texture, muddy transparency, clipped blur, repeated wallpaper-like motifs, and highlights that compete with the intended focus.

Before finishing, review at three durations:

1. Two seconds: is the large structure compelling?
2. Twenty seconds: do secondary relationships emerge?
3. Two minutes: is there still something to notice or interpret?

If restating the prompt exhausts the image, revise its relationships rather than adding generic polish.
