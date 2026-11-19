# SPDX-License-Identifier: MIT
"""Photographs: JPEG files that hold pixels, and the record of what they are.

A camera writes far more than pixels into a file: the time, the place, the
device, its settings, a thumbnail, sometimes the owner's name. A photograph
in this project is the owner's own, given for publication, and goes into the
tree only as :func:`clean` writes it: turned upright, its colors converted to
sRGB, encoded again from its pixels with no EXIF, ICC profile or comment. The
narrower copies are drawn from that file by :func:`narrowed`, with the same
settings, so the builder can make them again and compare.

The one thing added is the record of what the picture is (:mod:`.meta`): an
XMP packet in APP1 and its IIM twin in APP13, right after the JFIF header.
:func:`stamp` writes them on a published file without touching a byte from
its first table on, so the builder restamps the full-resolution file from its
record without encoding it again.

:func:`findings` reads every segment of a JPEG, through its scans to its end,
and refuses any that is not pixels, tables, the bare JFIF header or the
profile's two metadata segments, and any byte after the end-of-image marker.
Camera data never comes back: no EXIF segment is ever accepted.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import meta as media

if TYPE_CHECKING:
    from .meta import MediaMeta

PHOTOS_DIR = Path("press-kit/photos")

#: How every photograph is encoded: sRGB without a profile (what an untagged
#: JPEG is read as), quality 88, full chroma so the small words on a screen
#: stay sharp, baseline and optimized so the same pixels give the same bytes.
QUALITY = 88
SUBSAMPLING = 0

#: The segments a published JPEG may hold, by marker: start and end, the
#: bare JFIF header (APP0), quantization and Huffman tables, the frame
#: header, the restart interval and the scans.
ALLOWED_MARKERS = frozenset({0xD8, 0xD9, 0xE0, 0xDB, 0xC4, 0xC0, 0xC1, 0xC2, 0xDD, 0xDA})
#: And, with a record, the profile's XMP (APP1) and IIM (APP13), holding exactly what the record gives.
METADATA_MARKERS = frozenset({0xE1, 0xED})
MARKER_NAMES = {0xE1: "APP1 (EXIF or XMP)", 0xE2: "APP2 (ICC profile)", 0xED: "APP13 (IPTC)", 0xFE: "COM (a comment)"}


def encode(image: Any, meta: MediaMeta | None = None) -> bytes:
    """Return *image* as a JPEG that holds its pixels and, given a record, its metadata.

    The image's ``info`` is left behind, so Pillow never writes EXIF, XMP or a
    color profile it carried in.
    """
    bare_image = image.copy()
    bare_image.info = {}
    buffer = io.BytesIO()
    bare_image.save(buffer, "JPEG", quality=QUALITY, subsampling=SUBSAMPLING, optimize=True, progressive=False)
    data = buffer.getvalue()
    return data if meta is None else media.jpeg_stamp(data, meta)


def stamp(data: bytes, meta: MediaMeta) -> bytes:
    """Return a published JPEG with its metadata replaced by the record's, every byte from its first table on unchanged."""
    return media.jpeg_stamp(data, meta)


def bare(data: bytes) -> bytes:
    """Return a JPEG with only its JFIF header before its tables."""
    return media.jpeg_bare(data)


def clean(data: bytes, meta: MediaMeta | None = None) -> bytes:
    """Return a camera's JPEG as this project publishes it: upright, sRGB, pixels only, then the record given."""
    from PIL import Image, ImageCms, ImageOps  # noqa: PLC0415

    with Image.open(io.BytesIO(data)) as opened:
        upright = ImageOps.exif_transpose(opened)
        profile = opened.info.get("icc_profile")
        pixels = upright.convert("RGB")
    if profile:
        source = ImageCms.ImageCmsProfile(io.BytesIO(profile))
        pixels = ImageCms.profileToProfile(pixels, source, ImageCms.createProfile("sRGB"),
                                           renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC, outputMode="RGB")
    fresh = Image.new("RGB", pixels.size)
    fresh.paste(pixels)
    return encode(fresh, meta)


