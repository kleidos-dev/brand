# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The nine boards Kleidos runs on: their fronts, set side by side on a shelf at one scale.

``boards/<board>.svg`` are byte copies of the boards repository's
``<board>/svg/front.svg`` (MIT), listed with their digests and the commit they
were copied at in ``boards/boards.json`` (``tools/sync_from_boards.py`` copies
them and compares them with a checkout). Each front is a drawing at 1 SVG unit
= 1 mm, its case's top left corner at the origin, with the panel's active area
marked as ``<rect id="screen-active">``.

A source asks for a line-up with a shelf: a ``<rect data-boards="all">`` (or a
space-separated list of boards) with ``fill="none"``, whose box the boards
stand in, their cases' bottom edges on its bottom edge. Every shelf of one
drawing shares one scale, the largest at which each shelf's boards fit their
box, so the boards keep their true sizes against each other. ``data-gap``
(millimeters, 8 by default) is the space between two boards and ``data-align``
(``center``, ``start`` or ``end``) where a row shorter than its box sits.

:func:`fill` puts the fronts in place of the shelves. Each front is drawn as
the boards repository draws it, in the cases' own colors, gradients included,
with three things taken out: what the drawing says about itself (its title,
dimensions and press targets), its drop shadow, and the live text of its
printed legends, which is set again here as outlines from the pinned Inter
files, the face the drawings name. Nothing else is changed: the legends,
the marks printed on the products included, are the boards repository's.
:func:`paste_glass` then lays each board's own unlock screen, a real capture
from ``press-kit/screens/``, on its panel's active area.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from . import BRAND_ROOT, xmlsafe

BOARDS_DIR = Path("boards")
MANIFEST = BOARDS_DIR / "boards.json"
SCREENS_DIR = Path("press-kit/screens")
SVG_NS = "http://www.w3.org/2000/svg"
XLINK = "{http://www.w3.org/1999/xlink}href"
#: The front's margins around the case, outside the case's own box: left, top, right, bottom.
MARGINS = (12.0, 6.0, 12.0, 14.0)
#: Room left on each side of a case for what stands off its edges: the Sticks' side keys.
SIDE_MM = 1.0
#: The ids of what a front says about itself rather than what the board shows.
DROPPED_IDS = frozenset({"annotations", "hotspots", "screen-active", "screen-demo"})
#: The pinned Inter faces the legends are set in, by CSS weight.
INTER = {
    400: Path("fonts/inter/Inter-Regular.ttf"),
    500: Path("fonts/inter/Inter-Medium.ttf"),
    700: Path("fonts/inter/Inter-Bold.ttf"),
}
ANCHORS = {"start": 0.0, "middle": 0.5, "end": 1.0}
URL_REF = re.compile(r"url\(#([^)]+)\)")

Box = tuple[float, float, float, float]  # left, top, right, bottom


@dataclass(frozen=True)
class Front:
    """One board's front: its name, its case's size and its panel's active area, in millimeters."""

    slug: str
    name: str
    width: float
    height: float
    glass: Box
    resolution: tuple[int, int]


@dataclass(frozen=True)
class Placement:
    """Where a front is drawn: its board, its case's top left corner and its scale, in the drawing's
    units."""

    slug: str
    x: float
    y: float
    scale: float
    front: Front

    def box(self) -> Box:
        """Return the board's footprint: its case, and the room for its side keys."""
        side = SIDE_MM * self.scale
        return (
            self.x - side,
            self.y - side,
            self.x + self.front.width * self.scale + side,
            self.y + self.front.height * self.scale,
        )

    def glass(self) -> Box:
        """Return the panel's active area in the drawing's units."""
        left, top, right, bottom = self.front.glass
        return (
            self.x + left * self.scale,
            self.y + top * self.scale,
            self.x + right * self.scale,
            self.y + bottom * self.scale,
        )


def _local(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1] if isinstance(element.tag, str) else ""


