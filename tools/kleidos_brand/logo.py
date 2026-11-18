# SPDX-License-Identifier: MIT
"""The logo files: every SVG under ``logo/svg/``, drawn from the mark and the lockups' numbers.

A lockup's unit is the lettering's font unit (1000 to the em), so the
lettering's path keeps the font's own numbers and the mark is placed with one
``transform``. A file never holds live text.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import BRAND_ROOT, SVG_HEADER, lettering, mark, tokens

LOCKUPS_JSON = Path("logo/src/lockups.json")
SVG_DIR = Path("logo/svg")
PNG_DIR = Path("logo/png")


@dataclass(frozen=True)
class Logo:
    """One logo file: its stem, its SVG, its box and what its PNG copies are."""

    stem: str
    kind: str  # "mark", "mark-small", "lockup-horizontal", "lockup-stacked", "lettering"
    svg: str
    width: float
    height: float
    mark_share: float  # the mark box's side as a share of the file's height; 0 without a mark
    ground: str | None  # the baked ground's color, or None on transparency
    what: str
    px: int | None = None  # a small mark's one size: its file is drawn for that many pixels only
    paint: str | None = None  # a small mark's one color

    @property
    def family(self) -> str:
        """Return the stem without a small mark's size: what the README lists it under."""
        return self.stem.removesuffix(f"-{self.px}") if self.px else self.stem


def _number(value: float) -> str:
    rounded = round(value, 2)
    return str(int(rounded)) if rounded == int(rounded) else repr(rounded)


def _svg(width: float, height: float, body: list[str], title: str, origin: tuple[float, float] = (0, 0)) -> str:
    box = f"{_number(origin[0])} {_number(origin[1])} {_number(width)} {_number(height)}"
    return (
        SVG_HEADER
        + f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}" width="{_number(width)}" height="{_number(height)}" role="img">\n'
        + f"  <title>{title}</title>\n"
        + "\n".join(body)
        + "\n</svg>\n"
    )


def _lettering_path(line: lettering.Line, x: float, baseline: float, ink: str) -> str:
    return (
        f'  <path class="lettering" fill="{ink}" transform="translate({_number(x)} {_number(baseline)}) scale(1 -1)"'
        f' d="{line.path()}"/>'
    )


_BUILT: dict[tuple[bytes, ...], list[Logo]] = {}


def build(root: Path = BRAND_ROOT) -> list[Logo]:
    """Return every logo file, in the order the README lists them."""
    sources = (LOCKUPS_JSON, mark.MARK_SVG, mark.SMALL_JSON, tokens.TOKENS_JSON, lettering.FAMILIES["Mona Sans"])
    key = tuple(hashlib.sha256((root / source).read_bytes()).digest() for source in sources)
    if key not in _BUILT:
        _BUILT[key] = _build(root)
    return _BUILT[key]


