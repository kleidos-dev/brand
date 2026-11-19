# SPDX-License-Identifier: MIT
"""The metadata record of every picture and SVG this repository publishes (:mod:`.meta`).

Each record is made from what the builder already knows about the file: a
logo's kind and ground, the palette, a press image's entry in ``press.json``
(its title and alt text, in English and Spanish), a screen's board, the
photograph's own words. The license and the holders are this repository's
artwork line of ``REUSE.toml`` (GPL-3.0-or-later, its author); the checks
hold every record to what REUSE says for the file's path.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from . import meta
from .logo import variant as logo_variant

REPO = "brand"
LICENSE = "GPL-3.0-or-later"
HOLDERS = ("2026 José M. Requena Plens",)
RIGHTS_URL = meta.RIGHTS_URLS[REPO]
EXTRA = (meta.extra_terms(REPO),)

CREDIT_MONA_SANS = "Lettering outlined from Mona Sans, © 2022 The Mona Sans Project Authors, SIL Open Font License 1.1."
CREDIT_MONA_BOTH = "Words outlined from Mona Sans and Mona Sans Mono, © 2022 The Mona Sans Project Authors, SIL Open Font License 1.1."
CREDIT_SCREEN_FONTS = ("Screen text drawn by the firmware in Inter, © 2016 The Inter Project Authors, and JetBrains Mono,"
                       " © 2020 The JetBrains Mono Project Authors, SIL Open Font License 1.1.")
CREDIT_BOARDS = ("Board drawings from kleidos-dev/boards, MIT, their printed legends outlined from Inter,"
                 " © 2016 The Inter Project Authors, SIL Open Font License 1.1.")

#: The Spanish of the credits, for the press images in Spanish.
SPANISH = {
    CREDIT_MONA_BOTH: "Textos trazados a partir de Mona Sans y Mona Sans Mono, © 2022 The Mona Sans Project Authors, SIL Open Font License 1.1.",
    CREDIT_SCREEN_FONTS: ("Texto de pantalla dibujado por el firmware en Inter, © 2016 The Inter Project Authors, y JetBrains Mono,"
                          " © 2020 The JetBrains Mono Project Authors, SIL Open Font License 1.1."),
    CREDIT_BOARDS: ("Dibujos de las placas de kleidos-dev/boards, MIT, con sus serigrafías trazadas a partir de Inter,"
                    " © 2016 The Inter Project Authors, SIL Open Font License 1.1."),
}

#: How each kind of logo file is named in a title.
KIND_TITLES = {
    "mark": "Kleidos mark",
    "mark-small": "Kleidos small mark",
    "lockup-horizontal": "Kleidos horizontal lockup",
    "lockup-stacked": "Kleidos stacked lockup",
    "lettering": "Kleidos lettering",
}
#: How each variant of a logo file is named in a title, from its stem's last words.
VARIANT_TITLES = {
    "for-dark": "for dark grounds",
    "for-light": "for light grounds",
    "ink-dark": "dark ink",
    "ink-light": "light ink",
    "on-dark": "on its dark tile",
    "on-light": "on its white tile",
}
#: What each kind of logo file shows, for its alt text.
KIND_ALTS = {
    "mark": "The Kleidos mark: a keyhole inside a ring",
    "mark-small": "The Kleidos mark: a keyhole inside a ring",
    "lockup-horizontal": "The Kleidos logo: a keyhole inside a ring, beside the name Kleidos",
    "lockup-stacked": "The Kleidos logo: a keyhole inside a ring, above the name Kleidos",
    "lettering": "The name Kleidos",
}


def url(path: str | Path) -> str:
    """Return the public URL of a file of this repository."""
    return meta.identifier_url(REPO, path)


def _sentence(text: str) -> str:
    text = text.strip()
    return text[:1].upper() + text[1:] + ("" if text.endswith(".") else ".")


def _record(path: str | Path, title: str, description: str, alt: str, keywords: tuple[str, ...], dst: str,
            size: tuple[int, int] | None = None, **extra: Any) -> meta.MediaMeta:
    words = tuple(dict.fromkeys((*meta.BASE_KEYWORDS, *keywords)))
    return meta.MediaMeta(
        title=title, description=description, alt=alt, keywords=words, digital_source_type=dst,
        spdx=LICENSE, own_license=LICENSE, holders=HOLDERS, identifier_url=url(path), rights_url=RIGHTS_URL,
        extra_terms=EXTRA, profile=meta.profile_for(size) if size else "full", repo=REPO, spanish=SPANISH, **extra,
    )


def logo_title(stem: str, kind: str, px: int | None = None) -> str:
    """Return a logo file's title: its kind, its variant, and a PNG copy's height."""
    variant = next((words for key, words in VARIANT_TITLES.items() if stem.endswith(f"-{key}") or f"-{key}-" in f"{stem}-"), "in color")
    return f"{KIND_TITLES[kind]}, {variant}" + (f", {px} px" if px else "")


def logo(item: Any, path: str | Path, size: tuple[int, int] | None = None, source: str | None = None) -> meta.MediaMeta:
    """Return the record of a logo file: its SVG, or a PNG copy of *size* drawn from *source*."""
    height = size[1] if size else None
    title = logo_title(item.family, item.kind, item.px or height)
    keywords = ("logo", "keyhole", "brand") if item.kind != "lettering" else ("logo", "lettering", "brand")
    credits = (CREDIT_MONA_SANS,) if item.kind in ("lockup-horizontal", "lockup-stacked", "lettering") else ()
    return _record(path, title, f"The Kleidos logo: {item.what}.", KIND_ALTS[item.kind], keywords, "digitalCreation", size,
                   credits=credits, trademarks=(meta.TRADEMARK_NOTE_KLEIDOS,), source_url=source)


def palette(path: str | Path, size: tuple[int, int] | None = None, source: str | None = None) -> meta.MediaMeta:
    """Return the record of the palette's sheet, its SVG or its PNG."""
    return _record(path, "Kleidos color palette",
                   "The Kleidos palette: every brand, web and device color with its token name and its hex value.",
                   "The Kleidos palette", ("color palette", "design tokens", "brand"), "digitalCreation", size,
                   credits=(CREDIT_MONA_BOTH,), source_url=source)


