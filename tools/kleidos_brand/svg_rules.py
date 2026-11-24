# SPDX-FileCopyrightText: 2026 José M. Requena Plens
# SPDX-License-Identifier: MIT
"""What an SVG source of a brand image or of the social pack may hold.

A source is a small, flat drawing: three layers in order (``ground``,
``content``, ``guides``), plain shapes and live text, token colors only. No
opacity, filter, gradient, mask, ``<use>``, script, style sheet, link or
embedded picture, so nothing in it depends on a renderer's taste, and every
color in an export is one the tokens name.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from . import BRAND_ROOT, lettering, svgtext, xmlsafe

LAYERS = ("ground", "content", "guides")
ROOT_EXTRAS = frozenset({"title", "desc"})
ELEMENTS = frozenset(
    {
        "svg",
        "g",
        "title",
        "desc",
        "rect",
        "circle",
        "ellipse",
        "line",
        "polyline",
        "polygon",
        "path",
        "text",
        "tspan",
    }
)
BANNED_ATTRIBUTES = (
    "opacity",
    "fill-opacity",
    "stroke-opacity",
    "filter",
    "mask",
    "clip-path",
    "href",
)
COLOR_ATTRIBUTES = ("fill", "stroke")
VIEWBOX = re.compile(r"0 0 ([1-9]\d*) ([1-9]\d*)")
HEX = re.compile(r"#[0-9a-fA-F]{6}")
#: The sign of a registered trademark: Kleidos is not one, so it is never printed.
REGISTERED = chr(0xAE)


def _local(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def canvas(root: ET.Element) -> tuple[int, int] | None:
    """Return the canvas of a source, from its ``viewBox``."""
    match = VIEWBOX.fullmatch(root.get("viewBox", ""))
    return (int(match.group(1)), int(match.group(2))) if match else None


def findings(
    svg: Path, palette: frozenset[str], root: Path = BRAND_ROOT, name: str | None = None
) -> list[str]:
    """Return what in the source *svg* breaks the rules.

    :param palette: Every color the tokens define, lower-case ``#rrggbb``.
    :param root: The repository whose pinned fonts the words are checked against.
    """
    name = name or str(svg)
    raw = svg.read_text(encoding="utf-8")
    found: list[str] = []
    if REGISTERED in raw:
        found.append(
            f"{name}: prints the registered-trademark sign; Kleidos is not a registered trademark"
        )
    if re.search(r"<!DOCTYPE|<!ENTITY|<\?xml-stylesheet", raw):
        found.append(f"{name}: declares a DOCTYPE, an entity or a style sheet")
    try:
        tree = xmlsafe.fromstring(raw)
    except ET.ParseError as error:
        return [*found, f"{name}: not well-formed XML ({error})"]
    if _local(tree) != "svg" or canvas(tree) is None:
        return [*found, f"{name}: its root is not an <svg> with a viewBox of the form '0 0 W H'"]
    layers = [child.get("id") for child in tree if _local(child) == "g"]
    extras = [_local(child) for child in tree if _local(child) != "g"]
    if tuple(layers) != LAYERS:
        found.append(
            f"{name}: its layers are {layers}; a source has {', '.join(LAYERS)}, in that order"
        )
    found.extend(
        f"{name}: a <{extra}> stands outside the layers"
        for extra in extras
        if extra not in ROOT_EXTRAS
    )
    cmaps = {family: lettering.characters(family, root) for family in lettering.FAMILIES}
    for element in tree.iter():
        if not isinstance(element.tag, str):
            continue
        tag = _local(element)
        if tag not in ELEMENTS:
            found.append(f"{name}: holds a <{tag}>; a source holds plain shapes and text only")
            continue
        for key in element.attrib:
            plain = key.rsplit("}", 1)[-1]
            if plain in BANNED_ATTRIBUTES or plain.startswith("on"):
                found.append(
                    f"{name}: <{tag}> carries {plain}; a source has no opacity, filter, mask, link "
                    "or script"
                )
        style = element.get("style")
        if style is not None and not (tag == "text" and svgtext.OPSZ.fullmatch(style)):
            found.append(
                f"{name}: <{tag}> carries style={style!r}; only a text's optical size goes in a "
                "style"
            )
        for key in COLOR_ATTRIBUTES:
            value = element.get(key)
            if value is None or value == "none":
                continue
            if not HEX.fullmatch(value) or value.lower() not in palette:
                found.append(
                    f"{name}: <{tag} id={element.get('id')!r}> has {key}={value!r}, which is not a "
                    "token color"
                )
        if tag == "text":
            family = element.get("font-family", "")
            if family not in cmaps:
                found.append(
                    f"{name}: text {element.get('id')!r} is set in {family!r}; words are set in "
                    f"{' or '.join(cmaps)}"
                )
                continue
            try:
                text, _ = svgtext.words(element)
            except ValueError as error:
                found.append(f"{name}: {error}")
                continue
            missing = sorted({char for char in text if ord(char) not in cmaps[family]})
            if missing:
                found.append(
                    f"{name}: text {element.get('id')!r} has {''.join(missing)!r}, which {family} "
                    "has no glyph for"
                )
    return found


def outlined_findings(svg: Path, palette: frozenset[str], name: str | None = None) -> list[str]:
    """Return what is wrong with a generated SVG: live text, a color off the palette, anything
    embedded."""
    name = name or str(svg)
    raw = svg.read_text(encoding="utf-8")
    found: list[str] = []
    if REGISTERED in raw:
        found.append(f"{name}: prints the registered-trademark sign")
    if re.search(
        r"@font-face|data:font|data:image|<image\b|<script\b|<style\b|<use\b|<text\b", raw
    ):
        found.append(
            f"{name}: holds live text, a font, a picture, a script, a style sheet or a <use>; a "
            "generated SVG holds shapes only"
        )
    found.extend(
        f"{name}: is painted with {value}, which is not a token color"
        for value in re.findall(r'(?:fill|stroke)="([^"]+)"', raw)
        if value != "none" and value.lower() not in palette
    )
    return sorted(set(found))
