<!--
SPDX-FileCopyrightText: 2026 José M. Requena Plens
SPDX-License-Identifier: MIT
-->

# Kleidos: fact sheet

As of 2026-11-17.

## What it is

Kleidos is free firmware that turns one of the small ESP32 boards it runs on, from M5Stack and LILYGO, into a hardware password manager. Your passwords stay encrypted on the board, which types the one you pick into your computer or phone over Bluetooth, and only after you have unlocked it on the board itself.

## Facts

| | |
| --- | --- |
| Status | In development. Not released: there is nothing to download yet. |
| Boards | Nine, on the ESP32-S3 and the classic ESP32: M5StickS3, M5Stack Cardputer ADV, LILYGO T-Deck Plus, M5Stack CoreS3 SE; M5StickC Plus2, M5StickC Plus 1.1, M5StickC Plus SE, M5Stack CoreInk, M5Stack Core2 v1.3 |
| Link to the computer or phone | A Bluetooth LE keyboard: it sends keystrokes and reads nothing |
| Encryption | AES-256-CBC + HMAC-SHA256, its key derived from your PIN or passphrase by PBKDF2-SHA256 |
| Capacity | 90 to 500 credentials and 30 to 50 two-factor (TOTP) codes, depending on the board |
| Server, account, app | None |
| Cost | Nothing to pay the project and no account to open; you buy the board from whoever sells it |
| License | GNU General Public License, version 3 or any later version (GPL-3.0-or-later). The source is private until the repository is opened, a step on the roadmap |
| Made by | José M. Requena Plens (without the accent: Jose M. Requena Plens), on his own; <https://github.com/jmrplens> |
| Name | From the Ancient Greek κλειδός (kleidós), "of the key", the genitive of κλείς (kleís), key. While the project was meant only for the M5Stick boards, it was going to be called StickPass; it became Kleidos when it grew to other boards |
| Pronunciation | KLAY-dos (/ˈklei̯.dos/): two syllables, the stress on the first. It is the project's own pronunciation; the Ancient Greek genitive, kleidós, stresses the last syllable |
| History | First attempts in 2022, set aside and taken up again more than once; development started in April 2026; first working versions in June and July 2026; still in development, because the firmware has to be solid before it is offered to the community. The whole story: [`about/en/name-and-history.md`](../../about/en/name-and-history.md) |
| Site | <https://kleidos.dev> |
| Contact | mail@kleidos.dev |

## How to write the name

"Kleidos": a capital K and nothing else in capitals. Not "KLEIDOS", not "KleidOS", not "Kleidos OS". The address kleidos.dev is lower case. Kleidos is not a registered trademark, so no trademark sign goes beside it.

## Do not write

- That it is released: there is nothing to download or install yet (as of 2026-11-17).
- That it is a product you buy: it is firmware for a board you buy from whoever sells it. The project sells nothing.
- That it is a FIDO2 or U2F security key: it is a password manager, and it does no FIDO2, U2F, PIV or OpenPGP.
- That M5Stack or LILYGO make, sponsor or endorse it. Kleidos is an independent project, not affiliated with M5Stack or LILYGO.
- That it logs or reads what you type: it sends keystrokes and reads nothing.
- That it has been audited: nobody independent has audited it.

What it protects against, and what it does not, threat by threat: <https://kleidos.dev/security/>. Where the project stands: <https://kleidos.dev/roadmap/>.

## Images

The nine boards at one scale, each on its unlock screen, under the logo: [`../images/kleidos-boards-16x9-1920.png`](../images/kleidos-boards-16x9-1920.png) (16:9) and [`../images/kleidos-boards-4x5.png`](../images/kleidos-boards-4x5.png) (4:5), each also on white. A photograph of four boards running an earlier build of Kleidos (the M5Stack Cardputer ADV, the M5Stack Core2 v1.3, the M5StickS3 and the LILYGO T-Deck Plus): [`../photos/kleidos-photo-four-boards-1920.jpg`](../photos/kleidos-photo-four-boards-1920.jpg), also at 1200 px and at full resolution; credit "Photo: José M. Requena Plens". The logo and every other image: [`../README.md`](../README.md).

## Links

- <https://kleidos.dev>
- <https://github.com/kleidos-dev>
- <https://www.youtube.com/@kleidos>
- <https://makertube.net/c/kleidos>
