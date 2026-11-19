# SPDX-License-Identifier: MIT
"""The checks catch what they are for: each test plants one defect in a copy of the tree."""
from __future__ import annotations

import io
import shutil
import subprocess
import sys
from pathlib import Path

import check
from kleidos_brand import SVG_HEADER, public_tree

ROOT = Path(__file__).resolve().parents[1]

# Private data the tests plant, put together here so that this file holds none.
HOME_PATH = "/Us" + "ers/" + "someone/notes.txt"
PRIVATE_ADDRESS = "192." + "168.1.20"
HARDWARE_ADDRESS = "aa:bb:cc:" + "dd:ee:ff"
OTHER_EMAIL = "someone" + "@" + "elsewhere.org"
REGISTERED = chr(0xAE)
# REUSE-IgnoreStart
CC_TAG = "SPDX-License-Identifier: CC-BY-SA-4.0"
ONE_LINE_HEADER = "<!-- SPDX-License-Identifier: GPL-3.0-or-later. Additional terms under section 7 of the GNU GPL version 3: TRADEMARKS.md. -->\n"
# REUSE-IgnoreEnd


def found(tree: Path, *needles: str) -> bool:
    """Tell whether the check reports a finding that holds every needle."""
    return any(all(needle in line for needle in needles) for line in check.findings(tree))


