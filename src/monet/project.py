from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .canvas import build_svg
from .config import DEFAULT_BACKGROUND, DEFAULT_EXPORT_SCALE, DEFAULT_HEIGHT, DEFAULT_PROFILE, DEFAULT_WIDTH, PROFILES
from .renderer import render_svg_to_png

SCHEMA_VERSION = 1
_LAYER_PATTERN = re.compile(r"^(\d{3})\.svg$")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "artwork"


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _atomic_write_text(path: Path, content: str) -> None:
    _atomic_write_bytes(path, content.encode("utf-8"))


@dataclass
class SessionManifest:
    title: str
    prompt: str
    width: int
    height: int
    background: str
    profile: str
    created_at: str
    updated_at: str
    schema_version: int = SCHEMA_VERSION
    status: str = "active"
    render_count: int = 0
    finished_at: str | None = None
    last_error: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SessionManifest:
        if value.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"Unsupported session schema version: {value.get('schema_version')!r}")
        try:
            manifest = cls(**value)
        except TypeError as exc:
            raise ValueError(f"Invalid session manifest: {exc}") from exc
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Canvas dimensions must be positive")
        if self.profile not in PROFILES:
            raise ValueError(f"Unknown artistic profile: {self.profile}")
        if self.status not in {"active", "finished"}:
            raise ValueError(f"Unknown session status: {self.status}")
        if self.render_count < 0:
            raise ValueError("Render count cannot be negative")


@dataclass(frozen=True)
class RenderResult:
    svg_path: Path
    png_path: Path
    snapshot_svg_path: Path