def narrowed(data: bytes, width: int, meta: MediaMeta | None = None) -> bytes:
    """Return a copy of a published photograph *width* pixels wide, with the record given."""
    from PIL import Image  # noqa: PLC0415

    with Image.open(io.BytesIO(data)) as opened:
        height = round(width * opened.height / opened.width)
        return encode(opened.convert("RGB").resize((width, height), Image.Resampling.LANCZOS), meta)


#: Inside a scan's coded data, 0xFF is followed by a stuffed zero or a restart marker; any other
#: byte after it starts the next segment.
CODED_DATA_FOLLOWERS = frozenset({0x00, *range(0xD0, 0xD8)})


def walk(data: bytes) -> tuple[list[int], int]:
    """Return the markers of every segment of a JPEG, in file order, and where its last one ends.

    The walk goes through each scan's coded data to the segment after it, so a segment placed
    between two scans or after the last one is read too; it stops at the end-of-image marker.
    """
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG")
    found, position = [0xD8], 2
    while position + 2 <= len(data):
        if data[position] != 0xFF:
            raise ValueError("a segment does not start with a marker")
        marker = data[position + 1]
        if marker == 0xFF:  # a fill byte before a marker
            position += 1
            continue
        found.append(marker)
        position += 2
        if marker == 0xD9:
            return found, position
        if position + 2 > len(data):
            break
        position += int.from_bytes(data[position : position + 2], "big")
        if marker == 0xDA:
            while position + 1 < len(data) and not (data[position] == 0xFF and data[position + 1] not in CODED_DATA_FOLLOWERS):
                position += 1
    raise ValueError("the file ends before its end-of-image marker")


def markers(data: bytes) -> list[int]:
    """Return the markers of every segment of a JPEG, in file order."""
    return walk(data)[0]


def size(data: bytes) -> tuple[int, int]:
    """Return a JPEG's width and height."""
    from PIL import Image  # noqa: PLC0415

    with Image.open(io.BytesIO(data)) as opened:
        if opened.format != "JPEG":
            raise ValueError("not a JPEG")
        return opened.size


def findings(name: str, data: bytes, expected: tuple[int, int] | None = None, limit: int | None = None,
             meta: MediaMeta | None = None) -> list[str]:
    """Return what is wrong with a published photograph: its segments, its metadata, its size, its weight.

    :param meta: The file's record. Without one, any metadata segment is refused.
    """
    try:
        (found_markers, end), actual = walk(data), size(data)
    except (ValueError, OSError):
        return [f"{name}: not a JPEG"]
    found = []
    if end != len(data):
        found.append(f"{name}: carries {len(data) - end:,} bytes after its end-of-image marker")
    allowed = ALLOWED_MARKERS | (METADATA_MARKERS if meta is not None else frozenset())
    extra = sorted({marker for marker in found_markers if marker not in allowed})
    if extra:
        what = ", ".join(MARKER_NAMES.get(marker, f"marker 0x{marker:02X}") for marker in extra)
        holds = "pixels, tables and the profile's metadata" if meta is not None else "pixels and tables only"
        found.append(f"{name}: holds {what}; a published photograph holds {holds}")
    if meta is not None:
        found += media.jpeg_findings(name, data, meta)
    if 0xE0 in found_markers:
        app0 = data.index(b"\xff\xe0")
        length = int.from_bytes(data[app0 + 2 : app0 + 4], "big")
        if data[app0 + 4 : app0 + 9] != b"JFIF\x00" or length != 16:
            found.append(f"{name}: its APP0 segment is not the bare JFIF header (a thumbnail or an extension)")
    if expected is not None and actual != expected:
        found.append(f"{name}: is {actual[0]} x {actual[1]}, not {expected[0]} x {expected[1]}")
    if limit is not None and len(data) >= limit:
        found.append(f"{name}: is {len(data):,} bytes; the limit is under {limit:,}")
    return found
