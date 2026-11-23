#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""Build everything this repository generates, or check that what is committed is what the sources
give.

    tools/build.py                    regenerate the tokens' files, the logo files (with their
                                      opaque copies), the palette, the press images, the
                                      photographs' narrower copies, the WebP copy of every PNG
                                      and JPEG file, the metadata of every published picture,
                                      the record and the pages' tables
    tools/build.py --check            draw everything again and fail on any difference, pixel for
                                      pixel; refused under a browser other than the recorded one
    tools/build.py --check --static   what needs no browser: every text file, every table, and each
                                      picture's bytes against the record of what it was drawn from
    tools/build.py --check --tolerant draw again under any browser and fail on gross drift only
    tools/build.py --zip              write dist/kleidos-press-kit.zip (not committed)
    tools/build.py --kicad            also export the KiCad kit's fixture with kicad-cli and draw
                                      its previews (kicad/preview/); without it they are kept as
                                      they are

The KiCad kit's previews are the one kind of picture that needs KiCad: they
are drawn again only with ``--kicad`` (writing or checking), and the static
check holds them to their sources like every other picture.

The exact comparison belongs to the machine that exported: Chromium draws an
edge a shade apart from one version or system to the next. The static check
and the tolerant one run anywhere, and CI runs both.

Every published SVG and picture carries the record of what it is
(``kleidos_brand.meta``, made by ``kleidos_brand.records``): written here, in
the profile's fixed order, never by hand. The screen captures and the
full-resolution photograph are not drawn again: the builder writes their
metadata on them and leaves their pixels' bytes as they are.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kleidos_brand import (
    BRAND_ROOT,
    boards,
    kicad,
    kicad_preview,
    lettering,
    logo,
    mark,
    meta,
    palette,
    photos,
    png,
    press,
    raster,
    record,
    records,
    tokens,
    webp,
)

#: The share of pixels that may differ by more than a shade under another browser.
TOLERANCE = 0.005

MONA = lettering.FAMILIES["Mona Sans"]
MONO = lettering.FAMILIES["Mona Sans Mono"]
LOGO_INPUTS = (mark.MARK_SVG, logo.LOCKUPS_JSON, tokens.TOKENS_JSON, MONA)
SMALL_INPUTS = (mark.MARK_SVG, mark.SMALL_JSON, tokens.TOKENS_JSON)
GENERATED_DIRS = (
    logo.SVG_DIR,
    logo.PNG_DIR,
    logo.WEBP_DIR,
    press.SVG_DIR,
    press.IMAGES_DIR,
    Path("tokens/dist"),
    kicad.PREVIEW_DIR,
)
#: How a README table names a language of press.json.
LANGUAGES = {"en": "English", "es": "Spanish"}


@dataclass(frozen=True)
class Text:
    """A generated text file and what it must hold; a published SVG also has its metadata record."""

    path: Path
    content: str
    meta: meta.MediaMeta | None = None


#: How a picture is drawn: from the browser (None under a static check) and the run's cache.
Draw = Callable[["raster.Browser | None", dict[str, Any]], bytes]

#: Why a picture drawn by Chromium cannot be drawn: the static check opens no browser.
NEEDS_BROWSER = "this picture is drawn by the browser, and none is open (--static draws nothing)"


@dataclass(frozen=True)
class Picture:
    """A generated picture (a PNG, or a photograph's JPEG copy): its size, its limit, what it is
    drawn from and how."""

    path: Path
    size: tuple[int, int]
    source: str  # the SHA-256 of the SVG or capture it is drawn from
    inputs: tuple[Path, ...]
    draw: Draw
    what: str
    limit: int | None = None
    needs_browser: bool = True
    meta: meta.MediaMeta | None = None
    # Listed in its page's generated table; a capture or the full photograph has its own row.
    row: bool = True
    copy_of: Path | None = None  # an opaque or WebP copy: the published file it is made from
    lossless: bool = False  # a lossless WebP copy: it decodes to its copy_of's pixels exactly
    needs_kicad: bool = False  # drawn from a kicad-cli export: drawn again only with --kicad


