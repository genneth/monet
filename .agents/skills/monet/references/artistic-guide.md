# Artistic guide

Monet builds one SVG document from ordered layer files. Each layer should add a meaningful visual decision while preserving earlier work.

## Build order

Work roughly from atmosphere to structure:

1. Establish mood, light, and the large tonal fields.
2. Place the major forms and compositional masses.
3. Add depth through overlap, scale, edge quality, and atmospheric perspective.
4. Develop focal areas with greater contrast, sharpness, or internal detail.
5. Unify the palette with restrained glazes, reflected color, or repeated motifs.
6. Finish with only the highlights, texture, and corrections the image actually needs.

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
