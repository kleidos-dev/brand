# SPDX-License-Identifier: MIT
"""The KiCad kit's previews: its fixture exported by kicad-cli with each ground's sheet and theme, drawn to pixels.

The only part of the builder that needs KiCad (``tools/build.py --kicad``).
kicad-cli writes the fixture's page as an SVG whose words are outlines, so
the browser that draws it needs no font. The light preview is exported from a
copy of the fixture with its explicit colors turned to the light ground's
(``kleidos_kicad.recolor``), as every light export is.
"""

from __future__ import annotations

import hashlib
import importlib.util
import shutil
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

from . import BRAND_ROOT, kicad

#: The preview's pixels: an A4 page at about 6.7 pixels to the millimeter.
SIZE = (2000, 1414)
FIXTURE = kicad.FIXTURE_DIR / "fixture.kicad_sch"
FIXTURE_PRO = kicad.FIXTURE_DIR / "fixture.kicad_pro"


def path(ground: str) -> Path:
    return kicad.PREVIEW_DIR / f"kleidos-kicad-fixture-{ground}.png"


def inputs(ground: str, root: Path = BRAND_ROOT) -> tuple[Path, ...]:
    """Return the files a preview is drawn from."""
    mark = Path(kicad.load(root)["grounds"][ground]["mark"])
    return (
        FIXTURE,
        FIXTURE_PRO,
        kicad.SRC_JSON,
        kicad.ADVANCES_JSON,
        kicad.HELPER,
        Path("tokens/tokens.json"),
        mark,
    )


def source(ground: str, root: Path = BRAND_ROOT) -> str:
    """Return the SHA-256 of what a preview is drawn from: the fixture, then the kit's files as the builder writes them."""
    digest = hashlib.sha256()
    for name in (FIXTURE, FIXTURE_PRO, kicad.HELPER):
        digest.update((root / name).read_bytes())
    texts = kicad.texts(root)
    for name in (kicad.sheet_path(ground), kicad.theme_path(ground), kicad.STYLE_JSON):
        digest.update(texts[name].encode("utf-8"))
    return digest.hexdigest()


def helper(root: Path = BRAND_ROOT) -> ModuleType:
    """Return the kit's ``kleidos_kicad`` module, loaded from the tree at *root*."""
    spec = importlib.util.spec_from_file_location("kleidos_kicad", root / kicad.HELPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_svg(ground: str, root: Path = BRAND_ROOT) -> str:
    """Return the fixture's page as kicad-cli draws it on *ground*; raises when ERC reports anything."""
    kit = helper(root)
    env = kit.environment()
    with tempfile.TemporaryDirectory(prefix="kleidos-preview-") as scratch:
        work = Path(scratch) / "fixture"
        work.mkdir()
        shutil.copyfile(root / FIXTURE_PRO, work / FIXTURE_PRO.name)
        (work / FIXTURE.name).write_text(
            kit.recolor((root / FIXTURE).read_text(encoding="utf-8"), ground), encoding="utf-8"
        )
        count, report = kit.erc(work / FIXTURE.name, env)
        if count != 0:
            raise RuntimeError(
                f"{FIXTURE}: ERC reports {count} message(s) on the {ground} ground:\n{report}"
            )
        out = Path(scratch) / "svg"
        done = kit.export_svg(work / FIXTURE.name, out, env, ground)
        svgs = sorted(out.glob("*.svg"))
        if done.returncode or len(svgs) != 1:
            raise RuntimeError(f"kicad-cli did not export {FIXTURE}: {done.stdout}{done.stderr}")
        problems = kit.svg_findings(svgs[0], ground)
        if problems:
            raise RuntimeError("; ".join(problems))
        return svgs[0].read_text(encoding="utf-8")


def draw(ground: str, browser: Any, root: Path = BRAND_ROOT) -> Any:
    """Return the preview's pixels on *ground*, flattened on the ground's color (a Pillow image)."""
    from . import png  # noqa: PLC0415

    color = kicad.colors(root)[ground]["ground"]
    return png.clean(browser.draw(export_svg(ground, root), SIZE, f"kicad-{ground}"), flatten=color)
