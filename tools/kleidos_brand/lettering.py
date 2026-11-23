# SPDX-License-Identifier: MIT
"""Words as outlines: shaped with HarfBuzz, drawn from the pinned fonts with fontTools.

Nothing this project publishes holds live text, so no image needs a font
installed and no browser's text rasterizer takes part in an export. A line is
shaped once (kerning and ligatures on) on an instance of the pinned variable
font made in memory, and its glyphs' outlines are written as one SVG path in
font units; a ``transform`` on the path scales it to the size it is set at,
so the path's numbers are the font's own.

The instance is never written to disk: a saved subset or instance of a font
is a Modified Version under the OFL, and Mona Sans reserves its name.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from . import BRAND_ROOT

#: The two families an image's words may be set in, by the name a source uses.
FAMILIES = {
    "Mona Sans": Path("fonts/mona-sans/MonaSansVF[wdth,opsz,wght].ttf"),
    "Mona Sans Mono": Path("fonts/mona-sans/MonaSansMonoVF[wght].ttf"),
}

#: The name's lettering: Mona Sans at its display instance, tracked in.
NAME = "Kleidos"
NAME_AXES = (("opsz", 72.0), ("wdth", 112.5), ("wght", 650.0))
NAME_TRACKING = -0.02


@dataclass(frozen=True)
class Glyph:
    """One shaped glyph: its name, its origin in font units, and the character it came from."""

    name: str
    x: float
    y: float
    cluster: int


@dataclass(frozen=True)
class Line:
    """A shaped line of text, in font units, its baseline on y = 0 and y pointing up."""

    family: str
    axes: tuple[tuple[str, float], ...]
    text: str
    glyphs: tuple[Glyph, ...]
    advance: float
    upem: int
    root: Path

    def path(self, first: int = 0, last: int | None = None) -> str:
        """Return the SVG path data of the glyphs whose characters are in ``[first, last)``."""
        font, _ = _instance(self.root, self.family, self.axes)
        glyph_set = font.getGlyphSet()
        pen = SVGPathPen(glyph_set, ntos=_number)
        end = len(self.text) if last is None else last
        for glyph in self.glyphs:
            if first <= glyph.cluster < end:
                glyph_set[glyph.name].draw(TransformPen(pen, (1, 0, 0, 1, glyph.x, glyph.y)))
        return pen.getCommands()

    def bounds(self) -> tuple[float, float, float, float]:
        """Return the ink box of the line: ``(x_min, y_min, x_max, y_max)``, y pointing up."""
        font, _ = _instance(self.root, self.family, self.axes)
        glyph_set = font.getGlyphSet()
        pen = BoundsPen(glyph_set)
        for glyph in self.glyphs:
            glyph_set[glyph.name].draw(TransformPen(pen, (1, 0, 0, 1, glyph.x, glyph.y)))
        if pen.bounds is None:
            return 0.0, 0.0, 0.0, 0.0
        return pen.bounds


def _number(value: float) -> str:
    """Write a coordinate: an integer as one, anything else with at most two decimals."""
    rounded = round(value, 2)
    return str(int(rounded)) if rounded == int(rounded) else repr(rounded)


@lru_cache(maxsize=None)
def _digest(path: str, modified: int, size: int) -> str:
    """Return the SHA-256 of a font file, read once per state of the file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_INSTANCES: dict[tuple[str, tuple[tuple[str, float], ...]], tuple[TTFont, hb.Font]] = {}


def _instance(
    root: Path, family: str, axes: tuple[tuple[str, float], ...]
) -> tuple[TTFont, hb.Font]:
    """Return *family* at *axes*, as a fontTools font and a HarfBuzz one, both in memory.

    Instances are kept by the font file's bytes, not its place, so a copy of
    the tree (the tests make many) shares them.
    """
    if family not in FAMILIES:
        raise ValueError(
            f"{family!r} is not one of the families a word may be set in: {', '.join(FAMILIES)}"
        )
    path = root / FAMILIES[family]
    state = path.stat()
    key = (_digest(str(path), state.st_mtime_ns, state.st_size), axes)
    if key not in _INSTANCES:
        source = TTFont(path)
        limits = {axis.axisTag: axis.defaultValue for axis in source["fvar"].axes}
        for tag, value in axes:
            if tag not in limits:
                raise ValueError(f"{family} has no {tag!r} axis")
            limits[tag] = value
        data = io.BytesIO()
        instancer.instantiateVariableFont(source, limits).save(data)
        # Read back from the saved bytes, where every coordinate is the integer
        # HarfBuzz sees: the instance in memory still holds interpolated fractions.
        _INSTANCES[key] = (TTFont(io.BytesIO(data.getvalue())), hb.Font(hb.Face(data.getvalue())))
    return _INSTANCES[key]


def characters(family: str, root: Path = BRAND_ROOT) -> frozenset[int]:
    """Return the code points *family*'s pinned file has a glyph for."""
    return frozenset(TTFont(root / FAMILIES[family]).getBestCmap())


def shape(
    text: str,
    family: str,
    axes: tuple[tuple[str, float], ...],
    tracking: float = 0.0,
    root: Path = BRAND_ROOT,
) -> Line:
    """Return *text* shaped in *family* at *axes*.

    :param tracking: Space added after every character but the last, in ems.
    """
    axes = tuple(sorted(axes))
    font, shaper = _instance(root, family, axes)
    upem = font["head"].unitsPerEm
    missing = sorted({char for char in text if ord(char) not in font.getBestCmap()})
    if missing:
        raise ValueError(f"{family} has no glyph for {''.join(missing)!r}")
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(shaper, buffer, {"kern": True, "liga": True})
    order = font.getGlyphOrder()
    glyphs, pen_x, extra = [], 0.0, tracking * upem
    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions, strict=True):
        glyphs.append(
            Glyph(
                order[info.codepoint],
                pen_x + position.x_offset,
                float(position.y_offset),
                info.cluster,
            )
        )
        pen_x += position.x_advance + extra
    advance = pen_x - extra if glyphs else 0.0
    return Line(family, axes, text, tuple(glyphs), advance, upem, root)


def name_line(root: Path = BRAND_ROOT) -> Line:
    """Return the name's lettering: the one path "Kleidos" is ever drawn with."""
    return shape(NAME, "Mona Sans", NAME_AXES, NAME_TRACKING, root)
