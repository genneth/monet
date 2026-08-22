from __future__ import annotations

import resvg_py


def render_svg_to_png(svg_string: str, scale: float = 1.0) -> bytes:
    kwargs: dict = {"svg_string": svg_string}
    if scale != 1.0:
        kwargs["zoom"] = int(scale)
    return bytes(resvg_py.svg_to_bytes(**kwargs))
