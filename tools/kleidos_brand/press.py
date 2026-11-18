# SPDX-License-Identifier: MIT
"""The press images: one SVG template per layout, the words from one data file.

``press-kit/src/<layout>.svg`` is a source (:mod:`.svg_rules`) drawn in the
dark theme with its English words, so it reads as a picture on its own.
``press-kit/src/press.json`` lists the images made from each layout and holds
the words in every language. For one image the builder fills the lockup,
sets the words of its language, repaints for its theme, turns the words into
outlines and drops the guides; the result is what is published under
``press-kit/svg/`` and what Chromium draws to ``press-kit/images/``.

A layout may hold screen plates (``<rect data-screen="…">``): a real capture
under ``press-kit/screens/`` is pasted there after the drawing, at a whole
multiple of its own pixels, so no SVG ever embeds a picture.

A layout may also hold shelves (``<rect data-boards="…" fill="none">``,
:mod:`.boards`): the board fronts are drawn in their place, at one scale and
in their own colors, after the words are set and the theme is painted, and
each board's unlock screen is pasted on its panel after the drawing. An image
with plates or boards publishes no SVG: what it shows is partly pixels.
"""
from __future__ import annotations

import copy
import io
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import BRAND_ROOT, SVG_HEADER, boards, logo, svg_rules, svgtext, tokens

PRESS_JSON = Path("press-kit/src/press.json")
SRC_DIR = Path("press-kit/src")
SVG_DIR = Path("press-kit/svg")
IMAGES_DIR = Path("press-kit/images")
SCREENS_DIR = Path("press-kit/screens")
SVG_NS = svgtext.SVG_NS

#: A press image's weight limit: what a newsroom's system or a forum accepts without asking.
BYTE_LIMIT = 1_000_000

#: The roles a layout paints with in the dark theme, and their light twins.
THEMED = ("ground", "ink", "ink-2", "signal", "rule")


