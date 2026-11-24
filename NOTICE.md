<!--
SPDX-FileCopyrightText: 2026 José M. Requena Plens
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Notices

## What this repository holds, and under which license

Everything in this repository is the work of José M. Requena Plens, except the font files under `fonts/` (below). It is under one of two licenses:

- **GNU General Public License, version 3 or any later version** (GPL-3.0-or-later), the firmware's license: the artwork. The mark, the lockups and their PNG files, the KiCad drawing sheets that embed the mark and their previews, the press images, their templates and words, the screen captures, the photographs, the palette's page and sheet, and the pages about them.
- **MIT License**: what is more useful to everyone under a permissive license. The tokens and the files generated from them (`tokens/`), the KiCad kit's numbers, themes, helper and fixture (`kicad/`, below), the code, the checks and their tests (`tools/`, `tests/`), the CI (`.github/`), the pins and the configuration files, the texts that describe the project (`about/`, `press-kit/en/fact-sheet.md`, `press-kit/es/fact-sheet.md`), so anyone may quote them freely, and the board fronts under `boards/` (below).

`REUSE.toml` states it file by file and `LICENSES/` holds the three license texts. All three licenses here are approved by the Open Source Initiative; nothing in this repository is under any other license.

## The name and the mark

Kleidos is not a registered trademark. Under section 7(e) of the GNU GPL version 3, the GPL of this repository grants no rights under trademark law in the name "Kleidos" or in the Kleidos mark, and the MIT License grants none either. Under section 7(c), a modified version of a file under the GPL here must be marked in reasonable ways as different from the original, and must not misrepresent the origin of the material; a file passed on unchanged needs no mark. [`TRADEMARKS.md`](TRADEMARKS.md) holds both terms, the permission that lets anyone republish the logo, the press-kit images and the texts as they are with no license paperwork, and what the project asks of those who use its name. The PNG files carry no text of their own: this notice and `TRADEMARKS.md` speak for them.

## The board fronts

`boards/<board>.svg` are byte copies of the nine `<board>/svg/front.svg` drawings of the project's `boards` repository (<https://github.com/kleidos-dev/boards>), the work of the same author, licensed there under the MIT License; `boards/boards.json` records the commit they were taken at and each file's SHA-256. They are kept under that license here, with the same copyright line (`LICENSES/MIT.txt`). The line-up images under `press-kit/images/kleidos-boards-*` are drawn from them, with each board's own unlock screen on its panel: the images are GPL-3.0-or-later like the rest of the press kit, and the drawings in them stay available under the MIT License from those files. The boards themselves are M5Stack's and LILYGO's products; the legends printed on them, the makers' marks included (M5, LILYGO, CARDPUTER and the like), are drawn as the products show them so that each one can be recognized, and remain their owners' marks.

## The KiCad kit

`kicad/` holds the Kleidos KiCad style (`kicad/README.md`). Its two drawing sheets, `kicad/kleidos-dark.kicad_wks` and `kicad/kleidos-light.kicad_wks`, embed the mark as `logo/png/kleidos-mark-1024.png` and `logo/png/kleidos-mark-ink-dark-1024.png`, byte for byte: they are artwork, GPL-3.0-or-later, as are the previews under `kicad/preview/`. The style's numbers, the two color themes, the helper `kicad/kleidos_kicad.py` and the fixture are under the MIT License. The boards and meter repositories carry byte copies of the kit; a schematic drawn with it keeps its own repository's license and shows the mark placed unchanged under the press permission of `TRADEMARKS.md`.

## Fonts

The three families under `fonts/` are other people's work, kept as their upstream files, unmodified, each beside its license (`fonts/<family>/OFL.txt`; the text is also `LICENSES/OFL-1.1.txt`). Pins: `fonts/VERSIONS.md`.

- **Mona Sans and Mona Sans Mono** 2.0.27, from <https://github.com/github/mona-sans>: "Copyright 2022 The Mona Sans Project Authors (https://github.com/github/mona-sans), with Reserved Font Name "Mona"", SIL Open Font License 1.1.
- **Inter** 4.1, from <https://github.com/rsms/inter>: "Copyright (c) 2016 The Inter Project Authors (https://github.com/rsms/inter)", SIL Open Font License 1.1.
- **JetBrains Mono** 2.304, from <https://github.com/JetBrains/JetBrainsMono>: "Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono)", SIL Open Font License 1.1.

The name's lettering and every word in a generated image are glyph outlines or rasterized text of Mona Sans and Mona Sans Mono; the words on the screen captures are rasterized Inter and JetBrains Mono, as the firmware draws them, and the legends printed on the board fronts are glyph outlines of Inter, set from the pinned files when an image is built. The OFL leaves such documents outside itself ("The requirement for fonts to remain under this license does not apply to any document created using the fonts or their derivatives"), so those images are the project's own work, under GPL-3.0-or-later. The credit above is kept as a courtesy and as the license asks for the font files themselves.

## What is not here

- No board model, back drawing, schematic or icon: only the nine fronts above, copied from the `boards` repository. The KiCad kit's fixture is a small sheet of its own, no board's.
- No capture that shows another company's mark. The screens in the press kit are the firmware's unlock screen, which shows none.
- No photograph but the owner's own, under `press-kit/photos/`, with every metadata segment removed. It shows the boards as they are, their makers' print included (M5, LILYGO, CARDPUTER and the like), and their screens show an earlier build of Kleidos over demo entries named after well-known services; those names and marks remain their owners'.
- No vendor file of any kind.

## Other people's trademarks

M5Stack, LILYGO, Espressif and the names of their products are trademarks of their respective owners. They are named here to say which boards the firmware runs on. Kleidos is an independent project, not affiliated with, sponsored or endorsed by any of them, and the licenses in this repository grant no right to use any of those marks.
