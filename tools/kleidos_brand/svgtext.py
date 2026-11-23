# SPDX-License-Identifier: MIT
"""The ``<text>`` elements of an SVG source, turned into outlines.

A source keeps its words as live text, set in the pinned families by plain
presentation attributes, so it opens and edits in any SVG editor that has the
fonts. What is published and what is drawn to pixels holds paths only.

What a ``<text>`` may carry is small on purpose, so that what this module
draws is what a browser with the fonts would draw:

- ``x``, ``y``: the start (or middle, or end) of the baseline;
- ``font-family``: ``Mona Sans`` or ``Mona Sans Mono``;
- ``font-size``: in user units;
- ``font-weight``: the ``wght`` axis; ``font-stretch``: the ``wdth`` axis, as a percentage;
- ``style="font-variation-settings:'opsz' N"``: the optical size, the one property a style may hold;
- ``letter-spacing``: in ems (``-0.03em``);
- ``text-anchor``: ``start``, ``middle`` or ``end``;
- ``fill``: a token color;
- ``data-case="upper"``: the words are set in capitals;
- children: text, and ``<tspan fill="…">`` runs that change the color only.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from . import BRAND_ROOT, lettering

SVG_NS = "http://www.w3.org/2000/svg"
OPSZ = re.compile(r"""\s*font-variation-settings\s*:\s*["']opsz["']\s+(\d+(?:\.\d+)?)\s*;?\s*""")
EM = re.compile(r"(-?\d+(?:\.\d+)?)em")


def _local(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _number(value: float) -> str:
    rounded = round(value, 3)
    return str(int(rounded)) if rounded == int(rounded) else repr(rounded)


@dataclass(frozen=True)
class Run:
    """A stretch of a line in one color: its first and last character, and its fill."""

    first: int
    last: int
    fill: str


@dataclass(frozen=True)
class Set:
    """A ``<text>`` element as it is set: the shaped line, where it starts, its scale and its runs."""

    line: lettering.Line
    x: float
    y: float
    scale: float
    runs: tuple[Run, ...]

    def box(self) -> tuple[float, float, float, float]:
        """Return the ink box in user units: ``(left, top, right, bottom)``."""
        x0, y0, x1, y1 = self.line.bounds()
        return (
            self.x + x0 * self.scale,
            self.y - y1 * self.scale,
            self.x + x1 * self.scale,
            self.y - y0 * self.scale,
        )


def words(element: ET.Element) -> tuple[str, tuple[Run, ...]]:
    """Return a ``<text>`` element's words and their color runs, capitals applied."""
    upper = element.get("data-case") == "upper"
    base = element.get("fill", "#000000")
    text, runs = "", []

    def add(piece: str | None, fill: str) -> None:
        nonlocal text
        if not piece:
            return
        piece = re.sub(r"\s+", " ", piece)
        piece = piece.upper() if upper else piece
        runs.append(Run(len(text), len(text) + len(piece), fill))
        text += piece

    add(element.text, base)
    for child in element:
        if _local(child) != "tspan":
            raise ValueError(
                f"a <text> holds a <{_local(child)}>; only text and <tspan> runs are set"
            )
        add(child.text, child.get("fill", base))
        add(child.tail, base)
    stripped = text.strip()
    lead = len(text) - len(text.lstrip())
    fitted = tuple(
        Run(max(run.first - lead, 0), min(run.last - lead, len(stripped)), run.fill) for run in runs
    )
    return stripped, tuple(run for run in fitted if run.last > run.first)


def set_text(element: ET.Element, root: Path = BRAND_ROOT) -> Set:
    """Return *element* as it is set: shaped, placed and scaled."""
    family = element.get("font-family", "")
    size = float(element.get("font-size", "0"))
    if size <= 0:
        raise ValueError(f"text {element.get('id')!r} has no font-size")
    axes = []
    if family == "Mona Sans":
        stretch = element.get("font-stretch", "100%")
        axes.append(("wdth", float(stretch.rstrip("%"))))
        style = element.get("style")
        if style is not None:
            match = OPSZ.fullmatch(style)
            if not match:
                raise ValueError(
                    f"text {element.get('id')!r}: a style may hold font-variation-settings:'opsz' N and nothing else"
                )
            axes.append(("opsz", float(match.group(1))))
    axes.append(("wght", float(element.get("font-weight", "400"))))
    spacing = element.get("letter-spacing", "0em")
    match = EM.fullmatch(spacing)
    if not match:
        raise ValueError(
            f"text {element.get('id')!r}: letter-spacing is written in ems, not {spacing!r}"
        )
    text, runs = words(element)
    line = lettering.shape(text, family, tuple(axes), float(match.group(1)), root)
    scale = size / line.upem
    x, y = float(element.get("x", "0")), float(element.get("y", "0"))
    anchor = element.get("text-anchor", "start")
    if anchor == "middle":
        x -= line.advance * scale / 2
    elif anchor == "end":
        x -= line.advance * scale
    elif anchor != "start":
        raise ValueError(f"text {element.get('id')!r}: text-anchor is start, middle or end")
    return Set(line, x, y, scale, runs)


def outline(tree: ET.Element, root: Path = BRAND_ROOT) -> dict[str, Set]:
    """Replace every ``<text>`` under *tree* with a group of paths, and return each one as it was set.

    The group keeps the element's ``id`` and carries its words in
    ``aria-label``, so the outlined file still says what it reads.
    """
    done: dict[str, Set] = {}
    parents = {child: parent for parent in tree.iter() for child in parent}
    for element in [
        node for node in tree.iter() if isinstance(node.tag, str) and _local(node) == "text"
    ]:
        placed = set_text(element, root)
        group = ET.Element(f"{{{SVG_NS}}}g")
        if element.get("id"):
            group.set("id", element.get("id", ""))
            done[element.get("id", "")] = placed
        group.set("aria-label", placed.line.text)
        transform = f"translate({_number(placed.x)} {_number(placed.y)}) scale({_number(placed.scale)} {_number(-placed.scale)})"
        for run in placed.runs:
            data = placed.line.path(run.first, run.last)
            if data:
                ET.SubElement(
                    group,
                    f"{{{SVG_NS}}}path",
                    {"fill": run.fill, "transform": transform, "d": data},
                )
        group.tail = element.tail
        parent = parents[element]
        parent.insert(list(parent).index(element), group)
        parent.remove(element)
    return done
