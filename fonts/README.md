# Typography

Three families, all under the SIL Open Font License 1.1, kept here as their upstream files, unmodified, each beside its own `OFL.txt`. Pins: [`VERSIONS.md`](VERSIONS.md).

## Which family sets what

| Family | Where | What it sets |
| --- | --- | --- |
| Mona Sans (variable: width, optical size, weight) | the brand and the web | the name's lettering; headlines at width 112.5, weight 650, optical size 72; section heads at 106, 620, 72; text at width 100, weight 400 to 600, optical size 20 |
| Mona Sans Mono (variable: weight) | the brand and the web | labels in capitals and figures, weight 400 to 500, tracked out by 0.12 em |
| Inter (Regular, Medium, Bold) | the device's screens | labels, titles, rows, hints |
| JetBrains Mono (Regular, Medium) | the device's screens | PIN digits, one-time codes, counters, credential data |

The web's nine type roles (hero, chapter, section, figure, title, lede, body, small, label), each with its size, line height, tracking, face, weight, width and optical size, are tokens: [`../tokens/tokens.json`](../tokens/tokens.json), `web.type.roles`. The device's sizes by screen density are `device.density` there.

## The name's lettering

"Kleidos" is set once, in Mona Sans at width 112.5, weight 650 and optical size 72, tracked in by 0.02 em, with kerning on, and kept as one path (`tools/kleidos_brand/lettering.py`). A logo file never holds live text, and the name is never retyped in another weight, width or face as part of the logo.

## What the license asks, and what this repository does about it

- The fonts stay under the OFL and travel with their license: each family's folder holds its `OFL.txt`, and [`../NOTICE.md`](../NOTICE.md) carries the copyright lines.
- Mona Sans reserves the name "Mona". A subset, an instance or a converted copy (a WOFF2, for instance) is a Modified Version and may not carry that name. So this repository holds only the upstream files: `tools/check.py` refuses any font file that is not pinned in `VERSIONS.md` and any font inside an SVG. The builder instances the variable fonts in memory to draw outlines and never writes a font.
- The site publishes its own renamed subsets, Kleidos Sans and Kleidos Mono, cut from these files in the firmware repository. Those subsets stay the site's; they are not kept here.
- The OFL does not reach what is made with a font ("The requirement for fonts to remain under this license does not apply to any document created using the fonts or their derivatives"). The lettering's outline and every word in a generated image are such documents: they are the project's own work, under GPL-3.0-or-later.
