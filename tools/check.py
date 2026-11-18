#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Hold the tree to its rules. Needs no browser; the pre-commit hook and CI run it.

    tools/check.py            check this repository
    tools/check.py --root X   check the copy of it at X (the tests plant defects in one)

What it holds:

- built:     every generated file is what its sources give, every picture's bytes are the recorded
             ones, and none is stale (tools/build.py --check --static);
- mark:      every copy of the mark is logo/src/mark.svg's shapes, or the small mark the builder
             fits from them at a size logo/src/small-mark.json lists, and the keyhole is never
             drawn without its ring;
- sources:   each press template keeps the source rules (layers, plain shapes, token colors, the two
             families, no opacity or filter or picture), carries the lockup the logo files draw, and
             keeps every word and the lockup inside its safe area in every language; each
             photograph press.json lists is there, at its size, with no metadata segment, and
             nothing else is in its folder;
- generated: a generated SVG holds outlines only and opens with the license header;
- fonts:     only the pinned upstream files, byte for byte, and no font inside an SVG;
- boards:    each front under boards/ is the byte copy boards/boards.json records, and a line-up
             can draw it;
- licenses:  every declaration (an SPDX tag, a REUSE.toml identifier, a text in LICENSES/) is
             GPL-3.0-or-later, MIT or OFL-1.1; prose may name any license, a declaration may not;
- texts:     the Spanish term rule, the texts' agreement with about/facts.json (the name's
             origin, its former name and the history included, and the pronunciation printed
             where the owner has confirmed it and nowhere until he has), the press permission
             quoted whole where the press kit promises it, both additional terms (7(c) and 7(e))
             stated in TRADEMARKS.md;
- public:    nothing private, no picture out of place, no board drawing outside boards/, no
             registered-trademark sign but a board's own print.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402
from kleidos_brand import BRAND_ROOT, SVG_HEADER, boards, logo, mark, palette, photos, png, press, public_tree, svg_rules, tokens  # noqa: E402

ALLOWED_LICENSES = frozenset({"GPL-3.0-or-later", "MIT", "OFL-1.1"})
PICTURE_DIRS = ("logo/png", "colors", "press-kit/images", "press-kit/screens", photos.PHOTOS_DIR.as_posix())
SPANISH_BANNED = re.compile(r"\b(?:vault|vaults|b[oó]veda|b[oó]vedas)\b", re.I)
URL = re.compile(r"https?://[^\s<>)\"'`]+")
MISWRITTEN = re.compile(r"KLEIDOS|KleidOS|Kleidos OS")
VENDOR_FORMS = re.compile(r"(?<![\w/-])(?:lilygo|m5stack)(?![\w-])", re.I)  # prose, not a file name
TEXT_DIRS = ("about", "press-kit")
ABOUT_TEXTS = ("one-line", "one-paragraph", "one-page", "name-and-history")


def mark_findings(root: Path, files: list[Path]) -> list[str]:
    values = tokens.resolve(tokens.load(root))
    inks = frozenset({values["social.ink"], values["social.light.ink"]})
    shapes = mark.shapes(root)
    small = mark.small_marks(shapes, {mark.ring_color(shapes), *inks}, root)
    found = []
    below = mark.small_numbers(root)["below_px"]
    full = json.loads((root / tokens.TOKENS_JSON).read_text(encoding="utf-8"))["brand"]["logo"]["min-px-on-dark"]["$value"]
    if below != full or any(px >= below or px % 2 == 0 for px in mark.small_numbers(root)["sizes"]):
        found.append(f"{mark.SMALL_JSON}: the small mark is for sizes under {below} px, and the full mark holds from"
                     f" {full} px (tokens.json brand.logo.min-px-on-dark); the two agree, and every small size is odd and under it")
    for path in files:
        if path.suffix == ".svg":
            found += mark.findings(root / path, shapes, inks, path.as_posix(), small)
    return found


