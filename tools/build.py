#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build everything this repository generates, or check that what is committed is what the sources give.

    tools/build.py                    regenerate the tokens' files, the logo files, the palette,
                                      the press images, the photographs' narrower copies, the
                                      record and the pages' tables
    tools/build.py --check            draw everything again and fail on any difference, pixel for
                                      pixel; refused under a browser other than the recorded one
    tools/build.py --check --static   what needs no browser: every text file, every table, and each
                                      picture's bytes against the record of what it was drawn from
    tools/build.py --check --tolerant draw again under any browser and fail on gross drift only
    tools/build.py --zip              write dist/kleidos-press-kit.zip (not committed)

The exact comparison belongs to the machine that exported: Chromium draws an
edge a shade apart from one version or system to the next. The static check
and the tolerant one run anywhere, and CI runs both.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kleidos_brand import BRAND_ROOT, boards, lettering, logo, mark, palette, photos, png, press, raster, record, tokens  # noqa: E402

#: The share of pixels that may differ by more than a shade under another browser.
TOLERANCE = 0.005

MONA = lettering.FAMILIES["Mona Sans"]
MONO = lettering.FAMILIES["Mona Sans Mono"]
LOGO_INPUTS = (mark.MARK_SVG, logo.LOCKUPS_JSON, tokens.TOKENS_JSON, MONA)
GENERATED_DIRS = (logo.SVG_DIR, logo.PNG_DIR, press.SVG_DIR, press.IMAGES_DIR, Path("tokens/dist"))
#: How a README table names a language of press.json.
LANGUAGES = {"en": "English", "es": "Spanish"}


@dataclass(frozen=True)
class Text:
    """A generated text file and what it must hold."""

    path: Path
    content: str


@dataclass(frozen=True)
class Picture:
    """A generated picture (a PNG, or a photograph's JPEG copy): its size, its limit, what it is drawn from and how."""

    path: Path
    size: tuple[int, int]
    source: str  # the SHA-256 of the SVG or capture it is drawn from
    inputs: tuple[Path, ...]
    draw: Callable[[raster.Browser | None, dict[str, Any]], bytes]
    what: str
    limit: int | None = None
    needs_browser: bool = True