def press(image: Any, entry: dict[str, Any], path: str | Path, size: tuple[int, int] | None = None,
          source: str | None = None) -> meta.MediaMeta:
    """Return the record of a press image, its SVG or one of its PNG files, in the image's language."""
    about = entry["meta"]
    shows_screens = bool(image.plates or image.fronts)
    credits = [CREDIT_MONA_BOTH]
    trademarks = [meta.TRADEMARK_NOTE_KLEIDOS]
    keywords = ["press kit", "press image"]
    if image.fronts:
        credits.append(CREDIT_BOARDS)
    if shows_screens:
        credits.append(CREDIT_SCREEN_FONTS)
        trademarks += [meta.TRADEMARK_NOTE_M5, meta.TRADEMARK_NOTE_LILYGO]
        keywords += ["unlock screen", "M5Stack", "LILYGO", "ESP32"]
    spanish = {}
    if image.lang == "es":
        spanish = {"title_es": about["title"]["es"], "description_es": about["alt"]["es"], "alt_es": about["alt"]["es"]}
    return _record(path, about["title"]["en"], about["alt"]["en"], about["alt"]["en"], tuple(keywords),
                   "composite" if shows_screens else "digitalCreation", size, credits=tuple(credits),
                   trademarks=tuple(trademarks), source_url=source, language=image.lang, **spanish)


#: How an opaque logo copy is named in a title, by the variant of the file it copies.
OPAQUE_TITLES = {
    "for-light": "on white",
    "for-dark": "on black",
    "ink-dark": "dark ink on white",
    "ink-light": "light ink on black",
    "color": "in color on black",
}


def opaque(copy: Any, size: tuple[int, int]) -> meta.MediaMeta:
    """Return the record of an opaque logo copy (:class:`.logo.Opaque`): the PNG on transparency, flattened on its ground."""
    item = copy.item
    base = logo(item, copy.path, size, url(copy.source))
    what = item.what.replace(", on transparency", "")
    return replace(
        base,
        title=f"{KIND_TITLES[item.kind]}, {OPAQUE_TITLES[logo_variant(item.family)]}, {item.px or size[1]} px",
        description=(f"The Kleidos logo: {what}, flattened on {copy.ground} ({copy.color}): the opaque copy of"
                     f" {copy.source.name}, with no clear space added."),
        keywords=_words(base.keywords, "opaque"),
    )