def webp_path(path: Path) -> Path:
    """Return where the WebP copy of a published PNG or JPEG file goes: ``logo/webp/`` for a logo
    file, beside it otherwise."""
    folder = logo.WEBP_DIR if path.parent == logo.PNG_DIR else path.parent
    return folder / f"{path.stem}.webp"


def stamped_svg(path: Path, svg: str, record_: meta.MediaMeta) -> Text:
    """Return a published SVG with its record's title, description and metadata."""
    return Text(path, meta.svg_stamp(svg, record_, meta.svg_slug(path.stem)), record_)


def collect(root: Path = BRAND_ROOT) -> tuple[list[Text], list[Picture]]:
    """Return every file the builder owns: the text ones with their content, the pictures with their
    recipe."""
    loaded = tokens.load(root)
    texts = [
        Text(tokens.FLAT_JSON, tokens.flat_json(loaded)),
        Text(tokens.TOKENS_CSS, tokens.css(loaded)),
        *(Text(path, content) for path, content in kicad.texts(root).items()),
    ]
    pictures: list[Picture] = []

    # --- Logo files ----------------------------------------------------------------------
    published: dict[str, Text] = {}
    for item in logo.build(root):
        svg_path = logo.SVG_DIR / f"{item.stem}.svg"
        published[item.stem] = stamped_svg(svg_path, item.svg, records.logo(item, svg_path))
        texts.append(published[item.stem])
    shapes, small = mark.shapes(root), mark.small_numbers(root)
    for item, width, height, path in logo.png_plan(root):
        svg = published[item.stem].content
        about = records.logo(item, path, (width, height), records.url(published[item.stem].path))
        if item.px and item.paint:
            # A small mark's pixels are counted, not drawn by the browser: the same bytes on every
            # machine.
            def draw_small(
                _: raster.Browser | None,
                __: dict[str, Any],
                item: logo.Logo = item,
                about: meta.MediaMeta = about,
            ) -> bytes:
                if not (item.px and item.paint):
                    raise ValueError(f"{item.stem}: a small mark needs its size and its paint")
                image = mark.small_pixels(mark.small_fit(shapes, item.px, small), item.paint)
                return png.encode(png.clean(png.encode(image), flatten=item.ground), about)

            pictures.append(
                Picture(
                    path,
                    (width, height),
                    record.sha256(svg.encode()),
                    SMALL_INPUTS,
                    draw_small,
                    item.what,
                    needs_browser=False,
                    meta=about,
                )
            )
            continue

        def draw_logo(
            browser: raster.Browser | None,
            _: dict[str, Any],
            item: logo.Logo = item,
            size: tuple[int, int] = (width, height),
            svg: str = svg,
            about: meta.MediaMeta = about,
        ) -> bytes:
            if browser is None:
                raise RuntimeError(NEEDS_BROWSER)
            return png.encode(
                png.clean(browser.draw(svg, size, item.stem), flatten=item.ground), about
            )

        box = round(height * item.mark_share)
        what = item.what + (f"; the mark box is {box} px" if box else "")
        pictures.append(
            Picture(
                path,
                (width, height),
                record.sha256(svg.encode()),
                LOGO_INPUTS,
                draw_logo,
                what,
                meta=about,
            )
        )

    # --- The palette ---------------------------------------------------------------------
    bare_sheet, sheet_size = palette.svg(root)
    ground = tokens.resolve(loaded)["social.ground"]
    sheet_text = stamped_svg(palette.PALETTE_SVG, bare_sheet, records.palette(palette.PALETTE_SVG))
    sheet = sheet_text.content
    texts.append(sheet_text)
    sheet_meta = records.palette(palette.PALETTE_PNG, sheet_size, records.url(palette.PALETTE_SVG))

    def draw_palette(browser: raster.Browser | None, _: dict[str, Any]) -> bytes:
        if browser is None:
            raise RuntimeError(NEEDS_BROWSER)
        return png.encode(
            png.clean(browser.draw(sheet, sheet_size, "palette"), flatten=ground), sheet_meta
        )

    pictures.append(
        Picture(
            palette.PALETTE_PNG,
            sheet_size,
            record.sha256(sheet.encode()),
            (tokens.TOKENS_JSON, MONA, MONO),
            draw_palette,
            "the swatch sheet",
            meta=sheet_meta,
        )
    )

    # --- Press images --------------------------------------------------------------------
    data = press.load(root)
    # --- The screen captures and the photograph: their pixels kept, their metadata written -------
    # First in the list: the press images and the enlarged screens record these files' digests.
    for board, screen in data["screens"].items():
        native = press.SCREENS_DIR / f"kleidos-screen-{board}.png"
        size = tuple(screen["size"])
        about = records.screen(screen, native, size, source=meta.FIRMWARE_REPO_URL)

        def stamp_screen(
            _: raster.Browser | None,
            __: dict[str, Any],
            native: Path = native,
            about: meta.MediaMeta = about,
        ) -> bytes:
            return png.stamp((root / native).read_bytes(), about)

        pictures.append(
            Picture(
                native,
                size,
                record.sha256(png.bare((root / native).read_bytes())),
                (press.PRESS_JSON,),
                stamp_screen,
                f"the {screen['name']}'s unlock screen, as captured",
                needs_browser=False,
                meta=about,
                row=False,
            )
        )
    for photo in data.get("photos", {}).values():
        whole = photos.PHOTOS_DIR / f"{photo['file']}.jpg"
        about = records.photo(photo, whole, tuple(photo["size"]))

        def stamp_photo(
            _: raster.Browser | None,
            __: dict[str, Any],
            whole: Path = whole,
            about: meta.MediaMeta = about,
        ) -> bytes:
            return photos.stamp((root / whole).read_bytes(), about)

        pictures.append(
            Picture(
                whole,
                tuple(photo["size"]),
                record.sha256(photos.bare((root / whole).read_bytes())),
                (press.PRESS_JSON,),
                stamp_photo,
                f"{photo['what']}, at full resolution",
                needs_browser=False,
                meta=about,
                row=False,
            )
        )

    entries = {entry["file"]: entry for entry in data["images"]}
    for listed in press.images(root):
        entry = entries[
            listed.stem.removesuffix(f"-{listed.lang}")
            if listed.lang != data["default_lang"]
            else listed.stem
        ]
        svg_path = press.SVG_DIR / f"{listed.stem}.svg"
        image = listed
        if listed.publish_svg:
            published_press = stamped_svg(
                svg_path, listed.svg, records.press(listed, entry, svg_path)
            )
            texts.append(published_press)
            image = dataclasses.replace(listed, svg=published_press.content)
        screens = tuple(
            press.SCREENS_DIR / f"kleidos-screen-{plate.board}.png" for plate in image.plates
        )
        screens += tuple(boards.screen_path(placed.slug) for placed in image.fronts)
        lineup = (
            tuple(path for path in boards.inputs(root) if path not in screens)
            if image.fronts
            else ()
        )
        inputs = (
            *LOGO_INPUTS,
            MONO,
            press.PRESS_JSON,
            press.SRC_DIR / f"{image.layout}.svg",
            *screens,
            *lineup,
        )
        # A capture's metadata is not part of what an image is drawn from: its pixels' chunks are.
        source = record.sha256(
            image.svg.encode()
            + b"".join(png.bare((root / screen).read_bytes()) for screen in screens)
        )
        what = image.what + (
            ""
            if image.lang == data["default_lang"]
            else f", in {LANGUAGES.get(image.lang, image.lang)}"
        )

        def full(
            browser: raster.Browser | None, cache: dict[str, Any], image: press.Image = image
        ) -> Any:
            if image.stem not in cache:
                if browser is None:
                    raise RuntimeError(NEEDS_BROWSER)
                drawn = png.clean(
                    browser.draw(image.svg, image.size, image.stem), flatten=image.ground
                )
                cache[image.stem] = press.paste_screens(image, drawn, root)
            return cache[image.stem]

        full_path = image.png_paths()[0][0]
        for index, (path, size) in enumerate(image.png_paths()):
            upstream = (
                (records.url(svg_path) if image.publish_svg else None)
                if index == 0
                else records.url(full_path)
            )
            about = records.press(image, entry, path, size, upstream)

            def draw_press(
                browser: raster.Browser | None,
                cache: dict[str, Any],
                image: press.Image = image,
                size: tuple[int, int] = size,
                whole: bool = index == 0,
                about: meta.MediaMeta = about,
            ) -> bytes:
                if whole:
                    return png.encode(full(browser, cache, image), about)
                if image.plates or image.fronts:
                    return png.encode(press.narrowed(full(browser, cache, image), size), about)
                if browser is None:
                    raise RuntimeError(NEEDS_BROWSER)
                return png.encode(
                    png.clean(
                        browser.draw(image.svg, size, f"{image.stem}-{size[0]}"),
                        flatten=image.ground,
                    ),
                    about,
                )

            copy_note = "" if index == 0 else f", {size[0]} px wide"
            pictures.append(
                Picture(
                    path,
                    size,
                    source,
                    inputs,
                    draw_press,
                    what + copy_note,
                    press.BYTE_LIMIT,
                    meta=about,
                )
            )

    # --- Screens, enlarged ---------------------------------------------------------------
    for board, screen in data["screens"].items():
        native = press.SCREENS_DIR / f"kleidos-screen-{board}.png"
        scale = screen["scale"]
        size = (screen["size"][0] * scale, screen["size"][1] * scale)

        enlarged = press.SCREENS_DIR / f"kleidos-screen-{board}-{scale}x.png"
        about = records.screen(screen, enlarged, size, scale, records.url(native))

        def draw_screen(
            _: raster.Browser | None,
            __: dict[str, Any],
            native: Path = native,
            scale: int = scale,
            about: meta.MediaMeta = about,
        ) -> bytes:
            return png.encode(press.enlarged_screen((root / native).read_bytes(), scale), about)

        pictures.append(
            Picture(
                enlarged,
                size,
                record.sha256(png.bare((root / native).read_bytes())),
                (native, press.PRESS_JSON),
                draw_screen,
                f"the {screen['name']}'s unlock screen at {scale} times its own pixels",
                press.BYTE_LIMIT,
                False,
                about,
            )
        )

    # --- Photographs, narrower -----------------------------------------------------------
    for photo in data.get("photos", {}).values():
        whole = photos.PHOTOS_DIR / f"{photo['file']}.jpg"
        width, height = photo["size"]
        for copy_width in photo.get("copies", ()):
            narrow = photos.PHOTOS_DIR / f"{photo['file']}-{copy_width}.jpg"
            narrow_size = (copy_width, round(copy_width * height / width))
            about = records.photo(photo, narrow, narrow_size, records.url(whole))

            def draw_photo(
                _: raster.Browser | None,
                __: dict[str, Any],
                whole: Path = whole,
                copy_width: int = copy_width,
                about: meta.MediaMeta = about,
            ) -> bytes:
                return photos.narrowed((root / whole).read_bytes(), copy_width, about)

            pictures.append(
                Picture(
                    narrow,
                    narrow_size,
                    record.sha256(photos.bare((root / whole).read_bytes())),
                    (whole, press.PRESS_JSON),
                    draw_photo,
                    f"the same, {copy_width} px wide",
                    press.BYTE_LIMIT,
                    False,
                    about,
                )
            )
    # --- The KiCad kit's previews --------------------------------------------------------
    # (Not named ``ground``: draw_palette reads that name when it runs.)
    for kicad_ground in kicad.load(root)["grounds"]:
        preview = kicad_preview.path(kicad_ground)
        about = records.kicad_preview(kicad_ground, preview, kicad_preview.SIZE)

        def draw_kicad(
            browser: raster.Browser | None,
            _: dict[str, Any],
            side: str = kicad_ground,
            about: meta.MediaMeta = about,
        ) -> bytes:
            if browser is None:
                raise RuntimeError(NEEDS_BROWSER)
            return png.encode(kicad_preview.draw(side, browser, root), about)

        pictures.append(
            Picture(
                preview,
                kicad_preview.SIZE,
                kicad_preview.source(kicad_ground, root),
                kicad_preview.inputs(kicad_ground, root),
                draw_kicad,
                f"the KiCad kit's fixture on the {kicad_ground} ground",
                meta=about,
                row=False,
                needs_kicad=True,
            )
        )
    pictures += opaque_copies(root, pictures)
    pictures += webp_copies(root, pictures, data)
    return texts, pictures


