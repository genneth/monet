from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedResponse:
    notes: str = ""
    svg_elements: str = ""
    defs_elements: str = ""
    replace_layer_id: str | None = None
    replace_elements: str | None = None
    status: str = "continue"
    background: str | None = None


def _extract_tag(text: str, tag: str) -> str:
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_response(text: str) -> ParsedResponse:
    notes = _extract_tag(text, "notes")
    svg_elements = _extract_tag(text, "svg-elements")
    defs_elements = _extract_tag(text, "defs")
    status_raw = _extract_tag(text, "status")
    background = _extract_tag(text, "background") or None

    # Parse status
    status = "continue"
    if status_raw.lower().strip() in ("done", "complete", "finished"):
        status = "done"

    # Parse replace-layer
    replace_layer_id = None
    replace_elements = None
    replace_match = re.search(
        r'<replace-layer\s+id="([^"]+)">(.*?)</replace-layer>',
        text,
        re.DOTALL,
    )
    if replace_match:
        replace_layer_id = replace_match.group(1)
        replace_elements = replace_match.group(2).strip()

    return ParsedResponse(
        notes=notes,
        svg_elements=svg_elements,
        defs_elements=defs_elements,
        replace_layer_id=replace_layer_id,
        replace_elements=replace_elements,
        status=status,
        background=background,
    )
