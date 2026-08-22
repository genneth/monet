import json
from pathlib import Path
from unittest.mock import patch

import pytest

from monet.project import DrawingProject, SCHEMA_VERSION, slugify


def _create(tmp_path: Path, **kwargs) -> DrawingProject:
    return DrawingProject.create("test drawing", output=tmp_path / "session", **kwargs)


def test_create_initializes_file_backed_session(tmp_path):
    project = _create(tmp_path, width=400, height=300, background="#101820", profile="systems")

    manifest = json.loads(project.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["status"] == "active"
    assert manifest["profile"] == "systems"
    assert project.current_png_path.read_bytes().startswith(b"\x89PNG")
    assert project.next_layer_path().name == "001.svg"


def test_default_session_names_are_unique(tmp_path):
    first = DrawingProject.create("same prompt", output_root=tmp_path)
    second = DrawingProject.create("same prompt", output_root=tmp_path)

    assert first.root != second.root
    assert first.root.name.endswith("_same-prompt")
    assert first.root.parent.parent.parent == tmp_path


def test_slugify_has_fallback():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("你好") == "artwork"


def test_render_builds_ordered_layers_and_snapshot(tmp_path):
    project = _create(tmp_path)
    (project.layers_dir / "002.svg").write_text('<circle id="second" r="5"/>', encoding="utf-8")
    (project.layers_dir / "001.svg").write_text(
        '<rect id="first" width="10" height="10" fill="url(#iter001-fill)"/>',
        encoding="utf-8",
    )
    (project.layers_dir / "001.defs.svg").write_text(
        '<linearGradient id="iter001-fill"><stop stop-color="red"/></linearGradient>',
        encoding="utf-8",
    )

    result = project.render()
    svg = project.current_svg_path.read_text(encoding="utf-8")

    assert svg.index('id="first"') < svg.index('id="second"')
    assert "iter001-fill" in svg
    assert result.snapshot_svg_path == project.renders_dir / "001.svg"
    assert not (project.renders_dir / "001.png").exists()
    assert project.manifest.render_count == 1
    assert project.next_layer_path().name == "003.svg"


def test_invalid_edit_preserves_last_good_render(tmp_path):
    project = _create(tmp_path)
    before_svg = project.current_svg_path.read_bytes()
    before_png = project.current_png_path.read_bytes()
    (project.layers_dir / "001.svg").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Layer is empty"):
        project.render()

    assert project.current_svg_path.read_bytes() == before_svg
    assert project.current_png_path.read_bytes() == before_png
    assert project.manifest.render_count == 0
    assert "Layer is empty" in project.manifest.last_error


def test_reopen_resumes_from_disk(tmp_path):
    project = _create(tmp_path)
    (project.layers_dir / "001.svg").write_text('<circle r="5"/>', encoding="utf-8")
    project.render()

    reopened = DrawingProject.open(project.root)

    assert reopened.manifest.render_count == 1
    assert reopened.layer_files() == [reopened.layers_dir / "001.svg"]
    assert reopened.next_layer_path().name == "002.svg"


def test_background_failure_rolls_back_manifest(tmp_path):
    project = _create(tmp_path, background="#ffffff")

    with patch("monet.project.render_svg_to_png", side_effect=RuntimeError("render failed")):
        with pytest.raises(RuntimeError, match="render failed"):
            project.set_background("bad-color")

    reopened = DrawingProject.open(project.root)
    assert reopened.manifest.background == "#ffffff"
    assert reopened.manifest.last_error == "render failed"


def test_finish_writes_final_artifacts_and_closes_session(tmp_path):
    project = _create(tmp_path)
    (project.layers_dir / "001.svg").write_text(
        '<circle cx="100" cy="100" r="50" fill="blue"/>',
        encoding="utf-8",
    )

    result = project.finish()

    assert result.svg_path == project.root / "final.svg"
    assert result.png_path.read_bytes().startswith(b"\x89PNG")
    assert project.manifest.status == "finished"
    assert project.manifest.finished_at is not None
    assert "final_png" in project.status()
    with pytest.raises(ValueError, match="finished"):
        project.render()


def test_title_is_recorded_and_used_for_default_path(tmp_path):
    project = DrawingProject.create(
        "a very long and detailed prompt",
        title="Quiet Geometry",
        output_root=tmp_path,
    )

    assert project.manifest.title == "Quiet Geometry"
    assert project.root.name.endswith("_quiet-geometry")
    assert project.root.parent.parent.parent == tmp_path


def test_cannot_finish_blank_session(tmp_path):
    project = _create(tmp_path)

    with pytest.raises(ValueError, match="no layers"):
        project.finish()


def test_rejects_existing_output_directory(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()

    with pytest.raises(FileExistsError):
        DrawingProject.create("test", output=output)


def test_rejects_invalid_manifest(tmp_path):
    root = tmp_path / "broken"
    root.mkdir()
    (root / "session.json").write_text('{"schema_version": 999}', encoding="utf-8")

    with pytest.raises(ValueError, match="schema version"):
        DrawingProject.open(root)
