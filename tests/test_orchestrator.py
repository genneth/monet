import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from monet.canvas import SvgCanvas
from monet.orchestrator import DrawingSession, run_drawing_session
from monet.providers.base import DrawingResponse

# Standard planning response prepended to every test's mock responses
PLAN_RESPONSE = """\
<notes>Planning: I'll build this in layers, starting with background elements.</notes>
<status>continue</status>"""


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
        PLAN_RESPONSE,
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
        # 2 API calls: planning + 1 drawing iteration
        assert session.total_input_tokens == 200
        assert session.total_output_tokens == 100
        # Should have final files
        assert (Path(tmp) / "final.svg").exists()
        assert (Path(tmp) / "final.png").exists()
        # Should have iteration files
        assert (Path(tmp) / "iter-001.svg").exists()
        assert (Path(tmp) / "iter-001.png").exists()


def test_multi_iteration_session():
    responses = [
        PLAN_RESPONSE,
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
        PLAN_RESPONSE,
        *[
            f"""<notes>Iter {i}.</notes>
<svg-elements><circle cx="{i * 10}" cy="100" r="5"/></svg-elements>
<status>continue</status>"""
            for i in range(5)
        ],
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
        PLAN_RESPONSE,
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
        PLAN_RESPONSE,
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


def test_planning_notes_prepended():
    """Planning notes should appear in notes_history with [Artistic Plan] marker."""
    responses = [
        PLAN_RESPONSE,
        """<notes>Drawing now.</notes>
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

        assert len(session.notes_history) == 2
        assert session.notes_history[0].startswith("[Artistic Plan]")
        assert "Planning:" in session.notes_history[0]
        assert session.notes_history[1] == "Drawing now."


def test_planning_svg_ignored():
    """SVG elements produced during planning should be ignored."""
    plan_with_svg = """\
<notes>My plan.</notes>
<svg-elements><circle cx="100" cy="100" r="50" fill="red"/></svg-elements>
<status>continue</status>"""

    responses = [
        plan_with_svg,
        """<notes>Real drawing.</notes>
<svg-elements><rect width="100" height="100" fill="blue"/></svg-elements>
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

        # Only 1 layer from the drawing phase, none from planning
        assert len(session.canvas.layers) == 1
        assert 'fill="blue"' in session.canvas.layers["layer-1"]
        # Log should mention the warning
        log_text = (Path(tmp) / "artist-log.txt").read_text()
        assert "Planning phase produced SVG elements" in log_text


def test_planning_api_failure_graceful():
    """If the planning API call fails, drawing should continue without a plan."""
    provider = MagicMock()
    provider.name = "mock"
    provider.default_model = "mock-1"
    # First call (planning) raises, second call (drawing) succeeds
    provider.send_drawing_request.side_effect = [
        Exception("API error during planning"),
        DrawingResponse(
            raw_text="""<notes>Drawing without plan.</notes>
<svg-elements><circle r="10"/></svg-elements>
<status>done</status>""",
            input_tokens=100,
            output_tokens=50,
            model="mock-1",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmp:
        session = DrawingSession(
            prompt="test",
            provider=provider,
            canvas=SvgCanvas(),
            output_dir=Path(tmp),
            max_iterations=5,
        )
        result = run_drawing_session(session)

        assert result.exists()
        assert session.iteration == 1
        # No planning notes, just the drawing note
        assert len(session.notes_history) == 1
        assert "Drawing without plan" in session.notes_history[0]
        # Log should mention the failure
        log_text = (Path(tmp) / "artist-log.txt").read_text()
        assert "Planning phase failed" in log_text


def test_planning_always_enables_thinking():
    """Planning request should have thinking_enabled=True even when session has it off."""
    responses = [
        PLAN_RESPONSE,
        """<notes>Done.</notes>
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
            thinking_enabled=False,
        )
        run_drawing_session(session)

        # Planning call (first) should have thinking enabled
        plan_call = provider.send_drawing_request.call_args_list[0]
        plan_request = plan_call[0][0]
        assert plan_request.thinking_enabled is True
        assert plan_request.iteration == 0

        # Drawing call (second) should respect session setting (False)
        draw_call = provider.send_drawing_request.call_args_list[1]
        draw_request = draw_call[0][0]
        assert draw_request.thinking_enabled is False
        assert draw_request.iteration == 1
