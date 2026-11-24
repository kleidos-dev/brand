<!--
SPDX-FileCopyrightText: 2026 José M. Requena Plens
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Notices

The social pack, the `social/` folder of the brand repository. Brand's [`NOTICE.md`](../NOTICE.md) covers the whole repository; this file says what is particular to the pack.

## What the pack holds, and under which license

Everything in the pack is the work of José M. Requena Plens. The artwork (the SVG sources and the motifs, the exported images and their previews) and the pack's data are licensed under the GNU General Public License, version 3 or any later version (GPL-3.0-or-later), the firmware's license. The tooling, which is more useful to everyone under a permissive license, is under the MIT License, as the rest of brand's is: the code under `tools/` and the tests. Brand's `REUSE.toml` states it file by file and brand's `LICENSES/` holds both texts. Both licenses are approved by the Open Source Initiative; nothing in the pack is under any other.

## What comes from the rest of brand

The pack reads from the rest of the repository it is in and copies nothing:

- The mark and the lockup in every image are brand's (`logo/src/mark.svg` and the logo files drawn from it), the work of the same author, under the same license.
- The colors are brand's tokens (`tokens/tokens.json`).
- The terms are brand's [`TRADEMARKS.md`](../TRADEMARKS.md). The additional permission it gives (the press permission) names `logo/`, `press-kit/` and `about/`; it does not reach the images here, which are under the GPL with its two additional terms and no added permission. The images made to be republished are brand's press kit.
- The code under `tools/` imports brand's builders (`tools/kleidos_brand/`, MIT) and runs with the stack brand pins (`requirements.txt`).
- The nine boards on the YouTube banner and in the boards card's motif are brand's copies of the `boards` repository's front drawings (`boards/`, MIT, the work of the same author), drawn at one scale, and each board's panel shows its own unlock screen, a real capture from `press-kit/screens/`. The boards are M5Stack's and LILYGO's products; the legends printed on them, the makers' marks included, are drawn as the products show them so that each one can be recognized, and remain their owners'.

## Fonts

No font file is in the pack. Every word in an image here is glyph outlines or rasterized text of Mona Sans and Mona Sans Mono 2.0.27, read at export time from brand's `fonts/`, where the upstream files are kept unmodified beside their license: "Copyright 2022 The Mona Sans Project Authors (https://github.com/github/mona-sans), with Reserved Font Name "Mona"", SIL Open Font License 1.1, which the Open Source Initiative also approves. The OFL leaves such documents outside itself ("The requirement for fonts to remain under this license does not apply to any document created using the fonts or their derivatives"), so the images are the project's own work, under GPL-3.0-or-later. The credit is kept as a courtesy.

## The name and the mark

Kleidos is not a registered trademark. Under section 7(e) of the GNU GPL version 3, the license of the pack grants no rights under trademark law in the name "Kleidos" or in the Kleidos mark. Under section 7(c), a modified version of a file under the GPL here must be marked in reasonable ways as different from the original, and must not misrepresent the origin of the material; a file passed on unchanged needs no mark. Brand's [`TRADEMARKS.md`](../TRADEMARKS.md) holds both terms and what the project asks of those who use its name. Each PNG file carries the same facts in its own metadata (its creator, its copyright line, GPL-3.0-or-later with the license's address, the credits, the trademark notes and the address of `TRADEMARKS.md`), so they travel with the file; this notice and `TRADEMARKS.md` remain the full statement.

## What is not here

- No drawing, front, icon or model of a board in the pack: the fronts the images show are read from brand's `boards/` when they are drawn.
- No photograph or render of a device, and no capture of a screen in the pack: the captures on the boards' panels are read from brand's `press-kit/screens/` too.
- No vendor file of any kind.

## Other people's trademarks

YouTube, MakerTube, PeerTube and GitHub are named here to say where each image goes; M5Stack, LILYGO and Espressif to say which boards the firmware runs on. They are trademarks of their respective owners. Kleidos is an independent project, not affiliated with, sponsored or endorsed by any of them, and the license of the pack grants no right to use any of those marks.
