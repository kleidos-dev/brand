# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""The palette's own pages: the swatch sheet and the tables of ``colors/README.md``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import BRAND_ROOT, SVG_HEADER, lettering, tokens

PALETTE_SVG = Path("colors/palette.svg")
PALETTE_PNG = Path("colors/palette.png")

#: The rows of the sheet: a heading, then the tokens it shows and the ground their contrast is read
#: on.
ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Brand", ("brand.signal", "brand.select")),
    (
        "Web, dark",
        (
            "web.dark.ground",
            "web.dark.stage",
            "web.dark.surface",
            "web.dark.raised",
            "web.dark.ink",
            "web.dark.ink-2",
            "web.dark.ink-3",
            "web.dark.done",
            "web.dark.pending",
        ),
    ),
    (
        "Web, light",
        (
            "web.light.ground",
            "web.light.surface",
            "web.light.ink",
            "web.light.ink-2",
            "web.light.ink-3",
            "web.light.signal",
            "web.light.done",
            "web.light.pending",
        ),
    ),
    (
        "Device",
        (
            "device.dark.bg.base",
            "device.dark.bg.surface",
            "device.dark.bg.elevated",
            "device.dark.bg.accent",
            "device.dark.brand.primary",
            "device.dark.text.primary",
            "device.dark.text.secondary",
            "device.dark.text.muted",
            "device.dark.text.subtle",
        ),
    ),
    (
        "Device, status",
        (
            "device.dark.status.success",
            "device.dark.status.warning",
            "device.dark.status.caution",
            "device.dark.status.info",
            "device.dark.status.admin",
            "device.dark.bg.success",
            "device.dark.bg.warning",
            "device.dark.bg.titleWarning",
            "device.dark.bg.titleCaution",
        ),
    ),
    (
        "Device, e-paper",
        (
            "device.eink.k5-paper",
            "device.eink.k4",
            "device.eink.k3",
            "device.eink.k2",
            "device.eink.k1",
            "device.eink.k0-ink",
        ),
    ),
)

#: The pairs whose contrast the colors page states: a color, the ground it is read on, and what the
#: pair is.
PAIRS: tuple[tuple[str, str, str], ...] = (
    ("brand.signal", "web.dark.stage", "the mark's ring on the brand's ground"),
    ("brand.signal", "web.dark.ground", "the accent on the site's page"),
    ("brand.signal", "device.dark.bg.base", "the accent on a panel's black"),
    ("brand.signal", "brand.select", "the keyhole on the mark's body"),
    (
        "brand.signal",
        "web.light.surface",
        "the mark's ring on white: the body carries the mark there",
    ),
    ("brand.select", "web.light.surface", "the mark's body on white"),
    (
        "brand.select",
        "web.dark.stage",
        "the mark's body on the brand's ground: never a line on dark",
    ),
    ("web.dark.ink", "web.dark.stage", "names and titles on the brand's ground"),
    ("web.dark.ink", "web.dark.ground", "text on the site's page"),
    ("web.dark.ink-2", "web.dark.stage", "second lines on the brand's ground"),
    ("web.dark.ink-3", "web.dark.ground", "labels on the site's page"),
    ("web.dark.done", "web.dark.ground", "a status met"),
    ("web.dark.pending", "web.dark.ground", "a status not met yet"),
    ("web.light.signal", "web.light.ground", "the accent on the light page"),
    ("web.light.signal", "web.light.surface", "the accent on white"),
    ("web.light.ink", "web.light.ground", "text on the light page"),
    ("web.light.ink-2", "web.light.ground", "second lines on the light page"),
    ("web.light.ink-3", "web.light.ground", "labels on the light page"),
    ("device.dark.text.primary", "device.dark.bg.base", "text on a panel"),
    ("device.dark.text.secondary", "device.dark.bg.base", "hints on a panel"),
    ("device.dark.status.success", "device.dark.bg.base", "success"),
    ("device.dark.status.warning", "device.dark.bg.base", "warning"),
    ("device.dark.status.caution", "device.dark.bg.base", "caution"),
    ("device.dark.status.info", "device.dark.bg.base", "info"),
    ("device.dark.status.admin", "device.dark.bg.base", "the admin banner"),
)

MONO = (("wght", 500.0),)
SANS = (("opsz", 20.0), ("wdth", 100.0), ("wght", 600.0))


