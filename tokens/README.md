# Tokens

[`tokens.json`](tokens.json) is the one file that holds the brand's values: the mark's two colors and its construction, the site's palette and type roles, the device's palette and sizes, and the colors an image is painted with. It is DTCG-shaped (a token is an object with `$value` and `$type`); a color's value is a CSS color string, a hex where it is opaque; and a token with `$compose` is one color at an alpha over another, computed and never stored.

## Who owns what

| Group | Owner | What it is |
| --- | --- | --- |
| `brand` | here | `signal`, `select` and the mark's numbers |
| `social` | here | what an opaque image is painted with: aliases of the groups below, and `rule`, computed |
| `web` | the firmware repository, mirrored here | the site's token blocks (`site/assets/style.css`), under the names that sheet declares |
| `device` | the firmware repository, mirrored here | the device's palette (`src/ui/core/theme.h`) and sizes, under the names of the design-system skill's `tokens.json` |

The firmware repository is the source of `web` and `device` for now, and this file follows it. [`mirror.json`](mirror.json) records the digests of the files the mirror was last checked against.

```sh
.venv/bin/python tools/sync_from_kleidos.py --check <checkout of the firmware repository>
```

prints every difference: the `device` colors against the skill's file and `theme.h`, the `web` groups and type roles against the sheet's three token blocks, the mark against the firmware's copy, the font pins, the words the press images and the texts copy from the site, and whether any mirrored file changed since `mirror.json` was written. A difference is fixed here by hand, then `--record` writes the new digests. The path is an argument and is stored nowhere. CI cannot run it, because it cannot read the firmware repository: run it before a commit that touches the tokens, the mark, the fonts or the copied words.

## What is generated

`tools/build.py` writes [`dist/`](dist/) from `tokens.json`:

- [`dist/tokens.flat.json`](dist/tokens.flat.json): every opaque color by its dotted name, as lower-case hex. This is what the builders here and in `social` read.
- [`dist/kleidos-tokens.css`](dist/kleidos-tokens.css): custom properties under the site's own names (`--signal`, `--ink-2`, `--t-hero`), dark on `:root`, the light theme under its two selectors, the device's palette under `[data-kl="device"]`.

No C header is generated: the firmware keeps its own `theme.h`, and the sync script compares the values.
