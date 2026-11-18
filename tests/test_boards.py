# SPDX-License-Identifier: MIT
"""The board fronts: byte copies held to their manifest, drawn without live text, set at one true scale."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import check
import pytest
from kleidos_brand import boards

ROOT = Path(__file__).resolve().parents[1]
SVG = "http://www.w3.org/2000/svg"


def shelf_tree(*shelves: str) -> ET.Element:
    return ET.fromstring(f'<svg xmlns="{SVG}" viewBox="0 0 4000 2000"><g id="content">{"".join(shelves)}</g></svg>')


def test_the_copies_are_the_files_the_manifest_records() -> None:
    assert boards.findings(ROOT) == []
    manifest = boards.load(ROOT)
    assert manifest["license"] == "MIT" and len(manifest["commit"]) == 40
    assert len(manifest["boards"]) == 9, "all nine boards, not only one"


def test_a_changed_copy_is_found(tree: Path) -> None:
    path = tree / boards.front_path("sticks3")
    path.write_text(path.read_text(encoding="utf-8").replace("#0868f0", "#0868f1"), encoding="utf-8")
    assert any("sticks3.svg: its bytes are not" in line for line in check.findings(tree))


def test_a_board_drawing_outside_the_copies_is_refused(tree: Path) -> None:
    (tree / "press-kit/src/stray.svg").write_bytes((tree / boards.front_path("coreink")).read_bytes())
    assert any("stray.svg: carries a board drawing's markers" in line for line in check.findings(tree))


def test_a_front_is_drawn_without_what_it_says_about_itself() -> None:
    for slug in boards.order(ROOT):
        drawn = "".join(ET.tostring(element, encoding="unicode") for element in boards.drawing(slug, ROOT))
        assert "<text" not in drawn and "ns0:text" not in drawn, slug
        for marker in ("annotations", "hotspots", "screen-active", "feDropShadow", "<title"):
            assert marker not in drawn, (slug, marker)
        assert f'id="{slug}-' in drawn or "id=" not in drawn, "ids are made unique"


def test_a_legend_keeps_its_anchor_and_its_pinned_width() -> None:
    middle = ET.fromstring(f'<text xmlns="{SVG}" x="10" y="5" font-size="2" font-weight="700" text-anchor="middle" fill="#111111">M5</text>')
    start = ET.fromstring(f'<text xmlns="{SVG}" x="10" y="5" font-size="2" font-weight="700" fill="#111111">M5</text>')
    pinned = ET.fromstring(f'<text xmlns="{SVG}" x="0" y="0" font-size="2" textLength="6" lengthAdjust="spacingAndGlyphs" fill="#111111">ABC</text>')
    assert boards.legend_path(middle, ROOT).get("transform").startswith("translate(")
    x_middle = float(boards.legend_path(middle, ROOT).get("transform").split("(")[1].split()[0])
    x_start = float(boards.legend_path(start, ROOT).get("transform").split("(")[1].split()[0])
    assert x_middle < x_start == 10
    assert "scale(" in boards.legend_path(pinned, ROOT).get("transform")
    assert boards.face_for(300) == boards.INTER[400] and boards.face_for(600) == boards.INTER[700] and boards.face_for(800) == boards.INTER[700]


@pytest.mark.parametrize("size", ["0.55", "1.18", "1.51", "2.34", "3.2"])
def test_a_legend_is_drawn_at_its_own_size(size: str) -> None:
    """The glyphs are scaled to the font size exactly, however small the factor from font units is."""
    plain = ET.fromstring(f'<text xmlns="{SVG}" x="0" y="0" font-size="{size}" font-weight="700" fill="#111111">del</text>')
    sx, sy = (float(value) for value in boards.legend_path(plain, ROOT).get("transform").rsplit("scale(", 1)[1].rstrip(")").split())
    assert sx == pytest.approx(float(size) / 2048, rel=1e-4) and sy == pytest.approx(-float(size) / 2048, rel=1e-4)
    pinned = ET.fromstring(f'<text xmlns="{SVG}" x="0" y="0" font-size="{size}" font-weight="700" textLength="2.028" lengthAdjust="spacingAndGlyphs" fill="#111111">del</text>')
    sx, sy = (float(value) for value in boards.legend_path(pinned, ROOT).get("transform").rsplit("scale(", 1)[1].rstrip(")").split())
    assert sy == pytest.approx(-float(size) / 2048, rel=1e-4)
    x = float(boards.legend_path(pinned, ROOT).get("transform").split("(")[1].split()[0])
    assert x == 0


def test_every_shelf_of_a_drawing_shares_one_true_scale() -> None:
    tree = shelf_tree(
        '<rect data-boards="sticks3 coreink" x="100" y="100" width="3800" height="500" fill="none"/>',
        '<rect data-boards="cardputer tdeck-plus" x="100" y="800" width="3800" height="1100" fill="none"/>',
    )
    placed = boards.fill(tree, ROOT)
    assert len({round(item.scale, 9) for item in placed}) == 1
    by = {item.slug: item for item in placed}
    sticks, tdeck = by["sticks3"], by["tdeck-plus"]
    assert (sticks.front.width * sticks.scale) / (tdeck.front.width * tdeck.scale) == pytest.approx(sticks.front.width / tdeck.front.width)
    for item in placed:
        assert item.y + item.front.height * item.scale == pytest.approx(600 if item.slug in ("sticks3", "coreink") else 1900), "on the shelf"
    assert "data-boards" not in ET.tostring(tree, encoding="unicode")


def test_a_shelf_must_draw_nothing_and_name_real_boards() -> None:
    with pytest.raises(ValueError):
        boards.fill(shelf_tree('<rect data-boards="sticks3" x="0" y="0" width="10" height="10" fill="#000000"/>'), ROOT)
    with pytest.raises(ValueError):
        boards.fill(shelf_tree('<rect data-boards="sticks4" x="0" y="0" width="10" height="10" fill="none"/>'), ROOT)


def test_the_line_up_uses_every_board_in_the_manifest() -> None:
    manifest = json.loads((ROOT / boards.MANIFEST).read_text(encoding="utf-8"))
    tree = shelf_tree('<rect data-boards="all" x="0" y="0" width="4000" height="2000" fill="none"/>')
    assert [item.slug for item in boards.fill(tree, ROOT)] == list(manifest["boards"])