def _number(value: float) -> str:
    rounded = round(value, 3)
    return str(int(rounded)) if rounded == int(rounded) else repr(rounded)


def _factor(value: float) -> str:
    """Return a scale factor to six significant digits: font units to millimeters are
    ten-thousandths."""
    return f"{value:.6g}"


def load(root: Path = BRAND_ROOT) -> dict[str, Any]:
    """Return ``boards/boards.json``."""
    data: dict[str, Any] = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    return data


def order(root: Path = BRAND_ROOT) -> list[str]:
    """Return every board, in the order a line-up shows them."""
    return list(load(root)["boards"])


def front_path(slug: str) -> Path:
    """Return the copy of a board's front, relative to the repository."""
    return BOARDS_DIR / f"{slug}.svg"


def screen_path(slug: str) -> Path:
    """Return a board's unlock screen, relative to the repository."""
    return SCREENS_DIR / f"kleidos-screen-{slug}.png"


def inputs(root: Path = BRAND_ROOT) -> tuple[Path, ...]:
    """Return every file a line-up is drawn from: the manifest, the fronts, the screens and the
    faces."""
    slugs = order(root)
    return (
        MANIFEST,
        *(front_path(slug) for slug in slugs),
        *(screen_path(slug) for slug in slugs),
        *INTER.values(),
    )


def front(slug: str, root: Path = BRAND_ROOT) -> Front:
    """Return what a line-up measures on a board's front."""
    tree = xmlsafe.parse(root / front_path(slug))
    _, _, view_w, view_h = (float(part) for part in tree.get("viewBox", "").split())
    width, height = view_w - MARGINS[0] - MARGINS[2], view_h - MARGINS[1] - MARGINS[3]
    marker = next(element for element in tree.iter() if element.get("id") == "screen-active")
    x, y, w, h = (float(marker.get(key, "0")) for key in ("x", "y", "width", "height"))
    columns, rows = (int(part) for part in marker.get("data-resolution", "0x0").split("x"))
    return Front(
        slug,
        load(root)["boards"][slug]["name"],
        width,
        height,
        (x, y, x + w, y + h),
        (columns, rows),
    )


# --- The legends, as outlines --------------------------------------------------------------


def face_for(weight: int) -> Path:
    """Return the pinned face CSS picks for *weight*: 400 and 500 try each other, heavier ones go
    up, lighter ones down."""
    have = sorted(INTER)
    if weight in INTER:
        return INTER[weight]
    if weight > 500:
        return INTER[min((w for w in have if w > weight), default=max(have))]
    return INTER[max((w for w in have if w < weight), default=min(have))]


@cache
def _face(path: str) -> tuple[Any, Any]:
    import uharfbuzz as hb
    from fontTools.ttLib import TTFont

    data = Path(path).read_bytes()
    return TTFont(io.BytesIO(data)), hb.Font(hb.Face(data))


