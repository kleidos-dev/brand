# SPDX-License-Identifier: MIT
"""The KiCad style: the drawing sheets, the color themes and the resolved constants, written from the sources.

``kicad/src/style.json`` holds the style by hand (the sheet's geometry, the
mark's size, the sizes and widths, which KiCad keys take which role, the font
choice); ``tokens/tokens.json`` holds the colors, as the ``schematic`` group;
``logo/png/`` holds the mark each sheet embeds. This module writes, with no
KiCad needed:

- ``kicad/kleidos-<ground>.kicad_wks``: the drawing sheet, KiCad's default
  frame and zone grid with a new title block, the mark as a bitmap holding the
  logo file's bytes unchanged. No color and no font is named in it, so one
  layout serves both grounds and the sheet always shares the drawing's face;
- ``kicad/kleidos-<ground>.json``: the color theme, every value a token's;
- ``kicad/style.json``: the source with every role resolved to its color and
  KiCad's stroke-font advances (``kicad/src/stroke-advances.json``, measured),
  for the generators that draw with the kit.

The same sources always give the same bytes.
"""

from __future__ import annotations

import base64
import json
import re
import struct
from pathlib import Path
from typing import Any

from . import BRAND_ROOT, tokens

KICAD_DIR = Path("kicad")
SRC_JSON = KICAD_DIR / "src" / "style.json"
ADVANCES_JSON = KICAD_DIR / "src" / "stroke-advances.json"
STYLE_JSON = KICAD_DIR / "style.json"
HELPER = KICAD_DIR / "kleidos_kicad.py"
FIXTURE_DIR = KICAD_DIR / "fixture"
PREVIEW_DIR = KICAD_DIR / "preview"
#: The format version of the sheets written here: the one KiCad 10 reads and writes.
WKS_VERSION = 20231118
#: Base64 characters per quoted line of a bitmap's data.
B64_LINE = 76


def load(root: Path = BRAND_ROOT) -> dict[str, Any]:
    """Return ``kicad/src/style.json``."""
    return json.loads((root / SRC_JSON).read_text(encoding="utf-8"))


def sheet_path(ground: str) -> Path:
    return KICAD_DIR / f"kleidos-{ground}.kicad_wks"


def theme_path(ground: str) -> Path:
    return KICAD_DIR / f"kleidos-{ground}.json"


def kit_files(root: Path = BRAND_ROOT) -> list[Path]:
    """Return the files a consumer copies, in the order the sync tool writes them."""
    grounds = list(load(root)["grounds"])
    return [
        *(sheet_path(g) for g in grounds),
        *(theme_path(g) for g in grounds),
        STYLE_JSON,
        HELPER,
    ]


def png_size(data: bytes) -> tuple[int, int]:
    """Return a PNG file's width and height in pixels."""
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("not a PNG file")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def colors(
    root: Path = BRAND_ROOT, style: dict[str, Any] | None = None
) -> dict[str, dict[str, str]]:
    """Return every role's color on each ground, as ``#rrggbb``, from the ``schematic`` tokens."""
    style = style or load(root)
    values = tokens.resolve(tokens.load(root))
    return {
        ground: {role: values[f"schematic.{ground}.{role}"] for role in style["colors"]["roles"]}
        for ground in style["grounds"]
    }


def _rgb(color: str) -> str:
    red, green, blue = tokens.hex_rgb(color)
    return f"rgb({red}, {green}, {blue})"


def theme(ground: str, root: Path = BRAND_ROOT) -> str:
    """Return the text of ``kicad/kleidos-<ground>.json``: KiCad's color theme, every value a token's."""
    style = load(root)
    by_role = colors(root, style)[ground]
    keys = {
        key: _rgb(by_role[role])
        for role, names in style["colors"]["theme_keys"].items()
        for key in names
    }
    body = {
        "meta": {"name": style["grounds"][ground]["name"], "version": 5},
        "schematic": {"override_item_colors": False, **dict(sorted(keys.items()))},
    }
    return json.dumps(body, indent=2) + "\n"


def _num(value: float) -> str:
    return f"{value:g}"


def _segments(cells: dict[str, Any], outer: list[float]) -> list[tuple[float, float, float, float]]:
    """Return the title block's inner rules: every cell's edges, merged where collinear, the outer box left out."""
    runs: dict[tuple[str, float], list[tuple[float, float]]] = {}
    for cell in cells.values():
        x0, y0, x1, y1 = cell["box"]
        for kind, at, lo, hi in (
            ("h", y0, x0, x1),
            ("h", y1, x0, x1),
            ("v", x0, y0, y1),
            ("v", x1, y0, y1),
        ):
            on_outer = (kind == "h" and at in (outer[1], outer[3])) or (
                kind == "v" and at in (outer[0], outer[2])
            )
            if not on_outer:
                runs.setdefault((kind, at), []).append((lo, hi))
    out = []
    for (kind, at), spans in sorted(runs.items(), key=lambda item: (item[0][0], -item[0][1])):
        merged: list[list[float]] = []
        for lo, hi in sorted(spans):
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        for lo, hi in sorted(merged, key=lambda span: -span[1]):
            out.append((hi, at, lo, at) if kind == "h" else (at, hi, at, lo))
    return out


