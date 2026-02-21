from pathlib import Path
from unittest.mock import patch

import pytest

from monet.mcp_server import (
    add_layer,
    create_canvas,
    finish_drawing,
    replace_layer,
    save_artist_statement,
    set_background,
    view_canvas,
)
import monet.mcp_server as mcp_mod


@pytest.fixture(autouse=True)
def _reset_session():
    """Reset global session before each test."""
    mcp_mod._session = None
    yield
    mcp_mod._session = None


@pytest.fixture
def tmp_output(tmp_path):
    """Patch output dir to use a temp directory."""
    with patch("monet.mcp_server.Path") as mock_path:
        # Let Path behave normally except when constructing output dir
        mock_path.side_effect = Path
        yield tmp_path


def _create_in_tmpdir(tmp_path, prompt="test drawing", **kwargs):
    """Helper: create a canvas with output dir under tmp_path."""
    with patch("monet.mcp_server.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "20260221_120000"
        # Patch Path("output") to redirect to tmp_path
        original_path = Path

        def patched_path(*args):
            p = original_path(*args)
            if args and args[0] == "output":
                return tmp_path
            return p

        with patch("monet.mcp_server.Path", side_effect=patched_path):
            return create_canvas(prompt, **kwargs)


class TestCreateCanvas:
    def test_returns_guidelines_and_image(self, tmp_path):
        text, image = _create_in_tmpdir(tmp_path)

        assert "test drawing" in text
        assert "Canvas" in text
        assert "Artistic Guidelines" in text
        assert image.data is not None
        # PNG magic bytes
        assert image.data[:4] == b"\x89PNG"

    def test_initializes_session(self, tmp_path):
        _create_in_tmpdir(tmp_path)

        session = mcp_mod._session
        assert session is not None
        assert session.prompt == "test drawing"
        assert session.canvas.width == 800
        assert session.canvas.height == 600
        assert session.iteration == 0
        assert session.finished is False

    def test_custom_dimensions(self, tmp_path):
        _create_in_tmpdir(tmp_path, width=400, height=300, background="#000000")

        session = mcp_mod._session
        assert session.canvas.width == 400
        assert session.canvas.height == 300
        assert session.canvas.background == "#000000"

    def test_creates_output_dir(self, tmp_path):
        _create_in_tmpdir(tmp_path)

        session = mcp_mod._session
        assert session.output_dir.exists()

    def test_creates_log_file(self, tmp_path):
        _create_in_tmpdir(tmp_path)

        session = mcp_mod._session
        log = (session.output_dir / "artist-log.txt").read_text(encoding="utf-8")
        assert "test drawing" in log


class TestAddLayer:
    def test_adds_layer_and_returns_image(self, tmp_path):
        _create_in_tmpdir(tmp_path)

        text, image = add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')

        assert "layer-1" in text
        assert image.data[:4] == b"\x89PNG"

    def test_increments_iteration(self, tmp_path):
        _create_in_tmpdir(tmp_path)

        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')
        assert mcp_mod._session.iteration == 1

        add_layer('<rect x="10" y="10" width="50" height="50" fill="blue"/>')
        assert mcp_mod._session.iteration == 2

    def test_with_defs(self, tmp_path):
        _create_in_tmpdir(tmp_path)

        text, image = add_layer(
            '<rect fill="url(#iter1-grad)" width="100" height="100"/>',
            defs='<linearGradient id="iter1-grad"><stop offset="0" stop-color="red"/></linearGradient>',
        )

        assert "layer-1" in text
        assert "iter1-grad" in mcp_mod._session.canvas.to_svg()

    def test_invalid_svg_rolls_back(self, tmp_path):
        _create_in_tmpdir(tmp_path)

        # SVG renderers are lenient, so mock a render failure on the validation call.
        with patch("monet.mcp_server.render_svg_to_png", side_effect=Exception("bad SVG")):
            with pytest.raises(ValueError, match="rolled back"):
                add_layer("<not-valid-at-all/>")

        # Session should still be clean
        assert mcp_mod._session.iteration == 0
        assert len(mcp_mod._session.canvas.layers) == 0

    def test_saves_intermediates(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')

        session = mcp_mod._session
        assert (session.output_dir / "iter-001.svg").exists()
        assert (session.output_dir / "iter-001.png").exists()

    def test_before_create_raises(self):
        with pytest.raises(ValueError, match="No active session"):
            add_layer('<circle cx="100" cy="100" r="50"/>')


class TestReplaceLayer:
    def test_replaces_existing_layer(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="10" fill="red"/>')

        text, image = replace_layer("layer-1", '<circle cx="100" cy="100" r="50" fill="blue"/>')

        assert "Replaced layer-1" in text
        assert 'r="50"' in mcp_mod._session.canvas.to_svg()
        assert 'r="10"' not in mcp_mod._session.canvas.to_svg()

    def test_nonexistent_layer_raises(self, tmp_path):
        _create_in_tmpdir(tmp_path)

        with pytest.raises(ValueError, match="does not exist"):
            replace_layer("layer-99", "<rect/>")

    def test_before_create_raises(self):
        with pytest.raises(ValueError, match="No active session"):
            replace_layer("layer-1", "<rect/>")


class TestSetBackground:
    def test_changes_background(self, tmp_path):
        _create_in_tmpdir(tmp_path)

        text, image = set_background("#1a1a2e")

        assert "#1a1a2e" in text
        assert mcp_mod._session.canvas.background == "#1a1a2e"
        assert image.data[:4] == b"\x89PNG"

    def test_before_create_raises(self):
        with pytest.raises(ValueError, match="No active session"):
            set_background("#000000")


class TestViewCanvas:
    def test_returns_summary_and_image(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')

        text, image = view_canvas()

        assert "800x600" in text
        assert "layer-1" in text
        assert image.data[:4] == b"\x89PNG"

    def test_shows_finished_status(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')
        finish_drawing()

        text, image = view_canvas()
        assert "finished" in text.lower()

    def test_before_create_raises(self):
        with pytest.raises(ValueError, match="No active session"):
            view_canvas()


class TestFinishDrawing:
    def test_saves_final_files(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')

        text, image = finish_drawing()

        session = mcp_mod._session
        assert (session.output_dir / "final.svg").exists()
        assert (session.output_dir / "final.png").exists()
        assert "complete" in text.lower()
        assert image.data[:4] == b"\x89PNG"

    def test_marks_session_finished(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')
        finish_drawing()

        assert mcp_mod._session.finished is True

    def test_no_mutations_after_finish(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')
        finish_drawing()

        with pytest.raises(ValueError, match="finished"):
            add_layer('<rect x="0" y="0" width="10" height="10"/>')

        with pytest.raises(ValueError, match="finished"):
            set_background("#000")

    def test_view_still_works_after_finish(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')
        finish_drawing()

        text, image = view_canvas()
        assert image.data[:4] == b"\x89PNG"

    def test_includes_statement_prompt(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')

        text, _image = finish_drawing()

        assert "artist" in text.lower()
        assert "save_artist_statement" in text

    def test_before_create_raises(self):
        with pytest.raises(ValueError, match="No active session"):
            finish_drawing()


class TestSaveArtistStatement:
    def test_saves_file(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')
        finish_drawing()

        result = save_artist_statement("A luminous exploration of form.")

        session = mcp_mod._session
        path = session.output_dir / "artist-statement.txt"
        assert path.exists()
        assert path.read_text(encoding="utf-8") == "A luminous exploration of form."
        assert "saved" in result.lower()

    def test_before_finish_raises(self, tmp_path):
        _create_in_tmpdir(tmp_path)
        add_layer('<circle cx="100" cy="100" r="50" fill="red"/>')

        with pytest.raises(ValueError, match="not finished"):
            save_artist_statement("Too early.")

    def test_before_create_raises(self):
        with pytest.raises(ValueError, match="No active session"):
            save_artist_statement("No session.")
