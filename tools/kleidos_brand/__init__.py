# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The Kleidos brand's builders and checks, as one importable package.

``brand`` builds its own files with it (``tools/build.py``, ``tools/check.py``)
and the social pack (``social/``) imports it, so both draw with one set of
rules, one browser and one encoder:

- :mod:`.tokens`: the palette, read from ``tokens/tokens.json``;
- :mod:`.lettering`: words shaped with HarfBuzz and outlined from the pinned
  fonts, so no image ever needs a font installed;
- :mod:`.svgtext`: the ``<text>`` elements of an SVG source turned into paths;
- :mod:`.svg_rules`: what an SVG source may hold;
- :mod:`.mark`: the mark's shapes and the checks that hold every copy to them;
- :mod:`.raster` and :mod:`.png`: Chromium's drawing and the re-encoding from
  pixels alone;
- :mod:`.public_tree`: what must never be in a published tree;
- :mod:`.record`: the record of what each generated file was built from.

``sys.path`` needs the ``tools`` folder: ``tools/build.py`` adds it for
itself, and the social pack's ``social/tools/pack.py`` adds it for the pack.
"""

from __future__ import annotations

from pathlib import Path

#: The repository this package is in: ``brand``.
BRAND_ROOT = Path(__file__).resolve().parents[2]

#: The project's contact, one of the two addresses a published file may hold.
PROJECT_CONTACT = "mail@kleidos.dev"
#: The other one: the supplier REUSE.toml names, as in the boards repository.
PROJECT_SUPPLIER = "jmrplens@kleidos.dev"

#: The first lines of every SVG this project writes. The tag stands alone on
#: its line: REUSE reads the rest of a tag's line as part of the expression.
# REUSE-IgnoreStart
SVG_HEADER = (
    "<!--\n"
    "  SPDX-FileCopyrightText: 2026 José M. Requena Plens\n"
    "  SPDX-License-Identifier: GPL-3.0-or-later\n"
    "  Additional terms under section 7 of the GNU GPL version 3: TRADEMARKS.md\n"
    "-->\n"
)
# REUSE-IgnoreEnd