def _local(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def load(root: Path = BRAND_ROOT) -> dict[str, Any]:
    """Return ``press-kit/src/press.json``."""
    return json.loads((root / PRESS_JSON).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Plate:
    """Where a screen capture goes in an image: its board, its place and its whole scale."""

    board: str
    x: int
    y: int
    scale: int


@dataclass
class Image:
    """One press image: its name, its drawing and what is pasted on it."""

    stem: str
    layout: str
    theme: str
    lang: str
    size: tuple[int, int]
    svg: str
    ground: str
    sets: dict[str, svgtext.Set] = field(default_factory=dict)
    plates: tuple[Plate, ...] = ()
    safe: tuple[float, float, float, float] | None = None
    lockup_box: tuple[float, float, float, float] | None = None
    copies: tuple[int, ...] = ()
    publish_svg: bool = True
    what: str = ""
    fronts: tuple[boards.Placement, ...] = ()

    def png_paths(self) -> list[tuple[Path, tuple[int, int]]]:
        """Return each PNG of the image and its size: the full one, then its narrower copies."""
        width, height = self.size
        out = [(IMAGES_DIR / f"{self.stem}.png", self.size)]
        out += [(IMAGES_DIR / f"{self.stem}-{copy_width}.png", (copy_width, round(copy_width * height / width))) for copy_width in self.copies]
        return out


def _lockup_children(root: Path, kind: str, theme: str) -> tuple[list[ET.Element], logo.Logo]:
    stem = f"kleidos-lockup-{kind}-for-{theme}"
    chosen = next(item for item in logo.build(root) if item.stem == stem)
    tree = ET.fromstring(chosen.svg)
    return [child for child in tree if _local(child) != "title"], chosen


def _set_words(element: ET.Element, text: str, accent: str | None, accent_fill: str) -> None:
    """Write *text* into a ``<text>``, its *accent* words in a ``<tspan>`` of their own color."""
    for child in list(element):
        element.remove(child)
    if accent and accent in text:
        before, after = text.split(accent, 1)
        element.text = before
        span = ET.SubElement(element, f"{{{SVG_NS}}}tspan", {"fill": accent_fill})
        span.text = accent
        span.tail = after
    else:
        element.text = text


def lines_for(data: dict[str, Any], layout: str, lang: str, key: str) -> list[str]:
    """Return the lines a layout breaks the words *key* into, in *lang*."""
    return data["lines"].get(layout, {}).get(key, {}).get(lang, [data["words"][lang][key]])


def render(root: Path, entry: dict[str, Any], lang: str, data: dict[str, Any]) -> Image:
    """Return one image of *entry* in *lang*: its outlined SVG and what the checks measure on it."""
    values = tokens.resolve(tokens.load(root))
    layout, theme = entry["layout"], entry["theme"]
    ET.register_namespace("", SVG_NS)
    tree = ET.fromstring((root / SRC_DIR / f"{layout}.svg").read_text(encoding="utf-8"))
    size = svg_rules.canvas(tree)
    assert size is not None, f"{layout}.svg has no canvas"
    words = data["words"][lang]
    accent_fill = values["social.signal"]

    # The words of this language, line by line.
    by_id = {element.get("id"): element for element in tree.iter() if element.get("id")}
    for key in words:
        if key.endswith("_accent"):
            continue
        lines = lines_for(data, layout, lang, key)
        targets = [by_id[name] for name in ([key] if key in by_id else []) + [f"{key}.{index}" for index in range(8) if f"{key}.{index}" in by_id]]
        if not targets:
            continue
        if len(lines) > len(targets):
            raise ValueError(f"{layout}: {key!r} has {len(lines)} lines in {lang} and the layout has room for {len(targets)}")
        for index, target in enumerate(targets):
            if index < len(lines):
                _set_words(target, lines[index], words.get(f"{key}_accent"), accent_fill)
            else:
                _parent_of(tree, target).remove(target)

    # The lockup, as the logo files draw it for this theme.
    lockup_box = None
    holder = by_id.get("lockup")
    if holder is not None:
        children, chosen = _lockup_children(root, holder.get("data-lockup", "horizontal"), theme)
        for child in list(holder):
            holder.remove(child)
        holder.extend(children)
        lockup_box = _placed_box(holder.get("transform", ""), chosen.width, chosen.height)

    # The theme: every role's dark color gives way to its light twin, outside the lockup.
    ground = values["social.ground"]
    if theme == "light":
        swap = {values[f"social.{role}"]: values[f"social.light.{role}"] for role in THEMED}
        ground = values["social.light.ground"]
        inside = set(holder.iter()) if holder is not None else set()
        for element in tree.iter():
            if element in inside:
                continue
            for key in ("fill", "stroke"):
                value = element.get(key)
                if value is not None and value.lower() in swap:
                    element.set(key, swap[value.lower()])

    # What the checks measure, read before the guides go.
    safe = None
    guide = by_id.get("safe")
    if guide is not None:
        x, y = float(guide.get("x", "0")), float(guide.get("y", "0"))
        safe = (x, y, x + float(guide.get("width", "0")), y + float(guide.get("height", "0")))
    plates = []
    for element in tree.iter():
        board = element.get("data-screen")
        if board:
            plates.append(Plate(board, int(element.get("x", "0")), int(element.get("y", "0")), int(element.get("data-scale", "1"))))

    sets = svgtext.outline(tree, root)
    # The boards, after the theme: they keep their own colors on either ground.
    fronts = tuple(boards.fill(tree, root))
    guides = by_id.get("guides")
    if guides is not None:
        tree.remove(guides)
    for element in tree.iter():
        for key in [key for key in element.attrib if key.startswith("data-") and key != "data-screen"]:
            del element.attrib[key]
    ET.indent(tree, "  ")
    svg = SVG_HEADER + ET.tostring(tree, encoding="unicode") + "\n"
    stem = entry["file"] + ("" if lang == data["default_lang"] else f"-{lang}")
    return Image(stem, layout, theme, lang, size, svg, ground, sets, tuple(plates), safe, lockup_box,
                 tuple(entry.get("copies", ())), not plates and not fronts, entry.get("what", ""), fronts)


def _parent_of(tree: ET.Element, target: ET.Element) -> ET.Element:
    for parent in tree.iter():
        if target in list(parent):
            return parent
    raise ValueError("element has no parent")


def _placed_box(transform: str, width: float, height: float) -> tuple[float, float, float, float]:
    """Return where a group lands that is moved and scaled by ``translate(x y) scale(s)``."""
    match = re.fullmatch(r"translate\(([-\d.]+) ([-\d.]+)\) scale\(([-\d.]+)\)", transform)
    if not match:
        raise ValueError(f"a lockup is placed with 'translate(x y) scale(s)', not {transform!r}")
    x, y, scale = (float(part) for part in match.groups())
    return x, y, x + width * scale, y + height * scale


def images(root: Path = BRAND_ROOT) -> list[Image]:
    """Return every press image, in the order ``press.json`` lists them."""
    data = load(root)
    out = []
    for entry in data["images"]:
        for lang in entry.get("langs", data["langs"]):
            out.append(render(root, entry, lang, data))
    return out


def findings(image: Image) -> list[str]:
    """Return what in *image* leaves its safe area: a line of words, or the lockup."""
    if image.safe is None:
        return [f"{image.stem}: its layout has no 'safe' guide to measure against"]
    left, top, right, bottom = image.safe
    found = []
    boxes = {f"the words {name!r} ({placed.line.text!r})": placed.box() for name, placed in image.sets.items()}
    if image.lockup_box is not None:
        boxes["the lockup"] = image.lockup_box
    for placed in image.fronts:
        boxes[f"the board {placed.front.name}"] = placed.box()
    for what, (x0, y0, x1, y1) in boxes.items():
        if x0 < left or y0 < top or x1 > right or y1 > bottom:
            found.append(f"{image.stem}: {what} reaches outside the safe area ({x0:.0f}, {y0:.0f}, {x1:.0f}, {y1:.0f} against {left:.0f}, {top:.0f}, {right:.0f}, {bottom:.0f})")
    return found


def paste_screens(image: Image, drawn: Any, root: Path = BRAND_ROOT) -> Any:
    """Return *drawn* (a Pillow image) with each of the image's screens pasted on its plate."""
    from PIL import Image as Pillow  # noqa: PLC0415

    for plate in image.plates:
        with Pillow.open(root / SCREENS_DIR / f"kleidos-screen-{plate.board}.png") as screen:
            enlarged = screen.convert("RGB").resize((screen.width * plate.scale, screen.height * plate.scale), Pillow.Resampling.NEAREST)
        drawn.paste(enlarged, (plate.x, plate.y))
    return boards.paste_glass(drawn, list(image.fronts), root, drawn.width / image.size[0])


def narrowed(full: Any, size: tuple[int, int]) -> Any:
    """Return a narrower copy of an image that holds screens: the full one, resampled."""
    from PIL import Image as Pillow  # noqa: PLC0415

    return full.resize(size, Pillow.Resampling.LANCZOS)


def enlarged_screen(data: bytes, scale: int) -> Any:
    """Return a capture at *scale* times its own pixels, each pixel a square."""
    from PIL import Image as Pillow  # noqa: PLC0415

    with Pillow.open(io.BytesIO(data)) as screen:
        return screen.convert("RGB").resize((screen.width * scale, screen.height * scale), Pillow.Resampling.NEAREST)


def template_lockup_matches(root: Path, layout: str) -> bool:
    """Tell whether a layout's own copy of the lockup is the dark lockup the logo files draw."""
    tree = ET.fromstring((root / SRC_DIR / f"{layout}.svg").read_text(encoding="utf-8"))
    holder = next((element for element in tree.iter() if element.get("id") == "lockup"), None)
    if holder is None:
        return True
    children, _ = _lockup_children(root, holder.get("data-lockup", "horizontal"), "dark")

    def canon(elements: list[ET.Element]) -> list[tuple[str, tuple[tuple[str, str], ...], list[Any]]]:
        return [(_local(element), tuple(sorted(element.attrib.items())), canon(list(element))) for element in elements]

    return canon(copy.deepcopy(list(holder))) == canon(children)
