# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The mark: its five shapes, and the checks that hold every copy of it to them.

``logo/src/mark.svg`` is the only drawing kept by hand. Every other file that
shows the mark holds a ``<g class="mark">`` with those five shapes, attribute
for attribute, or a ``<g class="mark mark-ink">`` with the four shapes of the
one-ink mark (the ring, the body's outline, the bit and the stem in one ink,
the body's fill left out), or a ``<g class="mark mark-small">`` with the
small mark the builder fits to a size under ``logo/src/small-mark.json``'s
``below_px`` (the ring and a solid body in one color, the keyhole cut out of
it). The keyhole is never drawn without its ring: a shape with the size of the
mark's body, or a small mark's body, is refused anywhere but inside such a
group, so neither a ringless keyhole nor a loose, recolored copy of the mark
can be made of the mark's own shapes.
"""

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import BRAND_ROOT, xmlsafe

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


#: What a drawing holds that is not drawn: its title, its description, its metadata.
UNDRAWN = frozenset({"title", "desc", "metadata"})


def _drawn(element: ET.Element) -> list[ET.Element]:
    return [
        child for child in element if isinstance(child.tag, str) and tag_name(child) not in UNDRAWN
    ]


def shapes(root: Path = BRAND_ROOT) -> list[Shape]:
    """Return the mark's shapes as ``logo/src/mark.svg`` draws them, in order (its title and
    description are not shapes)."""
    tree = xmlsafe.parse(root / MARK_SVG)
    return [_shape(child) for child in _drawn(tree)]


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
    order = (
        "cx",
        "cy",
        "r",
        "x",
        "y",
        "width",
        "height",
        "rx",
        "fill",
        "fill-rule",
        "stroke",
        "stroke-width",
        "d",
    )
    lines = []
    for name, attributes in mark:
        pairs = sorted(
            attributes, key=lambda pair: order.index(pair[0]) if pair[0] in order else len(order)
        )
        lines.append(
            f"{indent}<{name} " + " ".join(f'{key}="{value}"' for key, value in pairs) + "/>"
        )
    return "\n".join(lines)


def group(
    mark: list[Shape], transform: str | None = None, ink: str | None = None, indent: str = "  "
) -> str:
    """Return the mark as a group: ``class="mark"``, or ``"mark mark-ink"`` when drawn in one
    *ink*."""
    drawn = mark if ink is None else ink_shapes(mark, ink)
    attributes = 'class="mark"' if ink is None else 'class="mark mark-ink"'
    if transform:
        attributes += f' transform="{transform}"'
    return f"{indent}<g {attributes}>\n{markup(drawn, indent + '  ')}\n{indent}</g>"


# --- The small mark ----------------------------------------------------------------------

SMALL_JSON = Path("logo/src/small-mark.json")


@dataclass(frozen=True)
class SmallFit:
    """The small mark at one size, in whole pixels: what ``small_shapes`` draws."""

    px: int  # the file's side
    ring: int  # the ring's outer diameter: the file's side
    ring_width: float
    body_width: int
    body_height: int
    eye_radius: float
    eye_up: int  # the eye's center, in pixels above the ring's center
    stem_width: int
    stem_length: int  # from the eye's center down, without the half pixel that closes it


def small_numbers(root: Path = BRAND_ROOT) -> dict[str, Any]:
    """Return ``logo/src/small-mark.json``."""
    data: dict[str, Any] = json.loads((root / SMALL_JSON).read_text(encoding="utf-8"))
    return data


def _odd_near(value: float) -> int:
    low = math.floor(value)
    if low % 2 == 0:
        low -= 1
    return low + 2 if (low + 2) - value <= value - low else low


def _parts(mark: list[Shape]) -> dict[str, dict[str, str]]:
    """Name the mark's five shapes: the ring, the body (its fill), the bit and the stem."""
    parts: dict[str, dict[str, str]] = {}
    for name, attributes in mark:
        pairs = dict(attributes)
        if name == "circle":
            parts["ring" if pairs.get("fill") == "none" else "bit"] = pairs
        elif "rx" in pairs:
            parts.setdefault("body", pairs)
            if pairs.get("stroke", "none") != "none":
                parts["body_line"] = pairs
        else:
            parts["stem"] = pairs
    return parts


def ring_color(mark: list[Shape]) -> str:
    """Return the ring's color as ``logo/src/mark.svg`` writes it."""
    return _parts(mark)["ring"]["stroke"]