def webp(about: meta.MediaMeta, path: str | Path, copied: str | Path, lossless: bool) -> meta.MediaMeta:
    """Return the record of the WebP copy of a published picture, from the record of the file it copies."""
    # The note names the copied file's format, not its name: a file name spells a vendor in lowercase.
    kind = Path(copied).suffix.lstrip(".").upper().replace("JPG", "JPEG")
    if lossless:
        notes = (f"A lossless WebP copy of the {kind} file of the same name, pixel for pixel.", "A lossless WebP copy, pixel for pixel.")
        notes_es = (f"Copia en WebP, sin pérdida, del archivo {kind} del mismo nombre, píxel a píxel.",
                    "Copia en WebP, sin pérdida, píxel a píxel.")
    else:
        notes = (f"A WebP copy of the {kind} file of the same name, lossy at quality 90.", "A lossy WebP copy at quality 90.")
        notes_es = (f"Copia en WebP del archivo {kind} del mismo nombre, con pérdida, a calidad 90.", "Copia en WebP, con pérdida, a calidad 90.")
    spanish = {}
    if about.language == "es":
        spanish = {"title_es": f"{about.title_es}, WebP", "description_es": _noted(str(about.description_es), notes_es)}
    return replace(about, title=f"{about.title}, WebP", description=_noted(about.description, notes), identifier_url=url(path),
                   source_url=url(copied), keywords=_words(about.keywords, "WebP"), **spanish)


#: The longest description the profile takes (:func:`.meta.record_problems`).
DESCRIPTION_LIMIT = 300


def _noted(description: str, notes: tuple[str, ...]) -> str:
    """Return *description* with the first of *notes* that keeps it within the profile's limit, the last one otherwise."""
    return next((f"{description} {note}" for note in notes if len(description) + 1 + len(note) <= DESCRIPTION_LIMIT),
                f"{description} {notes[-1]}")


def _words(keywords: tuple[str, ...], extra: str) -> tuple[str, ...]:
    """Return *keywords* with *extra* last, within the profile's twelve."""
    words = tuple(dict.fromkeys(keywords))
    return words if extra in words else (*words[:11], extra)


def _vendor(name: str) -> tuple[str, str]:
    return ("LILYGO", meta.TRADEMARK_NOTE_LILYGO) if name.startswith("LILYGO") else ("M5Stack", meta.TRADEMARK_NOTE_M5)


def screen(screen_: dict[str, Any], path: str | Path, size: tuple[int, int], scale: int | None = None,
           source: str | None = None) -> meta.MediaMeta:
    """Return the record of an unlock-screen capture, as captured or enlarged *scale* times."""
    name = screen_["name"]
    vendor, note = _vendor(name)
    width, height = screen_["size"]
    if scale:
        title = f"Kleidos unlock screen on the {name}, {scale}x"
        description = (f"The Kleidos firmware's unlock screen on the {name}, a real capture of {width} x {height} pixels"
                       f" enlarged {scale} times, each pixel a square.")
    else:
        title = f"Kleidos unlock screen on the {name}"
        description = f"The Kleidos firmware's unlock screen on the {name}, a real capture at its own {width} x {height} pixels."
    return _record(path, title, description, f"The Kleidos unlock screen on the {name}, asking for the PIN",
                   (name, vendor, "unlock screen", "screen capture", "PIN entry"), "screenCapture", size,
                   credits=(CREDIT_SCREEN_FONTS,), trademarks=(note, meta.TRADEMARK_NOTE_KLEIDOS), source_url=source)


def photo(photo_: dict[str, Any], path: str | Path, size: tuple[int, int], source: str | None = None) -> meta.MediaMeta:
    """Return the record of the photograph, at full resolution or a narrower copy."""
    boards = ("M5Stack Cardputer ADV", "M5Stack Core2 v1.3", "M5StickS3", "LILYGO T-Deck Plus")
    return _record(path, "Four boards running Kleidos, photograph", _sentence(photo_["what"]), photo_["alt"]["en"],
                   ("photograph", *boards, "M5Stack", "LILYGO"), "digitalCapture", size,
                   trademarks=(meta.TRADEMARK_NOTE_M5, meta.TRADEMARK_NOTE_LILYGO, meta.TRADEMARK_NOTE_KLEIDOS), source_url=source)


def kicad_preview(ground: str, path: str | Path, size: tuple[int, int] | None = None) -> meta.MediaMeta:
    """Return the record of a preview of the KiCad kit: its fixture drawn on *ground* with that ground's sheet and theme."""
    page = "dark" if ground == "dark" else "white"
    return _record(path, f"Kleidos KiCad style, {ground} ground",
                   f"The Kleidos KiCad kit's fixture drawn with its {ground} drawing sheet and color theme: one page that exercises"
                   " every rule of the style, with the Kleidos mark in the title block.",
                   f"A one-page KiCad schematic in the Kleidos style on a {page} page: cyan connections, labelled nets, a"
                   " legend table, and the title block with the Kleidos mark",
                   ("KiCad", "schematic", "drawing sheet", "color theme", "brand"), "digitalCreation", size,
                   trademarks=(meta.TRADEMARK_NOTE_KLEIDOS,))
