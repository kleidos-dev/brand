#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Hold what this repository mirrors to the firmware repository it mirrors.

    tools/sync_from_kleidos.py --check <firmware checkout> [--boards <boards checkout>]
    tools/sync_from_kleidos.py --record <firmware checkout>

For now the firmware repository is the source of the device's palette, the
site's tokens, the mark, the font pins and the words the texts and press
images copy from the site. ``--check`` prints
every difference and whether a mirrored file changed since the last record;
``--record`` writes the digests of the mirrored files to ``tokens/mirror.json``
once nothing differs. A difference is fixed here, by hand.

The checkout's path is an argument and is stored nowhere. CI cannot run this:
it cannot read the firmware repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kleidos_brand import BRAND_ROOT, mark, png, press, public_tree, tokens  # noqa: E402

MIRROR_JSON = Path("tokens/mirror.json")
SKILL_TOKENS = ".claude/skills/kleidos-design-system/assets/tokens.json"
THEME_H = "src/ui/core/theme.h"
STYLE_CSS = "site/assets/style.css"
MARK_SOURCE = "docs/design/handoff/assets/logo-full.svg"
FONT_PINS = "assets/fonts/VERSIONS.md"
STRINGS = "site/strings/{lang}.json"
MIRRORED = (SKILL_TOKENS, THEME_H, STYLE_CSS, MARK_SOURCE, FONT_PINS, STRINGS.format(lang="en"), STRINGS.format(lang="es"))

DECLARATION = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);")
CONSTANT = re.compile(r"constexpr\s+uint32_t\s+(k\w+)\s*=\s*0x([0-9a-fA-F]{6})\s*;")
DIGEST = re.compile(r"`([^`\s]+\.(?:ttf|otf|txt))`\s+`([0-9a-f]{64})`")


