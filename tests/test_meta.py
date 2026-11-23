# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The metadata profile (``kleidos_brand.meta``): golden bytes, limits, the short profile, Spanish,
REUSE.

The files under ``tests/fixtures/meta/`` are the profile's bytes for two fixed
records. Every repository that keeps a copy of the module reproduces them;
when the profile changes, they change everywhere at once, with
``META_PROFILE``. Write them again with ``KLEIDOS_WRITE_META_FIXTURES=1``.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

import build
import pytest

from kleidos_brand import meta, xmlsafe

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/meta"

#: A full record, in Spanish, with a credit, the trademark notes and the extra terms: every slot
#: written.
FULL = meta.MediaMeta(
    title="Kleidos press image: a fixture, 16:9",
    description="A fixture: the record every copy of the module turns into the same bytes. It "
    'holds <, > & ".',
    alt="A fixture for the golden files",
    keywords=(*meta.BASE_KEYWORDS, "fixture", "M5Stack", "LILYGO"),
    digital_source_type="composite",
    spdx="GPL-3.0-or-later AND MIT",
    own_license="GPL-3.0-or-later",
    holders=("2026 José M. Requena Plens", "2021 M5Stack"),
    identifier_url=meta.identifier_url("brand", "tests/fixtures/meta/full.png"),
    rights_url=meta.RIGHTS_URLS["brand"],
    credits=("A credit sentence.",),
    trademarks=(meta.TRADEMARK_NOTE_M5, meta.TRADEMARK_NOTE_LILYGO, meta.TRADEMARK_NOTE_KLEIDOS),
    extra_terms=(meta.extra_terms("brand"),),
    source_url=meta.identifier_url("brand", "tests/fixtures/meta/full.svg"),
    language="es",
    title_es="Imagen de prensa de Kleidos: un ejemplo, 16:9",
    description_es="Un ejemplo: el registro que cada copia del módulo convierte en los mismos "
    "bytes.",
    alt_es="Un ejemplo para los archivos de referencia",
    spanish={"A credit sentence.": "Una frase de crédito."},
)

#: A short record: what a picture under 64 px carries.
SHORT = meta.MediaMeta(
    title="Kleidos small mark, in color, 19 px",
    description="The Kleidos logo: the small mark.",
    alt="The Kleidos mark",
    keywords=meta.BASE_KEYWORDS,
    digital_source_type="digitalCreation",
    spdx="GPL-3.0-or-later",
    own_license="GPL-3.0-or-later",
    holders=("2026 José M. Requena Plens",),
    identifier_url=meta.identifier_url("brand", "tests/fixtures/meta/short.png"),
    rights_url=meta.RIGHTS_URLS["brand"],
    profile="short",
)


def bare_png(size: tuple[int, int]) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, (12, 15, 19)).save(buffer, "PNG")
    return buffer.getvalue()


def bare_jpeg() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), (200, 120, 40)).save(buffer, "JPEG", quality=88)
    return buffer.getvalue()


def png_chunks_bytes(record: meta.MediaMeta) -> bytes:
    return b"".join(meta._chunk(name, body) for name, body in meta.png_chunks(record))


GOLDEN = {
    "full.xmp": lambda: meta.xmp_packet(FULL),
    "short.xmp": lambda: meta.xmp_packet(SHORT),
    "full.png-chunks": lambda: png_chunks_bytes(FULL),
    "short.png-chunks": lambda: png_chunks_bytes(SHORT),
    "full.jpeg-segments": lambda: b"".join(meta.jpeg_segments(FULL)),
    "full.svg-block": lambda: meta.svg_block(FULL, "kl-fixture").encode("utf-8"),
}


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_the_profile_writes_its_golden_bytes(name: str) -> None:
    data = GOLDEN[name]()
    if os.environ.get("KLEIDOS_WRITE_META_FIXTURES") == "1":
        FIXTURES.mkdir(parents=True, exist_ok=True)
        (FIXTURES / name).write_bytes(data)
    assert (FIXTURES / name).read_bytes() == data, (
        f"{name}: the profile's bytes changed; bump META_PROFILE in every repository"
    )


