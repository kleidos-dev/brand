# SPDX-License-Identifier: MIT
"""The mark: its five shapes, and the checks that hold every copy of it to them.

``logo/src/mark.svg`` is the only drawing kept by hand. Every other file that
shows the mark holds a ``<g class="mark">`` with those five shapes, attribute
for attribute, or a ``<g class="mark mark-ink">`` with the four shapes of the
one-ink mark (the ring, the body's outline, the bit and the stem in one ink,
the body's fill left out). The keyhole is never drawn without its ring: a
shape with the size of the mark's body is refused anywhere but inside such a
group, so neither a ringless keyhole nor a loose, recolored copy of the mark
can be made of the mark's own shapes.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from . import BRAND_ROOT

MARK_SVG = Path("logo/src/mark.svg")
SVG_NS = "http://www.w3.org/2000/svg"

#: The mark box: 100 units, centered on the origin.
BOX = 100.0
#: How far the ring's outer edge sits inside the mark box, in mark units.
RING_INSET = BOX / 2 - (42 + 3 / 2)

Shape = tuple[str, tuple[tuple[str, str], ...]]


def tag_name(element: ET.Element) -> str:
    """Return an element's name without its namespace."""
    return element.tag.rsplit("}", 1)[-1]


def _shape(element: ET.Element) -> Shape:
    return tag_name(element), tuple(sorted(element.attrib.items()))


def shapes(root: Path = BRAND_ROOT) -> list[Shape]:
    """Return the mark's shapes as ``logo/src/mark.svg`` draws them, in order."""
    tree = ET.parse(root / MARK_SVG).getroot()
    return [_shape(child) for child in tree if isinstance(child.tag, str)]


def ink_shapes(mark: list[Shape], ink: str) -> list[Shape]:
    """Return the one-ink mark: every line and solid in *ink*, the body's fill left out."""
    out: list[Shape] = []
    for name, attributes in mark:
        pairs = dict(attributes)
        if pairs.get("stroke", "none") == "none" and name == "rect" and float(pairs["width"]) > 10:
            continue  # the body's fill
        for key in ("fill", "stroke"):
            if pairs.get(key, "none") != "none":
                pairs[key] = ink
        out.append((name, tuple(sorted(pairs.items()))))
    return out


def markup(mark: list[Shape], indent: str = "  ") -> str:
    """Return the shapes as SVG elements, one per line."""
    order = ("cx", "cy", "r", "x", "y", "width", "height", "rx", "fill", "stroke", "stroke-width")
    lines = []
    for name, attributes in mark:
        pairs = sorted(attributes, key=lambda pair: order.index(pair[0]) if pair[0] in order else len(order))
        lines.append(f"{indent}<{name} " + " ".join(f'{key}="{value}"' for key, value in pairs) + "/>")
    return "\n".join(lines)


def group(mark: list[Shape], transform: str | None = None, ink: str | None = None, indent: str = "  ") -> str:
    """Return the mark as a group: ``class="mark"``, or ``"mark mark-ink"`` when drawn in one *ink*."""
    drawn = mark if ink is None else ink_shapes(mark, ink)
    attributes = 'class="mark"' if ink is None else 'class="mark mark-ink"'
    if transform:
        attributes += f' transform="{transform}"'
    return f"{indent}<g {attributes}>\n{markup(drawn, indent + '  ')}\n{indent}</g>"


def _is_glyph(element: ET.Element) -> bool:
    """Tell the ringless keyhole's body: the 40 by 76 pill the firmware's glyph files draw."""
    if tag_name(element) != "rect":
        return False
    try:
        size = float(element.get("width", "0")), float(element.get("height", "0")), float(element.get("rx", "0"))
    except ValueError:
        return False
    return size == (40.0, 76.0, 20.0)


def _size(element: ET.Element) -> tuple[float, float, float] | None:
    """Return a rounded rectangle's width, height and corner radius, or None for anything else."""
    if tag_name(element) != "rect" or element.get("rx") is None:
        return None
    try:
        return float(element.get("width", "0")), float(element.get("height", "0")), float(element.get("rx", "0"))
    except ValueError:
        return None


def body_size(mark: list[Shape]) -> tuple[float, float, float]:
    """Return the width, height and corner radius of the mark's body, the keyhole's pill."""
    for name, attributes in mark:
        pairs = dict(attributes)
        if name == "rect" and "rx" in pairs:
            return float(pairs["width"]), float(pairs["height"]), float(pairs["rx"])
    raise ValueError(f"{MARK_SVG} draws no body")


def findings(svg: Path, mark: list[Shape], inks: frozenset[str], name: str | None = None) -> list[str]:
    """Return what is wrong with the mark in *svg*: a changed copy, a ringless keyhole.

    :param mark: The shapes of ``logo/src/mark.svg``.
    :param inks: The colors a one-ink mark may be drawn in.
    :param name: What to call the file in a finding.
    """
    name = name or str(svg)
    try:
        root = ET.parse(svg).getroot()
    except ET.ParseError as error:
        return [f"{name}: not well-formed XML ({error})"]
    found: list[str] = []
    geometry = [(tag, tuple(pair for pair in attributes if pair[0] not in ("fill", "stroke"))) for tag, attributes in mark]
    # Where the body may stand: inside a mark group, or in the file that is the mark's own drawing.
    is_source = [_shape(child) for child in root if isinstance(child.tag, str)] == mark
    in_group = {id(child) for group in root.iter() if tag_name(group) == "g" and "mark" in group.get("class", "").split()
                for child in group}
    body = body_size(mark)
    loose = 0
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        if _size(element) == body and not is_source and id(element) not in in_group:
            loose += 1
        labels = f"{element.get('id', '')} {element.get('class', '')}".lower()
        if "glyph" in labels:
            found.append(f"{name}: an element named for the ringless glyph ({labels.strip()}); the keyhole is never drawn without its ring")
        if _is_glyph(element):
            found.append(f"{name}: draws the ringless glyph's 40 x 76 body; the keyhole is never drawn without its ring")
        classes = element.get("class", "").split()
        if tag_name(element) != "g" or "mark" not in classes:
            continue
        drawn = [_shape(child) for child in element if isinstance(child.tag, str)]
        if "mark-ink" in classes:
            ink = dict(drawn[0][1]).get("stroke") if drawn else None
            if ink not in inks:
                found.append(f"{name}: a one-ink mark drawn in {ink}, which is not one of the inks ({', '.join(sorted(inks))})")
            elif drawn != ink_shapes(mark, ink):
                found.append(f"{name}: its one-ink mark is not {MARK_SVG}'s shapes in one ink")
        elif drawn != mark:
            same_geometry = [(tag, tuple(pair for pair in attributes if pair[0] not in ("fill", "stroke"))) for tag, attributes in drawn] == geometry
            what = "recolored" if same_geometry else "redrawn"
            found.append(f"{name}: its mark is {what}: the group's shapes are not {MARK_SVG}'s, attribute for attribute")
    if loose:
        found.append(f"{name}: draws the mark's keyhole outside a <g class=\"mark\"> ({loose} shape(s) with its body's size);"
                     " the keyhole is never drawn without its ring, and a copy of the mark is that group, whole")
    return found
