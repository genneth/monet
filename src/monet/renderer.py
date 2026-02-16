from __future__ import annotations

import base64
from pathlib import Path

import resvg_py


def render_svg_to_png(svg_string: str, scale: float = 1.0) -> bytes:
    kwargs: dict = {"svg_string": svg_string}
    if scale != 1.0:
        kwargs["zoom"] = int(scale)
    return bytes(resvg_py.svg_to_bytes(**kwargs))


def render_svg_to_png_base64(svg_string: str, scale: float = 1.0) -> str:
    png_bytes = render_svg_to_png(svg_string, scale=scale)
    return base64.standard_b64encode(png_bytes).decode("ascii")


def save_svg(svg_string: str, path: Path) -> None:
    path.write_text(svg_string, encoding="utf-8")


def save_png(png_bytes: bytes, path: Path) -> None:
    path.write_bytes(png_bytes)