def _flat(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def css_blocks(sheet: str) -> dict[str, dict[str, str]]:
    """Return the declarations of the sheet's three token blocks: dark, and the light theme written twice."""
    sheet = re.sub(r"/\*.*?\*/", "", sheet, flags=re.S)
    start = sheet.index("@layer tokens {")
    heads = {
        "dark": sheet.index(":root {", start),
        "light-system": sheet.index(':root:not([data-theme="dark"]) {', start),
        "light-chosen": sheet.index(':root[data-theme="light"] {', start),
    }
    blocks = {}
    for name, at in heads.items():
        body = sheet[sheet.index("{", at) + 1 : sheet.index("}", at)]
        blocks[name] = {key: re.sub(r"\s+", " ", value).strip() for key, value in DECLARATION.findall(body)}
    return blocks


def token_findings(kleidos: Path, root: Path = BRAND_ROOT) -> list[str]:
    """Return every token here that is not the firmware repository's value."""
    loaded = tokens.load(root)
    found = []

    # The device's colors: the skill's file, then the firmware's header.
    skill: dict[str, Any] = json.loads((kleidos / SKILL_TOKENS).read_text(encoding="utf-8"))
    constants = {name: f"#{value.lower()}" for name, value in CONSTANT.findall((kleidos / THEME_H).read_text(encoding="utf-8"))}
    seen = set()
    for name, token in tokens.leaves(loaded["device"]["dark"]).items():
        node: Any = skill["color"]
        for part in name.split("."):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        theirs = node.get("$value") if isinstance(node, dict) else None
        if theirs is None or theirs.lower() != token["$value"].lower():
            found.append(f"device.dark.{name}: {token['$value']} here, {theirs} in the skill's tokens.json")
        constant = token.get("$extensions", {}).get("dev.kleidos", {}).get("theme_h")
        seen.add(constant)
        if constants.get(constant) != token["$value"].lower():
            found.append(f"device.dark.{name}: {token['$value']} here, {constants.get(constant)} as {constant} in {THEME_H}")
    for constant in sorted(set(constants) - seen):
        found.append(f"{THEME_H}: {constant} = {constants[constant]} has no token here")
    for group in ("density", "radius", "stroke", "opacity", "motion", "font"):
        ours = {name: token["$value"] for name, token in tokens.leaves(loaded["device"][group]).items()}
        theirs = {name: token["$value"] for name, token in tokens.leaves(skill[group]).items()}
        for name in sorted(set(ours) | set(theirs)):
            if ours.get(name) != theirs.get(name):
                found.append(f"device.{group}.{name}: {ours.get(name)!r} here, {theirs.get(name)!r} in the skill's tokens.json")

    # The site's tokens: the sheet's dark block, and its light theme, written twice.
    blocks = css_blocks((kleidos / STYLE_CSS).read_text(encoding="utf-8"))
    web = loaded["web"]
    expected: dict[str, dict[str, str]] = {"dark": {}, "light-system": {}, "light-chosen": {}}
    for name, token in tokens.leaves(web["dark"]).items():
        expected["dark"][name] = token["$value"]
    for group in ("faces", "radius", "motion"):
        for name, token in tokens.leaves(web[group]).items():
            expected["dark"][name] = token["$value"]
    for role, parts in web["type"]["roles"].items():
        for part, suffix in tokens.TYPE_PARTS:
            expected["dark"][f"t-{role}{suffix}"] = parts[part]["$value"]
    for name, token in tokens.leaves(web["light"]).items():
        expected["light-system"][name] = expected["light-chosen"][name] = token["$value"]
    for block, names in expected.items():
        for name, ours in names.items():
            theirs = blocks[block].get(name)
            if theirs is None or _flat(theirs) != _flat(ours):
                found.append(f"web ({block}) --{name}: {ours!r} here, {theirs!r} in {STYLE_CSS}")
    return found


def other_findings(kleidos: Path, boards: Path | None, root: Path = BRAND_ROOT) -> list[str]:
    """Return what else differs: the mark, the fonts, the copied words, the screens."""
    found = []

    theirs = [(mark.tag_name(child), tuple(sorted(child.attrib.items()))) for child in ET.parse(kleidos / MARK_SOURCE).getroot()]
    if theirs != mark.shapes(root):
        found.append(f"{mark.MARK_SVG}: its shapes are not those of {MARK_SOURCE}")

    ours = public_tree.font_pins(root)
    pins = {f"fonts/{name}": digest for name, digest in DIGEST.findall(re.sub(r"`\s*\n\s*`", "` `", (kleidos / FONT_PINS).read_text(encoding="utf-8")))}
    for name in sorted(set(ours) | set(pins)):
        if name in pins and ours.get(name) != pins[name]:
            found.append(f"{name}: pinned at {ours.get(name)} here and at {pins[name]} in {FONT_PINS}")
        elif name not in pins and not name.endswith("OFL.txt"):
            found.append(f"{name}: pinned here and not in {FONT_PINS}")
    if boards is not None:
        for path in sorted((boards / "fonts" / "inter").iterdir()):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if ours.get(f"fonts/inter/{path.name}") != digest:
                found.append(f"fonts/inter/{path.name}: the boards repository's copy has other bytes ({digest})")

    data = press.load(root)
    for lang in data["langs"]:
        strings = json.loads((kleidos / STRINGS.format(lang=lang)).read_text(encoding="utf-8"))
        for key, source in data["from"].items():
            if data["words"][lang][key] != strings.get(source):
                found.append(f"press.json words.{lang}.{key}: {data['words'][lang][key]!r} here, {strings.get(source)!r} as {source} on the site")
        copied = {
            f"about/{lang}/one-paragraph.md": strings["home.lede"],
            f"about/{lang}/one-line.md": strings["home.meta_description"].split(". ")[0] + ".",
        }
        for name, text in copied.items():
            if (root / name).read_text(encoding="utf-8").strip() != text:
                found.append(f"{name}: is not the site's sentence ({text[:60]}…)")
    # A capture here carries its own metadata (kleidos_brand.meta), so it is held to its master's pixels, not its bytes.
    for board, screen in data["screens"].items():
        native = root / press.SCREENS_DIR / f"kleidos-screen-{board}.png"
        if png.differing(native.read_bytes(), (kleidos / screen["from"]).read_bytes()) != 0:
            found.append(f"{native.relative_to(root)}: does not hold the pixels of {screen['from']}")
    return found


def mirror_digests(kleidos: Path) -> dict[str, str]:
    """Return the digest of every mirrored file of the firmware repository."""
    return {name: hashlib.sha256((kleidos / name).read_bytes()).hexdigest() for name in MIRRORED}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", metavar="KLEIDOS", type=Path, help="print every difference from this checkout")
    mode.add_argument("--record", metavar="KLEIDOS", type=Path, help="write the mirrored files' digests, once nothing differs")
    parser.add_argument("--boards", metavar="BOARDS", type=Path, help="also compare the boards repository's copy of Inter")
    args = parser.parse_args(argv)
    kleidos = args.check or args.record
    found = token_findings(kleidos) + other_findings(kleidos, args.boards)
    digests = mirror_digests(kleidos)
    mirror = BRAND_ROOT / MIRROR_JSON
    if args.record:
        if found:
            for line in found:
                print(line)
            print(f"\n{len(found)} difference(s): fix them here before recording.")
            return 1
        body = {"$comment": "Written by tools/sync_from_kleidos.py --record: the digests of the firmware repository's files this repository mirrors, as last compared. Do not edit.", "files": digests}
        mirror.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        print(f"recorded {len(digests)} digests in {MIRROR_JSON}")
        return 0
    recorded = json.loads(mirror.read_text(encoding="utf-8"))["files"] if mirror.is_file() else {}
    for name, digest in digests.items():
        if recorded.get(name) != digest:
            found.append(f"{name}: changed since the mirror was last recorded; compare, then run --record")
    for line in found:
        print(line)
    if found:
        print(f"\n{len(found)} difference(s).")
        return 1
    print("sync check: the mirror is the firmware repository's, value for value, and nothing changed since it was recorded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
