# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The KiCad kit: what the builder writes, what the check refuses, what the sync tool hands over."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest
import sync_kicad

from kleidos_brand import kicad, tokens

ROOT = Path(__file__).resolve().parents[1]


def helper() -> ModuleType:
    spec = importlib.util.spec_from_file_location("kleidos_kicad_under_test", ROOT / kicad.HELPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def kit_digest(hash_seed: str) -> str:
    """Return the digest of the kit an interpreter of its own builds under a hash seed."""
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import hashlib; from pathlib import Path; from kleidos_brand import kicad; "
            "kit = {path.as_posix(): text for path, text in kicad.texts(Path.cwd()).items()}; "
            "print(hashlib.sha256(repr(kit).encode()).hexdigest())",
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": str(ROOT / "tools")},
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_the_builder_gives_the_same_bytes_under_any_hash_seed() -> None:
    assert kit_digest("1") == kit_digest("2")


def test_the_committed_kit_is_what_the_builder_gives() -> None:
    for path, content in kicad.texts(ROOT).items():
        assert (ROOT / path).read_text(encoding="utf-8") == content, path


@pytest.mark.parametrize("ground", ["dark", "light"])
def test_each_sheet_embeds_its_logo_file_unchanged_once(ground: str) -> None:
    style = kicad.load(ROOT)
    text = (ROOT / kicad.sheet_path(ground)).read_text(encoding="utf-8")
    assert kicad.embedded_marks(text) == [(ROOT / style["grounds"][ground]["mark"]).read_bytes()]


def test_a_bitmap_s_data_is_the_first_that_follows_it() -> None:
    assert kicad.embedded_marks('(data "Tg==") (bitmap (data) (data "QU"\n"I="))') == [b"AB"]
    sheet = '(bitmap (data "QQ==")) (data "Tg==") (bitmaps (data "Tg==")) (bitmap (data "Qg=="))'
    assert kicad.embedded_marks(sheet) == [b"A", b"B"]


def test_a_hostile_sheet_is_read_in_linear_time() -> None:
    start = time.process_time()
    assert kicad.embedded_marks("(bitmap " * 40_000) == []
    assert time.process_time() - start < 1


def test_the_mark_is_nine_millimeters_in_its_cell() -> None:
    text = (ROOT / kicad.sheet_path("dark")).read_text(encoding="utf-8")
    assert (
        '(bitmap (name "mark") (pos 101 11) (scale 0.103808)' in text
    )  # 9 mm of a 1024 px file at 300 ppi


def test_the_title_block_keeps_kicad_s_default_box_and_frame() -> None:
    text = (ROOT / kicad.sheet_path("dark")).read_text(encoding="utf-8")
    assert '(rect (name "") (start 110 34) (end 2 2))' in text
    assert "(left_margin 10) (right_margin 10) (top_margin 10) (bottom_margin 10)" in text
    assert (
        '(rect (name "") (start 0 0 ltcorner) (end 0 0 rbcorner) (repeat 2) (incrx 2) (incry 2))'
        in text
    )
    for variable in (
        "${TITLE}",
        "${FILENAME}",
        "Rev ${REVISION}",
        "${ISSUE_DATE}",
        "${PAPER}",
        "Sheet ${#} / ${##}",
        "${LICENSE}",
        "${SOURCE_URL}",
        "${COMPANY}",
        "${COMMENT1}",
        "${COMMENT4}",
    ):
        assert f'"{variable}"' in text, variable
    assert "KICAD_VERSION" not in text


def test_the_dark_theme_keeps_the_colors_the_boards_drawings_were_published_in() -> None:
    data = json.loads((ROOT / kicad.theme_path("dark")).read_text(encoding="utf-8"))["schematic"]
    assert data["background"] == "rgb(28, 28, 28)"
    assert data["wire"] == data["pin"] == "rgb(0, 210, 255)"
    assert data["label_global"] == "rgb(127, 230, 255)"
    assert data["note"] == "rgb(200, 210, 220)"
    assert data["worksheet"] == data["value"] == "rgb(136, 153, 170)"
    assert data["override_item_colors"] is False


def test_every_theme_color_is_a_token() -> None:
    palette = tokens.palette(tokens.load(ROOT))
    for ground in ("dark", "light"):
        for key, value in json.loads((ROOT / kicad.theme_path(ground)).read_text(encoding="utf-8"))[
            "schematic"
        ].items():
            if key != "override_item_colors":
                red, green, blue = (int(part) for part in value[4:-1].split(", "))
                assert tokens.rgb_hex((red, green, blue)) in palette, (ground, key)


def test_the_light_ground_is_readable_on_white() -> None:
    colors = kicad.colors(ROOT)["light"]
    for role in ("wire", "label", "ink-2", "addition", "dnp"):
        assert tokens.contrast(colors[role], colors["ground"]) >= 4.5, role


def test_a_theme_color_that_is_no_token_is_refused(tree: Path) -> None:
    path = tree / kicad.theme_path("dark")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            '"note": "rgb(200, 210, 220)"', '"note": "rgb(201, 210, 220)"'
        ),
        encoding="utf-8",
    )
    assert any("note is rgb(201, 210, 220)" in line for line in kicad.findings(tree))