def small_fit(mark: list[Shape], px: int, numbers: dict[str, Any]) -> SmallFit:
    """Fit the small mark to *px* pixels from the mark's own numbers.

    Every length is the mark's, scaled so that the ring's outer diameter is the
    ring's pixels, then rounded to a whole, odd number of pixels so that each
    edge falls on a pixel's edge and the keyhole stands on one pixel column.
    """
    pixels = numbers["pixels"]
    parts = _parts(mark)
    ring_r, ring_w = float(parts["ring"]["r"]), float(parts["ring"]["stroke-width"])
    line = float(parts["body_line"]["stroke-width"])
    body_w, body_h = float(parts["body"]["width"]) + line, float(parts["body"]["height"]) + line
    ring = px
    unit = ring / (2 * ring_r + ring_w)
    width = max(_odd_near(body_w * unit), pixels["eye"] + 2 * pixels["wall"])
    height = min(_odd_near(width * body_h / body_w), ring - 2 * pixels["ring"] - 2 * pixels["gap"])
    return SmallFit(
        px=px,
        ring=ring,
        ring_width=float(pixels["ring"]),
        body_width=width,
        body_height=height,
        eye_radius=float(pixels["eye_radius"]),
        eye_up=max(1, round(-float(parts["bit"]["cy"]) * unit)),
        stem_width=pixels["stem"],
        stem_length=max(2, round(float(parts["stem"]["height"]) * unit)),
    )


def _n(value: float) -> str:
    rounded = round(value, 3)
    return str(int(rounded)) if rounded == int(rounded) else repr(rounded)


def small_shapes(fit: SmallFit, color: str) -> list[Shape]:
    """Return the small mark in *color*: the ring, and the body as one path with the keyhole cut
    out.

    The body and the keyhole are one ``evenodd`` path, so the keyhole is a hole
    that shows whatever ground the mark stands on, never a second color.
    """
    c = fit.ring / 2
    radius = fit.body_width / 2
    x0, x1 = c - radius, c + radius
    y0, y1 = c - fit.body_height / 2, c + fit.body_height / 2
    body = (
        f"M{_n(x0)} {_n(y0 + radius)}A{_n(radius)} {_n(radius)} 0 0 1 {_n(x1)} {_n(y0 + radius)}"
        f"V{_n(y1 - radius)}A{_n(radius)} {_n(radius)} 0 0 1 {_n(x0)} {_n(y1 - radius)}Z"
    )
    eye_y = c - fit.eye_up
    half = fit.stem_width / 2
    drop = math.sqrt(fit.eye_radius**2 - half**2)  # where the stem's sides meet the eye
    foot = eye_y + fit.stem_length + 0.5
    keyhole = (
        f"M{_n(c + half)} {_n(eye_y + drop)}A{_n(fit.eye_radius)} {_n(fit.eye_radius)} 0 1 0 "
        f"{_n(c - half)} {_n(eye_y + drop)}"
        f"V{_n(foot)}H{_n(c + half)}Z"
    )
    ring = (
        ("cx", _n(c)),
        ("cy", _n(c)),
        ("fill", "none"),
        ("r", _n(c - fit.ring_width / 2)),
        ("stroke", color),
        ("stroke-width", _n(fit.ring_width)),
    )
    solid = (("d", body + keyhole), ("fill", color), ("fill-rule", "evenodd"))
    return [("circle", ring), ("path", solid)]


#: Samples per pixel along each axis when a small mark's coverage is counted.
SAMPLES = 16


