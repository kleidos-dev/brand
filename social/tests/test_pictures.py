# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The pictures themselves: what was exported, drawn again, and the mark by itself."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import export
import pack
import records
from kleidos_brand import meta, png, raster

if TYPE_CHECKING:
    from kleidos_brand.raster import Browser

ROOT = Path(__file__).resolve().parents[1]

#: The pixels of the first social pack's images of the mark alone (SHA-256 of their RGBA bytes),
#: drawn from the firmware repository's copy of the mark before this repository existed. The port
#: draws the same pixels from brand.
FIRST_PACK = {
    "png/youtube/avatar.png": "0ad28dd1a37089ce87438521c69c88709b2220ac5cc146165ccd8c3f65fc840f",
    "png/makertube/avatar.png": "30a10e39d63bd690ece7864511045f5c078d38f05d3bbb448daff83e5f9cf229",
    "png/youtube/watermark.png": "d7e5f7f88637e902cbb67792903ec55e359221356060fd92dc0cdf83ab118de9",
}


def _pixels(path: Path) -> str:
    from PIL import Image

    with Image.open(path) as opened:
        return hashlib.sha256(opened.convert("RGBA").tobytes()).hexdigest()


def test_the_record_names_every_picture_and_the_brand_files_it_read() -> None:
    recorded = json.loads((ROOT / "exports.json").read_text(encoding="utf-8"))
    collected = export.collect(ROOT)
    assert set(recorded["files"]) == {picture.path.as_posix() for picture in collected.pictures}
    for name, entry in recorded["files"].items():
        for needed in pack.BRAND_INPUTS:
            assert (pack.BRAND / needed).as_posix() in entry["inputs"], name
        assert not any(key.startswith("/") for key in entry["inputs"])
    assert "commit" not in json.dumps(
        recorded
    )  # digests only: a commit's name would not survive a squashed history


def test_every_card_weighs_less_than_github_accepts() -> None:
    for row in pack.rows(pack.load(ROOT)):
        assert row.file is not None
        data = (ROOT / row.file).read_bytes()
        assert png.size(data) == (2560, 1280)
        assert len(data) < 1_000_000


def test_the_mark_alone_is_the_first_pack_s_pixel_for_pixel() -> None:
    for name, digest in FIRST_PACK.items():
        assert _pixels(ROOT / name) == digest, name


def _texts(path: Path) -> dict[str, str]:
    chunks = meta.png_chunks_of(path.read_bytes())
    return dict(body.decode("latin-1").split("\0", 1) for name, body in chunks if name == "tEXt")


def test_every_picture_says_what_it_is_who_made_it_and_under_which_license() -> None:
    for picture in export.collect(ROOT).pictures:
        if picture.kind == "banner":
            continue  # an SVG: its metadata block is held in tests/test_readme_banners.py
        data = (ROOT / picture.path).read_bytes()
        names = png.chunk_names(data)
        assert names.index("iTXt") < names.index("IDAT"), (
            picture.path
        )  # before the pixels, for a reader that streams
        texts = _texts(ROOT / picture.path)
        assert list(texts) == [
            "Title",
            "Author",
            "Description",
            "Copyright",
            "License",
            "Comment",
        ], picture.path
        assert texts["Author"] == "José M. Requena Plens"
        assert texts["Copyright"] == "© 2026 José M. Requena Plens. GPL-3.0-or-later."
        assert (
            texts["License"] == "GPL-3.0-or-later https://spdx.org/licenses/GPL-3.0-or-later.html"
        )
        assert texts["Comment"].endswith(
            f"https://github.com/kleidos-dev/social/blob/main/{picture.path.as_posix()}"
        )
        assert not {"tIME", "zTXt", "eXIf", "sRGB", "iCCP"} & set(names), (
            picture.path
        )  # no time, no EXIF, no new color tag
        packet = next(body for name, body in meta.png_chunks_of(data) if name == "iTXt").decode(
            "utf-8"
        )
        assert "digitalsourcetype/digitalCreation" in packet and "xmp:CreateDate" not in packet


def test_a_picture_of_the_boards_credits_them_and_names_their_makers_marks() -> None:
    def terms(name: str) -> str:
        data = (ROOT / name).read_bytes()
        return next(body for chunk, body in meta.png_chunks_of(data) if chunk == "iTXt").decode(
            "utf-8"
        )

    for name in ("png/youtube/banner.png", "png/github/boards.png", "previews/cards.png"):
        assert "kleidos-dev/boards front drawings" in terms(
            name
        ) and "LILYGO and T-Deck are trademarks" in terms(name), name
    for name in ("png/youtube/avatar.png", "png/github/brand.png"):
        assert "front drawings" not in terms(name) and "M5Stack" not in terms(name), name
    for name in ("png/youtube/avatar.png", "png/github/boards.png"):
        assert "Mona Sans" in terms(name) and "press permission" not in terms(name), name