def test_the_packet_is_deterministic_unpadded_and_escaped() -> None:
    packet = meta.xmp_packet(FULL).decode("utf-8")
    assert packet == meta.xmp_packet(FULL).decode("utf-8")
    assert packet.startswith(
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    ) and packet.endswith('<?xpacket end="r"?>')
    assert (
        "xmptk" not in packet
        and "CreatorTool" not in packet
        and "xmpMM" not in packet
        and "  \n" not in packet
    )
    assert "&lt;, &gt; &amp; &quot;." in packet
    assert '<rdf:li xml:lang="es">Imagen de prensa de Kleidos: un ejemplo, 16:9</rdf:li>' in packet
    assert "<dc:language><rdf:Bag><rdf:li>es</rdf:li></rdf:Bag></dc:language>" in packet
    assert "Una frase de crédito." in packet and "no está afiliado a M5Stack" in packet
    assert (
        '<dc:rights><rdf:Alt><rdf:li xml:lang="x-default">© 2026 José M. Requena Plens; © 2021 '
        "M5Stack. GPL-3.0-or-later AND MIT.</rdf:li>" in packet
    )
    assert (
        packet.count("https://spdx.org/licenses/GPL-3.0-or-later.html") == 4
    )  # WebStatement, UsageTerms in English and Spanish, cc:license
    assert "https://spdx.org/licenses/MIT.html" in packet


def test_the_short_profile_carries_only_its_fields() -> None:
    packet = meta.xmp_packet(SHORT).decode("utf-8")
    for absent in (
        "dc:description",
        "dc:subject",
        "photoshop",
        "Iptc4xmpCore",
        "plus:",
        "UsageTerms",
    ):
        assert absent not in packet, absent
    for present in (
        "dc:title",
        "dc:creator",
        "dc:rights",
        "dc:identifier",
        "xmpRights:Marked",
        "xmpRights:WebStatement",
        "cc:license",
        "Iptc4xmpExt:DigitalSourceType",
    ):
        assert present in packet, present
    assert [keyword for keyword, _ in meta.png_text_items(SHORT)] == ["Copyright", "License"]
    assert meta.profile_for((19, 19)) == "short" and meta.profile_for((64, 10)) == "full"


def test_a_stamp_keeps_the_pixels_chunks_and_goes_before_the_first_idat() -> None:
    data = bare_png((80, 40))
    record = meta.MediaMeta(**{**SHORT.__dict__, "profile": "full", "spanish": {}})
    stamped = meta.png_stamp(data, record)
    names = [name for name, _ in meta.png_chunks_of(stamped)]
    assert names[:2] == ["IHDR", "tEXt"] and names.index("iTXt") == names.index("IDAT") - 1
    assert meta.png_bare(stamped) == data
    assert meta.png_stamp(stamped, record) == stamped, "stamping twice changes nothing"
    assert meta.png_findings("x.png", stamped, record) == []
    assert any(
        "M009" in line
        for line in meta.png_findings("x.png", meta.png_stamp(bare_png((19, 19)), record), record)
    )


def test_a_jpeg_stamp_keeps_every_byte_from_the_first_table() -> None:
    data = bare_jpeg()
    stamped = meta.jpeg_stamp(data, FULL)
    tables = data.index(b"\xff\xdb")
    assert stamped[stamped.index(b"\xff\xdb") :] == data[tables:]
    assert meta.jpeg_bare(stamped) == data
    assert meta.jpeg_findings("x.jpg", stamped, FULL) == []
    segments, _ = meta._jpeg_head(stamped)
    assert [marker for marker, _ in segments] == [0xE0, 0xE1, 0xED]


