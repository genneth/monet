from xml.etree import ElementTree

from monet.canvas import build_svg


def test_builds_ordered_layers_and_defs():
    svg = build_svg(
        400,
        300,
        "#101820",
        [
            ('<rect id="first" width="10" height="10"/>', '<linearGradient id="iter001-fill"/>'),
            ('<circle id="second" r="5"/>', None),
        ],
    )

    assert 'width="400"' in svg
    assert "iter001-fill" in svg
    assert svg.index('id="first"') < svg.index('id="second"')
    assert 'id="layer-1"' in svg
    assert 'id="layer-2"' in svg


def test_blank_canvas():
    svg = build_svg(800, 600, "#FFFFFF", [])

    assert "<defs>" not in svg
    assert 'fill="#FFFFFF"' in svg


def test_background_is_xml_escaped():
    root = ElementTree.fromstring(build_svg(100, 100, '" onload="bad', []))
    background = root.find("{http://www.w3.org/2000/svg}rect")

    assert background is not None
    assert background.attrib == {"width": "100%", "height": "100%", "fill": '" onload="bad'}