def test_the_watermark_is_transparent_and_the_avatar_is_not() -> None:
    from PIL import Image

    with Image.open(ROOT / "png/youtube/watermark.png") as opened:
        corner, middle = opened.getpixel((2, 2)), opened.getpixel((300, 300))
        assert isinstance(corner, tuple) and isinstance(middle, tuple)
        assert opened.mode == "RGBA" and corner[3] == 0 and middle[3] == 255
    with Image.open(ROOT / "png/youtube/avatar.png") as opened:
        assert opened.mode == "RGB"


@pytest.mark.browser
def test_every_picture_drawn_again_is_the_committed_one(chromium: Browser) -> None:
    recorded = json.loads((ROOT / "exports.json").read_text(encoding="utf-8"))
    if chromium.version != recorded["chromium"]:
        assert export.drawn_findings(ROOT, tolerant=True, browser=chromium) == []
        pytest.skip(
            f"exact pixels are compared under Chromium {recorded['chromium']}; this is"
            f" {chromium.version}"
        )
    assert export.drawn_findings(ROOT, browser=chromium) == []


@pytest.mark.browser
def test_a_mark_alone_one_pixel_off_is_caught(chromium: Browser, tree: Path) -> None:
    from PIL import Image

    recorded = json.loads((ROOT / "exports.json").read_text(encoding="utf-8"))
    if chromium.version != recorded["chromium"]:
        pytest.skip("exact pixels are compared under the recorded Chromium only")
    path = tree / "png/youtube/avatar.png"
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    image.putpixel((400, 400), (255, 255, 255))
    path.write_bytes(png.encode(image))
    found = export.drawn_findings(
        tree, only=frozenset({"png/youtube/avatar.png"}), browser=chromium
    )
    assert any(
        "is not brand's mark drawn by itself: it differs in 1 pixels" in line for line in found
    )
    assert any("drawn again, it differs in 1 pixels" in line for line in found)


@pytest.mark.browser
def test_a_mark_that_is_not_brand_s_is_caught_even_when_the_export_matches_its_source(
    chromium: Browser, tree_with_brand: Path
) -> None:
    recorded = json.loads((ROOT / "exports.json").read_text(encoding="utf-8"))
    if chromium.version != recorded["chromium"]:
        pytest.skip("exact pixels are compared under the recorded Chromium only")
    # Brand's mark changes; this repository's source still holds the old shapes, and so does its
    # export.
    mark = tree_with_brand / "brand/logo/src/mark.svg"
    mark.write_text(mark.read_text(encoding="utf-8").replace('r="42"', 'r="40"'), encoding="utf-8")
    found = export.drawn_findings(
        tree_with_brand, only=frozenset({"png/youtube/watermark.png"}), browser=chromium
    )
    assert any(
        "png/youtube/watermark.png: is not brand's mark drawn by itself" in line for line in found
    )


@pytest.mark.browser
def test_a_video_s_thumbnail_is_drawn_from_the_template(chromium: Browser) -> None:
    from PIL import Image

    data = export.thumbnail(
        ROOT, ["One sign-in,", "uncut"], ROOT / "png/youtube/avatar.png", chromium
    )
    assert png.size(data) == (3840, 2160)
    assert len(data) < pack.limit(pack.load(ROOT), "youtube-thumbnail")
    assert (
        png.findings("thumbnail", data, meta=records.thumbnail(ROOT, ["One sign-in,", "uncut"]))
        == []
    )
    with Image.open(io.BytesIO(data)) as opened:
        assert opened.convert("RGB").getpixel((2933, 1020)) != (
            10,
            12,
            15,
        )  # the picture, in its room


@pytest.mark.browser
def test_a_title_that_does_not_fit_is_refused(chromium: Browser) -> None:
    with pytest.raises(ValueError, match="reaches outside the safe area"):
        export.thumbnail(
            ROOT,
            ["A line that is much too long to fit on a thumbnail at this size"],
            None,
            chromium,
        )
    with pytest.raises(ValueError, match="one to 3 lines"):
        export.thumbnail(ROOT, ["a", "b", "c", "d"], None, chromium)