def test_a_sheet_with_a_font_a_color_or_another_mark_is_refused(tree: Path) -> None:
    path = tree / kicad.sheet_path("light")
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "(font (size 1.75 1.75) bold)",
        '(font (face "Inter") (size 1.75 1.75) bold (color 0 0 0 1))',
        1,
    )
    text = text.replace('(data\n      "', '(data\n      "AAAA', 1)
    path.write_text(text, encoding="utf-8")
    found = kicad.findings(tree)
    assert any("names a font" in line for line in found)
    assert any("names a color" in line for line in found)
    assert any("embeds 1 bitmap" in line and "unchanged" in line for line in found)


def test_the_tree_s_kit_has_no_finding() -> None:
    assert kicad.findings(ROOT) == []


def test_recolor_turns_the_explicit_colors_to_the_light_ground() -> None:
    kit = helper()
    text = "(color 255 184 0 1) (color 136 153 170 1) (color 1 2 3 1)"
    assert kit.recolor(text, "dark") == text
    assert kit.recolor(text, "light") == "(color 138 90 0 1) (color 74 82 92 1) (color 1 2 3 1)"


def test_sync_copies_the_kit_with_its_manifest_and_holds_it(tmp_path: Path) -> None:
    target = tmp_path / "kit"
    (target).mkdir()
    (target / "stale.json").write_text("{}", encoding="utf-8")
    written = sync_kicad.copy(target, ROOT, at="0" * 40)
    assert sorted(written) == sorted(
        [*(path.name for path in kicad.kit_files(ROOT)), sync_kicad.MANIFEST]
    )
    assert not (target / "stale.json").exists()
    data = json.loads((target / sync_kicad.MANIFEST).read_text(encoding="utf-8"))
    assert (
        data["kit"] == "kleidos-kicad/1"
        and data["commit"] == "0" * 40
        and data["source"] == sync_kicad.SOURCE
    )
    assert sync_kicad.findings(target, None) == []
    assert sync_kicad.findings(target, ROOT) == []
    (target / "__pycache__").mkdir()
    assert sync_kicad.findings(target, None) == []
    style = target / "style.json"
    style.write_bytes(style.read_bytes() + b" ")
    (target / "extra.txt").write_text("x", encoding="utf-8")
    found = sync_kicad.findings(target, ROOT)
    assert any("style.json: not the bytes" in line for line in found)
    assert any("extra.txt: not part of the kit" in line for line in found)


def test_text_width_sums_the_measured_advances() -> None:
    kit = helper()
    assert kit.text_width("MMMM", 1.0) == pytest.approx(4 * 1.1429)
    assert kit.text_width("il", 2.0) == pytest.approx(2 * (0.4762 + 0.5238))
    assert kit.text_width("\u2603", 1.0) == pytest.approx(
        max(kit.style()["font"]["stroke_advance"].values())
    )


def test_the_longest_board_title_fits_its_cell_and_a_longer_one_does_not() -> None:
    kit = helper()
    assert (
        kit.cell_findings([("title", "M5Stack Cardputer-Adv (K132-Adv): Power, sockets and ports")])
        == []
    )
    assert kit.cell_findings(
        [("title", "M5Stack Cardputer-Adv (K132-Adv): Power, sockets, ports and the long tail")]
    )


def test_the_helper_reads_its_own_folder() -> None:
    kit = helper()
    assert (ROOT / "kicad").resolve() == kit.KIT
    assert kit.connection_mm() == pytest.approx(0.1524)
    assert kit.theme_colors("dark")["background"] == "#1C1C1C"
    assert kit.export_args("light")[:4] == [
        "--theme",
        "kleidos-light",
        "--drawing-sheet",
        str(kit.sheet("light")),
    ]
    assert "--default-font" not in kit.export_args("dark")


def test_the_fixture_s_project_names_the_kit_s_sheet_and_its_variables() -> None:
    pro = json.loads((ROOT / "kicad/fixture/fixture.kicad_pro").read_text(encoding="utf-8"))
    assert pro["schematic"]["page_layout_descr_file"] == "../kleidos-dark.kicad_wks"
    assert pro["text_variables"] == {"LICENSE": "MIT", "SOURCE_URL": "github.com/kleidos-dev/brand"}


@pytest.mark.skipif(shutil.which("kicad-cli") is None, reason="kicad-cli is not installed")
def test_the_fixture_passes_erc_with_no_message() -> None:
    kit = helper()
    count, report = kit.erc(ROOT / "kicad/fixture/fixture.kicad_sch", kit.environment())
    assert count == 0, report