def _text(text: str, x: float, y: float, size: float, bold: bool, maxlen: float) -> str:
    weight = " bold" if bold else ""
    return f'  (tbtext "{text}" (name "") (pos {_num(x)} {_num(y)}) (font (size {_num(size)} {_num(size)}){weight}) (maxlen {_num(maxlen)}))'


def sheet(ground: str, root: Path = BRAND_ROOT) -> str:
    """Return the text of ``kicad/kleidos-<ground>.kicad_wks``."""
    style = load(root)
    geo, mark = style["sheet"], style["mark"]
    png = (root / style["grounds"][ground]["mark"]).read_bytes()
    width, height = png_size(png)
    if width != height:
        raise ValueError(f"{style['grounds'][ground]['mark']}: the mark's file is not square")
    scale = mark["mm"] / (width / mark["ppi"] * 25.4)
    margin, gap, step, zone = geo["margin"], geo["frame_gap"], geo["zone_step"], geo["zone_text"]
    half = step / 2
    rows = [
        f'(kicad_wks (version {WKS_VERSION}) (generator "kleidos_brand") (generator_version "1")',
        f"  (setup (textsize {_num(geo['cells']['file']['size'])} {_num(geo['cells']['file']['size'])})"
        f" (linewidth {_num(geo['line_width'])}) (textlinewidth {_num(geo['line_width'])})",
        f"    (left_margin {_num(margin)}) (right_margin {_num(margin)}) (top_margin {_num(margin)}) (bottom_margin {_num(margin)}))",
        f'  (rect (name "") (start 0 0 ltcorner) (end 0 0 rbcorner) (repeat 2) (incrx {_num(gap)}) (incry {_num(gap)}))',
        f'  (line (name "") (start {_num(step)} {_num(gap)} ltcorner) (end {_num(step)} 0 ltcorner) (repeat 30) (incrx {_num(step)}))',
        f'  (tbtext "1" (name "") (pos {_num(half)} {_num(gap / 2)} ltcorner) (font (size {_num(zone)} {_num(zone)})) (repeat 100) (incrx {_num(step)}))',
        f'  (line (name "") (start {_num(step)} {_num(gap)} lbcorner) (end {_num(step)} 0 lbcorner) (repeat 30) (incrx {_num(step)}))',
        f'  (tbtext "1" (name "") (pos {_num(half)} {_num(gap / 2)} lbcorner) (font (size {_num(zone)} {_num(zone)})) (repeat 100) (incrx {_num(step)}))',
        f'  (line (name "") (start 0 {_num(step)} ltcorner) (end {_num(gap)} {_num(step)} ltcorner) (repeat 30) (incry {_num(step)}))',
        f'  (tbtext "A" (name "") (pos {_num(gap / 2)} {_num(half)} ltcorner) (font (size {_num(zone)} {_num(zone)})) (justify center) (repeat 100) (incry {_num(step)}))',
        f'  (line (name "") (start 0 {_num(step)} rtcorner) (end {_num(gap)} {_num(step)} rtcorner) (repeat 30) (incry {_num(step)}))',
        f'  (tbtext "A" (name "") (pos {_num(gap / 2)} {_num(half)} rtcorner) (font (size {_num(zone)} {_num(zone)})) (justify center) (repeat 100) (incry {_num(step)}))',
    ]
    x0, y0, x1, y1 = geo["block"]
    rows.append(f'  (rect (name "") (start {_num(x1)} {_num(y1)}) (end {_num(x0)} {_num(y0)}))')
    for ax, ay, bx, by in _segments(geo["cells"], geo["block"]):
        rows.append(f'  (line (name "") (start {_num(ax)} {_num(ay)}) (end {_num(bx)} {_num(by)}))')
    data = base64.b64encode(png).decode("ascii")
    lines = "\n".join(f'      "{data[i : i + B64_LINE]}"' for i in range(0, len(data), B64_LINE))
    cx, cy = mark["center"]
    rows.append(
        f'  (bitmap (name "mark") (pos {_num(cx)} {_num(cy)}) (scale {scale:.6f})\n    (data\n{lines}\n    ))'
    )
    inset = geo["text_inset"]
    for name, cell in geo["cells"].items():
        bx0, by0, bx1, by1 = cell["box"]
        maxlen = bx1 - bx0 - 2 * inset
        if name == "comments":
            last = len(cell["lines"]) - 1
            for index, text in enumerate(cell["lines"]):
                rows.append(
                    _text(
                        text,
                        bx1 - inset,
                        cell["first"] - index * cell["pitch"],
                        cell["size"],
                        cell.get("bold_last", False) and index == last,
                        maxlen,
                    )
                )
        elif "text" in cell:
            rows.append(
                _text(
                    cell["text"],
                    bx1 - inset,
                    (by0 + by1) / 2,
                    cell["size"],
                    cell.get("bold", False),
                    maxlen,
                )
            )
    rows.append(")")
    return "\n".join(rows) + "\n"