def test_a_one_off_is_named_for_its_title_and_kept_out_of_the_pack() -> None:
    assert export.slug(["One sign-in,", "uncut"]) == "one-sign-in-uncut"
    assert "/dist/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


class NoBrowser:
    """A browser that draws nothing: it only counts how often one was opened."""

    opened = 0

    def __enter__(self) -> NoBrowser:
        type(self).opened += 1
        return self

    def __exit__(self, *_: object) -> None:
        pass


@pytest.fixture
def one_off_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return an empty tree the exporter writes its one-offs to, the working folder; the pictures
    themselves are stand-ins, drawn by no browser."""
    root = tmp_path / "social"
    (root / "png").mkdir(parents=True)
    monkeypatch.chdir(root)
    monkeypatch.setattr(export, "ROOT", root)
    monkeypatch.setattr(raster, "Browser", NoBrowser)
    monkeypatch.setattr(NoBrowser, "opened", 0)
    monkeypatch.setattr(export, "thumbnail", lambda *_: b"a picture")
    return root


def _files(folder: Path) -> list[str]:
    """Return every file under *folder*, what a link leads to left out."""
    return sorted(
        path.relative_to(folder).as_posix()
        for path in folder.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


@pytest.mark.parametrize(
    ("out", "written"),
    [
        ([], "dist/uncut.png"),
        (["--out", "dist"], "dist/uncut.png"),
        (["--out", "dist/video/one"], "dist/video/one/uncut.png"),
        (["--out", "png/../dist/video"], "dist/video/uncut.png"),
    ],
)
def test_a_one_off_is_written_to_its_folder(
    one_off_tree: Path, out: list[str], written: str
) -> None:
    assert export.main(["--title", "Uncut", *out]) == 0
    assert _files(one_off_tree) == [written]
    assert (one_off_tree / written).read_bytes() == b"a picture"


def test_the_one_offs_folder_is_the_repository_s_wherever_the_exporter_runs(
    one_off_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(one_off_tree / "png")
    assert export.main(["--title", "Uncut"]) == 0
    assert export.main(["--title", "Uncut", "--out", "../dist/video"]) == 0
    assert _files(one_off_tree) == ["dist/uncut.png", "dist/video/uncut.png"]


@pytest.mark.parametrize(
    "out",
    [
        "{tmp}/elsewhere",  # an absolute path
        "../elsewhere",
        ".",  # the repository itself
        "png",  # the pack's pictures
        "dist/../png",
        "dist/video/../../../elsewhere",
        "dist-of-another",  # a name that only starts as the folder's does
    ],
)
def test_a_one_off_outside_its_folder_is_refused(
    one_off_tree: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], out: str
) -> None:
    (tmp_path / "elsewhere").mkdir()
    before = sorted(tmp_path.rglob("*"))
    assert export.main(["--title", "Uncut", "--out", out.format(tmp=tmp_path)]) == 1
    assert "a one-off is written to dist/ or a folder inside it" in capsys.readouterr().out
    assert sorted(tmp_path.rglob("*")) == before
    assert NoBrowser.opened == 0  # refused before anything is drawn


@pytest.mark.parametrize(
    ("link", "target", "out"),
    [
        ("dist", "elsewhere", "dist"),  # the folder itself
        ("dist/video", "elsewhere", "dist/video"),  # a folder inside it
        ("dist/uncut.png", "elsewhere/kept.png", "dist"),  # the file
    ],
)
def test_a_link_out_of_the_one_offs_folder_is_refused(
    one_off_tree: Path, tmp_path: Path, link: str, target: str, out: str
) -> None:
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere/kept.png").write_bytes(b"kept")
    (one_off_tree / link).parent.mkdir(exist_ok=True)
    (one_off_tree / link).symlink_to(tmp_path / target)
    assert export.main(["--title", "Uncut", "--out", out]) == 1
    assert _files(tmp_path) == ["elsewhere/kept.png"]
    assert (tmp_path / "elsewhere/kept.png").read_bytes() == b"kept"


def test_only_a_readme_banner_is_drawn_without_a_browser() -> None:
    kinds = set()
    for picture in export.collect(ROOT).pictures:
        kinds.add(picture.kind)
        if picture.kind == "banner":
            assert picture.draw(None, {}) == (ROOT / picture.path).read_bytes()
            continue
        with pytest.raises(ValueError, match="it is drawn by a browser"):
            picture.draw(None, {})
    assert {"image", "card", "banner", "preview"} <= kinds
