from monet.renderer import render_svg_to_png


SIMPLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
    '<rect width="100" height="100" fill="red"/></svg>'
)


def test_render_svg_to_png():
    png = render_svg_to_png(SIMPLE_SVG)

    assert png.startswith(b"\x89PNG")


def test_render_with_scale():
    assert len(render_svg_to_png(SIMPLE_SVG, scale=2.0)) > len(render_svg_to_png(SIMPLE_SVG))