class DrawingProject:
    def __init__(self, root: Path, manifest: SessionManifest):
        self.root = root.resolve()
        self.manifest = manifest

    @property
    def manifest_path(self) -> Path:
        return self.root / "session.json"

    @property
    def layers_dir(self) -> Path:
        return self.root / "layers"

    @property
    def renders_dir(self) -> Path:
        return self.root / "renders"

    @property
    def current_svg_path(self) -> Path:
        return self.root / "current.svg"

    @property
    def current_png_path(self) -> Path:
        return self.root / "current.png"

    @classmethod
    def create(
        cls,
        prompt: str,
        *,
        title: str | None = None,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        background: str = DEFAULT_BACKGROUND,
        profile: str = DEFAULT_PROFILE,
        output: Path | None = None,
        output_root: Path = Path("output"),
    ) -> DrawingProject:
        if width <= 0 or height <= 0:
            raise ValueError("Canvas dimensions must be positive")
        if profile not in PROFILES:
            raise ValueError(f"Unknown artistic profile: {profile}")

        resolved_title = (title or prompt).strip()
        if not resolved_title:
            raise ValueError("Title cannot be empty")

        blank_svg = build_svg(width, height, background, [])
        blank_png = render_svg_to_png(blank_svg)

        if output is None:
            created = datetime.now()
            root = (
                output_root
                / created.strftime("%Y")
                / created.strftime("%m")
                / f"{created.strftime('%d_%H%M%S_%f')}_{slugify(resolved_title)}"
            )
        else:
            root = output
        root = root.expanduser()
        root.mkdir(parents=True, exist_ok=False)
        (root / "layers").mkdir()
        (root / "renders").mkdir()

        now = _now()
        manifest = SessionManifest(
            title=resolved_title,
            prompt=prompt,
            width=width,
            height=height,
            background=background,
            profile=profile,
            created_at=now,
            updated_at=now,
        )
        project = cls(root, manifest)
        project._save_manifest()
        _atomic_write_text(project.current_svg_path, blank_svg)
        _atomic_write_bytes(project.current_png_path, blank_png)
        _atomic_write_text(
            project.root / "artist-notes.md",
            f"# {resolved_title}\n\nPrompt: {prompt}\n\nProfile: {profile}\n",
        )
        return project

    @classmethod
    def open(cls, root: Path) -> DrawingProject:
        root = root.expanduser().resolve()
        manifest_path = root / "session.json"
        if not manifest_path.is_file():
            raise ValueError(f"Not a Monet session: {root}")
        try:
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read session manifest: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError("Session manifest must be a JSON object")
        return cls(root, SessionManifest.from_dict(value))

    def _save_manifest(self) -> None:
        self.manifest.validate()
        text = json.dumps(asdict(self.manifest), indent=2, sort_keys=True) + "\n"
        _atomic_write_text(self.manifest_path, text)

    def layer_files(self) -> list[Path]:
        layers: list[tuple[int, Path]] = []
        for path in self.layers_dir.iterdir():
            match = _LAYER_PATTERN.fullmatch(path.name)
            if match:
                layers.append((int(match.group(1)), path))
        return [path for _number, path in sorted(layers)]

    def next_layer_path(self) -> Path:
        numbers = [int(path.stem) for path in self.layer_files()]
        number = max(numbers, default=0) + 1
        if number > 999:
            raise ValueError("A session cannot contain more than 999 layers")
        return self.layers_dir / f"{number:03d}.svg"

    def build_svg(self) -> str:
        layers: list[tuple[str, str | None]] = []
        for layer_path in self.layer_files():
            elements = layer_path.read_text(encoding="utf-8").strip()
            if not elements:
                raise ValueError(f"Layer is empty: {layer_path}")
            defs_path = layer_path.with_name(f"{layer_path.stem}.defs.svg")
            defs = defs_path.read_text(encoding="utf-8").strip() if defs_path.exists() else None
            layers.append((elements, defs or None))
        return build_svg(self.manifest.width, self.manifest.height, self.manifest.background, layers)

    def _assert_active(self) -> None:
        if self.manifest.status != "active":
            raise ValueError("Drawing is finished and cannot be modified")

    def _record_error(self, exc: Exception) -> None:
        self.manifest.last_error = str(exc)
        self.manifest.updated_at = _now()
        self._save_manifest()

    def render(self) -> RenderResult:
        self._assert_active()
        try:
            svg = self.build_svg()
            png = render_svg_to_png(svg)
        except Exception as exc:
            self._record_error(exc)
            raise

        render_number = self.manifest.render_count + 1
        snapshot_svg = self.renders_dir / f"{render_number:03d}.svg"
        _atomic_write_text(snapshot_svg, svg)
        _atomic_write_text(self.current_svg_path, svg)
        _atomic_write_bytes(self.current_png_path, png)

        self.manifest.render_count = render_number
        self.manifest.last_error = None
        self.manifest.updated_at = _now()
        self._save_manifest()
        return RenderResult(self.current_svg_path, self.current_png_path, snapshot_svg)

    def set_background(self, color: str) -> RenderResult:
        self._assert_active()
        old_background = self.manifest.background
        self.manifest.background = color
        try:
            return self.render()
        except Exception:
            error = self.manifest.last_error
            self.manifest.background = old_background
            self.manifest.last_error = error
            self.manifest.updated_at = _now()
            self._save_manifest()
            raise

    def finish(self) -> RenderResult:
        self._assert_active()
        if not self.layer_files():
            raise ValueError("Cannot finish a drawing with no layers")
        try:
            svg = self.build_svg()
            current_png = render_svg_to_png(svg)
            final_png = render_svg_to_png(svg, scale=DEFAULT_EXPORT_SCALE)
        except Exception as exc:
            self._record_error(exc)
            raise

        render_number = self.manifest.render_count + 1
        snapshot_svg = self.renders_dir / f"{render_number:03d}.svg"
        _atomic_write_text(snapshot_svg, svg)
        _atomic_write_text(self.current_svg_path, svg)
        _atomic_write_bytes(self.current_png_path, current_png)
        _atomic_write_text(self.root / "final.svg", svg)
        _atomic_write_bytes(self.root / "final.png", final_png)

        now = _now()
        self.manifest.render_count = render_number
        self.manifest.status = "finished"
        self.manifest.finished_at = now
        self.manifest.last_error = None
        self.manifest.updated_at = now
        self._save_manifest()
        return RenderResult(self.root / "final.svg", self.root / "final.png", snapshot_svg)

    def status(self) -> dict[str, Any]:
        layers = self.layer_files()
        result: dict[str, Any] = {
            **asdict(self.manifest),
            "session": str(self.root),
            "layers": [str(path) for path in layers],
            "current_svg": str(self.current_svg_path),
            "current_png": str(self.current_png_path),
            "artist_notes": str(self.root / "artist-notes.md"),
        }
        if self.manifest.status == "active":
            next_layer = self.next_layer_path()
            result["next_layer"] = str(next_layer)
            result["next_defs"] = str(next_layer.with_name(f"{next_layer.stem}.defs.svg"))
        else:
            result["final_svg"] = str(self.root / "final.svg")
            result["final_png"] = str(self.root / "final.png")
        return result
