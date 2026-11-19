# SPDX-License-Identifier: MIT
"""PNG files built from pixels alone, and the checks on the ones in the tree.

A browser writes more than pixels into a screenshot. Every PNG this project
publishes is re-encoded by Pillow from the pixels only, so it carries no time
and no trace of the machine that drew it; then the record of what it is
(:mod:`.meta`) is added as the profile's fixed text chunks and XMP packet,
right before the pixels, and nothing else.
"""
from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

from . import meta as media

if TYPE_CHECKING:
    from .meta import MediaMeta

#: The chunks a published PNG may hold: pixels, color and layout, and the
#: profile's text chunks (``tEXt`` and the XMP ``iTXt``), only with the values
#: its record gives.
ALLOWED_CHUNKS = frozenset({"IHDR", "PLTE", "IDAT", "IEND", "tRNS", "gAMA", "cHRM", "sRGB", "iCCP", "sBIT", "bKGD", "pHYs"})
METADATA_CHUNKS = media.PNG_TEXT_CHUNKS


def clean(shot: bytes, flatten: str | None = None) -> Any:
    """Return a picture's pixels in a fresh image that carries nothing else.

    :param flatten: A ``#rrggbb`` ground to composite on, which drops the alpha channel.
    """
    from PIL import Image  # noqa: PLC0415

    with Image.open(io.BytesIO(shot)) as opened:
        pixels = opened.convert("RGBA")
        if flatten is None:
            fresh = Image.new("RGBA", pixels.size)
            fresh.paste(pixels)
            return fresh
        fresh = Image.new("RGB", pixels.size, flatten)
        fresh.paste(pixels, mask=pixels.getchannel("A"))
        return fresh


def encode(image: Any, meta: MediaMeta | None = None) -> bytes:
    """Return *image* as a PNG that holds its pixels and, given a record, its metadata.

    The image's ``info`` is left behind, so Pillow never writes a color profile
    or text it carried in; the record's chunks are added to the encoder's output.
    """
    bare = image.copy()
    bare.info = {}
    buffer = io.BytesIO()
    bare.save(buffer, "PNG", optimize=True)
    data = buffer.getvalue()
    return data if meta is None else media.png_stamp(data, meta)


def stamp(data: bytes, meta: MediaMeta) -> bytes:
    """Return a PNG with its metadata replaced by the record's, every other chunk's bytes unchanged."""
    return media.png_stamp(data, meta)


def bare(data: bytes) -> bytes:
    """Return a PNG without any text, time or EXIF chunk."""
    return media.png_bare(data)


def chunk_names(data: bytes) -> list[str]:
    """Return the names of a PNG's chunks, in file order."""
    names, position = [], 8
    while position + 8 <= len(data):
        length = int.from_bytes(data[position : position + 4], "big")
        names.append(data[position + 4 : position + 8].decode("latin-1"))
        if names[-1] == "IEND":
            break
        position += 12 + length
    return names


def size(data: bytes) -> tuple[int, int]:
    """Return a PNG's width and height, read from its header."""
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def differing(first: bytes, second: bytes) -> int | None:
    """Return how many pixels two pictures differ in, or ``None`` when their sizes differ."""
    from PIL import Image, ImageChops  # noqa: PLC0415

    with Image.open(io.BytesIO(first)) as one, Image.open(io.BytesIO(second)) as two:
        if one.size != two.size:
            return None
        left, right = one.convert("RGBA"), two.convert("RGBA")
        if left.tobytes() == right.tobytes():
            return 0
        bands = ImageChops.difference(left, right).split()
        merged = bands[0]
        for band in bands[1:]:
            merged = ImageChops.lighter(merged, band)
        return sum(merged.histogram()[1:])


def drift(first: bytes, second: bytes, step: int = 24) -> float | None:
    """Return the share of pixels that differ by more than *step* in any channel, or ``None`` on another size.

    This is the tolerant comparison a machine other than the exporting one
    runs: an edge drawn a shade apart passes, a word in a fallback face or a
    shape out of place does not.
    """
    from PIL import Image, ImageChops  # noqa: PLC0415

    with Image.open(io.BytesIO(first)) as one, Image.open(io.BytesIO(second)) as two:
        if one.size != two.size:
            return None
        bands = ImageChops.difference(one.convert("RGBA"), two.convert("RGBA")).split()
        merged = bands[0]
        for band in bands[1:]:
            merged = ImageChops.lighter(merged, band)
        far = sum(merged.histogram()[step + 1 :])
        return far / (one.size[0] * one.size[1])


def findings(name: str, data: bytes, expected: tuple[int, int] | None = None, limit: int | None = None,
             meta: MediaMeta | None = None) -> list[str]:
    """Return what is wrong with a published PNG: its chunks, its metadata, its size, its weight.

    :param meta: The file's record. Without one, a text chunk is refused like any other.
    """
    found = []
    try:
        actual = size(data)
    except ValueError:
        return [f"{name}: not a PNG"]
    allowed = ALLOWED_CHUNKS | (METADATA_CHUNKS if meta is not None else frozenset())
    extra = sorted(set(chunk_names(data)) - allowed)
    if extra:
        what = "pixels, color and layout chunks and the profile's metadata" if meta is not None else "pixels, color and layout chunks only"
        found.append(f"{name}: holds {', '.join(extra)}; a published PNG holds {what}")
    if meta is not None:
        found += media.png_findings(name, data, meta)
    if expected is not None and actual != expected:
        found.append(f"{name}: is {actual[0]} x {actual[1]}, not {expected[0]} x {expected[1]}")
    if limit is not None and len(data) >= limit:
        found.append(f"{name}: is {len(data):,} bytes; the limit is under {limit:,}")
    return found
