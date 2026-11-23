# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""WebP copies of the published pictures, built from pixels alone, and the checks on the ones in the
tree.

Every published PNG and photograph also comes as a WebP file of the same name,
encoded by Pillow's pinned libwebp from the decoded pixels of the file it
copies, never from a browser's screenshot, so it carries nothing else:

- flat artwork (the logo files, the palette's sheet, the press images, the
  screen captures) is encoded lossless, with the color under every fully
  transparent pixel kept, so it decodes to the PNG's pixels exactly;
- the photograph is encoded lossy at quality 90, the slowest and best method.

Then the record of what it is (:mod:`.meta`) is added as an XMP chunk after
the pixels' chunks, in the extended format, and nothing else: no EXIF, no
color profile. The same pixels give the same bytes for one libwebp version;
``exports.json`` records the version and the settings each file was encoded
with.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

from . import meta as media

if TYPE_CHECKING:
    from .meta import MediaMeta

#: How flat artwork is encoded: lossless, the most effort, the pixels under full transparency kept.
LOSSLESS = {"lossless": True, "quality": 100, "method": 6, "exact": True}
#: How a photograph is encoded: lossy at quality 90, the slowest and best method.
LOSSY = {"lossless": False, "quality": 90, "method": 6}


def settings() -> dict[str, Any]:
    """Return what ``exports.json`` records of the encoder: Pillow's and libwebp's versions and both
    settings."""
    import PIL
    from PIL import features

    return {
        "pillow": PIL.__version__,
        "libwebp": features.version("webp"),
        "lossless": LOSSLESS,
        "lossy": LOSSY,
    }


def pixels(data: bytes) -> Any:
    """Return the decoded pixels of a PNG, JPEG or WebP file in a fresh image: RGBA where it has
    alpha, RGB otherwise."""
    from PIL import Image

    with Image.open(io.BytesIO(data)) as opened:
        mode = (
            "RGBA"
            if opened.mode in ("RGBA", "LA", "PA") or "transparency" in opened.info
            else "RGB"
        )
        decoded = opened.convert(mode)
    fresh = Image.new(mode, decoded.size)
    fresh.paste(decoded)
    return fresh


def encode(image: Any, meta: MediaMeta | None = None, lossless: bool = True) -> bytes:
    """Return *image* as a WebP file that holds its pixels and, given a record, its metadata.

    The image's ``info`` is left behind, so Pillow never writes EXIF, XMP or a
    color profile it carried in.
    """
    bare = image.copy()
    bare.info = {}
    buffer = io.BytesIO()
    bare.save(buffer, "WEBP", **(LOSSLESS if lossless else LOSSY))
    data = media.webp_bare(buffer.getvalue())
    return data if meta is None else media.webp_stamp(data, meta)


def copy_of(data: bytes, meta: MediaMeta | None = None, lossless: bool = True) -> bytes:
    """Return the WebP copy of a published PNG or JPEG file, from its decoded pixels."""
    return encode(pixels(data), meta, lossless)


def is_lossless(data: bytes) -> bool:
    """Tell whether a WebP file holds lossless pixels."""
    return any(name == "VP8L" for name, _ in media.webp_chunks_of(data))


def size(data: bytes) -> tuple[int, int]:
    """Return a WebP picture's width and height, read from its pixels' chunk."""
    return media.webp_size(data)


def findings(
    name: str,
    data: bytes,
    expected: tuple[int, int] | None = None,
    limit: int | None = None,
    meta: MediaMeta | None = None,
) -> list[str]:
    """Return what is wrong with a published WebP file: its chunks, its metadata, its size, its
    weight.

    :param meta: The file's record. Without one, any chunk but the pixels' is refused.
    """
    try:
        chunks = media.webp_chunks_of(data)
        actual = media.webp_size(data)
    except ValueError as error:
        return [f"{name}: not a WebP file ({error})"]
    found = []
    allowed = media.WEBP_IMAGE_CHUNKS | ({"VP8X", "XMP "} if meta is not None else frozenset())
    extra = sorted({chunk.strip() for chunk, _ in chunks if chunk not in allowed})
    if extra:
        what = "its pixels and the profile's XMP" if meta is not None else "its pixels only"
        found.append(f"{name}: holds {', '.join(extra)}; a published WebP file holds {what}")
    if meta is not None:
        found += media.webp_findings(name, data, meta)
    if expected is not None and actual != expected:
        found.append(f"{name}: is {actual[0]} x {actual[1]}, not {expected[0]} x {expected[1]}")
    if limit is not None and len(data) >= limit:
        found.append(f"{name}: is {len(data):,} bytes; the limit is under {limit:,}")
    return found