def resolved(root: Path = BRAND_ROOT) -> str:
    """Return the text of ``kicad/style.json``: the source, every role's color resolved, every mark's digest named."""
    style = load(root)
    out = {
        "$comment": "Generated by tools/build.py from kicad/src/style.json and tokens/tokens.json. Do not edit; change those and build again."
    }
    out.update({key: value for key, value in style.items() if key != "$comment"})
    out["colors"] = {
        "roles": style["colors"]["roles"],
        "theme_keys": style["colors"]["theme_keys"],
        **colors(root, style),
    }
    out["sheet"] = {key: value for key, value in style["sheet"].items() if key != "$comment"}
    advances = json.loads((root / ADVANCES_JSON).read_text(encoding="utf-8"))
    out["font"] = {
        **{key: value for key, value in style["font"].items() if key != "$comment"},
        "stroke_advance": advances["advances"],
    }
    for ground, about in style["grounds"].items():
        data = (root / about["mark"]).read_bytes()
        out["grounds"][ground] = {
            **about,
            "mark_px": list(png_size(data)),
            "sheet": sheet_path(ground).name,
            "theme": theme_path(ground).name,
        }
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"


def texts(root: Path = BRAND_ROOT) -> dict[Path, str]:
    """Return every file this module writes, by path."""
    out: dict[Path, str] = {}
    for ground in load(root)["grounds"]:
        out[sheet_path(ground)] = sheet(ground, root)
        out[theme_path(ground)] = theme(ground, root)
    out[STYLE_JSON] = resolved(root)
    return out


# --- What tools/check.py holds -----------------------------------------------------------

#: A bitmap's data in a sheet: the quoted base64 lines.
BITMAP = re.compile(r'\(bitmap\b.*?\(data\s*((?:"[A-Za-z0-9+/=]*"\s*)+)\)', re.S)
FONT_FACE = re.compile(r"\(face\b")
COLOR = re.compile(r"\(color\b")


def embedded_marks(text: str) -> list[bytes]:
    """Return the bytes of every bitmap a sheet embeds."""
    return [
        base64.b64decode("".join(re.findall(r'"([^"]*)"', match.group(1))))
        for match in BITMAP.finditer(text)
    ]


def findings(root: Path = BRAND_ROOT) -> list[str]:
    """Return what breaks the KiCad style's rules in the tree at *root*.

    Every color of a theme is a token's value; each sheet embeds exactly its
    logo file's bytes, once; a sheet names no font and no color; the helper and
    the fixture are there. (That the generated files are what the builder gives
    is the built check's, ``tools/build.py --check --static``.)
    """
    found = []
    try:
        style = load(root)
    except (OSError, ValueError) as error:
        return [f"{SRC_JSON}: {error}"]
    palette = tokens.palette(tokens.load(root))
    for ground, about in style["grounds"].items():
        path = root / theme_path(ground)
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            for key, value in data.get("schematic", {}).items():
                if key == "override_item_colors":
                    if value is not False:
                        found.append(
                            f"{theme_path(ground)}: override_item_colors is false, so a drawing's explicit colors survive"
                        )
                    continue
                match = re.fullmatch(r"rgba?\((\d+), (\d+), (\d+)(?:, 1(?:\.0+)?)?\)", str(value))
                if (
                    not match
                    or tokens.rgb_hex(tuple(int(part) for part in match.groups())) not in palette
                ):  # type: ignore[arg-type]
                    found.append(
                        f"{theme_path(ground)}: {key} is {value}, which is no token's value"
                    )
        path = root / sheet_path(ground)
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        marks = embedded_marks(text)
        logo_bytes = (
            (root / about["mark"]).read_bytes() if (root / about["mark"]).is_file() else b""
        )
        if marks != [logo_bytes]:
            found.append(
                f"{sheet_path(ground)}: embeds {len(marks)} bitmap(s); it embeds {about['mark']}'s bytes, unchanged, once"
            )
        if FONT_FACE.search(text):
            found.append(f"{sheet_path(ground)}: names a font; the sheet takes the drawing's face")
        if COLOR.search(text):
            found.append(
                f"{sheet_path(ground)}: names a color; every line and text of the sheet takes the theme's worksheet color"
            )
    for needed in (
        HELPER,
        KICAD_DIR / "README.md",
        FIXTURE_DIR / "fixture.kicad_sch",
        FIXTURE_DIR / "fixture.kicad_pro",
    ):
        if not (root / needed).is_file():
            found.append(f"{needed}: missing")
    return found