def opaque_copies(root: Path, pictures: list[Picture]) -> list[Picture]:
    """Return the opaque copy of every logo PNG on transparency: its pixels flattened on white or
    black, no clear space added."""
    by_path = {picture.path: picture for picture in pictures}
    out = []
    for copy in logo.opaque_plan(root):
        drawn = by_path[copy.source]
        about = records.opaque(copy, (copy.width, copy.height))

        def draw_opaque(
            _: raster.Browser | None,
            __: dict[str, Any],
            copy: logo.Opaque = copy,
            about: meta.MediaMeta = about,
        ) -> bytes:
            return png.encode(
                png.clean((root / copy.source).read_bytes(), flatten=copy.color), about
            )

        what = (
            f"{copy.item.what.replace(', on transparency', '')}, flattened on {copy.ground} "
            f"({copy.color})"
        )
        out.append(
            Picture(
                copy.path,
                (copy.width, copy.height),
                drawn.source,
                (copy.source, logo.OPAQUE_JSON, tokens.TOKENS_JSON),
                draw_opaque,
                what,
                needs_browser=False,
                meta=about,
                copy_of=copy.source,
            )
        )
    return out


def webp_copies(root: Path, pictures: list[Picture], data: dict[str, Any]) -> list[Picture]:
    """Return the WebP copy of every published PNG and JPEG file: lossless from a PNG's pixels,
    lossy from a photograph's."""
    wholes = {
        photos.PHOTOS_DIR / f"{photo['file']}.jpg": photo
        for photo in data.get("photos", {}).values()
    }
    out = []
    for picture in pictures:
        if picture.meta is None or picture.path.suffix not in (".png", ".jpg"):
            continue
        path = webp_path(picture.path)
        lossless = picture.path.suffix == ".png"
        about = records.webp(picture.meta, path, picture.path, lossless)
        draw_webp: Draw
        if lossless:
            inputs: tuple[Path, ...] = (picture.path,)

            def draw_lossless(
                _: raster.Browser | None,
                __: dict[str, Any],
                picture: Picture = picture,
                about: meta.MediaMeta = about,
            ) -> bytes:
                return webp.copy_of((root / picture.path).read_bytes(), about)

            draw_webp = draw_lossless
        else:
            # A narrower photograph's WebP is drawn from the full-resolution file, as its JPEG is:
            # one lossy step, not two.
            whole = (
                picture.path
                if picture.path in wholes
                else next(path for path in picture.inputs if path in wholes)
            )
            inputs = (whole, press.PRESS_JSON)

            def draw_lossy(
                _: raster.Browser | None,
                __: dict[str, Any],
                whole: Path = whole,
                size: tuple[int, int] = picture.size,
                about: meta.MediaMeta = about,
            ) -> bytes:
                return webp.encode(
                    photos.resized((root / whole).read_bytes(), size), about, lossless=False
                )

            draw_webp = draw_lossy

        out.append(
            Picture(
                path,
                picture.size,
                picture.source,
                inputs,
                draw_webp,
                f"{picture.what}, as WebP",
                picture.limit,
                needs_browser=False,
                meta=about,
                row=False,
                copy_of=picture.path,
                lossless=lossless,
            )
        )
    return out