def planted(tree: Path, name: str) -> Path:
    """Return the path of a file a test plants, its folder made if the tree has none."""
    path = tree / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{path.name} does not hold {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_the_tree_as_committed_is_clean() -> None:
    assert check.findings(ROOT) == []


def test_a_copy_of_the_tree_is_clean(tree: Path) -> None:
    assert check.findings(tree) == []


# --- The mark ----------------------------------------------------------------------------


def test_a_ringless_glyph_is_refused(tree: Path) -> None:
    (tree / "logo/svg/extra.svg").write_text(
        SVG_HEADER + '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-50 -50 100 100">'
        '<rect x="-20" y="-38" width="40" height="76" rx="20" fill="#00d2ff"/></svg>\n', encoding="utf-8")
    assert found(tree, "logo/svg/extra.svg", "never drawn without its ring")


def test_a_keyhole_made_of_the_marks_own_shapes_is_refused(tree: Path) -> None:
    drawing = (tree / "logo/src/mark.svg").read_text(encoding="utf-8")
    ring = next(line for line in drawing.splitlines() if 'r="42"' in line)
    planted(tree, "notes/keyhole.svg").write_text(drawing.replace(ring + "\n", ""), encoding="utf-8")
    assert found(tree, "notes/keyhole.svg", "never drawn without its ring")


def test_a_loose_recolored_copy_of_the_mark_is_refused(tree: Path) -> None:
    drawing = (tree / "logo/src/mark.svg").read_text(encoding="utf-8")
    planted(tree, "notes/copy.svg").write_text(drawing.replace("#00D2FF", "#51cf66"), encoding="utf-8")
    assert found(tree, "notes/copy.svg", "outside a <g class=")


def test_the_marks_own_drawing_and_its_groups_are_accepted(tree: Path) -> None:
    shutil.copyfile(tree / "logo/src/mark.svg", planted(tree, "notes/mark.svg"))
    shutil.copyfile(tree / "logo/svg/kleidos-mark-ink-dark.svg", planted(tree, "notes/ink.svg"))
    assert not any("outside a <g class=" in line for line in check.findings(tree))


def test_a_group_named_for_the_glyph_is_refused(tree: Path) -> None:
    edit(tree / "press-kit/src/hero-16x9.svg", '<line id="rule"', '<line id="mark-glyph"')
    assert found(tree, "hero-16x9.svg", "named for the ringless glyph")


def test_a_recolored_ring_is_refused(tree: Path) -> None:
    edit(tree / "logo/svg/kleidos-mark.svg", 'stroke="#00D2FF" stroke-width="3"', 'stroke="#51cf66" stroke-width="3"')
    assert found(tree, "logo/svg/kleidos-mark.svg", "recolored")
    assert found(tree, "logo/svg/kleidos-mark.svg", "is not what its sources give")


def test_a_redrawn_mark_is_refused(tree: Path) -> None:
    edit(tree / "press-kit/src/hero-16x9.svg", '<circle cx="0" cy="0" r="42"', '<circle cx="0" cy="0" r="40"')
    assert found(tree, "hero-16x9.svg", "redrawn")
    assert found(tree, "hero-16x9.svg", "its lockup is not the one logo/svg/ draws")


def test_a_one_ink_mark_in_another_ink_is_refused(tree: Path) -> None:
    path = tree / "logo/svg/kleidos-mark-ink-dark.svg"
    path.write_text(path.read_text(encoding="utf-8").replace("#0c0f13", "#51cf66"), encoding="utf-8")
    assert found(tree, "kleidos-mark-ink-dark.svg", "not one of the inks")


def test_the_small_mark_is_fitted_from_the_marks_numbers() -> None:
    from kleidos_brand import mark

    shapes, numbers = mark.shapes(ROOT), mark.small_numbers(ROOT)
    fits = {px: mark.small_fit(shapes, px, numbers) for px in numbers["sizes"]}
    assert all(px < numbers["below_px"] for px in fits)
    # 19 and 21 px are the fits the owner approved on 2026-11-18, pixel for pixel.
    for px in (19, 21):
        fit = fits[px]
        assert (fit.ring, fit.body_width, fit.body_height, fit.eye_up, fit.stem_width, fit.stem_length) == (px, 7, 13, 1, 1, 3)
    assert min(fits) == 19, "nothing smaller than 19 px is drawn (owner, 2026-11-18)"
    for fit in fits.values():
        assert fit.ring % 2 == fit.body_width % 2 == fit.body_height % 2 == 1
        assert fit.body_width >= 3 + 2 and fit.body_height <= fit.ring - 4
    ring, body = mark.small_shapes(fits[21], "#00D2FF")
    assert ring[0] == "circle" and dict(ring[1])["stroke"] == "#00D2FF"
    assert dict(body[1])["fill-rule"] == "evenodd" and dict(body[1])["d"].count("Z") == 2, "the keyhole is a hole in the body"


def test_a_recolored_small_mark_is_refused(tree: Path) -> None:
    path = tree / "logo/svg/kleidos-mark-small-21.svg"
    path.write_text(path.read_text(encoding="utf-8").replace('fill="#00D2FF"', 'fill="#0f3460"'), encoding="utf-8")
    assert found(tree, "kleidos-mark-small-21.svg", "its small mark is not one the builder fits")


def test_a_small_mark_redrawn_off_its_pixels_is_refused(tree: Path) -> None:
    edit(tree / "logo/svg/kleidos-mark-small-21.svg", 'r="10"', 'r="9.5"')
    assert found(tree, "kleidos-mark-small-21.svg", "its small mark is not one the builder fits")


def test_a_small_keyhole_without_its_ring_is_refused(tree: Path) -> None:
    drawing = (tree / "logo/svg/kleidos-mark-small-19.svg").read_text(encoding="utf-8")
    body = next(line.strip() for line in drawing.splitlines() if line.strip().startswith("<path"))
    planted(tree, "notes/small-keyhole.svg").write_text(
        SVG_HEADER + f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 19 19">{body}</svg>\n', encoding="utf-8")
    assert found(tree, "notes/small-keyhole.svg", "outside a <g class=")


def test_the_small_mark_ends_where_the_full_mark_holds(tree: Path) -> None:
    edit(tree / "logo/src/small-mark.json", '"below_px": 24', '"below_px": 32')
    assert found(tree, "small-mark.json", "the two agree")


def test_an_even_small_size_is_refused(tree: Path) -> None:
    edit(tree / "logo/src/small-mark.json", '"sizes": [19, 21, 23]', '"sizes": [19, 20, 21, 23]')
    assert found(tree, "small-mark.json", "every small size is odd")


# --- Generated files ---------------------------------------------------------------------


def test_a_picture_that_is_not_the_recorded_one_is_refused(tree: Path) -> None:
    shutil.copyfile(tree / "logo/png/kleidos-mark-256.png", tree / "logo/png/kleidos-mark-ink-dark-256.png")
    assert found(tree, "kleidos-mark-ink-dark-256.png", "not the ones exports.json records")


def test_a_stale_picture_is_refused(tree: Path) -> None:
    edit(tree / "logo/src/lockups.json", '"lettering_origin_after_mark_em": 0.32', '"lettering_origin_after_mark_em": 0.4')
    assert found(tree, "logo/png/kleidos-lockup-horizontal-for-dark-512.png", "stale")
    assert found(tree, "logo/svg/kleidos-lockup-horizontal-for-dark.svg", "is not what its sources give")


def test_a_file_nothing_generates_is_refused(tree: Path) -> None:
    shutil.copyfile(tree / "logo/png/kleidos-mark-64.png", tree / "logo/png/kleidos-mark-48.png")
    assert found(tree, "logo/png/kleidos-mark-48.png", "nothing generates it")


def test_a_photograph_with_camera_data_is_refused(tree: Path) -> None:
    from PIL import Image

    path = tree / "press-kit/photos/kleidos-photo-four-boards.jpg"
    exif = Image.Exif()
    exif[0x010F] = "A camera maker"
    with Image.open(path) as photo:
        buffer = io.BytesIO()
        photo.save(buffer, "JPEG", quality=88, exif=exif.tobytes())
    path.write_bytes(buffer.getvalue())
    assert found(tree, "kleidos-photo-four-boards.jpg", "M005", "EXIF")


def test_a_photograph_with_a_comment_or_another_record_is_refused(tree: Path) -> None:
    path = tree / "press-kit/photos/kleidos-photo-four-boards-1200.jpg"
    data = path.read_bytes()
    tables = data.index(b"\xff\xdb")
    comment = b"\xff\xfe" + (2 + len(b"a note")).to_bytes(2, "big") + b"a note"
    path.write_bytes(data[:tables] + comment + data[tables:])
    assert found(tree, "kleidos-photo-four-boards-1200.jpg", "COM (a comment)")
    title = b"Four boards running Kleidos, photograph"
    assert data.count(title) == 2, "the title is in the XMP packet and in its IIM twin"
    path.write_bytes(data.replace(title, title.replace(b"photograph", b"photogrXph"), 1))
    assert found(tree, "kleidos-photo-four-boards-1200.jpg", "M002", "XMP")


def test_a_photograph_nothing_lists_is_refused(tree: Path) -> None:
    shutil.copyfile(tree / "press-kit/photos/kleidos-photo-four-boards-1200.jpg", tree / "press-kit/photos/kleidos-photo-other.jpg")
    assert found(tree, "kleidos-photo-other.jpg", "lists no photograph")


def test_a_photograph_without_its_alt_text_is_refused(tree: Path) -> None:
    edit(tree / "press-kit/README.md", "Cuatro placas con Kleidos sobre una mesa", "Cuatro placas sobre una mesa")
    assert found(tree, "press-kit/README.md", "alt text")


def test_the_7c_term_is_required(tree: Path) -> None:
    edit(tree / "TRADEMARKS.md", "section 7(c)", "section 7")
    assert found(tree, "TRADEMARKS.md", "section 7(c)")


def test_a_picture_with_a_text_chunk_is_refused(tree: Path) -> None:
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo

    path = tree / "press-kit/screens/kleidos-screen-coreink.png"
    note = PngInfo()
    note.add_text("Software", "a camera")
    with Image.open(path) as picture:
        buffer = io.BytesIO()
        picture.save(buffer, "PNG", pnginfo=note)
    path.write_bytes(buffer.getvalue())
    assert found(tree, "kleidos-screen-coreink.png", "tEXt")
    assert found(tree, "kleidos-screen-coreink.png", "M005", "Software")


def test_a_picture_with_a_time_or_a_changed_text_is_refused(tree: Path) -> None:
    import zlib

    path = tree / "logo/png/kleidos-mark-256.png"
    data = path.read_bytes()
    stamp = b"tIME" + bytes([7, 234, 11, 19, 1, 2, 3])
    clock = (7).to_bytes(4, "big") + stamp + zlib.crc32(stamp).to_bytes(4, "big")
    path.write_bytes(data[:33] + clock + data[33:])
    assert found(tree, "logo/png/kleidos-mark-256.png", "M005", "tIME")
    title = b"Kleidos mark, in color, 256 px"
    assert title in data
    # The same chunk, one word changed and its CRC made again: well-formed, but not what the record gives.
    at = data.index(b"tEXtTitle\x00" + title)
    length = int.from_bytes(data[at - 4 : at], "big")
    assert length == len(b"Title\x00" + title)
    chunk = b"tEXtTitle\x00" + title.replace(b"256 px", b"257 px")
    path.write_bytes(data[:at] + chunk + zlib.crc32(chunk).to_bytes(4, "big") + data[at + 8 + length :])
    assert found(tree, "logo/png/kleidos-mark-256.png", "M002", "Title")


def test_a_private_value_or_a_miswritten_vendor_in_a_record_is_refused(tree: Path) -> None:
    press_json = tree / "press-kit/src/press.json"
    edit(press_json, "on a dark ground.\",", f"on a dark ground, from {HOME_PATH}.\",")
    edit(press_json, "on a white ground.\",", "on a white ground, by Lilygo.\",")
    assert found(tree, "press-kit/images/kleidos-16x9.png", "M004", "a local path")
    assert found(tree, "press-kit/images/kleidos-16x9-light.png", "M010")


def test_a_media_file_with_no_record_is_refused(tree: Path) -> None:
    shutil.copyfile(tree / "colors/palette.png", planted(tree, "about/palette-copy.png"))
    assert found(tree, "about/palette-copy.png", "M008")


def test_a_generated_svg_without_its_header_is_refused(tree: Path) -> None:
    path = tree / "colors/palette.svg"
    path.write_text(path.read_text(encoding="utf-8").replace(SVG_HEADER, "", 1), encoding="utf-8")
    assert found(tree, "colors/palette.svg", "license header")


# --- Sources -----------------------------------------------------------------------------


def test_a_color_off_the_palette_is_refused(tree: Path) -> None:
    edit(tree / "press-kit/src/hero-1x1.svg", 'stroke-width="2"', 'stroke-width="2" stroke-opacity="0.5"')
    edit(tree / "press-kit/src/hero-16x9.svg", 'fill="#9aa3ad">kleidos.dev', 'fill="#ff00ff">kleidos.dev')
    assert found(tree, "hero-16x9.svg", "#ff00ff", "not a token color")
    assert found(tree, "hero-1x1.svg", "stroke-opacity")


def test_an_embedded_picture_or_a_filter_is_refused(tree: Path) -> None:
    edit(tree / "press-kit/src/hero-16x9.svg", '<line id="rule"', '<image href="x.png" width="10" height="10"/><line id="rule"')
    assert found(tree, "hero-16x9.svg", "<image>")
    assert found(tree, "hero-16x9.svg", "embeds a picture")


def test_words_outside_the_safe_area_are_refused(tree: Path) -> None:
    edit(tree / "press-kit/src/hero-16x9.svg", '<text id="title.0" x="280"', '<text id="title.0" x="1400"')
    assert found(tree, "kleidos-16x9-es", "title.0", "outside the safe area")


def test_another_face_is_refused(tree: Path) -> None:
    edit(tree / "press-kit/src/hero-1x1.svg", 'font-size="52" font-family="Mona Sans Mono"', 'font-size="52" font-family="Arial"')
    assert found(tree, "hero-1x1.svg", "is set in 'Arial'")


def test_lines_that_do_not_join_into_the_words_are_refused(tree: Path) -> None:
    edit(tree / "press-kit/src/press.json", '"en": ["Your passwords, on a board", "you already own."]', '"en": ["Your passwords, on a board", "you own."]')
    assert found(tree, "press.json", "do not join into its words")


# --- Texts -------------------------------------------------------------------------------


def test_the_spanish_term_rule(tree: Path) -> None:
    edit(tree / "about/es/one-page.md", "Tus contraseñas se quedan cifradas", "Tu bóveda se queda cifrada")
    assert found(tree, "about/es/one-page.md", "llavero")


def test_a_link_the_facts_do_not_list_is_refused(tree: Path) -> None:
    edit(tree / "press-kit/en/fact-sheet.md", "- <https://kleidos.dev>", "- <https://kleidos.example.net>")
    assert found(tree, "press-kit/en/fact-sheet.md", "kleidos.example.net", "does not list")


def test_a_vendor_written_another_way_is_refused(tree: Path) -> None:
    edit(tree / "about/en/one-page.md", "LILYGO T-Deck Plus", "LilyGO T-Deck Plus")
    assert found(tree, "about/en/one-page.md", "'LilyGO'")


def test_a_miswritten_name_is_refused(tree: Path) -> None:
    edit(tree / "about/en/one-line.md", "Kleidos is", "KLEIDOS is")
    assert found(tree, "about/en/one-line.md", "miswrites the name")


def test_a_history_text_that_drifts_from_the_facts_is_refused(tree: Path) -> None:
    edit(tree / "about/es/name-and-history.md", "En abril de 2026", "En mayo de 2026")
    edit(tree / "press-kit/en/fact-sheet.md", "it was going to be called StickPass", "it was going to be called something else")
    assert found(tree, "about/es/name-and-history.md", "'abril de 2026'")
    assert found(tree, "press-kit/en/fact-sheet.md", "'StickPass'")


def test_the_name_and_history_page_is_required(tree: Path) -> None:
    (tree / "about/en/name-and-history.md").unlink()
    assert found(tree, "about/en/name-and-history.md", "missing")


def test_a_history_event_without_its_words_is_refused(tree: Path) -> None:
    edit(tree / "about/facts.json", '"said": {"en": "April 2026", "es": "abril de 2026"},', '"said": {"en": "April 2026"},')
    assert found(tree, "history.events[1]", "said.es")


def test_a_confirmed_pronunciation_must_be_printed(tree: Path) -> None:
    edit(tree / "about/en/name-and-history.md", "says its name KLAY-dos", "says its name KLEE-dos")
    edit(tree / "press-kit/es/fact-sheet.md", "| Pronunciación | «kléi-dos» ", "| Pronunciación | ")
    assert found(tree, "about/en/name-and-history.md", "'KLAY-dos'", "has confirmed")
    assert found(tree, "press-kit/es/fact-sheet.md", "'kléi-dos'", "has confirmed")


def test_a_confirmed_pronunciation_needs_a_guide_in_each_language(tree: Path) -> None:
    edit(tree / "about/facts.json", '"guide": {"en": "KLAY-dos", "es": "kléi-dos"}', '"guide": {"en": "KLAY-dos"}')
    assert found(tree, "about/facts.json", "confirmed pronunciation", "guide in each")


def test_an_unconfirmed_pronunciation_stays_out_of_the_texts(tree: Path) -> None:
    edit(tree / "about/facts.json", '"confirmed": true', '"confirmed": false')
    assert found(tree, "about/en/name-and-history.md", "'KLAY-dos'", "not confirmed")
    assert found(tree, "press-kit/es/fact-sheet.md", "'kléi-dos'", "not confirmed")
    assert not found(tree, "has confirmed")


def test_the_press_permission_must_be_quoted_whole(tree: Path) -> None:
    edit(tree / "press-kit/USAGE.md", "The texts may be quoted, shortened and translated. ", "")
    assert found(tree, "press-kit/USAGE.md", "press permission")


def test_a_list_of_do_nots_must_say_it_is_a_request(tree: Path) -> None:
    edit(tree / "logo/README.md", "It adds no condition to the license", "It is a rule")
    assert found(tree, "logo/README.md", "request")


# --- Licenses ----------------------------------------------------------------------------


def test_a_creative_commons_tag_is_refused(tree: Path) -> None:
    (tree / "about/extra.md").write_text(f"<!-- {CC_TAG} -->\n\nText.\n", encoding="utf-8")
    assert found(tree, "about/extra.md", "CC-BY-SA-4.0")


def test_a_creative_commons_text_or_annotation_is_refused(tree: Path) -> None:
    (tree / "LICENSES/CC-BY-SA-4.0.txt").write_text("text\n", encoding="utf-8")
    with (tree / "REUSE.toml").open("a", encoding="utf-8") as reuse:
        reuse.write('\n[[annotations]]\npath = ["about/**"]\nprecedence = "override"\n'
                    'SPDX-FileCopyrightText = "2026 Someone"\nSPDX-License-Identifier = "CC0-1.0"\n')
    assert found(tree, "LICENSES/CC-BY-SA-4.0.txt")
    assert found(tree, "REUSE.toml", "CC0-1.0")


def test_prose_may_name_another_license(tree: Path) -> None:
    notice = tree / "NOTICE.md"
    notice.write_text(notice.read_text(encoding="utf-8") + "\nA neighbour once used CC BY-SA 4.0 and Apache-2.0.\n", encoding="utf-8")
    assert not public_tree.license_findings(tree, [Path("NOTICE.md")], check.ALLOWED_LICENSES)


def test_the_one_line_header_breaks_reuse_and_the_check(tree: Path, tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    (scratch / "LICENSES").mkdir(parents=True)
    shutil.copyfile(ROOT / "LICENSES/GPL-3.0-or-later.txt", scratch / "LICENSES/GPL-3.0-or-later.txt")
    body = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>\n'

    def lint(header: str) -> int:
        (scratch / "mark.svg").write_text(header + body, encoding="utf-8")
        return subprocess.run([sys.executable, "-m", "reuse", "--root", str(scratch), "lint"], capture_output=True, check=False).returncode

    assert lint(ONE_LINE_HEADER) != 0, "REUSE reads the rest of the tag's line as part of the expression"
    assert lint(SVG_HEADER) == 0
    path = tree / "logo/src/mark.svg"
    path.write_text(path.read_text(encoding="utf-8").replace(SVG_HEADER, ONE_LINE_HEADER, 1), encoding="utf-8")
    assert found(tree, "logo/src/mark.svg", "a tag stands alone on its line")


# --- Fonts -------------------------------------------------------------------------------


def test_a_font_that_is_not_pinned_is_refused(tree: Path) -> None:
    shutil.copyfile(tree / "fonts/inter/Inter-Bold.ttf", tree / "fonts/inter/Inter-Bold-subset.woff2")
    assert found(tree, "Inter-Bold-subset.woff2", "Modified Version")


def test_a_pinned_font_with_other_bytes_is_refused(tree: Path) -> None:
    path = tree / "fonts/mona-sans/MonaSansMonoVF[wght].ttf"
    path.write_bytes(path.read_bytes() + b"\0")
    assert found(tree, "MonaSansMonoVF[wght].ttf", "not the pinned upstream file's")


def test_a_font_inside_an_svg_is_refused(tree: Path) -> None:
    (tree / "logo/svg/extra.svg").write_text(
        SVG_HEADER + '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><style>@font-face{font-family:x;'
        'src:url(data:font/woff2;base64,AAAA)}</style></svg>\n', encoding="utf-8")
    assert found(tree, "logo/svg/extra.svg", "never a font")


# --- The public tree ---------------------------------------------------------------------


def test_private_data_is_refused(tree: Path) -> None:
    planted(tree, "notes/notes.md").write_text(
        f"Saved in {HOME_PATH}, served from {PRIVATE_ADDRESS}, board {HARDWARE_ADDRESS}, ask {OTHER_EMAIL}.\n", encoding="utf-8")
    for what in ("home-directory path", "private network address", "hardware address", "not the project's contact"):
        assert found(tree, "notes/notes.md", what), what


def test_the_registered_sign_is_refused(tree: Path) -> None:
    edit(tree / "README.md", "The identity of [Kleidos]", f"The identity of [Kleidos{REGISTERED}]")
    assert found(tree, "README.md", "registered-trademark sign")


def test_a_board_drawing_is_refused(tree: Path) -> None:
    (tree / "press-kit/src/front.svg").write_text(
        SVG_HEADER + '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><g id="ground"/><g id="content">'
        '<g id="hotspots"/></g><g id="guides"/></svg>\n', encoding="utf-8")
    assert found(tree, "press-kit/src/front.svg", "board drawing")


def test_a_picture_out_of_place_is_refused(tree: Path) -> None:
    shutil.copyfile(tree / "logo/png/kleidos-mark-64.png", planted(tree, "notes/mark.png"))
    assert found(tree, "notes/mark.png", "outside")
