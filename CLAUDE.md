# Monet — Artistic Guide

For software architecture, project layout, and coding conventions see [DESIGN.md](DESIGN.md).

## Philosophy

You are making SVG art. SVG is not oil paint, but it doesn't have to look like plastic. You can emulate painterly effects or embrace geometric precision. The best results come from leaning into what SVG does natively: gradients, transparency, blur, and clean geometry.

Your goal is mood and light, not literal depiction. Paint atmosphere first, structure second, detail last.

## Stylistic Approaches

### 1. The Painterly Approach (Impressionism, Baroque, Organic)
- **Vector Impasto:** Don't just fill a shape with a gradient. Build it up from hundreds of small, semi-transparent paths (dabs) of varying hues. This breaks the "digital" smoothness.
- **Texture is Mandatory:** Use `<feTurbulence>` filters to add grain. A flat gradient looks like vector art; a grainy gradient looks like physical media.
- **Subsurface Scattering:** For skin or organic matter, lay down a saturated "warm" layer (reds/oranges) *before* the main skin tones. Let it bleed through the edges to simulate life.
- **Lost Edges:** Use gradients that fade to `stop-opacity="0"` to let shadows merge with the background.

### 2. The Geometric Approach (Constructivism, Bauhaus, Minimalist)
- **Precision is Beauty:** A perfect circle or straight line is a feature, not a bug. Use them boldly.
- **Tension Lines:** Use very thin (`stroke-width="0.5"`) high-contrast lines to connect heavy shapes. This creates architectural tension.
- **Boolean Intersections:** Create interest where shapes overlap. Use semi-transparent fills to create new colors at intersections.
- **The "Void":** Geometric art needs breathing room. Don't fear large areas of negative space (dark or light) to balance heavy elements.

## How to Build a Piece

Work in roughly this order across your iterations:

1. **Mood & atmosphere** — Full-canvas gradient washes or noise textures to set the tonal palette. This is your underpainting.
2. **Major forms** — Blurred, soft-edged shapes for organic styles, or large distinct geometric planes for abstract styles. Establish the composition massing.
3. **Structure & depth** — Sharper mid-ground elements. Organic `<path>` curves for natural forms; precise vectors for architecture. Vary size, opacity, and rotation.
4. **Focal points** — The elements the eye should land on. Use radial gradients fading to transparent for luminous glows. Brighter, sharper, and more detailed than surroundings.
5. **Glazing & Unifying** — Large, very low opacity (5-10%) gradients or colored rects over the whole canvas or specific areas to unify the color palette and "bind" the layers together.
6. **Finishing touches** — Vignette, grain/texture filters, final sharp highlights (catchlights).

## SVG Techniques That Work Well

- **Gradients over flat fills** — A single radial gradient does what hundreds of flat ellipses cannot. Use them everywhere.
- **Noise Filters** — Use `<feTurbulence>` combined with `<feColorMatrix>` to create subtle grain. This kills the "plastic" look of vector gradients.
- **Blur for atmosphere** — `feGaussianBlur` dissolves edges naturally. Use different `stdDeviation` values for depth of field.
- **Layered transparency** — Overlapping translucent shapes mix colour optically. Build up in thin layers.
- **Radial glow for focal points** — A radial gradient from bright centre to fully transparent edge creates a luminous glow. Far more evocative than drawing literal petals or light rays.
- **Organic paths** — `<path>` with curves (C/S commands) for lily pads, shorelines, branches. Never use rectangles for natural forms.
- **Vignette** — Radial gradient (transparent centre, dark edges) on a full-canvas rect frames the composition and draws the eye inward.
- **Clipping Paths** — Use `<clipPath>` to contain "messy" painterly strokes inside a crisp outline (e.g., a figure or object), giving you a hard edge on the outside but a soft, textured interior.
- **Light bands** — Horizontal gradients for water surface reflections; vertical forms for tree/object reflections.

## Common Pitfalls

- **The "Plastic Doll" Effect** — Relying solely on smooth radial gradients for skin or faces makes them look like plastic toys. Break up the surface with texture and irregular "dabs" of color.
- **Rotation origin** — Always use `transform="rotate(angle cx cy)"`. Without cx/cy, rotation happens around (0,0) and elements scatter off-canvas.
- **Def ID conflicts** — **CRITICAL:** Every gradient/filter/pattern ID must be prefixed with the layer number: `iter3-sunGradient`, `iter7-blurFilter`. Reusing IDs breaks the rendering.
- **Chasing element count** — Complexity comes from the fills and layering, not just the number of shapes. 136 elements with rich filters beat 1,150 flat shapes.
- **Literal depiction** — Don't construct a flower petal by petal. A glowing radial gradient reads as "flower" and feels more alive.
- **Covering previous work** — Never redraw the full background or lay an opaque rect over everything. Layers accumulate — build on what's there.
- **The "Floating Object"** — Objects need to interact with their environment. Add cast shadows, contact shadows, and reflections to ground them.
- **Overworking** — 8-15 iterations is usually right. When you're adding marginal details, stop.

## Composition Matters More Than Technique

The difference between a good piece and a forgettable one is almost always compositional, not technical. Before you start drawing, think about:

- Where is the light coming from? Let that drive your warm/cool palette split.
- What gives depth? Vertical reflections against horizontal water. Overlapping planes at different blur levels. Atmospheric perspective (cooler, lighter, blurrier in the distance).
- Where should the eye rest? Place your brightest, sharpest element there. Let everything else support it.
- What's the emotional tone? Warm diffused light = peaceful. High contrast = dramatic. Cool muted palette = contemplative.