def collect(root: Path = BRAND_ROOT) -> tuple[list[Text], list[Picture]]:
    """Return every file the builder owns: the text ones with their content, the pictures with their recipe."""
    loaded = tokens.load(root)
    texts = [
        Text(tokens.FLAT_JSON, tokens.flat_json(loaded)),
        Text(tokens.TOKENS_CSS, tokens.css(loaded)),
    ]
    pictures: list[Picture] = []

    # --- Logo files ----------------------------------------------------------------------
    for item in logo.build(root):
        texts.append(Text(logo.SVG_DIR / f"{item.stem}.svg", item.svg))
    for item, width, height, path in logo.png_plan(root):
        def draw_logo(browser: raster.Browser | None, _: dict[str, Any], item: logo.Logo = item, size: tuple[int, int] = (width, height)) -> bytes:
            assert browser is not None
            return png.encode(png.clean(browser.draw(item.svg, size, item.stem), flatten=item.ground))

        box = round(height * item.mark_share)
        what = item.what + (f"; the mark box is {box} px" if box else "")
        pictures.append(Picture(path, (width, height), record.sha256(item.svg.encode()), LOGO_INPUTS, draw_logo, what))

    # --- The palette ---------------------------------------------------------------------
    sheet, sheet_size = palette.svg(root)
    ground = tokens.resolve(loaded)["social.ground"]
    texts.append(Text(palette.PALETTE_SVG, sheet))

    def draw_palette(browser: raster.Browser | None, _: dict[str, Any]) -> bytes:
        assert browser is not None
        return png.encode(png.clean(browser.draw(sheet, sheet_size, "palette"), flatten=ground))

    pictures.append(Picture(palette.PALETTE_PNG, sheet_size, record.sha256(sheet.encode()), (tokens.TOKENS_JSON, MONA, MONO),
                            draw_palette, "the swatch sheet"))

    # --- Press images --------------------------------------------------------------------
    data = press.load(root)
    for image in press.images(root):
        if image.publish_svg:
            texts.append(Text(press.SVG_DIR / f"{image.stem}.svg", image.svg))
        screens = tuple(press.SCREENS_DIR / f"kleidos-screen-{plate.board}.png" for plate in image.plates)
        screens += tuple(boards.screen_path(placed.slug) for placed in image.fronts)
        lineup = tuple(path for path in boards.inputs(root) if path not in screens) if image.fronts else ()
        inputs = (*LOGO_INPUTS, MONO, press.PRESS_JSON, press.SRC_DIR / f"{image.layout}.svg", *screens, *lineup)
        source = record.sha256(image.svg.encode() + b"".join((root / screen).read_bytes() for screen in screens))
        what = image.what + ("" if image.lang == data["default_lang"] else f", in {LANGUAGES.get(image.lang, image.lang)}")

        def full(browser: raster.Browser | None, cache: dict[str, Any], image: press.Image = image) -> Any:
            if image.stem not in cache:
                assert browser is not None
                drawn = png.clean(browser.draw(image.svg, image.size, image.stem), flatten=image.ground)
                cache[image.stem] = press.paste_screens(image, drawn, root)
            return cache[image.stem]

        for index, (path, size) in enumerate(image.png_paths()):
            def draw_press(browser: raster.Browser | None, cache: dict[str, Any], image: press.Image = image,
                           size: tuple[int, int] = size, whole: bool = index == 0) -> bytes:
                if whole:
                    return png.encode(full(browser, cache, image))
                if image.plates or image.fronts:
                    return png.encode(press.narrowed(full(browser, cache, image), size))
                assert browser is not None
                return png.encode(png.clean(browser.draw(image.svg, size, f"{image.stem}-{size[0]}"), flatten=image.ground))

            copy_note = "" if index == 0 else f", {size[0]} px wide"
            pictures.append(Picture(path, size, source, inputs, draw_press, what + copy_note, press.BYTE_LIMIT))

    # --- Screens, enlarged ---------------------------------------------------------------
    for board, screen in data["screens"].items():
        native = press.SCREENS_DIR / f"kleidos-screen-{board}.png"
        scale = screen["scale"]
        size = (screen["size"][0] * scale, screen["size"][1] * scale)

        def draw_screen(_: raster.Browser | None, __: dict[str, Any], native: Path = native, scale: int = scale) -> bytes:
            return png.encode(press.enlarged_screen((root / native).read_bytes(), scale))

        pictures.append(Picture(press.SCREENS_DIR / f"kleidos-screen-{board}-{scale}x.png", size, record.file_sha256(root / native),
                                (native, press.PRESS_JSON), draw_screen,
                                f"the {screen['name']}'s unlock screen at {scale} times its own pixels", press.BYTE_LIMIT, False))

    # --- Photographs, narrower -----------------------------------------------------------
    for photo in data.get("photos", {}).values():
        whole = photos.PHOTOS_DIR / f"{photo['file']}.jpg"
        width, height = photo["size"]
        for copy_width in photo.get("copies", ()):
            def draw_photo(_: raster.Browser | None, __: dict[str, Any], whole: Path = whole, copy_width: int = copy_width) -> bytes:
                return photos.narrowed((root / whole).read_bytes(), copy_width)

            pictures.append(Picture(photos.PHOTOS_DIR / f"{photo['file']}-{copy_width}.jpg", (copy_width, round(copy_width * height / width)),
                                    record.file_sha256(root / whole), (whole, press.PRESS_JSON), draw_photo,
                                    f"the same, {copy_width} px wide", press.BYTE_LIMIT, False))
    return texts, pictures


def picture_findings(name: str, data: bytes, size: tuple[int, int] | None = None, limit: int | None = None) -> list[str]:
    """Return what is wrong with a published picture, a PNG or a photograph's JPEG."""
    check = photos.findings if name.endswith(".jpg") else png.findings
    return check(name, data, size, limit)


# --- The pages' generated tables ---------------------------------------------------------