def legend_path(element: ET.Element, root: Path = BRAND_ROOT) -> ET.Element:
    """Return a ``<text>`` of a front as one ``<path>``: the same words, at the same place, in
    Inter's outlines.

    The words are shaped with HarfBuzz as a browser shapes them (kerning and
    ligatures on). A run whose width the drawing pins (``textLength`` with
    ``lengthAdjust="spacingAndGlyphs"``) is stretched to that width, as a
    browser stretches it.
    """
    import uharfbuzz as hb
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen

    if len(element):
        raise ValueError("a legend is one plain run of characters")
    text = re.sub(r"\s+", " ", element.text or "").strip()
    font, shaper = _face(str(root / face_for(int(element.get("font-weight", "400")))))
    missing = sorted({char for char in text if ord(char) not in font.getBestCmap()})
    if missing:
        raise ValueError(f"Inter has no glyph for {''.join(missing)!r}")
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(shaper, buffer, {"kern": True, "liga": True})
    order_ = font.getGlyphOrder()
    glyph_set = font.getGlyphSet()
    pen = SVGPathPen(glyph_set, ntos=_number)
    advance = 0.0
    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions, strict=True):
        glyph_set[order_[info.codepoint]].draw(
            TransformPen(pen, (1, 0, 0, 1, advance + position.x_offset, position.y_offset))
        )
        advance += position.x_advance
    scale = float(element.get("font-size", "0")) / font["head"].unitsPerEm
    widen = 1.0
    if element.get("textLength") is not None:
        if element.get("lengthAdjust") != "spacingAndGlyphs":
            raise ValueError(
                "a legend whose width is pinned stretches its glyphs "
                "(lengthAdjust='spacingAndGlyphs')"
            )
        widen = float(element.get("textLength", "0")) / (advance * scale)
    x = (
        float(element.get("x", "0"))
        - ANCHORS[element.get("text-anchor", "start")] * advance * scale * widen
    )
    y = float(element.get("y", "0"))
    own = element.get("transform", "")
    placed = (
        f"translate({_number(x)} {_number(y)}) scale({_factor(scale * widen)} {_factor(-scale)})"
    )
    path = ET.Element(
        f"{{{SVG_NS}}}path",
        {
            "fill": element.get("fill", "#000000"),
            "d": pen.getCommands(),
            "transform": f"{own} {placed}".strip(),
        },
    )
    path.set("aria-label", text)
    path.tail = element.tail
    return path


# --- A front, ready to place ---------------------------------------------------------------


def drawing(slug: str, root: Path = BRAND_ROOT, prefix: str | None = None) -> list[ET.Element]:
    """Return a board's front as the shapes a line-up draws, its ids made unique with *prefix*.

    Dropped: the title, the annotations, the press targets, the active-area
    marker and the drop shadow. Every legend's live text becomes a path.
    """
    ET.register_namespace("", SVG_NS)
    tree = xmlsafe.parse(root / front_path(slug))
    prefix = f"{slug}-" if prefix is None else prefix
    shadows = {
        element.get("id")
        for element in tree.iter()
        if _local(element) == "filter" and (element.get("id") or "").startswith("shadow_")
    }

    def prune(parent: ET.Element) -> None:
        for index, child in reversed(list(enumerate(list(parent)))):
            name = _local(child)
            if (
                name in ("title", "desc", "metadata")
                or child.get("id") in DROPPED_IDS
                or child.get("id") in shadows
            ):
                parent.remove(child)
            elif name == "text":
                parent.remove(child)
                parent.insert(index, legend_path(child, root))
            else:
                prune(child)

    prune(tree)
    for element in tree.iter():
        filtered = URL_REF.search(element.get("filter", ""))
        if filtered and filtered.group(1) in shadows:
            del element.attrib["filter"]
        for key in [key for key in element.attrib if key.startswith("data-")]:
            del element.attrib[key]
        if element.get("id"):
            element.set("id", prefix + element.get("id", ""))
        for key, value in list(element.attrib.items()):
            if "url(#" in value:
                element.set(
                    key, URL_REF.sub(lambda match: f"url(#{prefix}{match.group(1)})", value)
                )
            elif key in ("href", XLINK) and value.startswith("#"):
                element.set(key, f"#{prefix}{value[1:]}")

    def drop_empty(parent: ET.Element) -> None:
        for child in list(parent):
            drop_empty(child)
            if _local(child) in ("defs", "g") and len(child) == 0:
                parent.remove(child)

    drop_empty(tree)
    return [copy.deepcopy(child) for child in tree]


# --- The line-up ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Shelf:
    """A row of boards and the box they stand in."""

    box: Box
    slugs: tuple[str, ...]
    gap_mm: float = 8.0
    align: str = "center"


