<!--
SPDX-FileCopyrightText: 2026 José M. Requena Plens
SPDX-License-Identifier: MIT
-->

# Kleidos

Kleidos is free firmware that turns one of the small ESP32 boards it runs on, from M5Stack and LILYGO, into a hardware password manager. Your passwords stay encrypted on the board, which types the one you pick into your computer or phone over Bluetooth, and only after you have unlocked it on the board itself.

## How it is used

You unlock the board on the board itself, with a PIN or a passphrase. You pick an entry on its screen. The board types it into your computer or phone as a Bluetooth LE keyboard: it sends keystrokes and reads nothing. Before a new computer or phone receives a single keystroke, you confirm a six-digit number on the board's own screen.

## What it does without

There is no server and no account: no copy of your passwords is kept anywhere but on the board, unless you export a backup yourself. There is no app to install and no cloud to trust. There is nothing to pay the project: you buy the board from whoever sells it.

## The boards

A board, here, is a pocket-size ESP32 device that M5Stack or LILYGO sells finished, in its own case and with its own screen. Kleidos runs on nine of them.

- On the ESP32-S3: M5StickS3, M5Stack Cardputer ADV, LILYGO T-Deck Plus, M5Stack CoreS3 SE.
- On the classic ESP32: M5StickC Plus2, M5StickC Plus 1.1, M5StickC Plus SE, M5Stack CoreInk, M5Stack Core2 v1.3.

Kleidos is an independent project, not affiliated with M5Stack or LILYGO. Product names are their owners' trademarks.

## Where it stands

In development. Not released: there is nothing to download yet (as of 2026-11-17). Nobody independent has audited it. The roadmap says where the project stands: <https://kleidos.dev/roadmap/>. What it protects against, and what it does not, threat by threat: <https://kleidos.dev/security/>.

## Who makes it

José M. Requena Plens builds Kleidos on his own (<https://github.com/jmrplens>). The name comes from the Greek for "key"; its story, and the road from the first attempts in 2022 to today, are in [`name-and-history.md`](name-and-history.md).

## License

GNU General Public License, version 3 or any later version (GPL-3.0-or-later). The source is private until the repository is opened, a step on the roadmap. Kleidos is not a registered trademark; how the name and the mark may be used is in [`TRADEMARKS.md`](../../TRADEMARKS.md).

## Contact and links

- mail@kleidos.dev (OpenPGP fingerprint `94765B19FB505392C68AED600535C714FCEF3BC3`)
- <https://kleidos.dev>
- <https://github.com/kleidos-dev>
- <https://www.youtube.com/@kleidos>
- <https://makertube.net/c/kleidos>