def _build(root: Path) -> list[Logo]:
    numbers: dict[str, Any] = json.loads((root / LOCKUPS_JSON).read_text(encoding="utf-8"))
    values = tokens.resolve(tokens.load(root))
    shapes = mark.shapes(root)
    line = lettering.name_line(root)
    em = float(line.upem)
    ink_x0, ink_y0, ink_x1, ink_y1 = line.bounds()
    inks = {name: values[token] for name, token in numbers["inks"].items()}
    grounds = {name: values[token] for name, token in numbers["grounds"].items()}
    # A one-ink file is named for its ink: "ink-dark" is the dark ink, for a light ground.
    one_ink = {"ink-dark": inks["for-light"], "ink-light": inks["for-dark"]}
    # What stands on a baked ground: the light lettering on dark, the dark one on light.
    on = {"on-dark": ("for-dark", grounds["on-dark"]), "on-light": ("for-light", grounds["on-light"])}
    logos: list[Logo] = []

    def add(stem: str, kind: str, width: float, height: float, body: list[str], share: float, what: str,
            ground: str | None = None, pad: float = 0.0, origin: tuple[float, float] = (0, 0), px: int | None = None,
            paint: str | None = None) -> None:
        if ground is not None:
            body = [f'  <rect x="{_number(origin[0] - pad)}" y="{_number(origin[1] - pad)}" width="{_number(width + 2 * pad)}"'
                    f' height="{_number(height + 2 * pad)}" fill="{ground}"/>', *body]
        full_w, full_h = width + 2 * pad, height + 2 * pad
        logos.append(Logo(stem, kind, _svg(full_w, full_h, body, "Kleidos", (origin[0] - pad, origin[1] - pad)),
                          full_w, full_h, share, ground, what, px, paint))

    # --- The mark ------------------------------------------------------------------------
    box, half = mark.BOX, mark.BOX / 2
    add("kleidos-mark", "mark", box, box, [mark.group(shapes)], 1.0,
        "the mark, in color, on transparency", origin=(-half, -half))
    for name, ink in one_ink.items():
        add(f"kleidos-mark-{name}", "mark", box, box, [mark.group(shapes, ink=ink)], 1.0,
            f"the one-ink mark ({ink}), for one-color print and engraving", origin=(-half, -half))
    for name, (_, ground) in on.items():
        add(f"kleidos-mark-{name}", "mark", box, box, [mark.group(shapes)], 0.5,
            f"the mark on its {'dark tile' if name == 'on-dark' else 'white tile'} ({ground}), clear space included",
            ground=ground, pad=half, origin=(-half, -half))

    # --- The small mark, one file per size ------------------------------------------------
    small = mark.small_numbers(root)
    color = mark.ring_color(shapes)
    families = [("kleidos-mark-small", color, None, "the small mark, in color, on transparency, for a dark ground"),
                *((f"kleidos-mark-small-{name}", ink, None, f"the small mark in one ink ({ink})") for name, ink in one_ink.items()),
                ("kleidos-mark-small-on-dark", color, grounds["on-dark"], f"the small mark on its dark tile ({grounds['on-dark']})")]
    for family, paint, ground, what in families:
        for px in small["sizes"]:
            fit = mark.small_fit(shapes, px, small)
            add(f"{family}-{px}", "mark-small", px, px, [mark.small_group(mark.small_shapes(fit, paint))], 0.0,
                what, ground=ground, px=px, paint=paint)

    # --- The horizontal lockup -----------------------------------------------------------
    h = numbers["horizontal"]
    side = h["mark_side_em"] * em
    scale = side / box
    inset = mark.RING_INSET * scale
    baseline = side / 2 + h["baseline_below_mark_center_em"] * em
    letter_x = side + h["lettering_origin_after_mark_em"] * em
    width = letter_x + ink_x1 + inset
    placed = f"translate({_number(side / 2)} {_number(side / 2)}) scale({_number(scale)})"

    def horizontal(ink: str, mark_ink: str | None = None) -> list[str]:
        return [mark.group(shapes, placed, mark_ink), _lettering_path(line, letter_x, baseline, ink)]

    for name, ink in inks.items():
        add(f"kleidos-lockup-horizontal-{name}", "lockup-horizontal", width, side, horizontal(ink), 1.0,
            f"the mark and the name side by side, {name.replace('-', ' a ')} ground, on transparency")
    for name, ink in one_ink.items():
        add(f"kleidos-lockup-horizontal-{name}", "lockup-horizontal", width, side, horizontal(ink, ink), 1.0,
            f"the horizontal lockup in one ink ({ink})")
    for name, (letters, ground) in on.items():
        add(f"kleidos-lockup-horizontal-{name}", "lockup-horizontal", width, side, horizontal(inks[letters]), 0.5,
            f"the horizontal lockup on {ground}, clear space included", ground=ground, pad=side / 2)

    # --- The stacked lockup --------------------------------------------------------------
    s = numbers["stacked"]
    side = s["mark_side_em"] * em
    scale = side / box
    inset = mark.RING_INSET * scale
    cap = float(lettering._instance(root, line.family, line.axes)[0]["OS/2"].sCapHeight)  # noqa: SLF001
    baseline = side + s["cap_top_below_mark_em"] * em + cap
    ink_width = ink_x1 - ink_x0
    width = max(side, ink_width + 2 * inset)
    height = baseline - min(ink_y0, 0.0) + inset
    letter_x = (width - ink_width) / 2 - ink_x0
    placed = f"translate({_number(width / 2)} {_number(side / 2)}) scale({_number(scale)})"

    def stacked(ink: str, mark_ink: str | None = None) -> list[str]:
        return [mark.group(shapes, placed, mark_ink), _lettering_path(line, letter_x, baseline, ink)]

    for name, ink in inks.items():
        add(f"kleidos-lockup-stacked-{name}", "lockup-stacked", width, height, stacked(ink), side / height,
            f"the mark above the name, {name.replace('-', ' a ')} ground, on transparency")
    for name, ink in one_ink.items():
        add(f"kleidos-lockup-stacked-{name}", "lockup-stacked", width, height, stacked(ink, ink), side / height,
            f"the stacked lockup in one ink ({ink})")
    for name, (letters, ground) in on.items():
        add(f"kleidos-lockup-stacked-{name}", "lockup-stacked", width, height, stacked(inks[letters]),
            side / (height + side), f"the stacked lockup on {ground}, clear space included", ground=ground, pad=side / 2)

    # --- The lettering alone -------------------------------------------------------------
    for name, ink in inks.items():
        add(f"kleidos-lettering-{name}", "lettering", ink_width, ink_y1 - ink_y0,
            [_lettering_path(line, -ink_x0, ink_y1, ink)], 0.0,
            f"the name alone, {name.replace('-', ' a ')} ground, for a layout where the mark already stands nearby")
    return logos


def png_plan(root: Path = BRAND_ROOT) -> list[tuple[Logo, int, int, Path]]:
    """Return every PNG copy to draw: the logo, its width and height in pixels, and its path."""
    heights = json.loads((root / LOCKUPS_JSON).read_text(encoding="utf-8"))["png_heights"]
    plan = []
    for logo in build(root):
        if logo.px:
            plan.append((logo, logo.px, logo.px, PNG_DIR / f"{logo.stem}.png"))
            continue
        for height in heights[logo.kind]:
            width = round(height * logo.width / logo.height)
            plan.append((logo, width, height, PNG_DIR / f"{logo.stem}-{height}.png"))
    return plan