def bare_webp(lossless: bool, alpha: bool) -> bytes:
    from PIL import Image

    image = Image.new(
        "RGBA" if alpha else "RGB", (80, 40), (0, 210, 255, 128) if alpha else (12, 15, 19)
    )
    buffer = io.BytesIO()
    image.save(
        buffer, "WEBP", lossless=lossless, quality=90, method=6, exif=b"Exif\x00\x00MM", xmp=b"<x/>"
    )
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("lossless", "alpha"), [(True, True), (True, False), (False, True), (False, False)]
)
def test_a_webp_stamp_keeps_the_pixels_chunks_and_ends_with_the_packet(
    lossless: bool, alpha: bool
) -> None:
    record = meta.MediaMeta(**{**SHORT.__dict__, "profile": "full", "spanish": {}})
    carried = bare_webp(lossless, alpha)
    assert {"EXIF", "XMP "} <= {name for name, _ in meta.webp_chunks_of(carried)}, (
        "Pillow wrote what the stamp must drop"
    )
    stamped = meta.webp_stamp(carried, record)
    chunks = meta.webp_chunks_of(stamped)
    names = [name for name, _ in chunks]
    assert names[0] == "VP8X" and names[-1] == "XMP " and set(names[1:-1]) <= meta.WEBP_IMAGE_CHUNKS
    assert names.count("XMP ") == 1 and "EXIF" not in names and "ICCP" not in names
    flags = chunks[0][1][0]
    assert flags & meta.WEBP_FLAG_XMP and bool(flags & meta.WEBP_FLAG_ALPHA) is alpha
    assert chunks[-1][1] == meta.xmp_packet(record)
    pixels = [chunk for chunk in meta.webp_chunks_of(carried) if chunk[0] in meta.WEBP_IMAGE_CHUNKS]
    assert [chunk for chunk in chunks if chunk[0] in meta.WEBP_IMAGE_CHUNKS] == pixels, (
        "the pixels' bytes are kept"
    )
    assert meta.webp_stamp(stamped, record) == stamped, "stamping twice changes nothing"
    assert meta.webp_stamp(meta.webp_bare(stamped), record) == stamped
    assert meta.webp_size(stamped) == (80, 40)
    assert meta.webp_findings("x.webp", stamped, record) == []
    assert any("M005" in line for line in meta.webp_findings("x.webp", carried, record)), (
        "EXIF is refused"
    )
    assert any(
        "M001" in line for line in meta.webp_findings("x.webp", meta.webp_bare(stamped), record)
    )
    other = meta.MediaMeta(**{**record.__dict__, "title": "Another title"})
    assert any("M002" in line for line in meta.webp_findings("x.webp", stamped, other))
    from PIL import Image

    with Image.open(io.BytesIO(stamped)) as opened:
        assert opened.size == (80, 40) and (opened.mode == "RGBA") is alpha


def test_a_malformed_webp_is_reported_not_raised() -> None:
    record = meta.MediaMeta(**{**SHORT.__dict__, "profile": "full", "spanish": {}})
    stamped = meta.webp_stamp(bare_webp(True, False), record)
    assert any("M006" in line for line in meta.webp_findings("x.webp", stamped[:-3], record))
    assert any(
        "M006" in line for line in meta.webp_findings("x.webp", b"RIFF\x04\x00\x00\x00WEBQ", record)
    )


def test_the_limits_refuse_a_record_and_never_cut_it() -> None:
    with pytest.raises(ValueError, match="over 64 bytes"):
        meta.MediaMeta(**{**SHORT.__dict__, "title": "x" * 65})
    with pytest.raises(ValueError, match="over 128 bytes"):
        meta.MediaMeta(**{**SHORT.__dict__, "holders": ("2026 " + "y" * 130,)})
    with pytest.raises(ValueError, match="Latin-1"):
        meta.MediaMeta(**{**SHORT.__dict__, "title": "Kleidos — a dash"})
    with pytest.raises(ValueError, match="not in the expression"):
        meta.MediaMeta(**{**SHORT.__dict__, "own_license": "MIT"})
    with pytest.raises(ValueError, match="digital source type"):
        meta.MediaMeta(**{**SHORT.__dict__, "digital_source_type": "digitalArt"})
    with pytest.raises(ValueError, match="lacks a Spanish"):
        meta.MediaMeta(**{**SHORT.__dict__, "language": "es"})
    with pytest.raises(ValueError, match="IIM 2:80"):
        meta._iim((2, 80), b"z" * 33)
    with pytest.raises(ValueError, match="no public repository"):
        meta.license_url("LicenseRef-Kleidos-Brand-Marks", "firmware")


def test_the_svg_block_sits_inside_the_reuse_markers() -> None:
    block = meta.svg_block(FULL, "kl-fixture")
    start, end = block.index(meta.SVG_IGNORE_START), block.index(meta.SVG_IGNORE_END)
    assert start < block.index("<metadata") < block.index("</metadata>") < end
    assert block.index("©") > start
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><title>old</title><rect '
        'width="10" height="10"/></svg>'
    )
    stamped = meta.svg_stamp(svg, FULL, "kl-fixture")
    assert (
        'role="img" aria-labelledby="kl-fixture-t kl-fixture-d" lang="es">' in stamped
        and "<title>old</title>" not in stamped
    )
    assert meta.svg_stamp(stamped, FULL, "kl-fixture") == stamped
    assert stamped.endswith('<rect width="10" height="10"/></svg>')


def test_the_deny_list_names_each_class() -> None:
    home = "/Us" + "ers/someone/x"
    found = meta.deny_findings(
        "x",
        [
            home,
            "someone" + "@" + "example.org",
            "2026-11-19T01:02",
            "made in GIMP",
            "192." + "168.0.1",
        ],
    )
    for what in (
        "a local path",
        "an e-mail address",
        "a machine's time",
        "a tool's name",
        "a private host",
    ):
        assert any(what in line for line in found), what
    assert meta.deny_findings("x", meta.xmp_values(FULL)) == []
    assert (
        meta.strip_email("2026 José M. Requena Plens <someone" + "@" + "example.org>")
        == "2026 José M. Requena Plens"
    )