def picture_findings(
    name: str,
    data: bytes,
    size: tuple[int, int] | None = None,
    limit: int | None = None,
    about: meta.MediaMeta | None = None,
) -> list[str]:
    """Return what is wrong with a published picture, a PNG, a WebP copy or a photograph's JPEG, its
    metadata included."""
    check = (
        photos.findings
        if name.endswith(".jpg")
        else webp.findings
        if name.endswith(".webp")
        else png.findings
    )
    return check(name, data, size, limit, about)


# --- The pages' generated tables ---------------------------------------------------------


def blocks(
    root: Path, pictures: list[Picture], files: dict[str, Any]
) -> dict[Path, dict[str, str]]:
    """Return every generated block of every README page, by page and by name."""

    def weight(path: Path) -> str:
        entry = files.get(path.as_posix())
        return record.human_bytes(entry["bytes"]) if entry else "not built"

    logos = logo.build(root)
    by_family: dict[str, list[Picture]] = {}
    for picture in pictures:
        if picture.path.parent == logo.PNG_DIR:
            by_family.setdefault(picture.path.stem.rsplit("-", 1)[0], []).append(picture)
    opaque = {copy.item.family: copy for copy in logo.opaque_plan(root)}
    webps = {
        picture.copy_of: picture
        for picture in pictures
        if picture.copy_of is not None and picture.path.suffix == ".webp"
    }

    def copies(family: str) -> tuple[str, str]:
        drawn = by_family.get(family, [])
        return (
            ", ".join(f"[{picture.size[1]}](png/{picture.path.name})" for picture in drawn),
            ", ".join(
                f"[{picture.size[1]}](webp/{webps[picture.path].path.name})"
                for picture in drawn
                if picture.path in webps
            ),
        )

    logo_rows = [
        "| File | What it is | SVG | PNG, by height in pixels | WebP, by height in pixels |",
        "| --- | --- | --- | --- | --- |",
    ]
    listed: set[str] = set()
    for item in logos:
        if item.family in listed:
            continue
        listed.add(item.family)
        named = f"{item.family}-<px>" if item.px else item.family
        if item.px:
            svgs = ", ".join(
                f"[{other.px}](svg/{other.stem}.svg)"
                for other in logos
                if other.family == item.family
            )
        else:
            svgs = f"[svg](svg/{item.stem}.svg)"
        logo_rows.append(
            f"| `{named}` | {item.what} | {svgs} | {' | '.join(copies(item.family))} |"
        )
        if item.family in opaque:
            copy = opaque[item.family]
            flat = (
                f"{item.what.replace(', on transparency', '')}, flattened on {copy.ground} "
                f"({copy.color}): no transparency, no clear space added"
            )
            logo_rows.append(
                f"| `{copy.family}{'-<px>' if item.px else ''}` | {flat} | | "
                f"{' | '.join(copies(copy.family))} |"
            )

    def webp_cell(path: Path, folder: str) -> str:
        twin = webps.get(path)
        return f"[webp]({folder}/{twin.path.name}), {weight(twin.path)}" if twin else ""

    head = ["| File | Pixels | Weight | WebP | What it shows |", "| --- | --- | --- | --- | --- |"]
    press_rows, screen_rows, photo_rows = list(head), list(head), list(head)
    data = press.load(root)
    for photo in data.get("photos", {}).values():
        whole = photos.PHOTOS_DIR / f"{photo['file']}.jpg"
        weight_now = (
            record.human_bytes((root / whole).stat().st_size)
            if (root / whole).is_file()
            else "missing"
        )
        photo_rows.append(
            f"| [`{whole.name}`](photos/{whole.name}) | {photo['size'][0]} x {photo['size'][1]} | "
            f"{weight_now} |"
            f" {webp_cell(whole, 'photos')} | {photo['what']}, at full resolution |"
        )
    for board, screen in data["screens"].items():
        native = press.SCREENS_DIR / f"kleidos-screen-{board}.png"
        screen_rows.append(
            f"| [`{native.name}`](screens/{native.name}) | {screen['size'][0]} x "
            f"{screen['size'][1]} |"
            f" {record.human_bytes((root / native).stat().st_size)} | "
            f"{webp_cell(native, 'screens')} |"
            f" the {screen['name']}'s unlock screen, as captured |"
        )
    for picture in pictures:
        if picture.path.parts[0] != "press-kit" or not picture.row:
            continue
        folder = picture.path.parent.relative_to("press-kit").as_posix()
        row = (
            f"| [`{picture.path.name}`]({picture.path.relative_to('press-kit').as_posix()}) | "
            f"{picture.size[0]} x {picture.size[1]} |"
            f" {weight(picture.path)} | {webp_cell(picture.path, folder)} | {picture.what} |"
        )
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
        Path("press-kit/README.md"): {
            "images": "\n".join(press_rows),
            "screens": "\n".join(screen_rows),
            "photos": "\n".join(photo_rows),
        },
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
            found += [
                path.relative_to(root)
                for path in sorted((root / folder).iterdir())
                if path.is_file() and path.relative_to(root) not in owned
            ]
    return found


