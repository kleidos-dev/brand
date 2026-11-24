# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""Embedded metadata: what a published picture says about itself (profile ``kleidos-media-meta/1``).

Every picture Kleidos publishes carries the same facts, written by the builder
that makes it and never by hand: what it is, a description and an alt text,
who made it, its copyright line and license (an SPDX identifier and the
license's URL), where its public copy lives, keywords, and how it was made
(IPTC's Digital Source Type). Indexers read them from the file, desktop tools
show them, and they travel with every copy.

The module writes each format's own slots, in a fixed order, from fixed
constants and one :class:`MediaMeta` record per file, so the same record gives
the same bytes on every machine: no date, no random identifier, no tool or
version, no padding.

- XMP (:func:`xmp_packet`): one packet for PNG, JPEG and WebP, Dublin Core, IPTC
  Core and Extension, PLUS, XMP Rights and ccREL; the short profile for a
  picture under 64 px.
- PNG (:func:`png_stamp`): ``tEXt`` chunks (Latin-1) and the XMP packet in an
  ``iTXt`` chunk, right before the first ``IDAT``. The pixels' chunks keep
  their bytes.
- JPEG (:func:`jpeg_stamp`): the XMP packet in APP1 and an IIM block in APP13
  (with MWG's digest) after the JFIF header; no EXIF. Everything from the
  first table to the end keeps its bytes.
- WebP (:func:`webp_stamp`): the extended format, a ``VP8X`` header with the
  XMP flag (and the alpha flag where the picture has alpha), the pixels'
  chunks with their bytes unchanged, then the XMP packet in an ``XMP ``
  chunk; no EXIF and no color profile. WebP has no simple text slots, so the
  packet is the whole record.
- SVG (:func:`svg_stamp`): ``role``, ``aria-labelledby`` and ``lang`` on the
  root, a ``<title>``, a ``<desc>`` and Dublin Core plus ccREL in
  ``<metadata>``, between ``REUSE-IgnoreStart`` and ``REUSE-IgnoreEnd`` so
  REUSE never reads the rights line as a copyright notice.

:func:`reuse_truth` reads a file's license and copyright holders as REUSE
does; the checks hold every record to it. :func:`deny_findings` refuses a
value that holds a local path, a private host, a machine's time, a tool's
name or an e-mail address, and the identity patterns kept out of the tree
(``tools/deny-local.txt`` or ``KLEIDOS_DENY_EXTRA``).

``brand`` and its social pack (``social/``) share this file. The other
repositories keep a copy of it, and the golden files under
``tests/fixtures/meta/`` hold every copy to the same bytes.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import tomllib
import zlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

#: The profile's name. It goes into the record of what each picture was built from, never into a
#: file.
META_PROFILE = "kleidos-media-meta/1"

CREATOR = "José M. Requena Plens"
CREATOR_URL = "https://kleidos.dev"
PROJECT = "Kleidos"
PROJECT_URL = "https://kleidos.dev"
#: IPTC's Credit Line (22 bytes, under IIM's 32).
CREDIT = CREATOR
BASE_KEYWORDS = ("Kleidos", "hardware password manager", "open source")
ORG_URL = "https://github.com/kleidos-dev"
#: Where a file of the firmware repository is pointed at until that repository is public.
FIRMWARE_REPO_URL = "https://kleidos.dev"

TRADEMARK_NOTE_M5 = (
    "M5Stack and M5 are trademarks of their owner; Kleidos is not affiliated with M5Stack."
)
TRADEMARK_NOTE_LILYGO = (
    "LILYGO and T-Deck are trademarks of their owner; Kleidos is not affiliated with LILYGO."
)
TRADEMARK_NOTE_KLEIDOS = "The Kleidos name and logo are subject to the terms in TRADEMARKS.md."

#: The page that states each repository's terms: IPTC's Licensor URL.
RIGHTS_URLS = {
    "brand": f"{ORG_URL}/brand/blob/main/TRADEMARKS.md",
    "boards": f"{ORG_URL}/boards/blob/main/NOTICE.md",
    ".github": f"{ORG_URL}/.github/blob/main/LICENSE",
}

#: IPTC NewsCodes ``digitalsourcetype``: how a picture was made. Each writer states the concept's
#: whole URI in the markup it writes.
DIGITAL_SOURCE_TYPES = frozenset(
    {
        "digitalCapture",
        "screenCapture",
        "digitalCreation",
        "dataDrivenMedia",
        "composite",
        "trainedAlgorithmicMedia",
        "compositeWithTrainedAlgorithmicMedia",
        "compositeSynthetic",
    }
)

#: A raster whose longer side is under this many pixels carries the short profile.
SHORT_BELOW = 64

#: The Spanish of every fixed sentence a Spanish file's terms are built from.
SPANISH = {
    TRADEMARK_NOTE_M5: "M5Stack y M5 son marcas de su titular; Kleidos no está afiliado a M5Stack.",
    TRADEMARK_NOTE_LILYGO: "LILYGO y T-Deck son marcas de su titular; Kleidos no está afiliado a "
    "LILYGO.",
    TRADEMARK_NOTE_KLEIDOS: "El nombre y el logotipo de Kleidos están sujetos a las condiciones de "
    "TRADEMARKS.md.",
}


def extra_terms(repo: str) -> str:
    """Return the sentence that points to a repository's additional terms under the GPL."""
    return f"Additional terms under GPL section 7 and the press permission: {RIGHTS_URLS[repo]}."


SPANISH[extra_terms("brand")] = (
    "Condiciones adicionales según la sección 7 de la GPL y el permiso de prensa: "
    f"{RIGHTS_URLS['brand']}."
)


# --- Licenses ------------------------------------------------------------------------------

SPDX_SPLIT = re.compile(r" (?:AND|OR|WITH) |[()]")


def spdx_ids(expression: str) -> list[str]:
    """Return the identifiers of an SPDX expression, in order."""
    spaced = " ".join(expression.split())
    return [part.strip() for part in SPDX_SPLIT.split(spaced) if part.strip()]


def license_url(identifier: str, repo: str = "brand") -> str:
    """Return the URL of a license's text: SPDX's page, or the ``LICENSES/`` file of the public
    repository that declares it."""
    if identifier.startswith("LicenseRef-"):
        if repo not in RIGHTS_URLS:
            raise ValueError(
                f"{identifier} is declared in no public repository; a Web Statement never points "
                "to a page that is not a license"
            )
        return f"{ORG_URL}/{repo}/blob/main/LICENSES/{identifier}.txt"
    if not re.fullmatch(r"[A-Za-z0-9.+-]+", identifier):
        raise ValueError(f"not an SPDX identifier: {identifier!r}")
    return f"https://spdx.org/licenses/{identifier}.html"


def identifier_url(repo: str, path: str | Path) -> str:
    """Return the public URL of a file of a repository of the organization."""
    return f"{ORG_URL}/{repo}/blob/main/{Path(path).as_posix()}"


def strip_email(holder: str) -> str:
    """Return a REUSE copyright line without its ``<address>``."""
    kept, start = [], 0
    while (opened := holder.find("<", start)) >= 0 and (closed := holder.find(">", opened)) >= 0:
        kept.append(holder[start:opened].rstrip())
        start = closed + 1
    return "".join([*kept, holder[start:]]).strip()


# --- The record ----------------------------------------------------------------------------


@dataclass(frozen=True)
class MediaMeta:
    """Everything a published file says about itself."""

    title: str
    description: str
    alt: str
    keywords: tuple[str, ...]
    digital_source_type: str
    spdx: str
    own_license: str
    holders: tuple[str, ...]
    identifier_url: str
    rights_url: str
    credits: tuple[str, ...] = ()
    trademarks: tuple[str, ...] = ()
    extra_terms: tuple[str, ...] = ()
    source_url: str | None = None
    language: str = "en"
    title_es: str | None = None
    description_es: str | None = None
    alt_es: str | None = None
    content_date: str | None = None
    profile: str = "full"
    repo: str = "brand"
    spanish: dict[str, str] = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self) -> None:
        problems = record_problems(self)
        if problems:
            raise ValueError("; ".join(problems))

    @property
    def copyright(self) -> str:
        """Return the copyright line: holders, then the license expression."""
        return "© " + "; © ".join(self.holders) + f". {self.spdx}."

    @property
    def web_statement(self) -> str:
        """Return the URL of the license of the Kleidos-authored part."""
        return license_url(self.own_license, self.repo)

    def usage_terms(self, lang: str = "en") -> str:
        """Return the license, its URLs, the credits, the trademark notes and the extra terms, as
        one text."""
        urls = ", ".join(
            license_url(identifier, self.repo) for identifier in dict.fromkeys(spdx_ids(self.spdx))
        )
        lead = (
            f"Licensed under {self.spdx}: {urls}."
            if lang == "en"
            else f"Con licencia {self.spdx}: {urls}."
        )
        sentences = [*self.credits, *self.trademarks, *self.extra_terms]
        if lang != "en":
            table = {**SPANISH, **self.spanish}
            missing = [sentence for sentence in sentences if sentence not in table]
            if missing:
                raise ValueError(f"no Spanish for {missing[0]!r}")
            sentences = [table[sentence] for sentence in sentences]
        return " ".join([lead, *sentences])

    def visible(self, name: str) -> str:
        """Return the title, description or alt in the file's own language."""
        if self.language == "es":
            return str(getattr(self, f"{name}_es"))
        return str(getattr(self, name))


def record_problems(meta: MediaMeta) -> list[str]:
    """Return what makes a record unwritable: a limit passed, a value missing, a license out of its
    expression."""
    found = []
    if len(meta.title.encode()) > 64:
        found.append(f"the title {meta.title!r} is over 64 bytes")
    if len(meta.description) > 300:
        found.append(f"the description of {meta.title!r} is over 300 characters")
    if len(meta.alt) > 300:
        found.append(f"the alt text of {meta.title!r} is over 300 characters")
    if len(meta.keywords) > 12 or any(len(keyword.encode()) > 64 for keyword in meta.keywords):
        found.append(f"{meta.title!r} has more than 12 keywords or one over 64 bytes")
    if len(meta.copyright.encode()) > 128:
        found.append(f"the copyright line of {meta.title!r} is over 128 bytes; it is never cut")
    if meta.own_license not in spdx_ids(meta.spdx):
        found.append(f"{meta.own_license} is not in the expression {meta.spdx!r}")
    if meta.digital_source_type not in DIGITAL_SOURCE_TYPES:
        found.append(
            f"{meta.digital_source_type!r} is not an IPTC digital source type of this profile"
        )
    if meta.profile not in ("full", "short"):
        found.append(f"no profile {meta.profile!r}")
    if meta.language not in ("en", "es"):
        found.append(f"no language {meta.language!r}")
    if meta.language == "es" and not (meta.title_es and meta.description_es and meta.alt_es):
        found.append(
            f"{meta.title!r} is in Spanish and lacks a Spanish title, description or alt text"
        )
    for name in ("title", "description"):
        try:
            getattr(meta, name).encode("latin-1")
        except UnicodeEncodeError:
            found.append(
                f"the {name} of {meta.title!r} is not Latin-1, which a PNG text chunk needs; it is "
                "never transliterated"
            )
    try:
        meta.copyright.encode("latin-1")
    except UnicodeEncodeError:
        found.append(f"the copyright line of {meta.title!r} is not Latin-1")
    return found


def profile_for(size: tuple[int, int]) -> str:
    """Return the profile a raster of *size* carries."""
    return "short" if max(size) < SHORT_BELOW else "full"


# --- XMP -----------------------------------------------------------------------------------

#: Each prefix and its declaration, in the packet's order. A namespace URI is a name that readers
#: compare character by character and nothing fetches, so it is written as its vocabulary
#: publishes it, scheme included.
NAMESPACES = {
    "dc": 'xmlns:dc="http://purl.org/dc/elements/1.1/"',
    "photoshop": 'xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"',
    "Iptc4xmpCore": 'xmlns:Iptc4xmpCore="http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/"',
    "Iptc4xmpExt": 'xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"',
    "plus": 'xmlns:plus="http://ns.useplus.org/ldf/xmp/1.0/"',
    "xmpRights": 'xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/"',
    "cc": 'xmlns:cc="http://creativecommons.org/ns#"',
}
SHORT_NAMESPACES = ("dc", "Iptc4xmpExt", "xmpRights", "cc")
XMP_BEGIN = '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
XMP_END = '<?xpacket end="r"?>'


def escape(text: str) -> str:
    """Return *text* escaped for XML: ``& < > "`` and nothing else."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _alt(english: str, spanish: str | None) -> str:
    items = f'<rdf:li xml:lang="x-default">{escape(english)}</rdf:li>'
    if spanish:
        items += f'<rdf:li xml:lang="es">{escape(spanish)}</rdf:li>'
    return f"<rdf:Alt>{items}</rdf:Alt>"


def xmp_packet(meta: MediaMeta) -> bytes:
    """Return the record as an XMP packet, in the profile's fixed order, UTF-8, without padding."""
    es = meta.language == "es"
    short = meta.profile == "short"
    declared = "\n".join(
        f"        {declaration}"
        for name, declaration in NAMESPACES.items()
        if not short or name in SHORT_NAMESPACES
    )
    rows = [f"      <dc:title>{_alt(meta.title, meta.title_es if es else None)}</dc:title>"]
    if not short:
        rows.append(
            "      <dc:description>"
            f"{_alt(meta.description, meta.description_es if es else None)}"
            "</dc:description>"
        )
    rows.append(
        f"      <dc:creator><rdf:Seq><rdf:li>{escape(CREATOR)}</rdf:li></rdf:Seq></dc:creator>"
    )
    rows.append(f"      <dc:rights>{_alt(meta.copyright, None)}</dc:rights>")
    if not short:
        bag = "".join(f"<rdf:li>{escape(keyword)}</rdf:li>" for keyword in meta.keywords)
        rows.append(f"      <dc:subject><rdf:Bag>{bag}</rdf:Bag></dc:subject>")
    rows.append(f"      <dc:identifier>{escape(meta.identifier_url)}</dc:identifier>")
    if not short:
        if meta.source_url:
            rows.append(f"      <dc:source>{escape(meta.source_url)}</dc:source>")
        if es:
            rows.append("      <dc:language><rdf:Bag><rdf:li>es</rdf:li></rdf:Bag></dc:language>")
        rows.append(f"      <photoshop:Credit>{escape(CREDIT)}</photoshop:Credit>")
        rows.append(
            "      <Iptc4xmpCore:AltTextAccessibility>"
            f"{_alt(meta.alt, meta.alt_es if es else None)}"
            "</Iptc4xmpCore:AltTextAccessibility>"
        )
        rows.append('      <Iptc4xmpCore:CreatorContactInfo rdf:parseType="Resource">')
        rows.append(
            f"        <Iptc4xmpCore:CiUrlWork>{escape(CREATOR_URL)}</Iptc4xmpCore:CiUrlWork>"
        )
        rows.append("      </Iptc4xmpCore:CreatorContactInfo>")
    rows.append(
        "      <Iptc4xmpExt:DigitalSourceType>http://cv.iptc.org/newscodes/digitalsourcetype/"
        f"{meta.digital_source_type}</Iptc4xmpExt:DigitalSourceType>"
    )
    if not short:
        rows.append('      <plus:Licensor><rdf:Seq><rdf:li rdf:parseType="Resource">')
        rows.append(f"        <plus:LicensorName>{escape(CREATOR)}</plus:LicensorName>")
        rows.append(f"        <plus:LicensorURL>{escape(meta.rights_url)}</plus:LicensorURL>")
        rows.append("      </rdf:li></rdf:Seq></plus:Licensor>")
    rows.append("      <xmpRights:Marked>True</xmpRights:Marked>")
    rows.append(
        f"      <xmpRights:WebStatement>{escape(meta.web_statement)}</xmpRights:WebStatement>"
    )
    if not short:
        rows.append(
            "      <xmpRights:UsageTerms>"
            f"{_alt(meta.usage_terms('en'), meta.usage_terms('es') if es else None)}"
            "</xmpRights:UsageTerms>"
        )
    rows.append(f'      <cc:license rdf:resource="{escape(meta.web_statement)}"/>')
    text = "\n".join(
        [
            XMP_BEGIN,
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">',
            '  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">',
            '    <rdf:Description rdf:about=""',
            declared + ">",
            *rows,
            "    </rdf:Description>",
            "  </rdf:RDF>",
            "</x:xmpmeta>",
            XMP_END,
        ]
    )
    return text.encode("utf-8")


def xmp_values(meta: MediaMeta) -> list[str]:
    """Return every value a record writes, for the deny-list."""
    values = [
        meta.title,
        meta.description,
        meta.alt,
        *meta.keywords,
        meta.copyright,
        meta.identifier_url,
        meta.rights_url,
        meta.web_statement,
        meta.usage_terms("en"),
        *(meta.holders),
    ]
    if meta.source_url:
        values.append(meta.source_url)
    if meta.language == "es":
        values += [
            str(meta.title_es),
            str(meta.description_es),
            str(meta.alt_es),
            meta.usage_terms("es"),
        ]
    return values


# --- PNG -----------------------------------------------------------------------------------

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
#: The chunks this profile writes, and the ones it never lets stand: a time, compressed or EXIF
#: text.
PNG_TEXT_CHUNKS = frozenset({"tEXt", "iTXt"})
PNG_REFUSED_CHUNKS = frozenset({"tIME", "zTXt", "eXIf"})
XMP_KEYWORD = b"XML:com.adobe.xmp"


def png_chunks_of(data: bytes) -> list[tuple[str, bytes]]:
    """Return a PNG's chunks as (name, data) pairs, in file order."""
    if data[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG")
    out, position = [], 8
    while position + 8 <= len(data):
        length = int.from_bytes(data[position : position + 4], "big")
        name = data[position + 4 : position + 8].decode("latin-1")
        out.append((name, data[position + 8 : position + 8 + length]))
        position += 12 + length
        if name == "IEND":
            break
    return out


def _chunk(name: str, body: bytes) -> bytes:
    kind = name.encode("latin-1")
    return len(body).to_bytes(4, "big") + kind + body + zlib.crc32(kind + body).to_bytes(4, "big")


def png_text_items(meta: MediaMeta) -> list[tuple[str, str]]:
    """Return the ``tEXt`` keywords and values of a record, in the profile's order."""
    if meta.profile == "short":
        return [("Copyright", meta.copyright), ("License", f"{meta.spdx} {meta.web_statement}")]
    return [
        ("Title", meta.title),
        ("Author", CREATOR),
        ("Description", meta.description),
        ("Copyright", meta.copyright),
        ("License", f"{meta.spdx} {meta.web_statement}"),
        ("Comment", f"{PROJECT}, {PROJECT_URL}. {meta.identifier_url}"),
    ]


def png_chunks(meta: MediaMeta) -> list[tuple[str, bytes]]:
    """Return the metadata chunks of a record: ``tEXt`` ones, then the XMP packet in an ``iTXt``."""
    out = []
    for keyword, value in png_text_items(meta):
        try:
            out.append(("tEXt", keyword.encode("latin-1") + b"\0" + value.encode("latin-1")))
        except UnicodeEncodeError as error:
            raise ValueError(f"the PNG text {keyword!r} is not Latin-1: {value!r}") from error
    out.append(("iTXt", XMP_KEYWORD + b"\0\0\0\0\0" + xmp_packet(meta)))
    return out


def png_bare(data: bytes) -> bytes:
    """Return a PNG without any text, time or EXIF chunk: its pixel, color and layout chunks, bytes
    unchanged."""
    kept = [
        (name, body)
        for name, body in png_chunks_of(data)
        if name not in PNG_TEXT_CHUNKS | PNG_REFUSED_CHUNKS
    ]
    return PNG_SIGNATURE + b"".join(_chunk(name, body) for name, body in kept)


def png_stamp(data: bytes, meta: MediaMeta) -> bytes:
    """Return a PNG with the record's chunks right before its first ``IDAT``, every other chunk's
    bytes unchanged."""
    chunks = png_chunks_of(png_bare(data))
    first = next(index for index, (name, _) in enumerate(chunks) if name == "IDAT")
    chunks[first:first] = png_chunks(meta)
    return PNG_SIGNATURE + b"".join(_chunk(name, body) for name, body in chunks)


def png_size(data: bytes) -> tuple[int, int]:
    """Return a PNG's width and height."""
    chunks = png_chunks_of(data)
    return int.from_bytes(chunks[0][1][0:4], "big"), int.from_bytes(chunks[0][1][4:8], "big")


def png_findings(name: str, data: bytes, meta: MediaMeta) -> list[str]:
    """Return how a PNG's metadata differs from the record's: missing, different, misplaced or
    foreign."""
    try:
        chunks = png_chunks_of(data)
    except ValueError:
        return [f"{name}: M006: not a PNG"]
    found = []
    names = [chunk for chunk, _ in chunks]
    refused = sorted({chunk for chunk in names if chunk in PNG_REFUSED_CHUNKS})
    if refused:
        found.append(
            f"{name}: M005: holds {', '.join(refused)}; a published PNG holds no time, compressed "
            "text or EXIF"
        )
    profile = profile_for(png_size(data))
    if profile != meta.profile:
        found.append(
            f"{name}: M009: a {png_size(data)[0]} x {png_size(data)[1]} picture carries the "
            f"{profile} profile, not the {meta.profile} one"
        )
    expected = png_chunks(meta)
    texts = [(chunk, body) for chunk, body in chunks if chunk in PNG_TEXT_CHUNKS]
    if not texts:
        return [*found, f"{name}: M001: carries no metadata; run tools/build.py"]
    have = {body.split(b"\0", 1)[0]: body for chunk, body in texts}
    for chunk, body in expected:
        keyword = body.split(b"\0", 1)[0]
        label = keyword.decode("latin-1")
        if keyword not in have:
            found.append(f"{name}: M001: lacks its {chunk} {label!r}")
        elif have[keyword] != body:
            found.append(f"{name}: M002: its {chunk} {label!r} is not what its record gives")
    extra = sorted(
        {body.split(b"\0", 1)[0].decode("latin-1", "replace") for _, body in texts}
        - {body.split(b"\0", 1)[0].decode("latin-1") for _, body in expected}
    )
    if extra:
        found.append(f"{name}: M005: holds text chunks outside the profile ({', '.join(extra)})")
    if not found and data != png_stamp(data, meta):
        found.append(
            f"{name}: M006: its metadata chunks are not in the profile's order, right before the "
            "first IDAT"
        )
    return found


# --- JPEG ----------------------------------------------------------------------------------

XMP_APP1_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"
PHOTOSHOP_HEADER = b"Photoshop 3.0\x00"
#: The XMP packet's room in one APP1 segment: 65,533 bytes less the namespace header.
XMP_JPEG_LIMIT = 65_504
IIM_LIMITS = {5: 64, 25: 64, 80: 32, 110: 32, 116: 128, 120: 2000}


def _iim(dataset: tuple[int, int], value: bytes) -> bytes:
    record, number = dataset
    limit = IIM_LIMITS.get(number) if record == 2 else None
    if limit is not None and len(value) > limit:
        raise ValueError(
            f"IIM {record}:{number:02d} holds {len(value)} bytes; the limit is {limit}"
        )
    return b"\x1c" + bytes([record, number]) + len(value).to_bytes(2, "big") + value


def iim_block(meta: MediaMeta) -> bytes:
    """Return the record as IPTC IIM datasets, UTF-8, in the profile's order."""
    out = _iim((1, 90), b"\x1b%G") + _iim((2, 0), b"\x00\x04") + _iim((2, 5), meta.title.encode())
    if meta.profile == "full":
        out += b"".join(_iim((2, 25), keyword.encode()) for keyword in meta.keywords)
    out += _iim((2, 80), CREATOR.encode())
    if meta.profile == "full":
        out += _iim((2, 110), CREDIT.encode())
    out += _iim((2, 116), meta.copyright.encode())
    if meta.profile == "full":
        out += _iim((2, 120), meta.description.encode())
    return out


def _resource(number: int, payload: bytes) -> bytes:
    body = payload + (b"\x00" if len(payload) % 2 else b"")
    return (
        b"8BIM" + number.to_bytes(2, "big") + b"\x00\x00" + len(payload).to_bytes(4, "big") + body
    )


def _segment(marker: int, payload: bytes) -> bytes:
    if len(payload) + 2 > 0xFFFF:
        raise ValueError(f"a JPEG segment of {len(payload)} bytes does not fit")
    return bytes([0xFF, marker]) + (len(payload) + 2).to_bytes(2, "big") + payload


def jpeg_segments(meta: MediaMeta) -> tuple[bytes, bytes]:
    """Return the record's APP1 (XMP) and APP13 (IIM with its MD5 digest) segments.

    MWG's digest (Photoshop resource 1061) is an MD5 by its definition: a reader compares it to
    know whether the IIM was edited after the XMP. It authenticates nothing.
    """
    packet = xmp_packet(meta)
    if len(packet) > XMP_JPEG_LIMIT:
        raise ValueError(
            f"the XMP packet is {len(packet)} bytes; one APP1 segment holds {XMP_JPEG_LIMIT}"
        )
    iim = iim_block(meta)
    digest = hashlib.md5(iim, usedforsecurity=False).digest()
    app13 = PHOTOSHOP_HEADER + _resource(0x0404, iim) + _resource(0x0425, digest)
    return _segment(0xE1, XMP_APP1_HEADER + packet), _segment(0xED, app13)


def _jpeg_head(data: bytes) -> tuple[list[tuple[int, bytes]], int]:
    """Return the APPn and COM segments that open a JPEG, as (marker, whole segment), and where the
    next one starts."""
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG")
    segments, position = [], 2
    while position + 4 <= len(data) and data[position] == 0xFF:
        marker = data[position + 1]
        if not (0xE0 <= marker <= 0xEF or marker == 0xFE):
            break
        length = int.from_bytes(data[position + 2 : position + 4], "big")
        segments.append((marker, data[position : position + 2 + length]))
        position += 2 + length
    return segments, position


def jpeg_bare(data: bytes) -> bytes:
    """Return a JPEG with only its JFIF header before its tables, every byte from the first table on
    unchanged."""
    segments, position = _jpeg_head(data)
    kept = [whole for marker, whole in segments if marker == 0xE0]
    return b"\xff\xd8" + b"".join(kept) + data[position:]


def jpeg_stamp(data: bytes, meta: MediaMeta) -> bytes:
    """Return a JPEG with the record's APP1 and APP13 right after its JFIF header."""
    segments, position = _jpeg_head(data)
    app0 = [whole for marker, whole in segments if marker == 0xE0]
    return b"\xff\xd8" + b"".join(app0) + b"".join(jpeg_segments(meta)) + data[position:]


def jpeg_findings(name: str, data: bytes, meta: MediaMeta) -> list[str]:
    """Return how a JPEG's metadata differs from the record's."""
    try:
        segments, _ = _jpeg_head(data)
    except ValueError:
        return [f"{name}: M006: not a JPEG"]
    found = []
    app1, app13 = jpeg_segments(meta)
    markers = [marker for marker, _ in segments]
    have = dict.fromkeys(markers)
    foreign = sorted({marker for marker in markers if marker not in (0xE0, 0xE1, 0xED)})
    if foreign:
        found.append(
            f"{name}: M005: holds {', '.join(f'0x{marker:02X}' for marker in foreign)}; a "
            "published JPEG holds JFIF, XMP and IIM only"
        )
    xmp = [whole for marker, whole in segments if marker == 0xE1]
    iim = [whole for marker, whole in segments if marker == 0xED]
    if 0xE1 not in have or 0xED not in have:
        found.append(
            f"{name}: M001: lacks its {'XMP (APP1)' if 0xE1 not in have else 'IIM (APP13)'}; run "
            "tools/build.py"
        )
    if any(whole[4:].startswith(b"Exif") for whole in xmp):
        found.append(f"{name}: M005: holds EXIF; a published JPEG holds none")
    if xmp and xmp != [app1]:
        found.append(f"{name}: M002: its XMP is not what its record gives")
    if iim and iim != [app13]:
        found.append(
            f"{name}: M007: its IIM is not what its record gives, or disagrees with its XMP"
        )
    if not found and markers != [0xE0, 0xE1, 0xED]:
        found.append(f"{name}: M006: its segments are not JFIF, XMP, IIM, in that order")
    return found


# --- WebP ----------------------------------------------------------------------------------

#: The chunks that hold a WebP picture's pixels: lossless, or lossy with its alpha beside it.
WEBP_IMAGE_CHUNKS = frozenset({"VP8 ", "VP8L", "ALPH"})
#: ``VP8X`` flags: the picture has alpha, the file carries XMP.
WEBP_FLAG_ALPHA = 0x10
WEBP_FLAG_XMP = 0x04


def webp_chunks_of(data: bytes) -> list[tuple[str, bytes]]:
    """Return a WebP file's chunks as (name, data) pairs, in file order, each without its padding
    byte."""
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a WebP file")
    if int.from_bytes(data[4:8], "little") + 8 != len(data):
        raise ValueError("its RIFF size is not the file's")
    out, position = [], 12
    while position + 8 <= len(data):
        name = data[position : position + 4].decode("latin-1")
        length = int.from_bytes(data[position + 4 : position + 8], "little")
        if position + 8 + length > len(data):
            raise ValueError(f"its {name!r} chunk runs past the end of the file")
        out.append((name, data[position + 8 : position + 8 + length]))
        position += 8 + length + (length & 1)
    if position != len(data):
        raise ValueError("bytes after its last chunk")
    return out


def _webp_chunk(name: str, body: bytes) -> bytes:
    return (
        name.encode("latin-1")
        + len(body).to_bytes(4, "little")
        + body
        + (b"\x00" if len(body) & 1 else b"")
    )


def _webp_file(chunks: list[tuple[str, bytes]]) -> bytes:
    body = b"WEBP" + b"".join(_webp_chunk(name, payload) for name, payload in chunks)
    return b"RIFF" + len(body).to_bytes(4, "little") + body


def webp_image(data: bytes) -> tuple[int, int, bool]:
    """Return a WebP picture's width, height and whether it has alpha, read from its pixels' own
    chunk."""
    chunks = dict(webp_chunks_of(data))
    if "VP8L" in chunks:
        head = chunks["VP8L"]
        if len(head) < 5 or head[0] != 0x2F:
            raise ValueError("its VP8L chunk has no lossless signature")
        bits = int.from_bytes(head[1:5], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1, bool((bits >> 28) & 1)
    if "VP8 " in chunks:
        head = chunks["VP8 "]
        if len(head) < 10 or head[3:6] != b"\x9d\x01\x2a":
            raise ValueError("its VP8 chunk has no key frame")
        return (
            int.from_bytes(head[6:8], "little") & 0x3FFF,
            int.from_bytes(head[8:10], "little") & 0x3FFF,
            "ALPH" in chunks,
        )
    raise ValueError("no VP8 or VP8L chunk")


def _webp_vp8x(width: int, height: int, flags: int) -> bytes:
    return (
        bytes([flags, 0, 0, 0])
        + (width - 1).to_bytes(3, "little")
        + (height - 1).to_bytes(3, "little")
    )


def webp_bare(data: bytes) -> bytes:
    """Return a WebP file with its pixels' chunks only, their bytes unchanged: no XMP, EXIF or color
    profile.

    A lossless or opaque lossy picture becomes the simple format; a lossy one
    with alpha keeps a ``VP8X`` header that says only that.
    """
    chunks = [(name, body) for name, body in webp_chunks_of(data) if name in WEBP_IMAGE_CHUNKS]
    if any(name == "ALPH" for name, _ in chunks):
        width, height, _ = webp_image(data)
        chunks.insert(0, ("VP8X", _webp_vp8x(width, height, WEBP_FLAG_ALPHA)))
    return _webp_file(chunks)


def webp_stamp(data: bytes, meta: MediaMeta) -> bytes:
    """Return a WebP file in the extended format: a ``VP8X`` header, its pixels' chunks unchanged,
    then the record's XMP packet."""
    width, height, alpha = webp_image(data)
    pixels = [(name, body) for name, body in webp_chunks_of(data) if name in WEBP_IMAGE_CHUNKS]
    flags = WEBP_FLAG_XMP | (WEBP_FLAG_ALPHA if alpha else 0)
    return _webp_file(
        [("VP8X", _webp_vp8x(width, height, flags)), *pixels, ("XMP ", xmp_packet(meta))]
    )


def webp_size(data: bytes) -> tuple[int, int]:
    """Return a WebP picture's width and height."""
    width, height, _ = webp_image(data)
    return width, height


def webp_findings(name: str, data: bytes, meta: MediaMeta) -> list[str]:
    """Return how a WebP file's metadata differs from the record's: missing, different, misplaced or
    foreign."""
    try:
        chunks = webp_chunks_of(data)
        width, height, _ = webp_image(data)
    except ValueError as error:
        return [f"{name}: M006: not a well-formed WebP file ({error})"]
    found = []
    names = [chunk for chunk, _ in chunks]
    foreign = sorted(
        {chunk.strip() for chunk in names if chunk not in WEBP_IMAGE_CHUNKS | {"VP8X", "XMP "}}
    )
    if foreign:
        found.append(
            f"{name}: M005: holds {', '.join(foreign)}; a published WebP file holds its pixels and "
            "the profile's XMP only"
        )
    profile = profile_for((width, height))
    if profile != meta.profile:
        found.append(
            f"{name}: M009: a {width} x {height} picture carries the {profile} profile, not the "
            f"{meta.profile} one"
        )
    packets = [body for chunk, body in chunks if chunk == "XMP "]
    if not packets:
        return [*found, f"{name}: M001: carries no XMP; run tools/build.py"]
    if packets != [xmp_packet(meta)]:
        found.append(f"{name}: M002: its XMP is not what its record gives")
    if not found and data != webp_stamp(data, meta):
        found.append(
            f"{name}: M006: its chunks are not VP8X, the pixels' chunks and XMP, in that order, "
            "with the flags they need"
        )
    return found


# --- SVG -----------------------------------------------------------------------------------

SVG_IGNORE_START = "<!-- REUSE-IgnoreStart -->"
SVG_IGNORE_END = "<!-- REUSE-IgnoreEnd -->"


def svg_block(meta: MediaMeta, slug: str) -> str:
    """Return what a published SVG holds first: its title, its description and its metadata, two
    spaces in."""
    es = meta.language == "es"

    def plain_or_alt(name: str, english: str, spanish: str | None) -> str:
        if es:
            return f"<dc:{name}>{_alt(english, spanish)}</dc:{name}>"
        return f"<dc:{name}>{escape(english)}</dc:{name}>"

    bag = "".join(f"<rdf:li>{escape(keyword)}</rdf:li>" for keyword in meta.keywords)
    rows = [
        f'  <title id="{slug}-t">{escape(meta.visible("title"))}</title>',
        f'  <desc id="{slug}-d">{escape(meta.visible("description"))}</desc>',
        f"  {SVG_IGNORE_START}",
        f'  <metadata id="{slug}-m">',
        '    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"',
        f"             {NAMESPACES['dc']}",
        f"             {NAMESPACES['cc']}",
        f"             {NAMESPACES['Iptc4xmpExt']}>",
        '      <cc:Work rdf:about="">',
        "        <dc:format>image/svg+xml</dc:format>",
        '        <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>',
        f"        {plain_or_alt('title', meta.title, meta.title_es)}",
        f"        {plain_or_alt('description', meta.description, meta.description_es)}",
        "        "
        f"<dc:creator><cc:Agent><dc:title>{escape(CREATOR)}</dc:title></cc:Agent></dc:creator>",
        "        "
        f"<dc:publisher><cc:Agent><dc:title>{escape(PROJECT)}</dc:title></cc:Agent></dc:publisher>",
        "        "
        f"<dc:rights><cc:Agent><dc:title>{escape(meta.copyright)}</dc:title></cc:Agent></dc:rights>",
        f"        <dc:identifier>{escape(meta.identifier_url)}</dc:identifier>",
    ]
    if meta.source_url:
        rows.append(f"        <dc:source>{escape(meta.source_url)}</dc:source>")
    rows += [
        f"        <dc:language>{meta.language}</dc:language>",
        f"        <dc:subject><rdf:Bag>{bag}</rdf:Bag></dc:subject>",
        "        <Iptc4xmpExt:DigitalSourceType "
        'rdf:resource="http://cv.iptc.org/newscodes/digitalsourcetype/'
        f'{meta.digital_source_type}"/>',
        f'        <cc:license rdf:resource="{escape(meta.web_statement)}"/>',
        "      </cc:Work>",
        "    </rdf:RDF>",
        "  </metadata>",
        f"  {SVG_IGNORE_END}",
    ]
    return "\n".join(rows)


ROOT_TAG = re.compile(r"<svg\b[^<>]*>")
ROOT_ACCESS = re.compile(r'\s(?:role|aria-labelledby|lang)="[^"]*"')
LEADING_TITLE = re.compile(r"\A\s*<title\b[^>]*>.*?</title>", re.S)
LEADING_DESC = re.compile(r"\A\s*<desc\b[^>]*>.*?</desc>", re.S)
LEADING_METADATA = re.compile(
    r"\A\s*" + re.escape(SVG_IGNORE_START) + r".*?" + re.escape(SVG_IGNORE_END), re.S
)
LEADING_BARE_METADATA = re.compile(r"\A\s*<metadata\b.*?</metadata>", re.S)


def svg_slug(stem: str) -> str:
    """Return the id prefix of a file's title, description and metadata: unique to the file, safe in
    an id."""
    return "kl-" + re.sub(r"[^a-z0-9-]+", "-", stem.lower()).strip("-")


def svg_stamp(svg: str, meta: MediaMeta, slug: str) -> str:
    """Return *svg* with the record's root attributes and block, in place of any title, description
    or metadata it opened with."""
    match = ROOT_TAG.search(svg)
    if match is None:
        raise ValueError("no <svg> root")
    head, tag, rest = svg[: match.start()], match.group(0), svg[match.end() :]
    tag = ROOT_ACCESS.sub("", tag)
    tag = tag[:-1] + f' role="img" aria-labelledby="{slug}-t {slug}-d" lang="{meta.language}">'
    for pattern in (LEADING_TITLE, LEADING_DESC, LEADING_METADATA, LEADING_BARE_METADATA):
        rest = pattern.sub("", rest, count=1)
    return head + tag + "\n" + svg_block(meta, slug) + rest


def svg_findings(name: str, svg: str, meta: MediaMeta, slug: str) -> list[str]:
    """Return how a published SVG's metadata differs from the record's."""
    if svg == svg_stamp(svg, meta, slug):
        return []
    found = []
    if "<metadata" in svg and not (SVG_IGNORE_START in svg and SVG_IGNORE_END in svg):
        found.append(
            f"{name}: M011: its metadata stands outside REUSE-IgnoreStart and REUSE-IgnoreEnd"
        )
    if "<metadata" not in svg or "<desc" not in svg:
        found.append(f"{name}: M001: lacks its <desc> or its <metadata>; run tools/build.py")
    if not found:
        found.append(
            f"{name}: M002: its title, description, metadata or root attributes are not what its "
            "record gives"
        )
    return found


# --- REUSE ---------------------------------------------------------------------------------

# REUSE-IgnoreStart
IN_FILE_LICENSE = re.compile(r"SPDX-License-Identifier:(.*)")
IN_FILE_COPYRIGHT = re.compile(r"SPDX-FileCopyrightText:(.*)")
# REUSE-IgnoreEnd
IGNORE_MARKERS = ("REUSE-IgnoreStart", "REUSE-IgnoreEnd")
TEXT_SUFFIXES = frozenset(
    {
        ".svg",
        ".md",
        ".txt",
        ".json",
        ".py",
        ".toml",
        ".yml",
        ".yaml",
        ".css",
        ".obj",
        ".mtl",
        ".vtt",
    }
)


def _glob(pattern: str) -> re.Pattern[str]:
    out, index = "", 0
    while index < len(pattern):
        char = pattern[index]
        if pattern.startswith("**", index):
            out += ".*"
            index += 2
        elif char == "*":
            out += "[^/]*"
            index += 1
        elif char == "\\" and index + 1 < len(pattern):
            out += re.escape(pattern[index + 1])
            index += 2
        else:
            out += re.escape(char)
            index += 1
    return re.compile(out)


def block_spans(text: str, opener: str, closer: str) -> Iterator[tuple[int, int]]:
    """Yield where each block of *text* starts and stops: from an *opener* to the *closer* that
    follows it. An opener with no closer opens nothing."""
    stop = 0
    while (start := text.find(opener, stop)) >= 0:
        closed = text.find(closer, start + len(opener))
        if closed < 0:
            return
        stop = closed + len(closer)
        yield start, stop


def replace_blocks(text: str, opener: str, closer: str, replacement: str = "") -> str:
    """Return *text* with *replacement* in place of each of its blocks (:func:`block_spans`)."""
    kept, at = [], 0
    for start, stop in block_spans(text, opener, closer):
        kept += [text[at:start], replacement]
        at = stop
    return "".join([*kept, text[at:]])


def without_ignore_blocks(text: str) -> str:
    """Return *text* without what REUSE is told to ignore in it."""
    return replace_blocks(text, *IGNORE_MARKERS)


def _tag_values(tag: re.Pattern[str], text: str) -> list[str]:
    """Return what the lines of *text* state under *tag*, without the comment's closing mark."""
    values = []
    for line in tag.findall(text):
        value = line.strip()
        closing = next((mark for mark in ("-->", "*/") if value.endswith(mark)), "")
        value = value.removesuffix(closing).strip()
        if value:
            values.append(value)
    return values


def _as_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def reuse_truth(root: Path, path: str | Path, strip: bool = True) -> tuple[str, tuple[str, ...]]:
    """Return a file's license expression and copyright holders as REUSE 3.3 reads them.

    The file's own tags (outside ignore blocks) and the matching ``REUSE.toml``
    annotations, under their precedence: ``closest`` (the file's tags when it
    has them), ``aggregate`` (both) and ``override`` (the annotation alone);
    the last matching annotation wins. Holders lose their ``<address>`` unless
    *strip* is false.
    """
    name = Path(path).as_posix()
    licenses: list[str] = []
    holders: list[str] = []
    file = root / name
    if file.suffix.lower() in TEXT_SUFFIXES and file.is_file():
        text = without_ignore_blocks(file.read_text(encoding="utf-8", errors="replace"))
        licenses = _tag_values(IN_FILE_LICENSE, text)
        holders = _tag_values(IN_FILE_COPYRIGHT, text)
    chosen = None
    toml = root / "REUSE.toml"
    if toml.is_file():
        for annotation in tomllib.loads(toml.read_text(encoding="utf-8")).get("annotations", []):
            if any(_glob(pattern).fullmatch(name) for pattern in _as_list(annotation.get("path"))):
                chosen = annotation
    if chosen is not None:
        precedence = chosen.get("precedence", "closest")
        theirs_l = _as_list(chosen.get("SPDX-License-Identifier"))
        theirs_c = _as_list(chosen.get("SPDX-FileCopyrightText"))
        if precedence == "override" or (precedence == "closest" and not licenses and not holders):
            licenses, holders = theirs_l, theirs_c
        elif precedence == "aggregate":
            licenses, holders = licenses + theirs_l, holders + theirs_c
        elif precedence == "closest":
            licenses = licenses or theirs_l
            holders = holders or theirs_c
    licenses = list(dict.fromkeys(licenses))
    expression = " AND ".join(
        f"({item})" if " OR " in item and len(licenses) > 1 else item for item in licenses
    )
    cleaned = [strip_email(holder) if strip else holder for holder in holders]
    return expression, tuple(dict.fromkeys(cleaned))


# --- The deny-list -------------------------------------------------------------------------

DENY = (
    (
        "an e-mail address",
        re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ),
    (
        "a local path",
        re.compile(
            r"/Users/|/home/|/private/|/var/folders/|/tmp/|/Volumes/|file://|~/|[A-Za-z]:\\|\\Users\\"
        ),
    ),
    (
        "a private host or address",
        re.compile(
            r"\.local\b|\.lan\b|\.home\b|\blocalhost\b|\b192\.168\.\d+\.\d+\b|\b10\.\d+\.\d+\.\d+\b"
            r"|\b172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+\b|\bMacBook|\biMac\b|-mbp\b"
        ),
    ),
    ("a machine's time", re.compile(r"\d{4}[-:]\d{2}[-:]\d{2}[ T]\d{2}:\d{2}")),
    (
        "a tool's name or version",
        re.compile(
            r"\bLavf\d|\bLavc\d|x264 - "
            r"core|\blibx264\b|\bImageMagick\b|\bGIMP\b|\bInkscape\b|sodipodi:"
            r"|\bIllustrator\b|\bPillow\b|\bHeadlessChrome\b|Eeschema-SVG|Image::ExifTool"
        ),
    ),
)
#: The file of identity patterns kept out of the tree, one per line, beside the tools.
DENY_LOCAL = Path(__file__).resolve().parents[1] / "deny-local.txt"
DENY_ENV = "KLEIDOS_DENY_EXTRA"
#: Set to 1 by CI when the secret is not available (a fork, Dependabot, or not set yet): identity is
#: then warned about, not refused.
DENY_OPTIONAL_ENV = "KLEIDOS_DENY_OPTIONAL"


def identity_patterns() -> tuple[list[re.Pattern[str]], str]:
    """Return the identity patterns and where they came from: the environment, the local file, or
    nowhere."""
    raw = os.environ.get(DENY_ENV, "")
    source = "environment"
    if not raw.strip() and DENY_LOCAL.is_file():
        raw, source = DENY_LOCAL.read_text(encoding="utf-8"), "file"
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        return [], "missing"
    return [re.compile(line, re.I) for line in lines], source


def deny_findings(
    name: str, values: list[str], identity: list[re.Pattern[str]] | None = None
) -> list[str]:
    """Return every value that holds what the deny-list refuses, naming the class (and never an
    identity match)."""
    found = []
    for value in values:
        for what, pattern in DENY:
            match = pattern.search(value)
            if match:
                found.append(f"{name}: M004: a metadata value holds {what} ({match.group(0)[:40]})")
        found.extend(
            f"{name}: M004: a metadata value holds an identity pattern of the private deny-list"
            for pattern in identity or ()
            if pattern.search(value)
        )
    return sorted(set(found))


def matches(path: str, patterns: tuple[str, ...]) -> bool:
    """Tell whether a repository path matches one of the shell patterns (``**`` crossing
    folders)."""
    return any(
        fnmatch.fnmatchcase(path, pattern) or _glob(pattern).fullmatch(path) for pattern in patterns
    )
