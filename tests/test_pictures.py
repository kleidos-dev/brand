# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The pictures: encoded from pixels alone, compared exactly and with tolerance, drawn the same
twice."""

from __future__ import annotations

import hashlib
import io
import json
import time
from pathlib import Path
from typing import Any

import build
import pytest

from kleidos_brand import (
    boards,
    logo,
    meta,
    photos,
    png,
    press,
    raster,
    record,
    records,
    tokens,
    webp,
)

ROOT = Path(__file__).resolve().parents[1]


def picture(color: tuple[int, int, int, int], size: tuple[int, int] = (8, 8)) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, "PNG")
    return buffer.getvalue()


def rgba(image: Any, xy: tuple[int, int]) -> tuple[int, ...]:
    """Return the channels of one pixel of a Pillow image in a multi-band mode."""
    value = image.getpixel(xy)
    assert isinstance(value, tuple), f"{image.mode} is not a multi-band mode"
    return value


def test_a_cleaned_picture_carries_pixels_only() -> None:
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo

    note = PngInfo()
    note.add_text("Software", "a browser")
    buffer = io.BytesIO()
    Image.new("RGBA", (4, 4), (0, 210, 255, 255)).save(buffer, "PNG", pnginfo=note)
    assert "tEXt" in png.chunk_names(buffer.getvalue())
    cleaned = png.encode(png.clean(buffer.getvalue()))
    assert set(png.chunk_names(cleaned)) <= png.ALLOWED_CHUNKS
    assert png.differing(cleaned, buffer.getvalue()) == 0
    assert png.findings("x.png", buffer.getvalue(), (4, 4)) and not png.findings(
        "x.png", cleaned, (4, 4)
    )


def test_a_cleaned_photograph_carries_pixels_only() -> None:
    from PIL import Image, ImageCms

    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: turn 90 degrees clockwise to show it upright
    exif[0x010F] = "A camera maker"
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), (200, 120, 40)).save(
        buffer, "JPEG", exif=exif.tobytes(), icc_profile=profile, comment=b"a note"
    )
    camera = buffer.getvalue()
    assert {0xE1, 0xE2, 0xFE} <= set(photos.markers(camera))
    assert any("APP1" in line for line in photos.findings("x.jpg", camera))
    cleaned = photos.clean(camera)
    assert photos.findings("x.jpg", cleaned, (20, 40)) == [], (
        "upright, and nothing but pixels and tables"
    )
    with Image.open(io.BytesIO(cleaned)) as opened:
        assert (
            not opened.getexif()
            and "icc_profile" not in opened.info
            and "comment" not in opened.info
        )
    assert photos.clean(camera) == cleaned, "the same file gives the same bytes"
    assert photos.size(photos.narrowed(cleaned, 10)) == (10, 20)


def test_metadata_after_the_scan_or_after_the_end_is_seen() -> None:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), (200, 120, 40)).save(buffer, "JPEG", quality=88)
    clean = buffer.getvalue()
    assert photos.findings("x.jpg", clean, (16, 16)) == [] and photos.markers(clean)[-1] == 0xD9
    note = b"\xff\xfe" + (2 + len(b"a note")).to_bytes(2, "big") + b"a note"
    between = clean[:-2] + note + clean[-2:]
    assert 0xFE in photos.markers(between) and any(
        "COM" in line for line in photos.findings("x.jpg", between)
    )
    after = clean + b"Exif\x00\x00 a camera maker"
    assert any("after its end-of-image marker" in line for line in photos.findings("x.jpg", after))
    assert photos.findings("x.jpg", clean[:-2]) == ["x.jpg: not a JPEG"]


def test_every_photograph_is_clean_and_listed() -> None:
    data = press.load(ROOT)
    assert data["photos"], "the press kit has a photograph"
    for photo in data["photos"].values():
        path = photos.PHOTOS_DIR / f"{photo['file']}.jpg"
        whole = (ROOT / path).read_bytes()
        about = records.photo(photo, path, tuple(photo["size"]))
        assert photos.findings(photo["file"], whole, tuple(photo["size"]), meta=about) == []
        assert set(photos.markers(whole)) <= photos.ALLOWED_MARKERS | photos.METADATA_MARKERS
        assert photos.findings(photo["file"], photos.bare(whole), tuple(photo["size"])) == [], (
            "without its record, only pixels and tables"
        )
        assert set(photo["alt"]) == set(data["langs"]) and photo["credit"]


def test_one_pixel_off_is_seen_and_a_shade_apart_is_tolerated() -> None:
    from PIL import Image

    base = picture((10, 12, 15, 255))
    with Image.open(io.BytesIO(base)) as opened:
        moved = opened.copy()
    moved.putpixel((3, 3), (255, 255, 255, 255))
    buffer = io.BytesIO()
    moved.save(buffer, "PNG")
    assert png.differing(base, buffer.getvalue()) == 1
    assert png.drift(base, buffer.getvalue()) == 1 / 64
    assert png.drift(base, picture((14, 16, 19, 255))) == 0, "a few levels apart is not drift"
    assert png.differing(base, picture((10, 12, 15, 255), (8, 9))) is None
    assert png.findings("x.png", base, (8, 8), limit=10) == [
        f"x.png: is {len(base):,} bytes; the limit is under 10"
    ]


def test_every_committed_picture_is_recorded_and_within_its_limits() -> None:
    recorded = json.loads((ROOT / record.EXPORTS_JSON).read_text(encoding="utf-8"))
    _, pictures = build.collect(ROOT)
    assert {item.path.as_posix() for item in pictures} == set(recorded["files"])
    for item in pictures:
        data = (ROOT / item.path).read_bytes()
        sizer = {".jpg": photos.size, ".webp": webp.size}.get(item.path.suffix, png.size)
        assert sizer(data) == item.size, item.path
        assert hashlib.sha256(data).hexdigest() == recorded["files"][item.path.as_posix()]["sha256"]
        if item.limit is not None:
            assert len(data) < item.limit, item.path
        elif item.path.parts[0] == "press-kit":
            # A capture and the full-resolution photograph are kept as they are, with no limit of
            # their own.
            assert item.path.parent in (press.SCREENS_DIR, photos.PHOTOS_DIR) and not item.row, (
                item.path
            )


def test_every_logo_has_its_png_copies_and_every_press_image_both_languages() -> None:
    names = {path.name for path in (ROOT / logo.PNG_DIR).iterdir()}
    for item in logo.build(ROOT):
        assert any(
            name.startswith(f"{item.stem}-") or name == f"{item.stem}.png" for name in names
        ), item.stem
    images = {image.stem: image for image in press.images(ROOT)}
    for stem in (
        "kleidos-16x9",
        "kleidos-16x9-light",
        "kleidos-1x1",
        "kleidos-1x1-light",
        "kleidos-screens-16x9",
        "kleidos-boards-16x9",
        "kleidos-boards-16x9-light",
        "kleidos-boards-4x5",
        "kleidos-boards-4x5-light",
    ):
        assert stem in images and f"{stem}-es" in images
    assert images["kleidos-16x9-es"].sets["title.0"].line.text == "Tus contraseñas, en una placa"
    assert not any(press.findings(image) for image in images.values())
    assert {plate.board for plate in images["kleidos-screens-16x9"].plates} <= set(
        press.load(ROOT)["screens"]
    )
    for stem in ("kleidos-boards-16x9", "kleidos-boards-4x5-light-es"):
        assert [placed.slug for placed in images[stem].fronts] == boards.order(ROOT), (
            "every board, in the site's order"
        )
        assert not images[stem].publish_svg
    assert len({plate.board for plate in images["kleidos-screens-16x9"].plates}) >= 5, (
        "not only one board's screen"
    )


def test_the_small_marks_keyhole_is_a_hole() -> None:
    from PIL import Image

    with Image.open(ROOT / logo.PNG_DIR / "kleidos-mark-small-21.png") as opened:
        pixels = opened.convert("RGBA")
    assert pixels.size == (21, 21)
    assert rgba(pixels, (10, 9))[3] == 0, "the eye shows the ground"
    assert rgba(pixels, (10, 11))[3] == 0, "and so does the stem"
    assert rgba(pixels, (7, 9)) == (0, 210, 255, 255), "the body is solid in the ring's color"
    assert rgba(pixels, (10, 0))[3] > 128 and rgba(pixels, (10, 1))[3] == 0, (
        "the ring is one pixel, on the file's edge"
    )
    with Image.open(ROOT / logo.PNG_DIR / "kleidos-mark-small-on-dark-21.png") as opened:
        assert opened.convert("RGB").getpixel((10, 9)) == (10, 12, 15), (
            "on its tile, the keyhole is the tile"
        )


def test_the_archive_is_the_same_bytes_twice(tree: Path) -> None:
    first = build.write_zip(tree).read_bytes()
    assert build.write_zip(tree).read_bytes() == first
    import zipfile

    names = zipfile.ZipFile(io.BytesIO(first)).namelist()
    for needed in (
        "kleidos-press-kit/TRADEMARKS.md",
        "kleidos-press-kit/LICENSE",
        "kleidos-press-kit/LICENSES/MIT.txt",
        "kleidos-press-kit/press-kit/USAGE.md",
        "kleidos-press-kit/press-kit/svg/kleidos-16x9.svg",
        "kleidos-press-kit/logo/svg/kleidos-mark.svg",
        "kleidos-press-kit/press-kit/photos/kleidos-photo-four-boards.jpg",
        "kleidos-press-kit/press-kit/photos/kleidos-photo-four-boards-1920.jpg",
    ):
        assert needed in names


def test_every_published_picture_has_its_webp_copy() -> None:
    recorded = json.loads((ROOT / record.EXPORTS_JSON).read_text(encoding="utf-8"))
    assert (
        recorded["webp"]["lossless"] == webp.LOSSLESS
        and recorded["webp"]["lossy"] == webp.LOSSY
        and recorded["webp"]["libwebp"]
    )
    _, pictures = build.collect(ROOT)
    copies = {item.copy_of: item for item in pictures if item.path.suffix == ".webp"}
    originals = [item for item in pictures if item.path.suffix in (".png", ".jpg")]
    assert originals and {item.path for item in originals} == set(copies), (
        "one WebP copy for every PNG and JPEG file, no more"
    )
    for item in originals:
        twin = copies[item.path]
        assert (
            twin.path == build.webp_path(item.path) and twin.path.as_posix() in recorded["files"]
        ), twin.path
        assert twin.path.parent == (
            logo.WEBP_DIR if item.path.parent == logo.PNG_DIR else item.path.parent
        )
        data = (ROOT / twin.path).read_bytes()
        assert webp.is_lossless(data) is (item.path.suffix == ".png") is twin.lossless, twin.path
        assert webp.size(data) == item.size, twin.path
        assert webp.findings(twin.path.as_posix(), data, item.size, item.limit, twin.meta) == [], (
            twin.path
        )
        if twin.lossless:
            assert png.differing((ROOT / item.path).read_bytes(), data) == 0, (
                f"{twin.path}: not the PNG's pixels"
            )
        else:
            drift = png.drift((ROOT / item.path).read_bytes(), data)
            assert drift is not None and drift <= build.TOLERANCE, (
                f"{twin.path}: not the photograph"
            )
        assert twin.meta is not None and item.meta is not None
        assert (
            twin.meta.title == f"{item.meta.title}, WebP"
            and "WebP" in twin.meta.description
            and "WebP" in twin.meta.keywords
        )
        assert (
            twin.meta.source_url == records.url(item.path)
            and twin.meta.profile == item.meta.profile
        )


def test_a_webp_copy_is_the_same_bytes_twice() -> None:
    from PIL import Image

    flat = Image.new("RGBA", (40, 24), (0, 0, 0, 0))
    flat.paste((0, 210, 255, 255), (4, 4, 20, 20))
    photo = Image.radial_gradient("L").resize((40, 24)).convert("RGB")
    for image, lossless in ((flat, True), (photo, False)):
        first = webp.encode(image, lossless=lossless)
        assert webp.encode(image, lossless=lossless) == first
        assert (
            webp.is_lossless(first) is lossless and webp.findings("x.webp", first, (40, 24)) == []
        )
    buffer = io.BytesIO()
    flat.save(buffer, "PNG")
    copied = webp.copy_of(buffer.getvalue())
    assert (
        copied == webp.copy_of(buffer.getvalue()) and png.differing(buffer.getvalue(), copied) == 0
    )


#: The ground of an opaque copy, by the variant its file's name ends with (logo/src/opaque.json).
OPAQUE_GROUNDS = {
    "for-light": "white",
    "ink-dark": "white",
    "for-dark": "black",
    "ink-light": "black",
    "color": "black",
}


def test_every_logo_on_transparency_has_its_opaque_copy() -> None:
    from PIL import Image

    values = tokens.resolve(tokens.load(ROOT))
    grounds = {"white": values["social.light.ground"], "black": values["social.plate"]}
    assert grounds == {"white": "#ffffff", "black": "#000000"}
    plan = logo.opaque_plan(ROOT)
    transparent = [path for item, _, _, path in logo.png_plan(ROOT) if item.ground is None]
    assert sorted(copy.source for copy in plan) == sorted(transparent) and len(plan) == 38
    named = {path.name for path in (ROOT / logo.PNG_DIR).glob("*-opaque-*.png")}
    assert named == {copy.path.name for copy in plan}, "no opaque file the plan does not make"
    for copy in plan:
        family = copy.item.family
        assert copy.ground == OPAQUE_GROUNDS[logo.variant(family)], family
        assert copy.path.name == f"{family}-opaque-{copy.ground}-{copy.item.px or copy.height}.png"
        assert not any(name in copy.path.name for name in ("-on-dark", "-on-light")), (
            "an opaque copy is not a baked tile"
        )
        rgb = tuple(int(grounds[copy.ground][index : index + 2], 16) for index in (1, 3, 5))
        with Image.open(ROOT / copy.path) as opened, Image.open(ROOT / copy.source) as source:
            assert opened.mode == "RGB" and "transparency" not in opened.info, (
                f"{copy.path}: has alpha"
            )
            assert opened.size == source.size == (copy.width, copy.height)
            flat, alpha = opened.convert("RGB"), source.convert("RGBA").getchannel("A")
        clear = [
            (x, y)
            for x, y in (
                (0, 0),
                (copy.width - 1, 0),
                (0, copy.height - 1),
                (copy.width - 1, copy.height - 1),
            )
            if alpha.getpixel((x, y)) == 0
        ]
        assert clear, f"{copy.source}: no clear corner to read the ground at"
        for corner in clear:
            assert flat.getpixel(corner) == rgb, (
                f"{copy.path}: corner {corner} is not {copy.ground}"
            )


def test_an_opaque_copy_says_what_it_is() -> None:
    _, pictures = build.collect(ROOT)
    for copy in logo.opaque_plan(ROOT):
        about = next(item.meta for item in pictures if item.path == copy.path)
        assert (
            about is not None
            and copy.source.name in about.description
            and copy.ground in about.description
        )
        assert "opaque" in about.keywords and about.source_url == records.url(copy.source)
        assert about.profile == meta.profile_for((copy.width, copy.height))


def test_the_archive_holds_the_renditions(tree: Path) -> None:
    import zipfile

    names = zipfile.ZipFile(io.BytesIO(build.write_zip(tree).read_bytes())).namelist()
    for needed in (
        "kleidos-press-kit/logo/webp/kleidos-mark-1024.webp",
        "kleidos-press-kit/logo/png/kleidos-mark-opaque-black-1024.png",
        "kleidos-press-kit/logo/webp/kleidos-lockup-horizontal-for-light-opaque-white-512.webp",
        "kleidos-press-kit/press-kit/photos/kleidos-photo-four-boards.webp",
    ):
        assert needed in names, needed


def test_a_page_s_generated_block_is_replaced_whole_wherever_it_stands() -> None:
    begin, end = record.block_markers("sizes")
    page = f"One\n{begin}\nold\n{end}\nTwo\n{begin}{end}\n{end} {begin}"
    block = f"{begin}\n\nnew\\1\n\n{end}"
    assert (
        record.with_block(page, "sizes", "new\\1") == f"One\n{block}\nTwo\n{block}\n{end} {begin}"
    )
    for text in ("", begin, end, f"{end}{begin}", page.replace("sizes", "other")):
        with pytest.raises(ValueError, match="no generated block 'sizes'"):
            record.with_block(text, "sizes", "new")


def test_a_page_of_blocks_never_ended_is_refused_in_linear_time() -> None:
    begin, _ = record.block_markers("sizes")
    start = time.process_time()
    with pytest.raises(ValueError, match="no generated block"):
        record.with_block(begin * 10_000, "sizes", "new")
    assert time.process_time() - start < 1


@pytest.mark.browser
def test_drawn_again_every_picture_is_the_committed_one(chromium: raster.Browser) -> None:
    recorded = json.loads((ROOT / record.EXPORTS_JSON).read_text(encoding="utf-8"))
    exact = chromium.version == recorded["chromium"]
    _, pictures = build.collect(ROOT)
    cache: dict[str, Any] = {}
    for item in pictures:
        if item.path.parent not in (logo.PNG_DIR, press.IMAGES_DIR) or item.size[0] > 2600:
            continue
        again, kept = item.draw(chromium, cache), (ROOT / item.path).read_bytes()
        if exact:
            assert png.differing(again, kept) == 0, item.path
        else:
            drift = png.drift(again, kept)
            assert drift is not None and drift <= build.TOLERANCE, item.path


@pytest.mark.browser
def test_the_mark_alone_is_the_mark_file_drawn_by_itself(chromium: raster.Browser) -> None:
    source = (ROOT / "logo/src/mark.svg").read_text(encoding="utf-8")
    alone = png.encode(png.clean(chromium.draw(source, (256, 256), "mark-source")))
    assert png.differing(alone, (ROOT / "logo/png/kleidos-mark-256.png").read_bytes()) == 0
