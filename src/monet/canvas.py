from __future__ import annotations

from collections.abc import Iterable
from xml.sax.saxutils import quoteattr


def build_svg(
    width: int,
    height: int,
    background: str,
    layers: Iterable[tuple[str, str | None]],
) -> str:
    layer_list = list(layers)
    definitions = [defs.strip() for _elements, defs in layer_list if defs and defs.strip()]
    joined_defs = "\n    ".join(definitions)
    defs_block = f"  <defs>\n    {joined_defs}\n  </defs>\n" if definitions else ""

    groups = []
    for number, (elements, _defs) in enumerate(layer_list, start=1):
        indented = "\n".join(f"    {line}" for line in elements.strip().splitlines())
        groups.append(f'  <g id="layer-{number}">\n{indented}\n  </g>')
    layers_block = "\n".join(groups)
    if layers_block:
        layers_block += "\n"

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'  <rect width="100%" height="100%" fill={quoteattr(background)}/>\n'
        f"{defs_block}{layers_block}</svg>"
    )