def blocks(root: Path, pictures: list[Picture], files: dict[str, Any]) -> dict[Path, dict[str, str]]:
    """Return every generated block of every README page, by page and by name."""
    def weight(path: Path) -> str:
        entry = files.get(path.as_posix())
        return record.human_bytes(entry["bytes"]) if entry else "not built"

    logos = logo.build(root)
    by_stem: dict[str, list[Picture]] = {}
    for picture in pictures:
        if picture.path.parent == logo.PNG_DIR:
            by_stem.setdefault(picture.path.stem.rsplit("-", 1)[0], []).append(picture)
    logo_rows = ["| File | What it is | SVG | PNG, by height in pixels |", "| --- | --- | --- | --- |"]
    for item in logos:
        copies = ", ".join(f"[{picture.size[1]}](png/{picture.path.name})" for picture in by_stem.get(item.stem, []))
        logo_rows.append(f"| `{item.stem}` | {item.what} | [svg](svg/{item.stem}.svg) | {copies} |")

    press_rows = ["| File | Pixels | Weight | What it shows |", "| --- | --- | --- | --- |"]
    screen_rows = ["| File | Pixels | Weight | What it shows |", "| --- | --- | --- | --- |"]
    photo_rows = ["| File | Pixels | Weight | What it shows |", "| --- | --- | --- | --- |"]
    data = press.load(root)
    for photo in data.get("photos", {}).values():
        whole = photos.PHOTOS_DIR / f"{photo['file']}.jpg"
        weight_now = record.human_bytes((root / whole).stat().st_size) if (root / whole).is_file() else "missing"
        photo_rows.append(f"| [`{whole.name}`](photos/{whole.name}) | {photo['size'][0]} x {photo['size'][1]} | {weight_now} | {photo['what']}, at full resolution |")
    for board, screen in data["screens"].items():
        native = press.SCREENS_DIR / f"kleidos-screen-{board}.png"
        screen_rows.append(f"| [`{native.name}`](screens/{native.name}) | {screen['size'][0]} x {screen['size'][1]} |"
                           f" {record.human_bytes((root / native).stat().st_size)} | the {screen['name']}'s unlock screen, as captured |")
    for picture in pictures:
        if picture.path.parts[0] != "press-kit":
            continue
        row = f"| [`{picture.path.name}`]({picture.path.relative_to('press-kit').as_posix()}) | {picture.size[0]} x {picture.size[1]} | {weight(picture.path)} | {picture.what} |"
        if picture.path.parent == press.IMAGES_DIR:
            press_rows.append(row)
        elif picture.path.parent == press.SCREENS_DIR:
            screen_rows.append(row)
        elif picture.path.parent == photos.PHOTOS_DIR:
            photo_rows.append(row)
    return {
        Path("logo/README.md"): {"files": "\n".join(logo_rows)},
        Path("colors/README.md"): {
            "roles": palette.roles_table(root),
            "contrast": palette.contrast_table(root),
            "device": palette.device_table(root),
        },
        Path("press-kit/README.md"): {"images": "\n".join(press_rows), "screens": "\n".join(screen_rows), "photos": "\n".join(photo_rows)},
    }


def pages(root: Path, pictures: list[Picture], files: dict[str, Any]) -> list[Text]:
    """Return each README page as it reads with its generated blocks current."""
    out = []
    for page, named in blocks(root, pictures, files).items():
        text = (root / page).read_text(encoding="utf-8")
        for name, body in named.items():
            text = record.with_block(text, name, body)
        out.append(Text(page, text))
    return out


# --- Writing -----------------------------------------------------------------------------


def stale(root: Path, texts: list[Text], pictures: list[Picture]) -> list[Path]:
    """Return the files in the generated folders that nothing generates any more."""
    owned = {text.path for text in texts} | {picture.path for picture in pictures}
    found = []
    for folder in GENERATED_DIRS:
        if (root / folder).is_dir():
            found += [path.relative_to(root) for path in sorted((root / folder).iterdir()) if path.is_file() and path.relative_to(root) not in owned]
    return found


def write(root: Path = BRAND_ROOT) -> int:
    """Regenerate every file and the record."""
    texts, pictures = collect(root)
    for text in texts:
        (root / text.path).parent.mkdir(parents=True, exist_ok=True)
        (root / text.path).write_text(text.content, encoding="utf-8")
    for path in stale(root, texts, pictures):
        (root / path).unlink()
        print(f"removed {path}: nothing generates it")
    files: dict[str, Any] = {}
    cache: dict[str, Any] = {}
    with raster.Browser() as browser:
        for picture in pictures:
            data = picture.draw(browser, cache)
            (root / picture.path).parent.mkdir(parents=True, exist_ok=True)
            (root / picture.path).write_bytes(data)
            files[picture.path.as_posix()] = {
                "sha256": record.sha256(data),
                "bytes": len(data),
                "size": list(picture.size),
                "drawn_from": picture.source,
                "inputs": {path.as_posix(): record.file_sha256(root / path) for path in picture.inputs},
            }
        version = browser.version
    (root / record.EXPORTS_JSON).write_text(record.dump({"chromium": version, "files": files}), encoding="utf-8")
    for page in pages(root, pictures, files):
        (root / page.path).write_text(page.content, encoding="utf-8")
    print(f"wrote {len(texts)} text files and {len(pictures)} pictures, drawn with Chromium {version}")
    return 0


# --- Checking ----------------------------------------------------------------------------