def _words(
    text: str,
    family: str,
    axes: tuple[tuple[str, float], ...],
    size: float,
    x: float,
    y: float,
    fill: str,
    tracking: float,
    root: Path,
) -> str:
    line = lettering.shape(text, family, axes, tracking, root)
    scale = size / line.upem
    return (
        f'  <path fill="{fill}" transform="translate({x:g} {y:g}) scale({scale:g} {-scale:g})" '
        f'd="{line.path()}">'
        f"<title>{text}</title></path>"
    )


def svg(root: Path = BRAND_ROOT) -> tuple[str, tuple[int, int]]:
    """Return the swatch sheet and its canvas: every color with its name and its hex, words as
    outlines."""
    values = tokens.resolve(tokens.load(root))
    ground, ink, ink_2, rule = (
        values[f"social.{name}"] for name in ("ground", "ink", "ink-2", "rule")
    )
    chip, gap, left, top = 220, 28, 120, 120
    width = left * 2 + 9 * chip + 8 * gap
    body = []
    y = top
    for heading, names in ROWS:
        body.append(
            _words(heading.upper(), "Mona Sans Mono", MONO, 30, left, y + 30, ink_2, 0.12, root)
        )
        y += 64
        for index, name in enumerate(names):
            x = left + index * (chip + gap)
            body.append(
                f'  <rect x="{x - 2}" y="{y - 2}" width="{chip + 4}" height="{chip * 0.6 + 4:g}" '
                f'fill="{rule}"/>'
            )
            body.append(
                f'  <rect x="{x}" y="{y}" width="{chip}" height="{chip * 0.6:g}" '
                f'fill="{values[name]}"/>'
            )
            label = name.split(".", 2)[-1] if name.count(".") > 1 else name.split(".")[-1]
            body.append(_words(label, "Mona Sans", SANS, 26, x, y + chip * 0.6 + 44, ink, 0, root))
            body.append(
                _words(
                    values[name], "Mona Sans Mono", MONO, 24, x, y + chip * 0.6 + 82, ink_2, 0, root
                )
            )
        y += round(chip * 0.6) + 150
    height = y - 30 + top - 64
    head = (
        SVG_HEADER
        + f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" role="img">\n'
        + "  <title>The Kleidos palette: every color with its name and its value</title>\n"
        + f'  <rect x="0" y="0" width="{width}" height="{height}" fill="{ground}"/>\n'
    )
    return head + "\n".join(body) + "\n</svg>\n", (width, height)


def _swatch(color: str) -> str:
    return f"`{color}`"


def roles_table(root: Path = BRAND_ROOT) -> str:
    """Return the table of the colors page: every color with its value, its print start and its
    role."""
    loaded = tokens.load(root)
    values = tokens.resolve(loaded)
    found = tokens.leaves(loaded)
    lines = [
        "| Token | Hex | RGB | CMYK, by arithmetic | Role |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, names in ROWS:
        for name in names:
            color = values[name]
            red, green, blue = tokens.hex_rgb(color)
            cyan, magenta, yellow, black = tokens.cmyk(color)
            role = found[name].get("$description", "")
            lines.append(
                f"| `{name}` | {_swatch(color)} | {red}, {green}, {blue} | {cyan}, {magenta}, "
                f"{yellow}, {black} | {role} |"
            )
    return "\n".join(lines)


def contrast_table(root: Path = BRAND_ROOT) -> str:
    """Return the measured contrast of every pair the colors page states."""
    values = tokens.resolve(tokens.load(root))
    lines = ["| Color | On | Contrast | What the pair is |", "| --- | --- | --- | --- |"]
    for color, ground, what in PAIRS:
        ratio = tokens.contrast(values[color], values[ground])
        lines.append(
            f"| `{color}` {_swatch(values[color])} | `{ground}` {_swatch(values[ground])} | "
            f"{ratio:.2f}:1 | {what} |"
        )
    return "\n".join(lines)


def device_table(root: Path = BRAND_ROOT) -> str:
    """Return the device's colors with the constant that holds each in the firmware and its 16-bit
    value."""
    loaded = tokens.load(root)
    values = tokens.resolve(loaded)
    lines = ["| Token | Hex | RGB565 | Constant in `theme.h` |", "| --- | --- | --- | --- |"]
    for name, token in tokens.leaves(loaded["device"]["dark"], "device.dark.").items():
        constant: Any = token.get("$extensions", {}).get("dev.kleidos", {}).get("theme_h", "")
        lines.append(
            f"| `{name}` | `{values[name]}` | `{tokens.rgb565(values[name])}` | `{constant}` |"
        )
    return "\n".join(lines)