def write(root: Path = BRAND_ROOT, with_kicad: bool = False) -> int:
    """Regenerate every file and the record; the KiCad previews only *with_kicad*, kept as recorded
    otherwise."""
    texts, pictures = collect(root)
    kept = record.load(root).get("files", {})
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
            if picture.needs_kicad and not with_kicad:
                if picture.path.as_posix() in kept and (root / picture.path).is_file():
                    files[picture.path.as_posix()] = kept[picture.path.as_posix()]
                    continue
                raise SystemExit(
                    f"{picture.path}: missing; run tools/build.py --kicad (kicad-cli 10.0.8)"
                )
            data = picture.draw(browser, cache)
            (root / picture.path).parent.mkdir(parents=True, exist_ok=True)
            (root / picture.path).write_bytes(data)
            files[picture.path.as_posix()] = {
                "sha256": record.sha256(data),
                "bytes": len(data),
                "size": list(picture.size),
                "drawn_from": picture.source,
                "inputs": {
                    path.as_posix(): record.file_sha256(root / path) for path in picture.inputs
                },
            }
        version = browser.version
    record_ = {
        "chromium": version,
        "webp": webp.settings(),
        "meta_profile": meta.META_PROFILE,
        "files": files,
    }
    (root / record.EXPORTS_JSON).write_text(record.dump(record_), encoding="utf-8")
    for page in pages(root, pictures, files):
        (root / page.path).write_text(page.content, encoding="utf-8")
    print(
        f"wrote {len(texts)} text files and {len(pictures)} pictures, drawn with Chromium {version}"
    )
    return 0