def test_an_identifier_stands_between_the_operators_of_its_expression() -> None:
    assert meta.spdx_ids("MIT") == ["MIT"]
    assert meta.spdx_ids("GPL-3.0-or-later  AND\t(MIT OR Apache-2.0 WITH LLVM-exception)") == [
        "GPL-3.0-or-later",
        "MIT",
        "Apache-2.0",
        "LLVM-exception",
    ]
    assert meta.spdx_ids("MIT. More words") == ["MIT. More words"], "no license, and kept as it is"


def test_an_address_is_left_out_wherever_it_stands() -> None:
    assert meta.strip_email("2026 One <one> and Two  <two>") == "2026 One and Two"
    assert meta.strip_email("2026 One <not closed") == "2026 One <not closed"
    assert meta.strip_email("2026 One > Two") == "2026 One > Two"


# REUSE-IgnoreStart
def test_a_file_s_own_tags_are_read_without_the_comment_s_closing_mark(tmp_path: Path) -> None:
    (tmp_path / "page.md").write_text(
        "<!-- SPDX-FileCopyrightText: 2026 One -->\n"
        "/* SPDX-FileCopyrightText: 2021 Two */\n"
        "# SPDX-License-Identifier: \n"
        "SPDX-License-Identifier:\tMIT  -->  \n",
        encoding="utf-8",
    )
    assert meta.reuse_truth(tmp_path, "page.md") == ("MIT", ("2026 One", "2021 Two"))


# REUSE-IgnoreEnd


@pytest.mark.parametrize(
    ("text", "read"),
    [
        ("a[b]c", "a-c"),
        ("[a][b] c", "-- c"),
        ("a[b[c]d]e", "a-d]e"),
        ("a]b[c", "a]b[c"),
        ("a[b]c[d", "a-c[d"),
        ("", ""),
    ],
)
def test_a_block_is_what_stands_from_an_opener_to_the_next_closer(text: str, read: str) -> None:
    assert meta.replace_blocks(text, "[", "]", "-") == read


def test_a_block_s_closer_stands_after_its_whole_opener() -> None:
    assert meta.replace_blocks("a /*/ b */ c", "/*", "*/") == "a  c"


def test_a_tag_inside_an_ignore_block_is_not_the_file_s(tmp_path: Path) -> None:
    tag, start, end = (
        "SPDX-License-" + "Identifier",
        "REUSE-Ignore" + "Start",
        "REUSE-Ignore" + "End",
    )
    page = f"{tag}: MIT\n<!-- {start} -->\n{tag}: X\n<!-- {end} -->\n{tag}: Y\n{start}\n{tag}: Z\n"
    (tmp_path / "page.md").write_text(page, encoding="utf-8")
    assert meta.reuse_truth(tmp_path, "page.md") == ("MIT AND Y AND Z", ())


def own_tags(root: Path, tag: str) -> tuple[str, tuple[str, ...]]:
    (root / "page.md").write_text(f"{tag}: x" + " " * 2_000 + "y\n", encoding="utf-8")
    return meta.reuse_truth(root, "page.md")


def unclosed_blocks(root: Path) -> tuple[str, tuple[str, ...]]:
    (root / "page.md").write_text(("REUSE-Ignore" + "Start") * 10_000, encoding="utf-8")
    return meta.reuse_truth(root, "page.md")


@pytest.mark.parametrize(
    "read",
    [
        lambda root: meta.spdx_ids("MIT" + " " * 40_000 + "x"),
        lambda root: meta.strip_email("a" + " " * 40_000 + "b"),
        lambda root: meta.strip_email("<" * 40_000),
        lambda root: meta.strip_email("<>" * 40_000 + "a"),
        lambda root: own_tags(root, "SPDX-License-" + "Identifier"),
        lambda root: own_tags(root, "SPDX-FileCopyright" + "Text"),
        unclosed_blocks,
        lambda _: not meta.deny_findings("x", ["a." * 40_000]),
    ],
)
def test_a_hostile_text_is_read_in_linear_time(
    read: Callable[[Path], object], tmp_path: Path
) -> None:
    start = time.process_time()
    assert read(tmp_path)
    assert time.process_time() - start < 1


def test_a_drawing_whose_root_never_closes_is_refused_in_linear_time() -> None:
    start = time.process_time()
    with pytest.raises(ValueError, match="no <svg> root"):
        meta.svg_stamp("<svg " * 40_000, FULL, "x")
    assert time.process_time() - start < 1


