# SPDX-License-Identifier: MIT
"""The pictures: encoded from pixels alone, compared exactly and with tolerance, drawn the same twice."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import build
import pytest
from kleidos_brand import boards, logo, photos, png, press, record, records

ROOT = Path(__file__).resolve().parents[1]


def picture(color: tuple[int, int, int, int], size: tuple[int, int] = (8, 8)) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, "PNG")
    return buffer.getvalue()


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
    assert png.findings("x.png", buffer.getvalue(), (4, 4)) and not png.findings("x.png", cleaned, (4, 4))


def test_a_cleaned_photograph_carries_pixels_only() -> None:
    from PIL import Image, ImageCms

    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: turn 90 degrees clockwise to show it upright
    exif[0x010F] = "A camera maker"
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), (200, 120, 40)).save(buffer, "JPEG", exif=exif.tobytes(), icc_profile=profile, comment=b"a note")
    camera = buffer.getvalue()
    assert {0xE1, 0xE2, 0xFE} <= set(photos.markers(camera))
    assert any("APP1" in line for line in photos.findings("x.jpg", camera))
    cleaned = photos.clean(camera)
    assert photos.findings("x.jpg", cleaned, (20, 40)) == [], "upright, and nothing but pixels and tables"
    with Image.open(io.BytesIO(cleaned)) as opened:
        assert not opened.getexif() and "icc_profile" not in opened.info and "comment" not in opened.info
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
    assert 0xFE in photos.markers(between) and any("COM" in line for line in photos.findings("x.jpg", between))
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
        assert photos.findings(photo["file"], photos.bare(whole), tuple(photo["size"])) == [], "without its record, only pixels and tables"
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
    assert png.findings("x.png", base, (8, 8), limit=10) == [f"x.png: is {len(base):,} bytes; the limit is under 10"]


def test_every_committed_picture_is_recorded_and_within_its_limits() -> None:
    recorded = json.loads((ROOT / record.EXPORTS_JSON).read_text(encoding="utf-8"))
    _, pictures = build.collect(ROOT)
    assert {item.path.as_posix() for item in pictures} == set(recorded["files"])
    for item in pictures:
        data = (ROOT / item.path).read_bytes()
        assert (photos.size(data) if item.path.suffix == ".jpg" else png.size(data)) == item.size, item.path
        assert hashlib.sha256(data).hexdigest() == recorded["files"][item.path.as_posix()]["sha256"]
        if item.limit is not None:
            assert len(data) < item.limit, item.path
        elif item.path.parts[0] == "press-kit":
            # A capture and the full-resolution photograph are kept as they are, with no limit of their own.
            assert item.path.parent in (press.SCREENS_DIR, photos.PHOTOS_DIR) and not item.row, item.path


def test_every_logo_has_its_png_copies_and_every_press_image_both_languages() -> None:
    names = {path.name for path in (ROOT / logo.PNG_DIR).iterdir()}
    for item in logo.build(ROOT):
        assert any(name.startswith(f"{item.stem}-") or name == f"{item.stem}.png" for name in names), item.stem
    images = {image.stem: image for image in press.images(ROOT)}
    for stem in ("kleidos-16x9", "kleidos-16x9-light", "kleidos-1x1", "kleidos-1x1-light", "kleidos-screens-16x9",
                 "kleidos-boards-16x9", "kleidos-boards-16x9-light", "kleidos-boards-4x5", "kleidos-boards-4x5-light"):
        assert stem in images and f"{stem}-es" in images
    assert images["kleidos-16x9-es"].sets["title.0"].line.text == "Tus contraseñas, en una placa"
    assert not any(press.findings(image) for image in images.values())
    assert {plate.board for plate in images["kleidos-screens-16x9"].plates} <= set(press.load(ROOT)["screens"])
    for stem in ("kleidos-boards-16x9", "kleidos-boards-4x5-light-es"):
        assert [placed.slug for placed in images[stem].fronts] == boards.order(ROOT), "every board, in the site's order"
        assert not images[stem].publish_svg
    assert len({plate.board for plate in images["kleidos-screens-16x9"].plates}) >= 5, "not only one board's screen"


def test_the_small_marks_keyhole_is_a_hole() -> None:
    from PIL import Image

    with Image.open(ROOT / logo.PNG_DIR / "kleidos-mark-small-21.png") as opened:
        pixels = opened.convert("RGBA")
    assert pixels.size == (21, 21)
    assert pixels.getpixel((10, 9))[3] == 0, "the eye shows the ground"
    assert pixels.getpixel((10, 11))[3] == 0, "and so does the stem"
    assert pixels.getpixel((7, 9)) == (0, 210, 255, 255), "the body is solid in the ring's color"
    assert pixels.getpixel((10, 0))[3] > 128 and pixels.getpixel((10, 1))[3] == 0, "the ring is one pixel, on the file's edge"
    with Image.open(ROOT / logo.PNG_DIR / "kleidos-mark-small-on-dark-21.png") as opened:
        assert opened.convert("RGB").getpixel((10, 9)) == (10, 12, 15), "on its tile, the keyhole is the tile"


def test_the_archive_is_the_same_bytes_twice(tree: Path) -> None:
    first = build.write_zip(tree).read_bytes()
    assert build.write_zip(tree).read_bytes() == first
    import zipfile

    names = zipfile.ZipFile(io.BytesIO(first)).namelist()
    for needed in ("kleidos-press-kit/TRADEMARKS.md", "kleidos-press-kit/LICENSE", "kleidos-press-kit/LICENSES/MIT.txt", "kleidos-press-kit/press-kit/USAGE.md",
                   "kleidos-press-kit/press-kit/svg/kleidos-16x9.svg", "kleidos-press-kit/logo/svg/kleidos-mark.svg",
                   "kleidos-press-kit/press-kit/photos/kleidos-photo-four-boards.jpg", "kleidos-press-kit/press-kit/photos/kleidos-photo-four-boards-1920.jpg"):
        assert needed in names


@pytest.mark.browser
def test_drawn_again_every_picture_is_the_committed_one(chromium) -> None:  # noqa: ANN001
    recorded = json.loads((ROOT / record.EXPORTS_JSON).read_text(encoding="utf-8"))
    exact = chromium.version == recorded["chromium"]
    _, pictures = build.collect(ROOT)
    cache: dict = {}
    for item in pictures:
        if item.path.parent not in (logo.PNG_DIR, press.IMAGES_DIR) or item.size[0] > 2600:
            continue
        again, kept = item.draw(chromium, cache), (ROOT / item.path).read_bytes()
        if exact:
            assert png.differing(again, kept) == 0, item.path
        else:
            assert png.drift(again, kept) <= build.TOLERANCE, item.path


@pytest.mark.browser
def test_the_mark_alone_is_the_mark_file_drawn_by_itself(chromium) -> None:  # noqa: ANN001
    source = (ROOT / "logo/src/mark.svg").read_text(encoding="utf-8")
    alone = png.encode(png.clean(chromium.draw(source, (256, 256), "mark-source")))
    assert png.differing(alone, (ROOT / "logo/png/kleidos-mark-256.png").read_bytes()) == 0
