import json
from pathlib import Path

from click.testing import CliRunner

from monet.cli import main


def test_new_render_finish_workflow(tmp_path):
    runner = CliRunner()
    session = tmp_path / "art"

    created = runner.invoke(
        main,
        [
            "new",
            "a blue circle",
            "--title",
            "Blue Circle",
            "--width",
            "200",
            "--height",
            "200",
            "--output",
            str(session),
        ],
    )
    assert created.exit_code == 0, created.output
    created_status = json.loads(created.output)
    assert created_status["current_png"] == str(session.resolve() / "current.png")

    Path(created_status["next_layer"]).write_text(
        '<circle cx="100" cy="100" r="60" fill="blue"/>',
        encoding="utf-8",
    )
    rendered = runner.invoke(main, ["render", str(session)])
    assert rendered.exit_code == 0, rendered.output
    rendered_status = json.loads(rendered.output)
    assert rendered_status["render_count"] == 1
    assert Path(rendered_status["snapshot_svg"]).exists()
    assert "snapshot_png" not in rendered_status

    finished = runner.invoke(main, ["finish", str(session)])
    assert finished.exit_code == 0, finished.output
    finished_status = json.loads(finished.output)
    assert finished_status["status"] == "finished"
    assert Path(finished_status["final_png"]).exists()


def test_status_rejects_non_session(tmp_path):
    result = CliRunner().invoke(main, ["status", str(tmp_path)])

    assert result.exit_code != 0
    assert "Not a Monet session" in result.output


def test_new_does_not_overwrite_existing_directory(tmp_path):
    result = CliRunner().invoke(main, ["new", "test", "--output", str(tmp_path)])

    assert result.exit_code != 0
    assert "File exists" in result.output
