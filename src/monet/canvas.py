from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SvgCanvas:
    width: int = 800
    height: int = 600
    background: str = "#FFFFFF"
    layers: dict[str, str] = field(default_factory=dict)
    defs: dict[str, str] = field(default_factory=dict)
    _next_layer: int = field(default=1, repr=False)

    def add_layer(self, svg_elements: str, defs: str | None = None) -> str:
        layer_id = f"layer-{self._next_layer}"
        self._next_layer += 1
        self.layers[layer_id] = svg_elements.strip()
        if defs and defs.strip():
            self.defs[layer_id] = defs.strip()
        return layer_id

    def replace_layer(self, layer_id: str, svg_elements: str, defs: str | None = None) -> None:
        if layer_id not in self.layers:
            raise KeyError(f"Layer '{layer_id}' does not exist")
        self.layers[layer_id] = svg_elements.strip()
        if defs and defs.strip():
            self.defs[layer_id] = defs.strip()
        elif layer_id in self.defs:
            del self.defs[layer_id]

    def to_svg(self) -> str:
        all_defs = "\n    ".join(self.defs.values())
        defs_block = f"  <defs>\n    {all_defs}\n  </defs>\n" if all_defs else ""

        layers_block = ""
        for layer_id, content in self.layers.items():
            indented = "\n".join(f"    {line}" for line in content.splitlines())
            layers_block += f'  <g id="{layer_id}">\n{indented}\n  </g>\n'

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">\n'
            f'  <rect width="100%" height="100%" fill="{self.background}"/>\n'
            f"{defs_block}"
            f"{layers_block}"
            f"</svg>"
        )

    def get_layer_summary(self) -> str:
        if not self.layers:
            return "No layers yet."
        parts = []
        for layer_id, content in self.layers.items():
            # Count approximate number of SVG elements by looking for < tags
            # that aren't closing tags
            count = len(re.findall(r"<(?!/)[a-zA-Z]", content))
            parts.append(f"{layer_id}: ~{count} elements")
        return ", ".join(parts)