# --- Checking ----------------------------------------------------------------------------


def static_findings(root: Path = BRAND_ROOT) -> list[str]:
    """Return every difference between the tree and what its sources give, found without a
    browser."""
    texts, pictures = collect(root)
    recorded = record.load(root)
    files = recorded.get("files", {})
    found = []
    if files and recorded.get("meta_profile") != meta.META_PROFILE:
        found.append(
            f"exports.json: the pictures carry metadata profile {recorded.get('meta_profile')!r}, "
            f"not {meta.META_PROFILE!r}; run tools/build.py"
        )
    encoder = recorded.get("webp") or {}
    if files and (encoder.get("lossless"), encoder.get("lossy")) != (webp.LOSSLESS, webp.LOSSY):
        found.append(
            "exports.json: the WebP copies were encoded with other settings than "
            "kleidos_brand.webp's; run tools/build.py"
        )
    for text in [*texts, *pages(root, pictures, files)]:
        path = root / text.path
        if not path.is_file():
            found.append(f"{text.path}: missing; run tools/build.py")
        elif path.read_text(encoding="utf-8") != text.content:
            found.append(f"{text.path}: is not what its sources give; run tools/build.py")
    found.extend(
        f"{path}: nothing generates it; run tools/build.py or remove it"
        for path in stale(root, texts, pictures)
    )
    for picture in pictures:
        name = picture.path.as_posix()
        entry = files.get(name)
        path = root / picture.path
        if not path.is_file():
            found.append(f"{name}: missing; run tools/build.py")
            continue
        data = path.read_bytes()
        found += picture_findings(name, data, picture.size, picture.limit, picture.meta)
        if entry is None:
            found.append(f"{name}: exports.json has no record of it; run tools/build.py")
            continue
        if entry["sha256"] != record.sha256(data):
            found.append(
                f"{name}: its bytes are not the ones exports.json records; run tools/build.py"
            )
        if entry["drawn_from"] != picture.source:
            found.append(
                f"{name}: stale: what it is drawn from changed since it was drawn; run "
                "tools/build.py"
            )
        for source, digest in entry["inputs"].items():
            if not (root / source).is_file() or record.file_sha256(root / source) != digest:
                found.append(
                    f"{name}: stale: {source} changed since it was drawn; run tools/build.py"
                )
    for name in sorted(set(files) - {picture.path.as_posix() for picture in pictures}):
        found.append(f"exports.json: records {name}, which nothing generates; run tools/build.py")
    return found