def small_pixels(fit: SmallFit, color: str) -> Any:
    """Return the small mark as an RGBA image of *fit*'s pixels, each pixel's alpha its exact
    coverage.

    A browser draws an edge a shade apart from one system to the next, and at
    19 px that shade is a large share of the picture. These pixels are counted
    instead: each pixel's alpha is the share of its SAMPLES x SAMPLES sample
    points that fall inside the shapes ``small_shapes`` draws, the same on
    every machine.
    """
    from PIL import Image

    c = fit.ring / 2
    outer, inner = c**2, (c - fit.ring_width) ** 2
    radius = fit.body_width / 2
    top, bottom = c - fit.body_height / 2 + radius, c + fit.body_height / 2 - radius
    eye_y = c - fit.eye_up
    half = fit.stem_width / 2
    foot = eye_y + fit.stem_length + 0.5

    def inside(x: float, y: float) -> bool:
        if inner <= (x - c) ** 2 + (y - c) ** 2 <= outer:
            return True
        if abs(x - c) > radius:
            return False
        nearest = min(max(y, top), bottom)
        if (x - c) ** 2 + (y - nearest) ** 2 > radius**2:
            return False
        keyhole = (x - c) ** 2 + (y - eye_y) ** 2 <= fit.eye_radius**2 or (
            abs(x - c) <= half and eye_y <= y <= foot
        )
        return not keyhole

    offsets = [(index + 0.5) / SAMPLES for index in range(SAMPLES)]
    rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
    image = Image.new("RGBA", (fit.px, fit.px), (*rgb, 0))
    total = SAMPLES * SAMPLES
    for row in range(fit.px):
        for column in range(fit.px):
            count = sum(inside(column + dx, row + dy) for dy in offsets for dx in offsets)
            if count:
                image.putpixel((column, row), (*rgb, (count * 255 + total // 2) // total))
    return image


def small_group(shapes_: list[Shape], indent: str = "  ") -> str:
    """Return a small mark as its group, ``class="mark mark-small"``."""
    return f'{indent}<g class="mark mark-small">\n{markup(shapes_, indent + "  ")}\n{indent}</g>'


def small_marks(
    mark: list[Shape], colors: frozenset[str] | set[str], root: Path = BRAND_ROOT
) -> list[list[Shape]]:
    """Return every small mark the builder may draw: each size of ``small-mark.json`` in each of
    *colors*."""
    numbers = small_numbers(root)
    return [
        small_shapes(small_fit(mark, px, numbers), color)
        for px in numbers["sizes"]
        for color in sorted(colors)
    ]


def _is_glyph(element: ET.Element) -> bool:
    """Tell the ringless keyhole's body: the 40 by 76 pill the firmware's glyph files draw."""
    if tag_name(element) != "rect":
        return False
    try:
        size = (
            float(element.get("width", "0")),
            float(element.get("height", "0")),
            float(element.get("rx", "0")),
        )
    except ValueError:
        return False
    return size == (40.0, 76.0, 20.0)


def _size(element: ET.Element) -> tuple[float, float, float] | None:
    """Return a rounded rectangle's width, height and corner radius, or None for anything else."""
    if tag_name(element) != "rect" or element.get("rx") is None:
        return None
    try:
        return (
            float(element.get("width", "0")),
            float(element.get("height", "0")),
            float(element.get("rx", "0")),
        )
    except ValueError:
        return None


def body_size(mark: list[Shape]) -> tuple[float, float, float]:
    """Return the width, height and corner radius of the mark's body, the keyhole's pill."""
    for name, attributes in mark:
        pairs = dict(attributes)
        if name == "rect" and "rx" in pairs:
            return float(pairs["width"]), float(pairs["height"]), float(pairs["rx"])
    raise ValueError(f"{MARK_SVG} draws no body")


def findings(
    svg: Path,
    mark: list[Shape],
    inks: frozenset[str],
    name: str | None = None,
    small: list[list[Shape]] | None = None,
) -> list[str]:
    """Return what is wrong with the mark in *svg*: a changed copy, a ringless keyhole.

    :param mark: The shapes of ``logo/src/mark.svg``.
    :param inks: The colors a one-ink mark may be drawn in.
    :param name: What to call the file in a finding.
    :param small: Every small mark the builder may draw (``small_marks``); without it, none is
        accepted.
    """
    small = small or []
    small_bodies = {dict(shapes_[1][1])["d"] for shapes_ in small}
    name = name or str(svg)
    try:
        root = xmlsafe.parse(svg)
    except ET.ParseError as error:
        return [f"{name}: not well-formed XML ({error})"]
    found: list[str] = []
    geometry = [
        (tag, tuple(pair for pair in attributes if pair[0] not in ("fill", "stroke")))
        for tag, attributes in mark
    ]
    # Where the body may stand: inside a mark group, or in the file that is the mark's own drawing.
    is_source = [_shape(child) for child in _drawn(root)] == mark
    in_group = {
        id(child)
        for group in root.iter()
        if tag_name(group) == "g" and "mark" in group.get("class", "").split()
        for child in group
    }
    body = body_size(mark)
    loose = 0
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        if _size(element) == body and not is_source and id(element) not in in_group:
            loose += 1
        if (
            tag_name(element) == "path"
            and element.get("d") in small_bodies
            and id(element) not in in_group
        ):
            loose += 1
        labels = f"{element.get('id', '')} {element.get('class', '')}".lower()
        if "glyph" in labels:
            found.append(
                f"{name}: an element named for the ringless glyph ({labels.strip()}); the keyhole "
                "is never drawn without its ring"
            )
        if _is_glyph(element):
            found.append(
                f"{name}: draws the ringless glyph's 40 x 76 body; the keyhole is never drawn "
                "without its ring"
            )
        classes = element.get("class", "").split()
        if tag_name(element) != "g" or "mark" not in classes:
            continue
        drawn = [_shape(child) for child in element if isinstance(child.tag, str)]
        if "mark-small" in classes:
            if drawn not in small:
                found.append(
                    f"{name}: its small mark is not one the builder fits from {MARK_SVG} and "
                    f"{SMALL_JSON},"
                    " at one of its sizes, in the ring's color or one of the inks"
                )
        elif "mark-ink" in classes:
            ink = dict(drawn[0][1]).get("stroke") if drawn else None
            if ink not in inks:
                found.append(
                    f"{name}: a one-ink mark drawn in {ink}, which is not one of the inks "
                    f"({', '.join(sorted(inks))})"
                )
            elif drawn != ink_shapes(mark, ink):
                found.append(f"{name}: its one-ink mark is not {MARK_SVG}'s shapes in one ink")
        elif drawn != mark:
            same_geometry = [
                (tag, tuple(pair for pair in attributes if pair[0] not in ("fill", "stroke")))
                for tag, attributes in drawn
            ] == geometry
            what = "recolored" if same_geometry else "redrawn"
            found.append(
                f"{name}: its mark is {what}: the group's shapes are not {MARK_SVG}'s, attribute "
                "for attribute"
            )
    if loose:
        found.append(
            f'{name}: draws the mark\'s keyhole outside a <g class="mark"> ({loose} shape(s) with '
            "its body's size);"
            " the keyhole is never drawn without its ring, and a copy of the mark is that group, "
            "whole"
        )
    return found
