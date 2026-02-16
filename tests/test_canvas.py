from monet.canvas import SvgCanvas


def test_blank_canvas():
    c = SvgCanvas()
    svg = c.to_svg()
    assert 'width="800"' in svg
    assert 'height="600"' in svg
    assert 'fill="#FFFFFF"' in svg
    assert c.get_layer_summary() == "No layers yet."


def test_add_layer():
    c = SvgCanvas()
    lid = c.add_layer('<circle cx="100" cy="100" r="50"/>')
    assert lid == "layer-1"
    assert "layer-1" in c.layers
    svg = c.to_svg()
    assert '<g id="layer-1">' in svg
    assert '<circle cx="100" cy="100" r="50"/>' in svg


def test_add_multiple_layers():
    c = SvgCanvas()
    l1 = c.add_layer('<rect width="100" height="100"/>')
    l2 = c.add_layer('<circle r="50"/>')
    assert l1 == "layer-1"
    assert l2 == "layer-2"
    assert "layer-1" in c.to_svg()
    assert "layer-2" in c.to_svg()


def test_add_layer_with_defs():
    c = SvgCanvas()
    c.add_layer(
        '<rect fill="url(#g1)" width="100" height="100"/>',
        '<linearGradient id="g1"><stop offset="0" stop-color="red"/></linearGradient>',
    )
    svg = c.to_svg()
    assert "<defs>" in svg
    assert "linearGradient" in svg


def test_replace_layer():
    c = SvgCanvas()
    c.add_layer('<circle r="10"/>')
    c.replace_layer("layer-1", '<circle r="50"/>')
    assert 'r="50"' in c.to_svg()
    assert 'r="10"' not in c.to_svg()


def test_replace_nonexistent_layer():
    c = SvgCanvas()
    try:
        c.replace_layer("layer-99", "<rect/>")
        assert False, "Should have raised KeyError"
    except KeyError:
        pass


def test_layer_summary():
    c = SvgCanvas()
    c.add_layer('<circle r="10"/><rect width="5" height="5"/>')
    summary = c.get_layer_summary()
    assert "layer-1" in summary
    assert "~2" in summary


def test_custom_dimensions():
    c = SvgCanvas(width=400, height=300, background="#000000")
    svg = c.to_svg()
    assert 'width="400"' in svg
    assert 'height="300"' in svg
    assert 'fill="#000000"' in svg