def drawn_findings(
    root: Path = BRAND_ROOT, tolerant: bool = False, with_kicad: bool = False
) -> list[str]:
    """Return every picture that, drawn again, is not the committed one; the KiCad previews only
    *with_kicad*."""
    _, pictures = collect(root)
    recorded = record.load(root)
    found = []
    cache: dict[str, Any] = {}
    encoder = webp.settings()
    with raster.Browser() as browser:
        if not tolerant and browser.version != recorded.get("chromium"):
            return [
                f"this machine draws with Chromium {browser.version} and the pictures were drawn "
                f"with {recorded.get('chromium')}:"
                " an exact comparison would report the browser, not the pictures. Install the "
                "pinned Playwright"
                " (requirements.txt, then 'python -m playwright install chromium'), or run --check "
                "--tolerant."
            ]
        if not tolerant and encoder["libwebp"] != (recorded.get("webp") or {}).get("libwebp"):
            return [
                f"this machine encodes WebP with libwebp {encoder['libwebp']} and the copies were "
                "encoded with"
                f" {(recorded.get('webp') or {}).get('libwebp')}: install the pinned Pillow "
                "(requirements.txt), or run --check --tolerant."
            ]
        for picture in pictures:
            path = root / picture.path
            if not path.is_file():
                continue
            if picture.lossless and picture.copy_of is not None:
                # A lossless copy is held to its file's pixels exactly, under any browser and any
                # libwebp.
                count = png.differing((root / picture.copy_of).read_bytes(), path.read_bytes())
                if count != 0:
                    how = (
                        "is another size"
                        if count is None
                        else f"differs from {picture.copy_of.name} in {count} pixels"
                    )
                    found.append(f"{picture.path}: a lossless copy that {how}; run tools/build.py")
                continue
            if picture.needs_kicad and not with_kicad:
                continue
            again, kept = picture.draw(browser, cache), path.read_bytes()
            if tolerant:
                share = png.drift(again, kept)
                if share is None or share > TOLERANCE:
                    how = (
                        "is another size"
                        if share is None
                        else f"differs in {share:.2%} of its pixels"
                    )
                    found.append(
                        f"{picture.path}: drawn again under Chromium {browser.version}, it {how}; "
                        f"the limit is {TOLERANCE:.1%}"
                    )
            else:
                count = png.differing(again, kept)
                if count != 0:
                    how = "is another size" if count is None else f"differs in {count} pixels"
                    found.append(
                        f"{picture.path}: drawn again, it {how}; run tools/build.py and look at it"
                    )
    return found