def static_findings(root: Path = BRAND_ROOT) -> list[str]:
    """Return every difference between the tree and what its sources give, found without a browser."""
    texts, pictures = collect(root)
    recorded = record.load(root)
    files = recorded.get("files", {})
    found = []
    for text in [*texts, *pages(root, pictures, files)]:
        path = root / text.path
        if not path.is_file():
            found.append(f"{text.path}: missing; run tools/build.py")
        elif path.read_text(encoding="utf-8") != text.content:
            found.append(f"{text.path}: is not what its sources give; run tools/build.py")
    for path in stale(root, texts, pictures):
        found.append(f"{path}: nothing generates it; run tools/build.py or remove it")
    for picture in pictures:
        name = picture.path.as_posix()
        entry = files.get(name)
        path = root / picture.path
        if not path.is_file():
            found.append(f"{name}: missing; run tools/build.py")
            continue
        data = path.read_bytes()
        found += picture_findings(name, data, picture.size, picture.limit)
        if entry is None:
            found.append(f"{name}: exports.json has no record of it; run tools/build.py")
            continue
        if entry["sha256"] != record.sha256(data):
            found.append(f"{name}: its bytes are not the ones exports.json records; run tools/build.py")
        if entry["drawn_from"] != picture.source:
            found.append(f"{name}: stale: what it is drawn from changed since it was drawn; run tools/build.py")
        for source, digest in entry["inputs"].items():
            if not (root / source).is_file() or record.file_sha256(root / source) != digest:
                found.append(f"{name}: stale: {source} changed since it was drawn; run tools/build.py")
    for name in sorted(set(files) - {picture.path.as_posix() for picture in pictures}):
        found.append(f"exports.json: records {name}, which nothing generates; run tools/build.py")
    return found


def drawn_findings(root: Path = BRAND_ROOT, tolerant: bool = False) -> list[str]:
    """Return every picture that, drawn again, is not the committed one."""
    _, pictures = collect(root)
    recorded = record.load(root)
    found = []
    cache: dict[str, Any] = {}
    with raster.Browser() as browser:
        if not tolerant and browser.version != recorded.get("chromium"):
            return [
                f"this machine draws with Chromium {browser.version} and the pictures were drawn with {recorded.get('chromium')}:"
                " an exact comparison would report the browser, not the pictures. Install the pinned Playwright"
                " (requirements.txt, then 'python -m playwright install chromium'), or run --check --tolerant."
            ]
        for picture in pictures:
            path = root / picture.path
            if not path.is_file():
                continue
            again, kept = picture.draw(browser, cache), path.read_bytes()
            if tolerant:
                share = png.drift(again, kept)
                if share is None or share > TOLERANCE:
                    how = "is another size" if share is None else f"differs in {share:.2%} of its pixels"
                    found.append(f"{picture.path}: drawn again under Chromium {browser.version}, it {how}; the limit is {TOLERANCE:.1%}")
            else:
                count = png.differing(again, kept)
                if count != 0:
                    how = "is another size" if count is None else f"differs in {count} pixels"
                    found.append(f"{picture.path}: drawn again, it {how}; run tools/build.py and look at it")
    return found


# --- The press kit as one archive --------------------------------------------------------

ZIP_PATHS = ("press-kit/README.md", "press-kit/USAGE.md", "press-kit/en", "press-kit/es", "press-kit/images", "press-kit/screens",
             "press-kit/photos", "press-kit/svg", "logo/README.md", "logo/svg", "logo/png", "about", "LICENSE", "LICENSES", "NOTICE.md", "TRADEMARKS.md")


def write_zip(root: Path = BRAND_ROOT) -> Path:
    """Write ``dist/kleidos-press-kit.zip``: the same bytes on every run from the same tree."""
    target = root / "dist" / "kleidos-press-kit.zip"
    target.parent.mkdir(exist_ok=True)
    members: list[Path] = []
    for name in ZIP_PATHS:
        path = root / name
        members += sorted(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else [path]
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for member in members:
            info = zipfile.ZipInfo(f"kleidos-press-kit/{member.relative_to(root).as_posix()}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, member.read_bytes())
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="compare instead of writing")
    parser.add_argument("--static", action="store_true", help="with --check: only what needs no browser")
    parser.add_argument("--tolerant", action="store_true", help="with --check: draw again and fail on gross drift only")
    parser.add_argument("--zip", action="store_true", help="write dist/kleidos-press-kit.zip")
    args = parser.parse_args(argv)
    if args.zip:
        print(f"wrote {write_zip().relative_to(BRAND_ROOT)}")
        return 0
    if not args.check:
        return write()
    found = static_findings()
    if not args.static:
        found += drawn_findings(tolerant=args.tolerant)
    for line in found:
        print(line)
    if found:
        print(f"\n{len(found)} finding(s).")
        return 1
    print("build check: every generated file is what its sources give.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
