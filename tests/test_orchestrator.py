import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from monet.canvas import SvgCanvas
from monet.orchestrator import DrawingSession, run_drawing_session
from monet.providers.base import DrawingResponse


def _make_mock_provider(responses: list[str]) -> MagicMock:
    provider = MagicMock()
    provider.name = "mock"
    provider.default_model = "mock-1"
    provider.send_drawing_request.side_effect = [
        DrawingResponse(raw_text=text, input_tokens=100, output_tokens=50, model="mock-1") for text in responses
    ]
    return provider


def test_basic_session():
    responses = [
        """<notes>Adding a circle.</notes>
<svg-elements><circle cx="400" cy="300" r="100" fill="blue"/></svg-elements>
<status>done</status>""",
    ]
    provider = _make_mock_provider(responses)

    with tempfile.TemporaryDirectory() as tmp:
        session = DrawingSession(
            prompt="a blue circle",
            provider=provider,
            canvas=SvgCanvas(),
            output_dir=Path(tmp),
            max_iterations=5,
        )
        result = run_drawing_session(session)

        assert result.exists()
        assert result.name == "final.svg"
        assert session.iteration == 1
        assert session.total_input_tokens == 100
        assert session.total_output_tokens == 50
        # Should have final files
        assert (Path(tmp) / "final.svg").exists()
        assert (Path(tmp) / "final.png").exists()
        # Should have iteration files
        assert (Path(tmp) / "iter-001.svg").exists()
        assert (Path(tmp) / "iter-001.png").exists()


def test_multi_iteration_session():
    responses = [
        """<notes>Background first.</notes>
<svg-elements><rect width="800" height="600" fill="skyblue"/></svg-elements>
<status>continue</status>""",
        """<notes>Adding sun.</notes>
<svg-elements><circle cx="600" cy="100" r="60" fill="yellow"/></svg-elements>
<status>continue</status>""",
        """<notes>Done!</notes>
<svg-elements><text x="400" y="500">Hello</text></svg-elements>
<status>done</status>""",
    ]
    provider = _make_mock_provider(responses)

    with tempfile.TemporaryDirectory() as tmp:
        session = DrawingSession(
            prompt="sunset",
            provider=provider,
            canvas=SvgCanvas(),
            output_dir=Path(tmp),
            max_iterations=10,
        )
        run_drawing_session(session)

        assert session.iteration == 3
        assert "layer-1" in session.canvas.layers
        assert "layer-2" in session.canvas.layers
        assert "layer-3" in session.canvas.layers


def test_max_iterations_cap():
    responses = [
        f"""<notes>Iter {i}.</notes>
<svg-elements><circle cx="{i * 10}" cy="100" r="5"/></svg-elements>
<status>continue</status>"""
        for i in range(5)
    ]
    provider = _make_mock_provider(responses)

    with tempfile.TemporaryDirectory() as tmp:
        session = DrawingSession(
            prompt="test",
            provider=provider,
            canvas=SvgCanvas(),
            output_dir=Path(tmp),
            max_iterations=3,
        )
        run_drawing_session(session)

        assert session.iteration == 3


def test_replace_layer():
    responses = [
        """<notes>Red circle.</notes>
<svg-elements><circle cx="400" cy="300" r="100" fill="red"/></svg-elements>
<status>continue</status>""",
        """<notes>Fixing to blue.</notes>
<replace-layer id="layer-1">
<circle cx="400" cy="300" r="100" fill="blue"/>
</replace-layer>
<svg-elements></svg-elements>
<status>done</status>""",
    ]
    provider = _make_mock_provider(responses)

    with tempfile.TemporaryDirectory() as tmp:
        session = DrawingSession(
            prompt="test",
            provider=provider,
            canvas=SvgCanvas(),
            output_dir=Path(tmp),
            max_iterations=5,
        )
        run_drawing_session(session)

        assert 'fill="blue"' in session.canvas.layers["layer-1"]


def test_background_change():
    responses = [
        """<notes>Dark bg.</notes>
<background>#000000</background>
<svg-elements><circle r="10"/></svg-elements>
<status>done</status>""",
    ]
    provider = _make_mock_provider(responses)

    with tempfile.TemporaryDirectory() as tmp:
        session = DrawingSession(
            prompt="test",
            provider=provider,
            canvas=SvgCanvas(),
            output_dir=Path(tmp),
            max_iterations=5,
        )
        run_drawing_session(session)

        assert session.canvas.background == "#000000"
