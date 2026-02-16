from monet.response_parser import parse_response


def test_full_response():
    text = """
<notes>Starting with the sky background gradient.</notes>

<defs>
<linearGradient id="iter1-sky">
  <stop offset="0" stop-color="#87CEEB"/>
  <stop offset="1" stop-color="#FFD700"/>
</linearGradient>
</defs>

<svg-elements>
<rect width="800" height="600" fill="url(#iter1-sky)"/>
</svg-elements>

<status>continue</status>
"""
    r = parse_response(text)
    assert "sky background" in r.notes
    assert "linearGradient" in r.defs_elements
    assert "<rect" in r.svg_elements
    assert r.status == "continue"
    assert r.replace_layer_id is None
    assert r.background is None


def test_done_status():
    text = "<notes>Finished.</notes><svg-elements></svg-elements><status>done</status>"
    r = parse_response(text)
    assert r.status == "done"


def test_done_variants():
    for word in ("done", "Done", "complete", "finished", "DONE"):
        text = f"<status>{word}</status>"
        r = parse_response(text)
        assert r.status == "done", f"Failed for '{word}'"


def test_replace_layer():
    text = """
<notes>Fixing layer 2.</notes>
<replace-layer id="layer-2">
<circle cx="400" cy="300" r="100" fill="red"/>
</replace-layer>
<svg-elements></svg-elements>
<status>continue</status>
"""
    r = parse_response(text)
    assert r.replace_layer_id == "layer-2"
    assert "<circle" in r.replace_elements


def test_background_change():
    text = """
<notes>Darkening.</notes>
<background>#1a1a2e</background>
<svg-elements><rect width="10" height="10"/></svg-elements>
<status>continue</status>
"""
    r = parse_response(text)
    assert r.background == "#1a1a2e"


def test_missing_tags():
    text = "Just some random text without tags"
    r = parse_response(text)
    assert r.notes == ""
    assert r.svg_elements == ""
    assert r.status == "continue"


def test_empty_elements():
    text = "<notes></notes><svg-elements></svg-elements><status>continue</status>"
    r = parse_response(text)
    assert r.notes == ""
    assert r.svg_elements == ""