def source_findings(root: Path) -> list[str]:
    colors = tokens.palette(tokens.load(root))
    data = press.load(root)
    found = []
    for source in sorted((root / press.SRC_DIR).glob("*.svg")):
        name = source.relative_to(root).as_posix()
        found += svg_rules.findings(source, colors, root, name)
        if not source.read_text(encoding="utf-8").startswith(SVG_HEADER):
            found.append(f"{name}: does not open with the license header")
        if not press.template_lockup_matches(root, source.stem):
            found.append(f"{name}: its lockup is not the one logo/svg/ draws; paste the group again from the for-dark file")
    for layout, keys in data["lines"].items():
        for key, by_lang in keys.items():
            for lang, lines in by_lang.items():
                if " ".join(lines) != data["words"][lang][key]:
                    found.append(f"press.json: the lines of {layout} for {key!r} in {lang} do not join into its words")
    for lang, words in data["words"].items():
        for key in [key for key in words if key.endswith("_accent")]:
            if words[key] not in words[key.removesuffix("_accent")]:
                found.append(f"press.json: the accent of {key.removesuffix('_accent')!r} in {lang} is not part of its words")
    try:
        for image in press.images(root):
            found += press.findings(image)
    except (ValueError, KeyError, ET.ParseError) as error:
        found.append(f"press-kit/src: {error}")
    for board, screen in data["screens"].items():
        native = root / press.SCREENS_DIR / f"kleidos-screen-{board}.png"
        if not native.is_file():
            found.append(f"{native.relative_to(root)}: missing")
        else:
            found += png.findings(native.relative_to(root).as_posix(), native.read_bytes(), tuple(screen["size"]))
    expected = set()
    for photo in data.get("photos", {}).values():
        whole = photos.PHOTOS_DIR / f"{photo['file']}.jpg"
        expected |= {whole, *(photos.PHOTOS_DIR / f"{photo['file']}-{width}.jpg" for width in photo.get("copies", ()))}
        for key in ("size", "what", "credit", "given"):
            if not photo.get(key):
                found.append(f"press.json: the photograph {photo['file']!r} has no {key!r}")
        if any(not (photo.get("alt") or {}).get(lang) for lang in data["langs"]):
            found.append(f"press.json: the photograph {photo['file']!r} needs an alt text in each of {', '.join(data['langs'])}")
        readme = (root / "press-kit/README.md").read_text(encoding="utf-8")
        for needed in (photo.get("credit"), *(photo.get("alt") or {}).values()):
            if needed and needed not in readme:
                found.append(f"press-kit/README.md: does not give {needed[:50]!r}, the photograph {photo['file']!r}'s credit or alt text")
        if not (root / whole).is_file():
            found.append(f"{whole}: missing")
        else:
            found += photos.findings(whole.as_posix(), (root / whole).read_bytes(), tuple(photo["size"]))
    if (root / photos.PHOTOS_DIR).is_dir():
        for path in sorted((root / photos.PHOTOS_DIR).iterdir()):
            if path.is_file() and path.relative_to(root) not in expected:
                found.append(f"{path.relative_to(root).as_posix()}: press.json lists no photograph or copy by this name")
    return found


def generated_findings(root: Path) -> list[str]:
    colors = tokens.palette(tokens.load(root))
    found = []
    generated = [*sorted((root / logo.SVG_DIR).glob("*.svg")), *sorted((root / press.SVG_DIR).glob("*.svg")), root / palette.PALETTE_SVG]
    for path in [*generated, root / mark.MARK_SVG]:
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        if not path.read_text(encoding="utf-8").startswith(SVG_HEADER):
            found.append(f"{name}: does not open with the license header (the tag alone on its line, then where the additional terms are)")
        if path != root / mark.MARK_SVG:
            found += svg_rules.outlined_findings(path, colors, name)
    return found


def license_findings(root: Path, files: list[Path]) -> list[str]:
    found = public_tree.license_findings(root, files, ALLOWED_LICENSES)
    text, copy = root / "LICENSE", root / "LICENSES" / "GPL-3.0-or-later.txt"
    if not text.is_file() or not copy.is_file() or text.read_bytes() != copy.read_bytes():
        found.append("LICENSE: is not the text of LICENSES/GPL-3.0-or-later.txt")
    return found