def arrange(shelves: list[Shelf], root: Path = BRAND_ROOT) -> list[Placement]:
    """Return where every board of every shelf goes, all at one scale."""
    fronts = {slug: front(slug, root) for shelf in shelves for slug in shelf.slugs}

    def span(shelf: Shelf) -> tuple[float, float]:
        width = sum(fronts[slug].width + 2 * SIDE_MM for slug in shelf.slugs) + shelf.gap_mm * (
            len(shelf.slugs) - 1
        )
        height = max(fronts[slug].height + SIDE_MM for slug in shelf.slugs)
        return width, height

    scale = min(
        min(
            (shelf.box[2] - shelf.box[0]) / span(shelf)[0],
            (shelf.box[3] - shelf.box[1]) / span(shelf)[1],
        )
        for shelf in shelves
    )
    out = []
    for shelf in shelves:
        width = span(shelf)[0] * scale
        room = (shelf.box[2] - shelf.box[0]) - width
        left = shelf.box[0] + {"start": 0.0, "center": room / 2, "end": room}[shelf.align]
        for slug in shelf.slugs:
            board = fronts[slug]
            x = left + SIDE_MM * scale
            out.append(Placement(slug, x, shelf.box[3] - board.height * scale, scale, board))
            left = x + (board.width + SIDE_MM + shelf.gap_mm) * scale
    return out


def _offset(parents: dict[ET.Element, ET.Element], element: ET.Element) -> tuple[float, float]:
    """Return the translation every ancestor of *element* adds; only ``translate(x y)`` and a plain
    scale of 1 are read."""
    dx = dy = 0.0
    node = parents.get(element)
    while node is not None:
        transform = node.get("transform", "")
        if transform:
            match = re.fullmatch(
                r"translate\((-?[\d.]+)[ ,](-?[\d.]+)\)(?: scale\(1\))?", transform.strip()
            )
            if not match:
                raise ValueError(
                    f"a shelf sits inside a group moved by {transform!r}; only translate(x y) is "
                    "read"
                )
            dx, dy = dx + float(match.group(1)), dy + float(match.group(2))
        node = parents.get(node)
    return dx, dy


def shelves_in(tree: ET.Element, root: Path = BRAND_ROOT) -> list[tuple[ET.Element, Shelf]]:
    """Return every shelf of *tree*, with its box in the drawing's own units."""
    parents = {child: parent for parent in tree.iter() for child in parent}
    out = []
    for element in tree.iter():
        asked = element.get("data-boards")
        if asked is None:
            continue
        if (
            _local(element) != "rect"
            or element.get("fill") != "none"
            or element.get("stroke", "none") != "none"
        ):
            raise ValueError('a shelf is a <rect data-boards="…" fill="none"> that draws nothing')
        slugs = tuple(order(root)) if asked.strip() == "all" else tuple(asked.split())
        unknown = [slug for slug in slugs if slug not in load(root)["boards"]]
        if unknown or not slugs:
            raise ValueError(f"a shelf asks for {asked!r}; the boards are {', '.join(order(root))}")
        dx, dy = _offset(parents, element)
        x, y = float(element.get("x", "0")) + dx, float(element.get("y", "0")) + dy
        box = (x, y, x + float(element.get("width", "0")), y + float(element.get("height", "0")))
        align = element.get("data-align", "center")
        if align not in ("center", "start", "end"):
            raise ValueError(f"a shelf aligns its row at center, start or end, not {align!r}")
        out.append((element, Shelf(box, slugs, float(element.get("data-gap", "8")), align)))
    return out