# --- The press kit as one archive --------------------------------------------------------

ZIP_PATHS = (
    "press-kit/README.md",
    "press-kit/USAGE.md",
    "press-kit/en",
    "press-kit/es",
    "press-kit/images",
    "press-kit/screens",
    "press-kit/photos",
    "press-kit/svg",
    "logo/README.md",
    "logo/svg",
    "logo/png",
    "logo/webp",
    "about",
    "LICENSE",
    "LICENSES",
    "NOTICE.md",
    "TRADEMARKS.md",
)


def write_zip(root: Path = BRAND_ROOT) -> Path:
    """Write ``dist/kleidos-press-kit.zip``: the same bytes on every run from the same tree."""
    target = root / "dist" / "kleidos-press-kit.zip"
    target.parent.mkdir(exist_ok=True)
    members: list[Path] = []
    for name in ZIP_PATHS:
        path = root / name
        members += (
            sorted(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else [path]
        )
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for member in members:
            info = zipfile.ZipInfo(
                f"kleidos-press-kit/{member.relative_to(root).as_posix()}",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, member.read_bytes())
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="compare instead of writing")
    parser.add_argument(
        "--static", action="store_true", help="with --check: only what needs no browser"
    )
    parser.add_argument(
        "--tolerant",
        action="store_true",
        help="with --check: draw again and fail on gross drift only",
    )
    parser.add_argument("--zip", action="store_true", help="write dist/kleidos-press-kit.zip")
    parser.add_argument(
        "--kicad",
        action="store_true",
        help="also export the KiCad kit's previews with kicad-cli (writing or checking)",
    )
    args = parser.parse_args(argv)
    if args.zip:
        print(f"wrote {write_zip().relative_to(BRAND_ROOT)}")
        return 0
    if not args.check:
        return write(with_kicad=args.kicad)
    found = static_findings()
    if not args.static:
        found += drawn_findings(tolerant=args.tolerant, with_kicad=args.kicad)
    for line in found:
        print(line)
    if found:
        print(f"\n{len(found)} finding(s).")
        return 1
    print("build check: every generated file is what its sources give.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