def name_and_history_findings(root: Path, facts: dict, langs: list[str], texts: list[Path]) -> list[str]:
    """Hold the name's origin, its former name, its pronunciation and the history to facts.json.

    A confirmed pronunciation is printed, the guide of the page's language and the IPA, on each
    name-and-history page and fact sheet; an unconfirmed one is printed in no text.
    """
    found = []
    name, history = facts["name"], facts.get("history") or {}
    origin, former, said = name.get("origin") or {}, name.get("former") or {}, name.get("pronunciation") or {}
    events = history.get("events") or []
    confirmed = said.get("confirmed") is True
    guides = said.get("guide") if isinstance(said.get("guide"), dict) else {}
    if confirmed and (not said.get("source") or not said.get("ipa") or any(not guides.get(lang) for lang in langs)):
        found.append(f"about/facts.json: a confirmed pronunciation needs its source, its ipa and a guide in each of {', '.join(langs)}")
    for lang in langs:
        if not isinstance(origin.get(lang), str) or not isinstance(former.get(lang), str):
            found.append(f"about/facts.json: name.origin and name.former need a text in {lang!r}")
    if not origin.get("greek") or not former.get("written") or not history.get("source") or not history.get("as_of"):
        found.append("about/facts.json: the name needs origin.greek and former.written, the history its source and as_of")
    for index, event in enumerate(events):
        missing = [key for key in ("when", *langs) if not event.get(key)] + [f"said.{lang}" for lang in langs if not (event.get("said") or {}).get(lang)]
        if missing:
            found.append(f"about/facts.json: history.events[{index}] lacks {', '.join(missing)}")
    if not events:
        found.append("about/facts.json: the history has no events")
    for lang in langs:
        for page in (f"about/{lang}/name-and-history.md", f"press-kit/{lang}/fact-sheet.md"):
            path = root / page
            if not path.is_file():
                continue  # a missing page is reported where the texts are listed
            body = path.read_text(encoding="utf-8")
            for needed in (origin.get("greek"), former.get("written"), *((event.get("said") or {}).get(lang) for event in events)):
                if needed and needed not in body:
                    found.append(f"{page}: does not hold {needed!r}, which about/facts.json states for the name or the history")
            if confirmed:
                for needed in (guides.get(lang), said.get("ipa")):
                    if needed and needed not in body:
                        found.append(f"{page}: does not print the pronunciation {needed!r}, which the owner has confirmed (about/facts.json)")
    if said and not confirmed:
        unconfirmed = [*(guides.values() if guides else [said.get("guide")]), said.get("ipa")]
        for path in texts:
            body = path.read_text(encoding="utf-8")
            for form in unconfirmed:
                if form and form in body:
                    found.append(f"{path.relative_to(root).as_posix()}: prints the pronunciation {form!r}, which the owner has not confirmed")
    return found