def fill(tree: ET.Element, root: Path = BRAND_ROOT) -> list[Placement]:
    """Put the fronts in place of every shelf of *tree*, and return where each one went.

    Each shelf ``<rect>`` gives way to a ``<g class="boards">`` in its place,
    one ``<g>`` per board inside it, moved and scaled to its spot.
    """
    found = shelves_in(tree, root)
    if not found:
        return []
    placements = arrange([shelf for _, shelf in found], root)
    parents = {child: parent for parent in tree.iter() for child in parent}
    queue = list(placements)
    for element, shelf in found:
        parent = parents[element]
        dx, dy = _offset(parents, element)
        group = ET.Element(f"{{{SVG_NS}}}g", {"class": "boards"})
        for _ in shelf.slugs:
            placed = queue.pop(0)
            board = ET.SubElement(
                group,
                f"{{{SVG_NS}}}g",
                {
                    "class": f"board {placed.slug}",
                    "transform": (
                        f"translate({_number(placed.x - dx)} {_number(placed.y - dy)})"
                        f" scale({_number(placed.scale)})"
                    ),
                },
            )
            board.extend(drawing(placed.slug, root))
        group.tail = element.tail
        parent.insert(list(parent).index(element), group)
        parent.remove(element)
    return placements


def paste_glass(
    image: Any, placements: list[Placement], root: Path = BRAND_ROOT, factor: float = 1.0
) -> Any:
    """Return *image* (a Pillow image) with each board's unlock screen on its panel's active area.

    :param factor: The image's pixels per unit of the drawing the placements were made in.
    """
    from PIL import Image

    for placed in placements:
        left, top, right, bottom = (value * factor for value in placed.glass())
        x0, y0, x1, y1 = round(left), round(top), round(right), round(bottom)
        width, height = x1 - x0, y1 - y0
        with Image.open(root / screen_path(placed.slug)) as opened:
            screen = opened.convert("RGB")
        if (screen.width, screen.height) != placed.front.resolution:
            raise ValueError(
                f"{screen_path(placed.slug)}: is {screen.width} x {screen.height}; the front's "
                f"panel is {placed.front.resolution}"
            )
        if width > screen.width or height > screen.height:
            # Enlarged pixel for pixel first, so the screen's edges stay sharp, then brought to the
            # panel's size.
            whole = math.ceil(max(width / screen.width, height / screen.height))
            screen = screen.resize(
                (screen.width * whole, screen.height * whole), Image.Resampling.NEAREST
            )
        image.paste(screen.resize((width, height), Image.Resampling.LANCZOS), (x0, y0))
    return image


def digest(path: Path) -> str:
    """Return a file's SHA-256."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def findings(root: Path = BRAND_ROOT) -> list[str]:
    """Return every copied front that is not the file the manifest records, and every front a
    line-up cannot draw."""
    found: list[str] = []
    try:
        manifest = load(root)
    except (OSError, ValueError) as error:
        return [f"{MANIFEST}: cannot be read ({error})"]
    found.extend(
        f"{MANIFEST}: has no {key!r}"
        for key in ("repository", "commit", "license", "boards")
        if key not in manifest
    )
    if manifest.get("license") != "MIT":
        found.append(
            f"{MANIFEST}: the fronts are copied under the MIT License, the boards repository's"
        )
    listed = {front_path(slug).as_posix() for slug in manifest.get("boards", {})} | {
        MANIFEST.as_posix()
    }
    if (root / BOARDS_DIR).is_dir():
        found.extend(
            f"{path.relative_to(root).as_posix()}: the manifest does not list it"
            for path in sorted((root / BOARDS_DIR).iterdir())
            if path.is_file() and path.relative_to(root).as_posix() not in listed
        )
    for slug, entry in manifest.get("boards", {}).items():
        path = root / front_path(slug)
        if not path.is_file():
            found.append(f"{front_path(slug)}: missing")
            continue
        if digest(path) != entry.get("sha256"):
            found.append(
                f"{front_path(slug)}: its bytes are not the ones {MANIFEST} records; copy it again "
                "with tools/sync_from_boards.py"
            )
        if not (root / screen_path(slug)).is_file():
            found.append(
                f"{screen_path(slug)}: missing; every board in a line-up shows its unlock screen"
            )
        try:
            drawing(slug, root)
            front(slug, root)
        except (ValueError, KeyError, StopIteration, ET.ParseError) as error:
            found.append(
                f"{front_path(slug)}: a line-up cannot draw it ({error or type(error).__name__})"
            )
    return found
