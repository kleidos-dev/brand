#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the KiCad kit through kicad-cli: the fixture on each ground, ERC and both exports.

    tools/check_kicad.py     needs kicad-cli (KICAD_CLI names another); CI runs it in kicad/kicad:10.0.8

For each ground: ERC on the fixture (recolored for the ground, as every light
export is) reports no message; the SVG export has the theme's background and
one width for every wire-colored line; the PDF export is written. A sheet or a
theme KiCad cannot read fails here. Standard library only, so it runs in
KiCad's container with that image's own Python.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kleidos_brand import BRAND_ROOT, kicad, kicad_preview  # noqa: E402


def main() -> int:
    kit = kicad_preview.helper(BRAND_ROOT)
    found = []
    for ground in kicad.load(BRAND_ROOT)["grounds"]:
        try:
            kicad_preview.export_svg(ground, BRAND_ROOT)
        except RuntimeError as error:
            found.append(f"{ground}: {error}")
            continue
        with tempfile.TemporaryDirectory(prefix="kleidos-kicad-pdf-") as scratch:
            pdf = Path(scratch) / "fixture.pdf"
            done = kit.export_pdf(BRAND_ROOT / kicad_preview.FIXTURE, pdf, kit.environment(), ground)
            if done.returncode or not pdf.is_file() or pdf.stat().st_size == 0:
                found.append(f"{ground}: kicad-cli wrote no PDF: {done.stdout}{done.stderr}")
            elif b"/Subtype /Image" not in pdf.read_bytes() and b"/Subtype/Image" not in pdf.read_bytes():
                found.append(f"{ground}: the PDF draws no image: the sheet's mark is missing")
        print(f"{ground}: ERC clean, the theme's background, one wire width, a PDF with the mark")
    for line in found:
        print(f"FAIL {line}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