def text_findings(root: Path) -> list[str]:
    found = []
    facts = json.loads((root / "about/facts.json").read_text(encoding="utf-8"))
    data = press.load(root)
    if facts["name"]["written"] != "Kleidos" or facts["mark"]["registered_trademark"] is not False:
        found.append("about/facts.json: the name is written 'Kleidos' and is not a registered trademark")
    links = set(facts["links"].values()) | {facts["creator"]["url"], facts["status"]["see"]}
    vendors = set(facts["vendors"])
    texts = sorted(path for folder in TEXT_DIRS for path in (root / folder).rglob("*.md"))
    for path in texts:
        name = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        if "/es/" in f"/{name}" and SPANISH_BANNED.search(text):
            found.append(f"{name}: a Spanish text says 'vault' or 'bóveda'; the container is 'llavero', its content 'tus contraseñas'")
        for url in URL.findall(text):
            if url.rstrip(".,;:") not in links:
                found.append(f"{name}: links to {url}, which about/facts.json does not list")
        for form in VENDOR_FORMS.findall(text):
            if form not in vendors:
                found.append(f"{name}: writes a vendor as {form!r}; about/facts.json writes {', '.join(sorted(vendors))}")
    for name in (f"about/{lang}/{size}.md" for lang in data["langs"] for size in ABOUT_TEXTS):
        text = (root / name).read_text(encoding="utf-8") if (root / name).is_file() else None
        if text is None:
            found.append(f"{name}: missing")
        elif MISWRITTEN.search(text):
            found.append(f"{name}: miswrites the name; it is 'Kleidos', a capital K and nothing else in capitals")
    for lang in data["langs"]:
        for key, value in data["words"][lang].items():
            if lang == "es" and SPANISH_BANNED.search(value):
                found.append(f"press.json: words.es.{key} says 'vault' or 'bóveda'")
            if MISWRITTEN.search(value):
                found.append(f"press.json: words.{lang}.{key} miswrites the name")
        paragraph = (root / f"about/{lang}/one-paragraph.md").read_text(encoding="utf-8").strip()
        if paragraph not in (root / "press-kit/README.md").read_text(encoding="utf-8"):
            found.append(f"press-kit/README.md: does not quote about/{lang}/one-paragraph.md as it is")
        sheet = root / f"press-kit/{lang}/fact-sheet.md"
        if not sheet.is_file():
            found.append(f"press-kit/{lang}/fact-sheet.md: missing")
        else:
            body = sheet.read_text(encoding="utf-8")
            for needed in (paragraph, facts["license"]["spdx"], facts["contact"]["email"], facts["creator"]["name"], facts["creator"]["name_ascii"]):
                if needed not in body:
                    found.append(f"press-kit/{lang}/fact-sheet.md: does not hold {needed[:50]!r}, which about/facts.json states")
    found += name_and_history_findings(root, facts, data["langs"], texts)
    trademarks = (root / "TRADEMARKS.md").read_text(encoding="utf-8") if (root / "TRADEMARKS.md").is_file() else ""
    for needed in ("Kleidos is not a registered trademark", "section 7(e)", "section 7(c)", "This part is a request. It adds no condition to the license."):
        if needed not in trademarks:
            found.append(f"TRADEMARKS.md: does not say {needed!r}")
    permission = next((line for line in trademarks.splitlines() if line.startswith("**Additional permission under section 7")), None)
    usage = (root / "press-kit/USAGE.md").read_text(encoding="utf-8")
    if permission is None or permission not in usage:
        found.append("press-kit/USAGE.md: does not quote the press permission of TRADEMARKS.md whole")
    for page in ("logo/README.md", "press-kit/USAGE.md"):
        if "adds no condition to the license" not in (root / page).read_text(encoding="utf-8"):
            found.append(f"{page}: lists what not to do without saying it is a request that adds no condition to the license")
    return found


def findings(root: Path = BRAND_ROOT) -> list[str]:
    """Return everything in the tree at *root* that breaks a rule."""
    files = public_tree.tracked(root)
    try:
        found = build.static_findings(root)
    except (ValueError, KeyError, ET.ParseError, OSError) as error:
        found = [f"the sources cannot be built, so nothing generated was compared: {error}"]
    found += mark_findings(root, files)
    found += source_findings(root)
    found += generated_findings(root)
    found += public_tree.font_findings(root, files, public_tree.font_pins(root))
    found += license_findings(root, files)
    found += text_findings(root)
    found += boards.findings(root)
    found += public_tree.findings(root, files, PICTURE_DIRS, board_dirs=(boards.BOARDS_DIR.as_posix(),))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=BRAND_ROOT, help="the tree to check (default: this repository)")
    args = parser.parse_args(argv)
    found = findings(args.root.resolve())
    for line in found:
        print(line)
    if found:
        print(f"\n{len(found)} finding(s).")
        return 1
    print("check: the tree keeps its rules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
