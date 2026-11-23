# SPDX-License-Identifier: MIT
"""The name's lettering and the lockups: one stable path, placed by the numbers of lockups.json."""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from kleidos_brand import lettering, logo, mark, svgtext

ROOT = Path(__file__).resolve().parents[1]

#: The lettering's path, pinned: a change of font, of instance or of shaping changes it.
NAME_PATH_SHA256 = "3a19303e137dc2d1f6275f2a3f6299cca0ed6b656e6e78cb46788bf011aaa9a8"


def test_the_name_is_seven_glyphs_shaped_once() -> None:
    line = lettering.name_line(ROOT)
    assert [glyph.name for glyph in line.glyphs] == ["K", "l", "e", "i", "d", "o", "s"]
    assert line.upem == 1000
    assert line.path() == lettering.name_line(ROOT).path()
    assert hashlib.sha256(line.path().encode()).hexdigest() == NAME_PATH_SHA256


def test_the_path_is_in_whole_or_half_font_units() -> None:
    numbers = re.findall(r"-?\d+(?:\.\d+)?", lettering.name_line(ROOT).path())
    assert numbers and all(float(number) * 2 == int(float(number) * 2) for number in numbers)


def test_a_missing_glyph_is_an_error() -> None:
    try:
        lettering.shape("中", "Mona Sans", lettering.NAME_AXES, 0, ROOT)
    except ValueError as error:
        assert "no glyph" in str(error)
    else:
        raise AssertionError("a character the font lacks was shaped")


def test_lockup_geometry_is_the_numbers_of_lockups_json() -> None:
    numbers = json.loads((ROOT / logo.LOCKUPS_JSON).read_text(encoding="utf-8"))
    logos = {item.stem: item for item in logo.build(ROOT)}
    line = lettering.name_line(ROOT)

    def placed(stem: str) -> tuple[list[float], list[float]]:
        tree = ET.fromstring(logos[stem].svg)
        group = next(element for element in tree.iter() if element.get("class") == "mark")
        path = next(element for element in tree.iter() if element.get("class") == "lettering")
        return (
            [float(n) for n in re.findall(r"-?[\d.]+", group.get("transform", ""))],
            [float(n) for n in re.findall(r"-?[\d.]+", path.get("transform", ""))],
        )

    h = numbers["horizontal"]
    (cx, cy, scale), (x, baseline, *_) = placed("kleidos-lockup-horizontal-for-dark")
    side = h["mark_side_em"] * 1000
    assert scale * mark.BOX == side and (cx, cy) == (side / 2, side / 2)
    assert x == side + h["lettering_origin_after_mark_em"] * 1000
    assert baseline == side / 2 + h["baseline_below_mark_center_em"] * 1000

    s = numbers["stacked"]
    (cx, cy, scale), (x, baseline, *_) = placed("kleidos-lockup-stacked-for-dark")
    side = s["mark_side_em"] * 1000
    x0, _, x1, _ = line.bounds()
    assert scale * mark.BOX == side and cy == side / 2
    assert baseline == side + s["cap_top_below_mark_em"] * 1000 + 729
    assert abs((x + (x0 + x1) / 2) - cx) < 0.01, (
        "the lettering's ink is centered on the mark's axis"
    )


def test_every_logo_file_shows_the_whole_mark_or_none() -> None:
    shapes = mark.shapes(ROOT)
    assert len(shapes) == 5
    for item in logo.build(ROOT):
        tree = ET.fromstring(item.svg)
        groups = [element for element in tree.iter() if "mark" in element.get("class", "").split()]
        assert len(groups) == (0 if item.kind == "lettering" else 1), item.stem
        assert "<text" not in item.svg


def test_text_becomes_outlines_with_its_words_kept() -> None:
    source = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200"><g id="content">'
        '<text id="line" x="400" y="120" text-anchor="middle" font-family="Mona Sans" font-size="100" font-weight="650"'
        ' font-stretch="112.5%" letter-spacing="-0.03em" fill="#eceef1">on a <tspan fill="#00d2ff">board</tspan>.</text></g></svg>'
    )
    tree = ET.fromstring(source)
    sets = svgtext.outline(tree, ROOT)
    group = next(element for element in tree.iter() if element.get("id") == "line")
    assert group.get("aria-label") == "on a board."
    assert [path.get("fill") for path in group] == ["#eceef1", "#00d2ff", "#eceef1"]
    left, _, right, _ = sets["line"].box()
    assert abs((left + right) / 2 - 400) < 12, "a middle-anchored line is centered on its x"
    assert not [element for element in tree.iter() if element.tag.endswith("text")]