def test_the_iim_digest_needs_no_security_use_of_md5(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Python built for FIPS refuses MD5 unless the caller says it is not for security."""

    def fips(data: bytes, *, usedforsecurity: bool = True) -> object:
        if usedforsecurity:
            raise ValueError("disabled for FIPS")
        return hashlib.new("md5", data, usedforsecurity=False)

    monkeypatch.setattr("hashlib.md5", fips)
    _, app13 = meta.jpeg_segments(FULL)
    digest = hashlib.new("md5", meta.iim_block(FULL), usedforsecurity=False).digest()
    assert app13.endswith(digest)


def test_the_vocabularies_are_named_as_they_publish_themselves() -> None:
    """A namespace is compared character by character, so its scheme is part of its name."""
    iptc = "http://iptc.org/std/Iptc4xmpExt/2008-02-29/"
    packet = xmlsafe.fromstring(meta.xmp_packet(FULL))
    used = {element.tag[1:].split("}")[0] for element in packet.iter()}
    assert used == {
        "adobe:ns:meta/",
        "http://creativecommons.org/ns#",
        "http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/",
        iptc,
        "http://ns.adobe.com/photoshop/1.0/",
        "http://ns.adobe.com/xap/1.0/rights/",
        "http://ns.useplus.org/ldf/xmp/1.0/",
        "http://purl.org/dc/elements/1.1/",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }
    block = xmlsafe.fromstring(f"<svg>{meta.svg_block(FULL, 'kl-x')}</svg>")
    kind = "http://cv.iptc.org/newscodes/digitalsourcetype/composite"

    def source_type(root: ET.Element) -> ET.Element:
        found = root.find(f".//{{{iptc}}}DigitalSourceType")
        assert found is not None
        return found

    assert source_type(packet).text == kind
    resource = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
    assert source_type(block).get(resource) == kind


def test_every_record_agrees_with_the_reuse_tool() -> None:
    """The small resolver against REUSE itself, for every published file, and the metadata adds no
    copyright line REUSE would read."""
    reuse = shutil.which("reuse") or str(Path(sys.executable).with_name("reuse"))
    if not Path(reuse).is_file():
        pytest.skip("the reuse tool is not installed")
    report = subprocess.run(
        [reuse, "--root", str(ROOT), "spdx"], capture_output=True, text=True, check=True
    ).stdout
    files: dict[str, tuple[list[str], list[str]]] = {}
    for block in report.split("\nFileName: ")[1:]:
        name = block.split("\n", 1)[0].removeprefix("./")
        licenses = re.findall(r"^LicenseInfoInFile: (.+)$", block, re.M)
        texts = re.findall(r"FileCopyrightText: <text>(.*?)</text>", block, re.S)
        holders = [
            line.strip().removeprefix("SPDX-FileCopyrightText:").strip()
            for text in texts
            for line in text.splitlines()
            if line.strip()
        ]
        files[name] = (licenses, holders)
    texts, pictures = build.collect(ROOT)
    records = {item.path.as_posix(): item.meta for item in texts if item.meta is not None} | {
        item.path.as_posix(): item.meta for item in pictures if item.meta is not None
    }
    assert records, "the builder makes records"
    for name, record in records.items():
        licenses, holders = files[name]
        assert meta.reuse_truth(ROOT, name) == (
            " AND ".join(dict.fromkeys(licenses)),
            tuple(dict.fromkeys(meta.strip_email(h) for h in holders)),
        ), name
        assert (record.spdx, record.holders) == meta.reuse_truth(ROOT, name), name


@pytest.mark.skipif(
    shutil.which("exiftool") is None, reason="exiftool is not installed (read-only cross-check)"
)
def test_exiftool_reads_the_profile_in_every_published_raster() -> None:
    import json

    _, pictures = build.collect(ROOT)
    paths = [item.path.as_posix() for item in pictures]
    rows = json.loads(
        subprocess.run(
            ["exiftool", "-j", "-G1", "-a", "-charset", "utf8", *paths],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    for row in rows:
        name = row["SourceFile"]
        for key in (
            "XMP-dc:Title",
            "XMP-dc:Creator",
            "XMP-dc:Rights",
            "XMP-xmpRights:WebStatement",
            "XMP-cc:License",
            "XMP-iptcExt:DigitalSourceType",
        ):
            assert key in row, f"{name}: exiftool does not see {key}"
        assert not any(
            key.split(":")[0] in ("IFD0", "ExifIFD", "GPS", "ICC_Profile") for key in row
        ), name
