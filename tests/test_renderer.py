import base64
import tempfile
from pathlib import Path

from monet.renderer import render_svg_to_png, render_svg_to_png_base64, save_png, save_svg


SIMPLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>'
)


def test_render_svg_to_png():
    png = render_svg_to_png(SIMPLE_SVG)
    assert isinstance(png, bytes)
    assert len(png) > 0
    # PNG magic bytes
    assert png[:4] == b"\x89PNG"


def test_render_svg_to_png_base64():
    b64 = render_svg_to_png_base64(SIMPLE_SVG)
    assert isinstance(b64, str)
    decoded = base64.standard_b64decode(b64)
    assert decoded[:4] == b"\x89PNG"


def test_render_with_scale():
    png_1x = render_svg_to_png(SIMPLE_SVG, scale=1.0)
    png_2x = render_svg_to_png(SIMPLE_SVG, scale=2.0)
    # 2x should be larger
    assert len(png_2x) > len(png_1x)


def test_save_svg():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.svg"
        save_svg(SIMPLE_SVG, path)
        assert path.read_text() == SIMPLE_SVG


def test_save_png():
    png = render_svg_to_png(SIMPLE_SVG)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.png"
        save_png(png, path)
        assert path.read_bytes() == png
