# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The sync script, against a small tree shaped like the firmware repository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import sync_from_kleidos as sync

from kleidos_brand import mark, png, press, public_tree, tokens

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def firmware(tmp_path: Path) -> Path:
    """Return a tree that holds, where the firmware repository holds them, the values this one
    mirrors."""
    base = tmp_path / "firmware"
    loaded = tokens.load(ROOT)
    values = tokens.resolve(loaded)

    # The design-system skill's tokens and the firmware's header.
    skill: dict[str, Any] = {"color": {}}
    constants = []
    for name, token in tokens.leaves(loaded["device"]["dark"]).items():
        node = skill["color"]
        *folders, leaf = name.split(".")
        for folder in folders:
            node = node.setdefault(folder, {})
        node[leaf] = {"$value": token["$value"].upper()}
        constants.append(
            f"constexpr uint32_t {token['$extensions']['dev.kleidos']['theme_h']} = "
            f"0x{token['$value'][1:]};"
        )
    for group in ("density", "radius", "stroke", "opacity", "motion", "font"):
        skill[group] = json.loads(json.dumps(loaded["device"][group]))
    write(base / sync.SKILL_TOKENS, json.dumps(skill))
    write(base / sync.THEME_H, "\n".join(constants) + "\n")

    # The site's sheet: the dark block, and the light theme written twice.
    web = loaded["web"]
    dark = [
        f"    --{name}: {token['$value']};" for name, token in tokens.leaves(web["dark"]).items()
    ]
    for group in ("faces", "radius", "motion"):
        dark += [
            f"    --{name}: {token['$value']};" for name, token in tokens.leaves(web[group]).items()
        ]
    for role, parts in web["type"]["roles"].items():
        dark += [
            f"    --t-{role}{suffix}: {parts[part]['$value']};"
            for part, suffix in tokens.TYPE_PARTS
        ]
    light = "\n".join(
        f"    --{name}: {token['$value']};" for name, token in tokens.leaves(web["light"]).items()
    )
    write(
        base / sync.STYLE_CSS,
        "@layer tokens {\n  :root {\n    /* The page. */\n" + "\n".join(dark) + "\n  }\n"
        '  @media (prefers-color-scheme: light) {\n    :root:not([data-theme="dark"]) {\n'
        + light
        + "\n    }\n  }\n"
        '  :root[data-theme="light"] {\n' + light + "\n  }\n}\n",
    )

    # The mark, the font pins, the site's words, the screens.
    shapes = "".join(
        f"<{name} " + " ".join(f'{key}="{value}"' for key, value in attributes) + f"></{name}>"
        for name, attributes in mark.shapes(ROOT)
    )
    write(
        base / sync.MARK_SOURCE,
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-50 -50 100 100">{shapes}</svg>',
    )
    pins = "\n".join(
        f"  - `{name.removeprefix('fonts/')}`\n    `{digest}`"
        for name, digest in public_tree.font_pins(ROOT).items()
    )
    write(base / sync.FONT_PINS, pins + "\n")
    data = press.load(ROOT)
    for lang in data["langs"]:
        strings = {source: data["words"][lang][key] for key, source in data["from"].items()}
        strings["home.lede"] = public_tree.prose(ROOT / f"about/{lang}/one-paragraph.md")
        strings["home.meta_description"] = (
            public_tree.prose(ROOT / f"about/{lang}/one-line.md") + " More."
        )
        write(base / sync.STRINGS.format(lang=lang), json.dumps(strings))
    for board, screen in data["screens"].items():
        (base / screen["from"]).parent.mkdir(parents=True, exist_ok=True)
        # The firmware's master as it holds it: the same pixels, without the metadata written here.
        (base / screen["from"]).write_bytes(
            png.bare((ROOT / press.SCREENS_DIR / f"kleidos-screen-{board}.png").read_bytes())
        )
    assert values["brand.signal"] == "#00d2ff"
    return base


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_a_tree_with_the_same_values_has_no_difference(firmware: Path) -> None:
    assert sync.token_findings(firmware, ROOT) == []
    assert sync.other_findings(firmware, None, ROOT) == []
    assert set(sync.mirror_digests(firmware)) == set(sync.MIRRORED)


def test_a_changed_constant_is_reported(firmware: Path) -> None:
    header = firmware / sync.THEME_H
    header.write_text(
        header.read_text(encoding="utf-8").replace("kPrimary = 0x00d2ff", "kPrimary = 0x00d2fe"),
        encoding="utf-8",
    )
    assert any(
        "kPrimary" in line and "#00d2fe" in line for line in sync.token_findings(firmware, ROOT)
    )


def test_a_changed_site_token_is_reported_in_each_block(firmware: Path) -> None:
    sheet = firmware / sync.STYLE_CSS
    sheet.write_text(
        sheet.read_text(encoding="utf-8")
        .replace("--ink: #0c0f13;", "--ink: #000000;", 1)
        .replace("--stage: #0a0c0f;", "--stage: #000000;"),
        encoding="utf-8",
    )
    found = sync.token_findings(firmware, ROOT)
    assert any("light-system" in line and "--ink" in line for line in found)
    assert not any("light-chosen" in line for line in found), (
        "only the first light block was changed"
    )
    assert any("(dark) --stage" in line for line in found)


def test_changed_words_a_changed_mark_and_a_changed_pin_are_reported(firmware: Path) -> None:
    strings = firmware / sync.STRINGS.format(lang="es")
    strings.write_text(
        strings.read_text(encoding="utf-8").replace("ya tienes", "ya es tuya"), encoding="utf-8"
    )
    logo = firmware / sync.MARK_SOURCE
    logo.write_text(logo.read_text(encoding="utf-8").replace('r="42"', 'r="41"'), encoding="utf-8")
    pins = firmware / sync.FONT_PINS
    pins.write_text(
        pins.read_text(encoding="utf-8").replace("40d692fc", "00000000"), encoding="utf-8"
    )
    found = sync.other_findings(firmware, None, ROOT)
    assert any("words.es.title" in line for line in found)
    assert any("logo/src/mark.svg" in line for line in found)
    assert any("Inter-Regular.ttf" in line for line in found)


def test_a_capture_is_held_to_its_master_pixels_not_its_bytes(firmware: Path) -> None:
    from PIL import Image

    data = press.load(ROOT)
    board, screen = next(iter(data["screens"].items()))
    master = firmware / screen["from"]
    assert (
        master.read_bytes()
        != (ROOT / press.SCREENS_DIR / f"kleidos-screen-{board}.png").read_bytes()
    ), "the copy here carries metadata"
    assert sync.other_findings(firmware, None, ROOT) == []
    with Image.open(master) as opened:
        moved = opened.convert("RGBA")
    moved.putpixel((0, 0), (255, 0, 255, 255))
    moved.save(master, "PNG")
    assert any(
        f"kleidos-screen-{board}.png" in line and "pixels" in line
        for line in sync.other_findings(firmware, None, ROOT)
    )
